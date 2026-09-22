"""Step 1.7: funding rates on tests/fixtures/bis/*.csv and tests/fixtures/fred/IR3TIB01*.csv."""

from pathlib import Path

import pandas as pd
import pytest

from curvecarry import config
from curvecarry.loaders import base, short_rates

BIS = [Path("tests/fixtures/bis") / f"CBPOL_{a}.csv" for a in short_rates.BIS_AREAS]
IB = [Path("tests/fixtures/fred") / f"{s}.csv" for s in short_rates.INTERBANK.values()]
IMM = [Path("tests/fixtures/fred") / f"{s}.csv" for s in short_rates.IMMEDIATE.values()]


@pytest.fixture(scope="module")
def rates() -> pd.DataFrame:
    return short_rates.parse(BIS + IB + IMM)


def test_units_policy(rates: pd.DataFrame) -> None:
    p = rates[rates["kind"] == "policy"]
    assert p["rate"].between(-0.05, 0.5).all() and p["rate"].max() > 0.001
    raw = pd.read_csv("tests/fixtures/bis/CBPOL_US.csv").iloc[0]
    got = p[
        (p["area"] == "US")
        & (p["date"] == base.month_end(pd.Series([pd.Timestamp(raw["TIME_PERIOD"] + "-01")]))[0])
    ]
    assert got["rate"].item() == pytest.approx(raw["OBS_VALUE"] / 100.0)


def test_units_interbank(rates: pd.DataFrame) -> None:
    ib = rates[rates["kind"] == "interbank_3m"]
    assert ib["rate"].between(-0.05, 0.5).all() and ib["rate"].max() > 0.001
    assert set(ib["area"]) == {"US", "GB", "JP", "CA", "EZ"}


def test_units_immediate(rates: pd.DataFrame) -> None:
    im = rates[rates["kind"] == "immediate"]
    assert im["rate"].between(-0.05, 0.5).all() and im["rate"].max() > 0.001
    assert set(im["area"]) == {"US", "GB", "JP", "CA", "EZ"}
    raw = pd.read_csv("tests/fixtures/fred/IRSTCI01JPM156N.csv", na_values=["."]).iloc[0]
    got = im[(im["area"] == "JP") & (im["date"] == "1985-07-31")]["rate"].item()
    assert raw["observation_date"] == "1985-07-01"
    assert got == pytest.approx(raw["IRSTCI01JPM156N"] / 100.0)


def test_month_end_stamp(rates: pd.DataFrame) -> None:
    assert rates["date"].equals(base.month_end(rates["date"]))
    assert not rates.duplicated(["date", "area", "kind"]).any()


def test_bis_end_of_period_asserted(tmp_path: Path) -> None:
    src = Path("tests/fixtures/bis/CBPOL_US.csv").read_text(encoding="utf-8")
    bad = tmp_path / "CBPOL_US.csv"
    bad.write_text(src.replace("End of period", "Average"), encoding="utf-8")
    with pytest.raises(ValueError, match="End of period"):
        short_rates.parse_bis(bad)


def _synthetic_rates() -> pd.DataFrame:
    months = pd.date_range("1998-10-31", "1999-03-31", freq="ME")
    rows = []
    for d in months:
        rows += [
            (d, "DE", 0.030, "policy", "bis"),
            (d, "FR", 0.031, "policy", "bis"),
            (d, "XM", 0.040, "policy", "bis"),
            (d, "US", 0.050, "policy", "bis"),
            (d, "GB", 0.060, "policy", "bis"),
            (d, "JP", 0.005, "policy", "bis"),
            (d, "CA", 0.045, "policy", "bis"),
            (d, "EZ", 0.035, "interbank_3m", "fred"),
            (d, "US", 0.052, "interbank_3m", "fred"),
            (d, "GB", 0.062, "interbank_3m", "fred"),
            (d, "JP", 0.006, "interbank_3m", "fred"),
            (d, "CA", 0.047, "interbank_3m", "fred"),
        ]
    return pd.DataFrame(rows, columns=["date", "area", "rate", "kind", "source"])


def test_eur_splice() -> None:
    cfg = config.load()
    f = short_rates.build_funding(_synthetic_rates(), cfg)

    def rate(country: str, date: str) -> float:
        r = f[(f["country"] == country) & (f["kind"] == "policy") & (f["date"] == date)]
        return r["rate"].item()

    assert rate("DE", "1998-12-31") == 0.030 and rate("DE", "1999-01-31") == 0.040
    assert rate("FR", "1998-12-31") == 0.031 and rate("FR", "1999-01-31") == 0.040
    assert rate("US", "1998-12-31") == 0.050 and rate("US", "1999-01-31") == 0.050
    assert (f[(f["country"] == "DE") & (f["kind"] == "interbank_3m")]["rate"] == 0.035).all()


def _with_immediate(rates: pd.DataFrame, value: float = 0.009) -> pd.DataFrame:
    """Add an OECD immediate series for every area over the synthetic months."""
    months = sorted(rates["date"].unique())
    rows = [
        (d, a, value, "immediate", "fred") for d in months for a in ["US", "GB", "JP", "CA", "EZ"]
    ]
    return pd.concat([rates, pd.DataFrame(rows, columns=rates.columns)], ignore_index=True)


def test_policy_gap_filled_from_immediate_and_labelled() -> None:
    """A planted 3-month hole in the BIS JP series is filled from IRSTCI01JP, labelled."""
    cfg = config.load()
    rates = _with_immediate(_synthetic_rates())
    hole = pd.date_range("1998-12-31", "1999-02-28", freq="ME")
    rates = rates[
        ~((rates["area"] == "JP") & (rates["kind"] == "policy") & rates["date"].isin(hole))
    ]
    f = short_rates.build_funding(rates, cfg)
    jp = f[(f["country"] == "JP") & (f["kind"] == "policy")].set_index("date")
    assert list(jp.index) == sorted(rates["date"].unique())  # no month missing any more
    assert (jp.loc[hole, "source"] == "fred_immediate").all()
    assert (jp.loc[hole, "rate"] == 0.009).all()
    assert (jp.drop(hole)["source"] == "bis").all() and (jp.drop(hole)["rate"] == 0.005).all()
    fill = short_rates.funding_fill_rows(f)
    row = fill[fill["country"] == "JP"].iloc[0]
    assert (row["first"], row["last"], row["months_filled"]) == ("1998-12-31", "1999-02-28", 3)
    assert (fill[fill["country"] != "JP"]["months_filled"] == 0).all()


def test_bis_value_never_overwritten() -> None:
    """Where BIS has a value the immediate rate is ignored, even when it differs."""
    cfg = config.load()
    f = short_rates.build_funding(_with_immediate(_synthetic_rates(), value=0.123), cfg)
    pol = f[f["kind"] == "policy"]
    assert (pol["source"] == "bis").all() and not (pol["rate"] == 0.123).any()
    assert short_rates.funding_fill_rows(f)["months_filled"].eq(0).all()
    # and the fill never extends a series before its first or after its last BIS month
    rates = _with_immediate(_synthetic_rates())
    rates = rates[
        ~((rates["area"] == "JP") & (rates["kind"] == "policy") & (rates["date"] >= "1999-03-01"))
    ]
    jp = short_rates.build_funding(rates, cfg)
    jp = jp[(jp["country"] == "JP") & (jp["kind"] == "policy")]
    assert jp["date"].max() == pd.Timestamp("1999-02-28") and (jp["source"] == "bis").all()


def test_funding_table_covers_every_country_and_kind() -> None:
    cfg = config.load()
    f = short_rates.build_funding(_synthetic_rates(), cfg)
    pairs = set(zip(f["country"], f["kind"], strict=True))
    for c in cfg["countries"]:
        assert (c, "policy") in pairs and (c, "interbank_3m") in pairs
    assert list(f.columns) == short_rates.FUNDING_COLUMNS
    assert set(f["currency"]) == {"USD", "GBP", "EUR", "JPY", "CAD"}
