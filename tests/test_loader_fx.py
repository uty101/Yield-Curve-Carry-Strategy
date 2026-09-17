"""Step 1.7: FX on tests/fixtures/fred/DEX*.csv (header + 50 rows each)."""

from pathlib import Path

import pandas as pd
import pytest

from curvecarry.loaders import base, fx

PATHS = [Path("tests/fixtures/fred") / f"{s}.csv" for s, _ in fx.QUOTES.values()]


@pytest.fixture(scope="module")
def usd_daily() -> pd.DataFrame:
    return fx.parse_usd(PATHS)


def test_fx_direction(usd_daily: pd.DataFrame) -> None:
    m = fx.monthly(fx.to_base(usd_daily, "USD"))
    lo_hi = {"GBP": (1.0, 3.0), "EUR": (0.8, 1.7), "JPY": (0.002, 0.015), "CAD": (0.6, 1.1)}
    for cur, (lo, hi) in lo_hi.items():
        s = m[m["currency"] == cur]["spot"]
        assert s.between(lo, hi).all(), (cur, s.min(), s.max())
    assert (m[m["currency"] == "USD"]["spot"] == 1.0).all()
    # DEXJPUS 1971-01-04 is 357.73 JPY per USD -> 1/357.73 USD per JPY
    j = usd_daily[(usd_daily["currency"] == "JPY") & (usd_daily["obs_date"] == "1971-01-04")]
    assert j["usd_per_foreign"].item() == pytest.approx(1 / 357.73)


def test_fx_non_usd_base(usd_daily: pd.DataFrame) -> None:
    gbp_base = fx.to_base(usd_daily, "GBP")
    usd_base = fx.to_base(usd_daily, "USD")
    usd_in_gbp = gbp_base[gbp_base["currency"] == "USD"].set_index("obs_date")["spot"]
    gbp_in_usd = usd_base[usd_base["currency"] == "GBP"].set_index("obs_date")["spot"]
    both = pd.concat([usd_in_gbp, gbp_in_usd], axis=1, keys=["a", "b"]).dropna()
    assert len(both) > 10
    assert ((both["a"] * both["b"]) - 1.0).abs().max() < 1e-12
    assert (gbp_base[gbp_base["currency"] == "GBP"]["spot"] == 1.0).all()
    # a third currency in GBP base equals its USD-base value divided by GBP's
    jpy_gbp = gbp_base[gbp_base["currency"] == "JPY"].set_index("obs_date")["spot"]
    jpy_usd = usd_base[usd_base["currency"] == "JPY"].set_index("obs_date")["spot"]
    chk = pd.concat([jpy_gbp, jpy_usd / gbp_in_usd], axis=1).dropna()
    assert (chk.iloc[:, 0] - chk.iloc[:, 1]).abs().max() < 1e-15


def test_fx_last_observation_of_month() -> None:
    daily = pd.DataFrame(
        {
            "obs_date": pd.to_datetime(["2020-01-02", "2020-01-15", "2020-01-31", "2020-02-03"]),
            "currency": "GBP",
            "spot": [1.30, 1.31, 1.32, 1.29],
        }
    )
    m = fx.monthly(daily)
    assert m["date"].tolist() == [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
    assert m["spot"].tolist() == [1.32, 1.29]


def test_fx_month_end_stamp(usd_daily: pd.DataFrame) -> None:
    m = fx.monthly(fx.to_base(usd_daily, "USD"))
    assert m["date"].equals(base.month_end(m["date"]))
    assert not m.duplicated(["date", "currency"]).any()


def test_unknown_series_refused(tmp_path: Path) -> None:
    p = tmp_path / "DEXSZUS.csv"
    p.write_text("observation_date,DEXSZUS\n2020-01-02,0.97\n")
    with pytest.raises(ValueError, match="DEXSZUS"):
        fx.parse_usd([p])
