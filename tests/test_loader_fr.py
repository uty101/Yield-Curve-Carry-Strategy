"""Step 1.6: France loader on tests/fixtures/bdf/tec*.csv (header + 50 rows each). No key."""

from pathlib import Path

import pandas as pd
import pytest

from curvecarry import manifest
from curvecarry.loaders import base, fr

FIX = Path("tests/fixtures/bdf")
PATHS = [FIX / f"tec{n}.csv" for n in fr.TENORS]


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    monthly = base.month_end_sample(fr.parse(PATHS))
    return base.validate_curve(base.to_curveframe(monthly, "FR", "par", "bdf"))


def test_units_fr(frame: pd.DataFrame) -> None:
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    raw = pd.read_csv(FIX / "tec10.csv", sep=";", dtype=str).dropna(subset=["obs_value"]).iloc[0]
    daily = fr.parse_file(FIX / "tec10.csv")
    got = daily[daily["obs_date"] == pd.Timestamp(raw["time_period"])]["yield"].item()
    assert got == pytest.approx(float(raw["obs_value"]) / 100.0)


def test_tenors_fr(frame: pd.DataFrame) -> None:
    assert set(frame["tenor_years"]) == {1, 2, 3, 5, 7, 10, 15, 20, 25, 30}
    assert frame["curve_type"].eq("par").all()


def test_dates_fr(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_fr(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_fetch_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(fr.ENV_KEY, raising=False)
    called = []
    monkeypatch.setattr(manifest, "fetch_bytes", lambda *a, **k: called.append(1) or b"x")
    with pytest.raises(RuntimeError, match=fr.ENV_KEY):
        fr.fetch({})
    assert called == []  # no request was made


def test_empty_export_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(fr.ENV_KEY, "not-a-real-key")
    header_only = (FIX / "tec10.csv").read_bytes().splitlines(keepends=True)[0]
    monkeypatch.setattr(manifest, "fetch_bytes", lambda *a, **k: header_only)
    written = []
    monkeypatch.setattr(manifest, "write_raw", lambda *a, **k: written.append(a))
    with pytest.raises(RuntimeError, match="empty export"):
        fr.fetch({})
    assert written == []


def test_key_never_in_logged_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(fr.ENV_KEY, "SECRET-KEY-VALUE")
    seen: dict = {}

    def fake_fetch(url, *, params=None, headers=None, timeout=0):
        seen["headers"] = headers
        return (FIX / "tec10.csv").read_bytes()

    monkeypatch.setattr(manifest, "fetch_bytes", fake_fetch)
    monkeypatch.setattr(fr, "MIN_DATA_ROWS", 10)
    logged = []
    monkeypatch.setattr(manifest, "write_raw", lambda c, p, url, s: logged.append(url))
    fr.fetch({})
    assert seen["headers"]["Authorization"].startswith("Apikey ")
    assert all("SECRET" not in u for u in logged) and len(logged) == len(fr.TENORS)


def test_missing_status_rows_dropped() -> None:
    raw = pd.read_csv(FIX / "tec10.csv", sep=";", dtype=str)
    daily = fr.parse_file(FIX / "tec10.csv")
    assert len(daily) == raw["obs_value"].notna().sum()
    assert daily["yield"].notna().all()
