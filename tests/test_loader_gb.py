"""Step 1.2: UK loader on tests/fixtures/boe/*.xlsx (one trimmed file per archive file)."""

import datetime as dt
import math
import zipfile
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from curvecarry.loaders import base, gb

FIX = Path("tests/fixtures/boe")
PATHS = sorted(FIX.glob("*.xlsx"))
EARLY = [p for p in PATHS if "1970" in p.name][0]
LATE = [p for p in PATHS if "2016" in p.name][0]


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    monthly = gb.to_monthly(gb.parse(PATHS))
    return base.validate_curve(base.to_curveframe(monthly, "GB", "zero", "boe"))


def test_units_gb(frame: pd.DataFrame) -> None:
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    # 1970-01-31, 1y: 8.635354135184983 percent, continuous -> exp(0.08635354)-1
    y = frame[(frame["date"] == "1970-01-31") & (frame["tenor_years"] == 1.0)]["yield"].item()
    assert y == pytest.approx(math.exp(0.08635354135184983) - 1, abs=1e-12)


def test_tenors_gb(frame: pd.DataFrame) -> None:
    late = frame[frame["date"] >= "2016-01-01"]
    assert set(range(1, 31)) <= set(late["tenor_years"])
    early = frame[frame["date"] < "1980-01-01"]
    assert {1, 2, 3, 5, 7, 10} <= set(early["tenor_years"])
    assert frame["tenor_years"].min() == 0.5 and frame["tenor_years"].max() == 40.0
    assert frame["curve_type"].eq("zero").all()


def test_dates_gb(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_gb(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_all_archive_files_are_read(frame: pd.DataFrame, tmp_path: Path) -> None:
    years = set(frame["date"].dt.year)
    assert 1970 in years and 2016 in years and 2025 in years  # one fixture per archive file
    # the same three files inside a zip (the real raw layout) give the same frame
    z = tmp_path / "glcnominalmonthedata_20260917.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for p in PATHS:
            zf.write(p, p.name)
    via_zip = gb.to_monthly(gb.parse([z]))
    direct = gb.to_monthly(gb.parse(PATHS))
    pd.testing.assert_frame_equal(
        via_zip.sort_values(["date", "tenor_years"]).reset_index(drop=True),
        direct.sort_values(["date", "tenor_years"]).reset_index(drop=True),
    )


def test_compounding_conversion_applied_once(tmp_path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.active.title = "info"
    ws = wb.create_sheet("4. spot curve")
    ws.append([None, "UK nominal spot curve"])
    ws.append(["Maturity"])
    ws.append(["years:", 0.5, 1, 2])
    ws.append([dt.datetime(2020, 1, 31), 5.0, 5.0, 5.0])
    p = tmp_path / "x.xlsx"
    wb.save(p)
    out = gb.parse([p])
    assert len(out) == 3
    assert out["yield"].tolist() == pytest.approx([math.exp(0.05) - 1] * 3, abs=1e-14)
    assert out["yield"].iloc[0] != pytest.approx(0.05, abs=1e-6)  # not left as the raw decimal


def test_last_business_day_is_stamped_to_month_end() -> None:
    late = gb.parse([[p for p in PATHS if "2025" in p.name][0]])
    monthly = gb.to_monthly(late)
    assert monthly["date"].equals(base.month_end(monthly["date"]))
    assert pd.Timestamp("2026-08-31") in set(monthly["date"])  # raw row is dated 2026-08-28
