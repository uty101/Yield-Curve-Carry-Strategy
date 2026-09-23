"""Step 5.2: duration-neutral weights, on synthetic signal frames."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import config
from curvecarry import weights as wt

BUDGET = 5.0
COUNTRIES = ["US", "GB", "DE", "JP", "CA", "FR"]
TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]


def _cfg(scope: str = "book", minimum: int = 9, budget: float = BUDGET) -> dict:
    return {
        "weights": {
            "duration_neutral_scope": scope,
            "long_duration_budget": budget,
            "min_eligible_buckets": minimum,
        }
    }


def _signal(n_per_country: dict[str, int], dates=("2010-01-31",), seed: int = 0) -> pd.DataFrame:
    """A signal frame with ``n`` eligible buckets per country, distinct signals and durations."""
    rng = np.random.default_rng(seed)
    rows = []
    for date in dates:
        for country, n in n_per_country.items():
            for tenor in TENORS[:n]:
                rows.append(
                    {
                        "date": pd.Timestamp(date),
                        "country": country,
                        "tenor_years": tenor,
                        "signal": float(rng.normal()),
                        "duration": float(tenor) * 0.9,
                        "yield": 0.03,
                        "eligible": True,
                        "excluded_reason": "",
                    }
                )
    return pd.DataFrame(rows)


def test_duration_neutral_every_month() -> None:
    sig = _signal({c: 8 for c in COUNTRIES}, dates=("2010-01-31", "2010-02-28", "2010-03-31"))
    held, _ = wt.duration_neutral_weights(sig, _cfg())
    assert held["date"].nunique() == 3
    for _, g in held.groupby("date"):
        assert abs(g["wd"].sum()) < 1e-10


def test_long_leg_hits_budget() -> None:
    held, _ = wt.duration_neutral_weights(_signal({c: 8 for c in COUNTRIES}), _cfg())
    long = held[held["leg"] == "long"]
    short = held[held["leg"] == "short"]
    assert long["wd"].sum() == pytest.approx(BUDGET, abs=1e-12)
    assert short["wd"].sum() == pytest.approx(-BUDGET, abs=1e-12)


def test_equal_duration_contribution_within_leg() -> None:
    held, _ = wt.duration_neutral_weights(_signal({c: 8 for c in COUNTRIES}), _cfg())
    for leg, sign in (("long", 1.0), ("short", -1.0)):
        g = held[held["leg"] == leg]
        assert g["wd"].nunique() == 1
        assert g["wd"].iloc[0] == pytest.approx(sign * BUDGET / len(g), abs=1e-12)
        # and the capital weight is that duration divided by the bucket's own duration
        assert np.allclose(g["weight"] * g["duration"], g["wd"], atol=1e-12)


def test_legs_never_overlap() -> None:
    held, _ = wt.duration_neutral_weights(_signal({c: 8 for c in COUNTRIES}), _cfg())
    long = set(
        zip(
            held[held["leg"] == "long"]["country"],
            held[held["leg"] == "long"]["tenor_years"],
            strict=True,
        )
    )
    short = set(
        zip(
            held[held["leg"] == "short"]["country"],
            held[held["leg"] == "short"]["tenor_years"],
            strict=True,
        )
    )
    assert long & short == set()


def test_third_rule() -> None:
    """k = n // 3 a side. 48 eligible -> 16 and 16; 9 -> 3 and 3."""
    held, _ = wt.duration_neutral_weights(_signal({c: 8 for c in COUNTRIES}), _cfg())
    assert (held["leg"] == "long").sum() == 16
    assert (held["leg"] == "short").sum() == 16

    nine, _ = wt.duration_neutral_weights(_signal({"US": 8, "GB": 1}), _cfg())
    assert (nine["leg"] == "long").sum() == 3
    assert (nine["leg"] == "short").sum() == 3

    # The plan's original 7 -> 2 and 2 still holds where the minimum allows it;
    # under amendment 3 (minimum 9) a 7-bucket month is flat instead, below.
    seven, _ = wt.duration_neutral_weights(_signal({"US": 7}), _cfg(minimum=6))
    assert (seven["leg"] == "long").sum() == 2
    assert (seven["leg"] == "short").sum() == 2


def test_country_scope_neutral_per_country() -> None:
    sig = _signal({c: 8 for c in COUNTRIES})
    held, _ = wt.duration_neutral_weights(sig, _cfg(scope="country"))
    assert set(held["country"]) == set(COUNTRIES)
    for country, g in held.groupby("country"):
        assert abs(g["wd"].sum()) < 1e-10, country
        assert g[g["leg"] == "long"]["wd"].sum() == pytest.approx(BUDGET / 6, abs=1e-12)
    # the book still carries exactly B in its long leg
    assert held[held["leg"] == "long"]["wd"].sum() == pytest.approx(BUDGET, abs=1e-12)


def test_country_scope_skips_a_country_with_fewer_than_three_tenors() -> None:
    """k_c = n_c // 3 is 0 there, so it holds nothing and the budget splits over the rest."""
    held, _ = wt.duration_neutral_weights(
        _signal({"US": 8, "GB": 8, "JP": 2}), _cfg(scope="country")
    )
    assert set(held["country"]) == {"US", "GB"}
    assert held[held["leg"] == "long"]["wd"].sum() == pytest.approx(BUDGET, abs=1e-12)
    for _, g in held.groupby("country"):
        assert abs(g["wd"].sum()) < 1e-10


def test_empty_month_below_minimum_is_logged() -> None:
    held, empty = wt.duration_neutral_weights(_signal({"US": 8}), _cfg())
    assert len(held) == 0
    assert len(empty) == 1
    row = empty.iloc[0]
    assert row["date"] == "2010-01-31"
    assert int(row["n_eligible"]) == 8
    assert int(row["min_eligible_buckets"]) == 9
    assert row["reason"] == "below min_eligible_buckets"


def test_min_eligible_buckets_is_nine() -> None:
    """Amendment 3 is pre-registered: a silent revert of the default fails here."""
    assert int(config.load()["weights"]["min_eligible_buckets"]) == 9


def test_ties_are_broken_by_country_then_tenor() -> None:
    sig = _signal({"US": 8, "GB": 8})
    sig["signal"] = 0.0  # every bucket tied
    held, _ = wt.duration_neutral_weights(sig, _cfg())
    long = held[held["leg"] == "long"].sort_values(["country", "tenor_years"])
    assert list(zip(long["country"], long["tenor_years"], strict=True)) == [
        ("GB", 1.0),
        ("GB", 2.0),
        ("GB", 3.0),
        ("GB", 5.0),
        ("GB", 7.0),
    ]
