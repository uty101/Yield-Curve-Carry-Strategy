"""US check curve: the Fed's Gürkaynak–Sack–Wright zero-coupon yields (Session 2, amendment 3).

``feds200628.csv`` from federalreserve.gov, daily from 1961-06-14. The file's
own header states the convention: *"Zero-coupon yield, Continuously
Compounded, SVENYXX"* (and the par yields SVENPYXX are coupon-equivalent).
Columns ``SVENY01 .. SVENY30``, percent, ``NA`` where the fit does not reach
the tenor (30y from 1985-11): ``/ 100`` then ``exp(z) - 1`` to the package's
annual compounding, once, in ``parse``. Month-end sampled like the curves.
Used only for ``data/checks/us_zero_vs_gsw.csv`` — the bootstrapped US zero
curve against an independent smoothed fit. Never placed in the panel.

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


def fetch(cfg: dict) -> list[Path]:
    content = manifest.fetch_bytes(URL, timeout=600)
    path = manifest.raw_path(SOURCE, NAME, "csv", base.today())
    manifest.write_raw(content, path, URL, SOURCE)
    return [path]


def continuous_to_annual(r: pd.Series | np.ndarray | float):
    return np.exp(r) - 1.0


def parse(paths: list[Path]) -> pd.DataFrame:
    """Raw csv -> daily long frame ``obs_date, tenor_years, yield`` (decimal, annual)."""
    frames = []
    for p in paths:
        text = Path(p).read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        if not any(ln.strip() == CONVENTION_LINE for ln in lines[:30]):
            raise ValueError(f"{p}: header does not state {CONVENTION_LINE!r}")
        start = next(i for i, ln in enumerate(lines) if ln.startswith("Date,"))
        df = pd.read_csv(io.StringIO("\n".join(lines[start:])), na_values=["NA"])
        cols = [c for c in df.columns if c.startswith("SVENY")]
        if len(cols) != 30:
            raise ValueError(f"{p}: expected 30 SVENY columns, found {len(cols)}")
        long = df.melt(id_vars="Date", value_vars=cols, var_name="col", value_name="pct")
        frames.append(
            pd.DataFrame(
                {
                    "obs_date": pd.to_datetime(long["Date"]),
                    "tenor_years": long["col"].str[5:].astype(int).astype("float64"),
                    "yield": continuous_to_annual(long["pct"] / 100.0),  # once
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, NAME)]


def load(cfg: dict) -> pd.DataFrame:
    """Month-end GSW zero yields -> ``data/interim/gsw_us.parquet`` (date, tenor_years, yield)."""
    monthly = base.month_end_sample(parse(latest_paths()))
    assert monthly["yield"].between(base.YIELD_LO, base.YIELD_HI).all()
    assert monthly["yield"].max() > base.YIELD_MIN_MAX
    base.INTERIM.mkdir(parents=True, exist_ok=True)
    monthly.to_parquet(base.INTERIM / "gsw_us.parquet", index=False)
    return monthly
