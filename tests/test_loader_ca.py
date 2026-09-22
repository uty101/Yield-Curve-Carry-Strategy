"""Step 1.5: Canada loader on tests/fixtures/boc/zero_curve.csv (header + 50 rows). No network."""

import math
from pathlib import Path

import pandas as pd
import pytest

from curvecarry.loaders import base, ca

FIX = Path("tests/fixtures/boc/zero_curve.csv")


@pytest.fixture(scope="module")
def daily() -> pd.DataFrame:
    return ca.parse([FIX])


@pytest.fixture(scope="module")
def frame(daily: pd.DataFrame) -> pd.DataFrame:
    monthly = base.month_end_sample(daily)
    return base.validate_curve(base.to_curveframe(monthly, "CA", "zero", "boc"))


def test_units_ca(frame: pd.DataFrame) -> None:
    """The decisive one: the file is already decimal; a division by 100 would fail max > 0.001."""
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    assert frame["yield"].max() > 0.05  # 1986: Canadian zero rates were around 9-10%


def test_tenors_ca(daily: pd.DataFrame, frame: pd.DataFrame) -> None:
    # the header carries 120 tenors, 0.25 .. 30 in 0.25 steps
    assert sorted(set(daily["tenor_years"])) == [round(0.25 * k, 2) for k in range(1, 121)]
    # in the fixture (1986) the curve is observed to 25 years; every observed tenor is on the grid
    observed = set(frame["tenor_years"])
    assert observed <= {round(0.25 * k, 2) for k in range(1, 121)}
    assert {0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 25} <= observed
    assert frame["curve_type"].eq("zero").all() and frame["country"].eq("CA").all()


def test_dates_ca(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_ca(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_na_is_missing(daily: pd.DataFrame) -> None:
    # 1986-01-01 is a row of `na`: it must contribute no yield, not a zero
    d = daily[daily["obs_date"] == "1986-01-01"]
    assert len(d) == 120 and d["yield"].isna().all()
    assert not (daily["yield"] == 0.0).any()


def test_no_division_by_100(tmp_path: Path) -> None:
    """A cell 0.0226506 comes back as exp(0.0226506) - 1, never as 0.000226506."""
    header = "Date, " + ", ".join(f"ZC{int(round(25 * k)):04d}YR" for k in range(1, 121)) + ", "
    row = "2026-07-31, " + ", ".join(["0.0226506000"] * 120) + ", "
    p = tmp_path / "zero_curve_20260917.csv"
    p.write_text(header + "\n" + row + "\n", encoding="utf-8")
    out = ca.parse([p])
    assert out["yield"].tolist() == pytest.approx([math.exp(0.0226506) - 1] * 120, abs=1e-14)
    assert out["yield"].iloc[0] > 0.02  # not 0.000226506


def test_compounding_conversion_applied_once(tmp_path: Path) -> None:
    """Continuous 5% -> annual exp(0.05) - 1 = 5.127%, applied exactly once (issue #8)."""
    header = "Date, " + ", ".join(f"ZC{int(round(25 * k)):04d}YR" for k in range(1, 121)) + ", "
    row = "2020-01-31, " + ", ".join(["0.05"] * 120) + ", "
    p = tmp_path / "zero_curve_20260917.csv"
    p.write_text(header + "\n" + row + "\n", encoding="utf-8")
    out = ca.parse([p])
    assert len(out) == 120
    assert out["yield"].tolist() == pytest.approx([math.exp(0.05) - 1] * 120, abs=1e-14)
    assert out["yield"].iloc[0] != pytest.approx(0.05, abs=1e-6)  # not left as continuous
    assert out["yield"].iloc[0] != pytest.approx(math.exp(math.exp(0.05) - 1) - 1, abs=1e-6)


def test_column_to_tenor() -> None:
    assert ca.tenor_of("ZC025YR") == 0.25 and ca.tenor_of("ZC3000YR") == 30.0
    assert ca.tenor_of(" ZC1025YR") == 10.25
    with pytest.raises(ValueError):
        ca.tenor_of("Date")
