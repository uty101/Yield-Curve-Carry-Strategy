"""US: FRED constant-maturity Treasury par yields (step 1.1).

Series ``DGS3MO DGS6MO DGS1 DGS2 DGS3 DGS5 DGS7 DGS10 DGS20 DGS30``, daily,
percent, ``"."`` for a missing day. ``curve_type = par`` (semi-annual
coupon, ``config.coupon_frequency.US = 2``). DGS3MO and DGS6MO (0.25 and
0.5 years, from 1981-09) are the observed short end. DGS20 has no data
1987-01..1993-09 and DGS30 none 2002-03..2006-01; both are recorded in
``data/checks/coverage.csv`` and never filled.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

SOURCE = "fred"
COUNTRY = "US"
CURVE_TYPE = "par"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES: dict[str, float] = {
    "DGS3MO": 0.25,
    "DGS6MO": 0.5,
    "DGS1": 1.0,
    "DGS2": 2.0,
    "DGS3": 3.0,
    "DGS5": 5.0,
    "DGS7": 7.0,
    "DGS10": 10.0,
    "DGS20": 20.0,
    "DGS30": 30.0,
}


def fetch(cfg: dict) -> list[Path]:
    """Download every series to ``data/raw/fred/<series>_<date>.csv`` and record it."""
    out = []
    for series in SERIES:
        url = URL.format(series=series)
        content = manifest.fetch_bytes(url)
        path = manifest.raw_path(SOURCE, series, "csv", base.today())
        manifest.write_raw(content, path, url, SOURCE)
        out.append(path)
    return out


def parse(paths: list[Path]) -> pd.DataFrame:
    """Raw FRED csvs -> daily long frame ``obs_date, tenor_years, yield`` (decimal)."""
    frames = []
    for p in paths:
        df = pd.read_csv(p, na_values=["."])
        series = [c for c in df.columns if c != "observation_date"]
        assert len(series) == 1, f"{p}: expected one value column, got {series}"
        s = series[0]
        if s not in SERIES:
            raise ValueError(f"{p}: unknown FRED series {s!r}")
        frames.append(
            pd.DataFrame(
                {
                    "obs_date": pd.to_datetime(df["observation_date"]),
                    "tenor_years": SERIES[s],
                    "yield": df[s].astype("float64") / 100.0,  # percent -> decimal, once
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, s) for s in SERIES]


def load(cfg: dict) -> pd.DataFrame:
    daily = parse(latest_paths())
    monthly = base.month_end_sample(daily)
    df = base.validate_curve(base.to_curveframe(monthly, COUNTRY, CURVE_TYPE, SOURCE))
    base.write_interim(df, COUNTRY)
    checks.write_coverage(df, "observed")
    return df
