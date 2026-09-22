"""Step 1.8: harmonise on synthetic CurveFrames. No files, no network."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import checks, config, harmonise
from curvecarry.loaders import base

STANDARD = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]


@pytest.fixture(scope="module")
def cfg() -> dict:
    return config.load()


def _frame(country: str, tenors: list[float], dates: list[str], ctype: str, source: str):
    rows = [(d, country, t, 0.01 + 0.001 * t, ctype, source) for d in dates for t in tenors]
    df = pd.DataFrame(rows, columns=base.CURVE_COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return base.validate_curve(df)


def test_standard_tenors_from_jp_like_input(cfg: dict) -> None:
    tenors = [float(t) for t in range(1, 11)] + [15.0, 20.0, 25.0, 30.0]
    out = harmonise.to_standard(_frame("JP", tenors, ["2020-01-31"], "par", "mof"), cfg)
    std = out[out["standard"]]
    assert sorted(std["tenor_years"]) == STANDARD
    assert not out["interpolated"].any()
    assert list(out.columns) == harmonise.PANEL_COLUMNS


def test_standard_tenors_from_boc_like_input(cfg: dict) -> None:
    full = [0.25 * k for k in range(1, 121)]
    out = harmonise.to_standard(_frame("CA", full, ["2020-01-31"], "zero", "boc"), cfg)
    assert sorted(out[out["standard"]]["tenor_years"]) == STANDARD
    assert not out["interpolated"].any() and len(out) == 120
    to25 = [0.25 * k for k in range(1, 101)]
    out = harmonise.to_standard(_frame("CA", to25, ["2020-01-31"], "zero", "boc"), cfg)
    assert 30.0 not in set(out["tenor_years"])  # beyond the longest observed: absent
    assert sorted(out[out["standard"]]["tenor_years"]) == STANDARD[:-1]


def test_non_standard_tenors_kept(cfg: dict) -> None:
    us = _frame("US", [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30], ["2020-01-31"], "par", "fred")
    out = harmonise.to_standard(us, cfg)
    assert {0.25, 0.5} <= set(out["tenor_years"])
    assert not out[out["tenor_years"].isin([0.25, 0.5])]["standard"].any()
    jp = _frame("JP", [1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40], ["2020-01-31"], "par", "mof")
    out = harmonise.to_standard(jp, cfg)
    assert {15.0, 25.0, 40.0} <= set(out[~out["standard"]]["tenor_years"])


def test_interpolated_rows_are_flagged_and_inside_range_only(cfg: dict) -> None:
    # US-like 1987: no 20y observed; 10y and 30y are -> 20y interpolated between them
    df = _frame("US", [1, 2, 3, 5, 7, 10, 30], ["1987-06-30"], "par", "fred")
    out = harmonise.to_standard(df, cfg)
    row = out[out["tenor_years"] == 20.0].iloc[0]
    assert row["interpolated"] and row["standard"]
    y10 = df[df["tenor_years"] == 10.0]["yield"].item()
    y30 = df[df["tenor_years"] == 30.0]["yield"].item()
    assert row["yield"] == pytest.approx(y10 + (y30 - y10) * (20 - 10) / (30 - 10), abs=1e-15)
    assert out["interpolated"].sum() == 1
    # early-1960s US: 1y, 3y, 5y, 10y, 20y observed -> 2y and 7y interpolated, 30y absent
    df = _frame("US", [1, 3, 5, 10, 20], ["1962-01-31"], "par", "fred")
    out = harmonise.to_standard(df, cfg)
    assert sorted(out[out["interpolated"]]["tenor_years"]) == [2.0, 7.0]
    assert 30.0 not in set(out["tenor_years"])


def test_no_funding_row_on_curve(cfg: dict) -> None:
    df = _frame("US", [0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30], ["2020-01-31"], "par", "fred")
    out = harmonise.to_standard(df, cfg)
    assert not out["source"].isin(["bis", "fred_immediate"]).any()
    allowed = set(df["tenor_years"]) | set(STANDARD)
    assert set(out["tenor_years"]) <= allowed
    assert (out["tenor_years"] > 0).all()


def test_one_curve_type_per_country_month(cfg: dict) -> None:
    a = _frame("US", [1, 2, 5, 10], ["2020-01-31"], "par", "fred")
    b = _frame("US", [3.0], ["2020-01-31"], "zero", "x")
    with pytest.raises(ValueError, match="mixed"):
        harmonise.to_standard(pd.concat([a, b], ignore_index=True), cfg)
    ok = harmonise.to_standard(a, cfg)
    assert ok.groupby(["country", "date"])["curve_type"].nunique().eq(1).all()


def test_no_forward_fill(cfg: dict) -> None:
    df = _frame("DE", [1, 2, 5, 10, 30], ["2020-01-31", "2020-03-31"], "zero", "bundesbank")
    out = harmonise.to_standard(df, cfg)
    assert pd.Timestamp("2020-02-29") not in set(out["date"])
    assert set(out["date"]) == {pd.Timestamp("2020-01-31"), pd.Timestamp("2020-03-31")}


def test_panel_stops_at_strategy_end(cfg: dict, tmp_path: Path, monkeypatch) -> None:
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    dates = [end - pd.offsets.MonthEnd(1), end, end + pd.offsets.MonthEnd(1)]
    strs = [d.strftime("%Y-%m-%d") for d in dates]
    df = _frame("US", [1, 2, 5, 10], strs, "par", "fred")
    cut = harmonise.cut_to_strategy_end(df, cfg)
    assert cut["date"].max() == end and len(cut) == 8
    # through build(): interim is read, processed is cut, interim untouched
    interim, processed = tmp_path / "interim", tmp_path / "processed"
    interim.mkdir()
    for c in cfg["countries"]:
        _frame(c, STANDARD, strs, "zero", "s").to_parquet(
            interim / f"curves_{c.lower()}.parquet", index=False
        )
    monkeypatch.setattr(checks, "COVERAGE", tmp_path / "coverage.csv")
    panel = harmonise.build(cfg, interim=interim, processed=processed)
    assert panel["date"].max() == end
    assert pd.read_parquet(interim / "curves_us.parquet")["date"].max() > end
    assert pd.read_parquet(processed / "curves.parquet")["date"].max() == end
    h = pd.read_csv(tmp_path / "coverage.csv", keep_default_na=False)
    assert (h["last_date"] == end.date().isoformat()).all() and len(h) == 48


def test_interp_import_is_the_only_interpolator() -> None:
    src = Path("src/curvecarry/harmonise.py").read_text(encoding="utf-8")
    assert "np.interp" not in src and "interpolate_yield" in src
    assert np is not None
