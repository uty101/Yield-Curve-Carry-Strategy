"""Step 1.1: US loader on tests/fixtures/fred/DGS*.csv (header + 50 rows each). No network."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import checks
from curvecarry.loaders import base, us

FIX = Path("tests/fixtures/fred")
PATHS = [FIX / f"{s}.csv" for s in us.SERIES]


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    monthly = base.month_end_sample(us.parse(PATHS))
    return base.validate_curve(base.to_curveframe(monthly, "US", "par", "fred"))


def test_units_us(frame: pd.DataFrame) -> None:
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    # 1962-01-02 DGS10 is 4.06 percent in the raw file -> 0.0406
    raw = pd.read_csv(FIX / "DGS10.csv").iloc[0]
    assert raw["observation_date"] == "1962-01-02" and raw["DGS10"] == 4.06
    daily = us.parse([FIX / "DGS10.csv"])
    assert daily.loc[daily["obs_date"] == "1962-01-02", "yield"].item() == pytest.approx(0.0406)


def test_tenors_us(frame: pd.DataFrame) -> None:
    assert set(frame["tenor_years"]) == {0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30}
    assert frame["curve_type"].eq("par").all() and frame["country"].eq("US").all()


def test_dates_us(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_us(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_month_end_is_last_observation_not_average() -> None:
    daily = pd.DataFrame(
        {
            "obs_date": pd.to_datetime(["2020-03-02", "2020-03-16", "2020-03-31"]),
            "tenor_years": 10.0,
            "yield": [0.01, 0.02, 0.03],
        }
    )
    out = base.month_end_sample(daily)
    assert len(out) == 1
    assert out["date"].item() == pd.Timestamp("2020-03-31")
    assert out["yield"].item() == 0.03  # last, not the 0.02 average
    # a missing last day: the last non-null print is taken, per tenor
    daily.loc[2, "yield"] = np.nan
    assert base.month_end_sample(daily)["yield"].item() == 0.02


def test_gap_is_recorded_not_filled(tmp_path: Path) -> None:
    months = pd.date_range("1985-01-31", "1995-12-31", freq="ME")
    keep = [
        m for m in months if not (pd.Timestamp("1987-01-01") <= m <= pd.Timestamp("1988-12-31"))
    ]
    df = base.to_curveframe(
        pd.DataFrame({"date": keep, "tenor_years": 20.0, "yield": 0.05}), "US", "par", "fred"
    )
    df = base.validate_curve(df)
    cov = checks.write_coverage(df, "observed", path=tmp_path / "coverage.csv")
    row = cov.iloc[0]
    assert row["months_missing"] == 24 and row["gaps"] == "1987-01..1988-12"
    assert row["months_present"] == len(keep)
    assert not df["date"].between("1987-01-01", "1988-12-31").any()


def test_parse_rejects_unknown_series(tmp_path: Path) -> None:
    p = tmp_path / "DGS99.csv"
    p.write_text("observation_date,DGS99\n2020-01-02,1.0\n")
    with pytest.raises(ValueError, match="DGS99"):
        us.parse([p])
