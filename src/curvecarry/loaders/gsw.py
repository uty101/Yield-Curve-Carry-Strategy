"""US check curve: the Fed's Gürkaynak–Sack–Wright zero-coupon yields (Session 2, amendment 3).

``feds200628.csv`` from federalreserve.gov, daily from 1961-06-14. The file's
own header states the convention: *"Zero-coupon yield, Continuously
Compounded, SVENYXX"* (and the par yields SVENPYXX are coupon-equivalent).
Columns ``SVENY01 .. SVENY30``, percent, ``NA`` where the fit does not reach
the tenor (30y from 1985-11): ``/ 100`` then ``exp(z) - 1`` to the package's
annual compounding, once, in ``parse``. Month-end sampled like the curves.
``parse_par`` reads the par yields ``SVENPY01 .. SVENPY30`` (Session 2 fix
4): coupon-equivalent, i.e. the same semiannual bond-equivalent basis as
the Treasury CMT curve, so ``/ 100`` and nothing else. ``load`` writes
``gsw_us.parquet`` (zero) and ``gsw_us_par.parquet`` (par). Used only for
the checks ``us_zero_vs_gsw.csv``, ``us_par_vs_gsw.csv`` and
``bootstrap_on_gsw.csv`` — the bootstrapped US zero curve against an
independent smoothed fit. Never placed in the panel.

The file is a staff research product, not an official release; the Fed's
note says it is subject to revision. Raw copies are dated in the manifest.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import manifest
from curvecarry.loaders import base

SOURCE = "gsw"
NAME = "feds200628"
URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
CONVENTION_LINE = "Zero-coupon yield,Continuously Compounded,SVENYXX"
PAR_CONVENTION_LINE = "Par yield,Coupon-Equivalent,SVENPYXX"


def fetch(cfg: dict) -> list[Path]:
    content = manifest.fetch_bytes(URL, timeout=600)
    path = manifest.raw_path(SOURCE, NAME, "csv", base.today())
    manifest.write_raw(content, path, URL, SOURCE)
    return [path]


def continuous_to_annual(r: pd.Series | np.ndarray | float):
    return np.exp(r) - 1.0


def _parse(paths: list[Path], prefix: str, convention: str, convert) -> pd.DataFrame:
    frames = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        if not any(ln.strip() == convention for ln in lines[:30]):
            raise ValueError(f"{p}: header does not state {convention!r}")
        start = next(i for i, ln in enumerate(lines) if ln.startswith("Date,"))
        df = pd.read_csv(io.StringIO("\n".join(lines[start:])), na_values=["NA"])
        cols = [c for c in df.columns if c.startswith(prefix) and c[len(prefix) :].isdigit()]
        if len(cols) != 30:
            raise ValueError(f"{p}: expected 30 {prefix} columns, found {len(cols)}")
        long = df.melt(id_vars="Date", value_vars=cols, var_name="col", value_name="pct")
        frames.append(
            pd.DataFrame(
                {
                    "obs_date": pd.to_datetime(long["Date"]),
                    "tenor_years": long["col"].str[len(prefix) :].astype(int).astype("float64"),
                    "yield": convert(long["pct"] / 100.0),  # once
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def parse(paths: list[Path]) -> pd.DataFrame:
    """Raw csv -> daily long frame ``obs_date, tenor_years, yield`` (zero, decimal, annual)."""
    return _parse(paths, "SVENY", CONVENTION_LINE, continuous_to_annual)


def parse_par(paths: list[Path]) -> pd.DataFrame:
    """Raw csv -> daily long frame of the par yields ``SVENPYnn`` (decimal, coupon-equivalent:
    the CMT basis; no compounding conversion)."""
    return _parse(paths, "SVENPY", PAR_CONVENTION_LINE, lambda x: x)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, NAME)]


def load(cfg: dict) -> pd.DataFrame:
    """Month-end GSW zero yields -> ``data/interim/gsw_us.parquet`` (date, tenor_years, yield)."""
    base.INTERIM.mkdir(parents=True, exist_ok=True)
    monthly = base.month_end_sample(parse(latest_paths()))
    assert monthly["yield"].between(base.YIELD_LO, base.YIELD_HI).all()
    assert monthly["yield"].max() > base.YIELD_MIN_MAX
    monthly.to_parquet(base.INTERIM / "gsw_us.parquet", index=False)
    par = base.month_end_sample(parse_par(latest_paths()))
    assert par["yield"].between(base.YIELD_LO, base.YIELD_HI).all()
    assert par["yield"].max() > base.YIELD_MIN_MAX
    par.to_parquet(base.INTERIM / "gsw_us_par.parquet", index=False)
    return monthly
