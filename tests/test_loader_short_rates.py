"""Step 1.7: funding rates on tests/fixtures/bis/*.csv and tests/fixtures/fred/IR3TIB01*.csv."""

from pathlib import Path

import pandas as pd
import pytest

from curvecarry import config
from curvecarry.loaders import base, short_rates

BIS = [Path("tests/fixtures/bis") / f"CBPOL_{a}.csv" for a in short_rates.BIS_AREAS]
IB = [Path("tests/fixtures/fred") / f"{s}.csv" for s in short_rates.INTERBANK.values()]


@pytest.fixture(scope="module")
def rates() -> pd.DataFrame:
    return short_rates.parse(BIS + IB)


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


def test_funding_table_covers_every_country_and_kind() -> None:
    cfg = config.load()
    f = short_rates.build_funding(_synthetic_rates(), cfg)
    pairs = set(zip(f["country"], f["kind"], strict=True))
    for c in cfg["countries"]:
        assert (c, "policy") in pairs and (c, "interbank_3m") in pairs
    assert list(f.columns) == short_rates.FUNDING_COLUMNS
    assert set(f["currency"]) == {"USD", "GBP", "EUR", "JPY", "CAD"}
