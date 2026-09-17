"""Step 1.4: Japan loader on tests/fixtures/mof/*.csv (2 header lines + 50 rows each)."""

from pathlib import Path

import pandas as pd
import pytest

from curvecarry.loaders import base, jp

FIX = Path("tests/fixtures/mof")
PATHS = [FIX / "jgbcme_all.csv", FIX / "jgbcme.csv"]


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    monthly = base.month_end_sample(jp.parse(PATHS))
    return base.validate_curve(base.to_curveframe(monthly, "JP", "par", "mof"))


def test_units_jp(frame: pd.DataFrame) -> None:
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    daily = jp.parse_file(FIX / "jgbcme_all.csv")
    first = daily[(daily["obs_date"] == "1974-09-24") & (daily["tenor_years"] == 1.0)]
    assert first["yield"].item() == pytest.approx(0.10327)  # raw 10.327 percent


def test_tenors_jp(frame: pd.DataFrame) -> None:
    cols = jp.parse_file(FIX / "jgbcme.csv")["tenor_years"].unique()
    assert set(cols) == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40}
    assert {1, 2, 3, 5, 7, 10, 20, 30} <= set(cols)
    assert frame["curve_type"].eq("par").all()


def test_dates_jp(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_jp(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_dash_is_missing_not_zero() -> None:
    daily = jp.parse_file(FIX / "jgbcme_all.csv")
    d = daily[daily["obs_date"] == "1974-09-24"]
    assert set(d["tenor_years"]) == {1, 2, 3, 4, 5, 6, 7, 8, 9}  # 10Y..40Y are "-"
    assert (daily["yield"] != 0).all()


def test_historical_wins_on_overlap(tmp_path: Path) -> None:
    hist = tmp_path / "jgbcme_all.csv"
    cur = tmp_path / "jgbcme.csv"
    hist.write_text("Interest Rate,,(Unit : %)\nDate,1Y,2Y\n2026/9/1,1.5,1.8\n", encoding="utf-8")
    cur.write_text(
        "Interest Rate (September 2026),,(Unit : %)\nDate,1Y,2Y\n"
        '2026/9/1,9.9,9.9\n2026/9/2,1.6,1.9\n"  note line",,\n',
        encoding="utf-8",
    )
    out = jp.parse([cur, hist])  # order given does not matter
    d1 = out[(out["obs_date"] == "2026-09-01") & (out["tenor_years"] == 1.0)]["yield"].item()
    assert d1 == pytest.approx(0.015)
    assert len(out) == 4  # 2 days x 2 tenors; the note line is dropped


def test_current_file_note_line_is_skipped() -> None:
    daily = jp.parse_file(FIX / "jgbcme.csv")
    assert daily["obs_date"].notna().all()
    assert daily["obs_date"].min() == pd.Timestamp("2026-09-01")
