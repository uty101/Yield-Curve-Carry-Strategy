"""Canada: Bank of Canada zero-coupon yield curve (step 1.5).

One csv from the GET form ``https://www.bankofcanada.ca/stats/results/csv``
(``lookupPage=lookup_yield_curve.php, startRange=1986-01-01, searchRange=all``),
daily from 1986-01-02, columns ``Date, ZC025YR .. ZC3000YR`` — 120 tenors,
0.25 to 30 years in 0.25-year steps (``tenor = int(col[2:-2]) / 100``),
``na`` for a missing value, a trailing empty column. **Values are already
decimals** (the data page: "The data are expressed as decimals (e.g. 0.0500
= 5.00% yield)"): there is no division by 100 in this loader.

Compounding (issue #8, decided 2026-09-22): the BoC zero rates are
**continuously compounded** — Bolder, Johnson & Metzler (2004) define
z(t, T) as the continuously compounded yield (pp. 25–26), restated in the
data appendix of "Riding the yield curve: a spanning analysis" (RQFA, 2012),
and Bank of Canada Technical Report 84 (Bolder & Stréliski) derives the zero
curve continuously compounded (eq. 6 and 7). The package convention is
annual compounding, so ``z_annual = exp(z) - 1`` is applied here, once, in
``parse`` (``decisions/compounding.md``). ``curve_type = zero``.

The Valet benchmark group (``benchmark_<date>.csv``) is fetched as the
recorded fallback and is not loaded (issue #1 answer 5).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

SOURCE = "boc"
COUNTRY = "CA"
CURVE_TYPE = "zero"
NAME = "zero_curve"
URL = "https://www.bankofcanada.ca/stats/results/csv"
PARAMS = {
    "lookupPage": "lookup_yield_curve.php",
    "startRange": "1986-01-01",
    "searchRange": "all",
    "submit": "Submit",
}
BENCHMARK_NAME = "benchmark"
BENCHMARK_URL = "https://www.bankofcanada.ca/valet/observations/group/bond_yields_benchmark/csv"
N_TENORS = 120  # 0.25 .. 30.00 in 0.25 steps


def fetch(cfg: dict) -> list[Path]:
    """The zero curve (whole history, one GET) and the Valet benchmark fallback."""
    out = []
    content = manifest.fetch_bytes(URL, params=PARAMS, timeout=600)
    query = "&".join(f"{k}={v}" for k, v in PARAMS.items())
    path = manifest.raw_path(SOURCE, NAME, "csv", base.today())
    manifest.write_raw(content, path, f"{URL}?{query}", SOURCE)
    out.append(path)
    content = manifest.fetch_bytes(BENCHMARK_URL)
    path = manifest.raw_path(SOURCE, BENCHMARK_NAME, "csv", base.today())
    manifest.write_raw(content, path, BENCHMARK_URL, SOURCE)
    out.append(path)
    return out


def continuous_to_annual(r: pd.Series | np.ndarray | float):
    """Continuously compounded decimal rate -> annually compounded decimal rate."""
    return np.exp(r) - 1.0


def tenor_of(column: str) -> float:
    """``ZC025YR`` -> 0.25, ``ZC3000YR`` -> 30.0."""
    c = column.strip()
    if not (c.startswith("ZC") and c.endswith("YR")):
        raise ValueError(f"not a BoC zero-curve column: {column!r}")
    return int(c[2:-2]) / 100.0


def parse(paths: list[Path]) -> pd.DataFrame:
    """Raw csv(s) -> daily long frame ``obs_date, tenor_years, yield`` (decimal, annual)."""
    frames = []
    for p in paths:
        df = pd.read_csv(p, skipinitialspace=True, na_values=["na"], dtype=str)
        df.columns = [c.strip() for c in df.columns]
        if "Date" not in df.columns:
            raise ValueError(f"{p}: no Date column; columns {list(df.columns)[:5]}")
        # the trailing comma gives an unnamed empty column; only ZC<nnnn>YR columns are tenors
        cols = [c for c in df.columns if c.startswith("ZC") and c.endswith("YR")]
        if len(cols) != N_TENORS:
            raise ValueError(f"{p}: expected {N_TENORS} ZC columns, found {len(cols)}")
        long = df.melt(id_vars="Date", value_vars=cols, var_name="col", value_name="z")
        long["tenor_years"] = long["col"].map(tenor_of)
        z = pd.to_numeric(long["z"], errors="coerce")  # already decimal: no division
        frames.append(
            pd.DataFrame(
                {
                    "obs_date": pd.to_datetime(long["Date"]),
                    "tenor_years": long["tenor_years"].astype("float64"),
                    "yield": continuous_to_annual(z),  # continuous -> annual, once
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, NAME)]


def load(cfg: dict) -> pd.DataFrame:
    daily = parse(latest_paths())
    monthly = base.month_end_sample(daily)
    df = base.validate_curve(base.to_curveframe(monthly, COUNTRY, CURVE_TYPE, SOURCE))
    base.write_interim(df, COUNTRY)
    checks.write_coverage(df, "observed")
    return df
