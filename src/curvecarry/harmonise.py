"""Step 1.8: one panel, the 8 standard tenors marked.

``to_standard`` keeps every observed tenor of every country-month and adds
the standard tenors (``config.tenors``) that are not observed, by
``interpolate_yield`` where the tenor lies between observed tenors and not
at all beyond the longest or before the shortest observed (rule 13). Two
flags: ``interpolated`` (the row was added here) and ``standard``
(``tenor_years`` is in ``config.tenors``). No funding row is added to any
curve (amendment B). No forward fill: a country-month absent in the source
is absent here.

``build`` reads ``data/interim/curves_<cc>.parquet`` for every country in
``config.countries``, keeps months ``<= config.sample.strategy_end``
(Session 1 part B amendment: the partial current month stays in ``data/interim``
only), writes ``data/processed/curves.parquet`` and the coverage rows
``stage = harmonised`` for the standard tenors.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks
from curvecarry.interp import interpolate_yield
from curvecarry.loaders import base

PROCESSED = Path("data/processed")
PANEL_COLUMNS = [*base.CURVE_COLUMNS, "interpolated", "standard"]


def standard_tenors(cfg: dict) -> list[float]:
    return [float(t) for t in cfg["tenors"]]


def to_standard(curve_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """CurveFrame -> CurveFrame + ``interpolated`` + ``standard`` (see module docstring)."""
    std = standard_tenors(cfg)
    df = curve_df[base.CURVE_COLUMNS].copy()
    df["interpolated"] = False
    added = []
    for (country, date), g in df.groupby(["country", "date"], sort=False):
        types = g["curve_type"].unique()
        if len(types) != 1:
            raise ValueError(f"{country} {date.date()}: mixed curve types {list(types)}")
        t = g["tenor_years"].to_numpy(dtype="float64")
        y = g["yield"].to_numpy(dtype="float64")
        have = set(np.round(t, 6))
        missing = [s for s in std if round(s, 6) not in have]
        if not missing or t.size < 2:
            continue
        lo, hi = t.min(), t.max()
        inside = [s for s in missing if lo < s < hi]  # never beyond the observed range
        if not inside:
            continue
        vals = interpolate_yield(t, y, np.asarray(inside))
        for s, v in zip(inside, vals, strict=True):
            added.append((date, country, s, float(v), types[0], g["source"].iloc[0], True))
    if added:
        extra = pd.DataFrame(added, columns=[*base.CURVE_COLUMNS, "interpolated"])
        df = pd.concat([df, extra], ignore_index=True)
    df["standard"] = df["tenor_years"].round(6).isin([round(s, 6) for s in std])
    df["interpolated"] = df["interpolated"].astype(bool)
    df["standard"] = df["standard"].astype(bool)
    df = df.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)
    assert not df.duplicated(["date", "country", "tenor_years"]).any()
    return df[PANEL_COLUMNS]


def cut_to_strategy_end(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Keep months <= config.sample.strategy_end (the partial current month is dropped)."""
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    return df[df["date"] <= end].reset_index(drop=True)


def build(cfg: dict, interim: Path = base.INTERIM, processed: Path = PROCESSED) -> pd.DataFrame:
    frames = []
    for country in cfg["countries"]:
        p = Path(interim) / f"curves_{country.lower()}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"{p}: run `uv run curvecarry build --step {country.lower()}`")
        frames.append(pd.read_parquet(p))
    panel = base.validate_curve(pd.concat(frames, ignore_index=True))
    panel = to_standard(cut_to_strategy_end(panel, cfg), cfg)
    base.validate_curve(panel[base.CURVE_COLUMNS])
    Path(processed).mkdir(parents=True, exist_ok=True)
    panel.to_parquet(Path(processed) / "curves.parquet", index=False)
    checks.write_coverage(
        panel[panel["standard"]][base.CURVE_COLUMNS], "harmonised", path=checks.COVERAGE
    )
    return panel
