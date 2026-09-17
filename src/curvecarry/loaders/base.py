"""What every loader shares: the CurveFrame schema, month-end sampling, validation.

CurveFrame columns, in order: ``date`` (calendar month end), ``country``
(ISO2), ``tenor_years`` (float), ``yield`` (decimal, annually compounded),
``curve_type`` (``zero`` | ``par``), ``source`` (manifest source name).
Yields are decimals everywhere inside the package (global rule 2): the
division by 100 happens in each loader's ``parse`` and nowhere else.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

CURVE_COLUMNS = ["date", "country", "tenor_years", "yield", "curve_type", "source"]
CURVE_TYPES = {"zero", "par"}
YIELD_LO, YIELD_HI, YIELD_MIN_MAX = -0.05, 0.5, 0.001
INTERIM = Path("data/interim")


def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def month_end(dates: pd.Series) -> pd.Series:
    """Stamp each date to its calendar month end at midnight."""
    d = pd.to_datetime(dates)
    return (d + pd.offsets.MonthEnd(0)).dt.normalize()


def month_end_sample(daily: pd.DataFrame) -> pd.DataFrame:
    """Per (calendar month, tenor), the last non-null observation in that month.

    Input columns ``obs_date, tenor_years, yield``; output ``date`` (month
    end), ``tenor_years``, ``yield``. Per tenor, not per day, so a tenor that
    stops mid-month is sampled at its own last print. Never an average.
    """
    d = daily.dropna(subset=["yield"]).copy()
    d["obs_date"] = pd.to_datetime(d["obs_date"])
    d = d.sort_values(["tenor_years", "obs_date"])
    d["date"] = month_end(d["obs_date"])
    last = d.groupby(["date", "tenor_years"], as_index=False).last()
    return last[["date", "tenor_years", "yield"]].sort_values(["date", "tenor_years"])


def to_curveframe(
    monthly: pd.DataFrame, country: str, curve_type: str, source: str
) -> pd.DataFrame:
    out = monthly[["date", "tenor_years", "yield"]].copy()
    out["date"] = pd.to_datetime(out["date"])
    out["country"] = country
    out["tenor_years"] = out["tenor_years"].astype("float64")
    out["yield"] = out["yield"].astype("float64")
    out["curve_type"] = curve_type
    out["source"] = source
    return out[CURVE_COLUMNS]


def validate_curve(df: pd.DataFrame) -> pd.DataFrame:
    """Assert the CurveFrame contract and return the frame sorted."""
    assert list(df.columns) == CURVE_COLUMNS, f"columns {list(df.columns)} != {CURVE_COLUMNS}"
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), "date must be datetime64"
    assert df["date"].equals(month_end(df["date"])), "every date must be a calendar month end"
    assert df["yield"].notna().all(), "NaN yield rows must be dropped before validation"
    y = df["yield"]
    assert y.between(YIELD_LO, YIELD_HI).all(), (
        f"yield outside [{YIELD_LO}, {YIELD_HI}]: max {y.max()} min {y.min()}: percent?"
    )
    assert y.max() > YIELD_MIN_MAX, f"max yield {y.max()} <= {YIELD_MIN_MAX}: divided by 100 twice?"
    assert set(df["curve_type"].unique()) <= CURVE_TYPES, "curve_type must be zero or par"
    key = ["date", "country", "tenor_years"]
    assert not df.duplicated(key).any(), "duplicate (date, country, tenor_years)"
    out = df.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)
    for _, g in out.groupby(["country", "tenor_years"]):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique, "dates not monotone"
    return out


def write_interim(df: pd.DataFrame, country: str, root: Path = INTERIM) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"curves_{country.lower()}.parquet"
    df.to_parquet(p, index=False)
    return p
