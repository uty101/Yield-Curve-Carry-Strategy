"""Step 5.1: the carry signal and its eligibility rules, on synthetic frames."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import signal as sig

DATE = pd.Timestamp("2010-01-31")


def _carry(**over) -> pd.DataFrame:
    """One bucket-month; any column can be overridden."""
    row = {
        "date": DATE,
        "country": "US",
        "tenor_years": 5.0,
        "yield": 0.03,
        "carry": 0.02,
        "rolldown": 0.001,
        "duration": 4.0,
    }
    row.update(over)
    return pd.DataFrame([row])


def _universe(pairs=(("US", "5"),), date: pd.Timestamp = DATE) -> pd.DataFrame:
    by_country: dict[str, list[str]] = {}
    for c, t in pairs:
        by_country.setdefault(c, []).append(t)
    return pd.DataFrame(
        [
            {
                "date": date,
                "country": c,
                "n_tenors": len(ts),
                "tenors": ";".join(ts),
                "n_total_all_countries": sum(len(v) for v in by_country.values()),
            }
            for c, ts in by_country.items()
        ]
    )


def _cfg(floor: float = 0.002) -> dict:
    return {"signal": {"yield_floor": floor}}


def test_signal_hand_computed() -> None:
    """carry 0.02, rolldown 0.001, D 4 -> (0.02 + 12 x 0.001) / 4 = 0.008."""
    out = sig.compute_signal(_carry(), _universe(), _cfg())
    assert out.loc[0, "signal"] == pytest.approx(0.008, abs=1e-15)
    assert bool(out.loc[0, "eligible"]) is True
    assert out.loc[0, "excluded_reason"] == ""


def test_below_floor_is_ineligible() -> None:
    out = sig.compute_signal(_carry(**{"yield": 0.0019}), _universe(), _cfg(floor=0.002))
    assert bool(out.loc[0, "eligible"]) is False
    assert out.loc[0, "excluded_reason"] == "below_floor"
    # the signal itself is still reported
    assert np.isfinite(out.loc[0, "signal"])


def test_missing_input_and_not_in_universe_are_distinct_reasons() -> None:
    """Amendment 3: a bucket the return engine cannot price is excluded by name."""
    nan_duration = sig.compute_signal(_carry(duration=np.nan), _universe(), _cfg())
    assert nan_duration.loc[0, "excluded_reason"] == "missing_input"

    absent = sig.compute_signal(_carry(), _universe(pairs=(("US", "10"),)), _cfg())
    assert absent.loc[0, "excluded_reason"] == "not_in_universe"

    # missing_input wins over a floor breach: one row, one reason, in that order
    both = sig.compute_signal(
        _carry(duration=np.nan, **{"yield": 0.0001}), _universe(), _cfg(floor=0.002)
    )
    assert both.loc[0, "excluded_reason"] == "missing_input"


def test_exclusion_counts_match_rows() -> None:
    carry = pd.concat(
        [
            _carry(country="US", tenor_years=5.0, **{"yield": 0.03}),
            _carry(country="US", tenor_years=10.0, **{"yield": 0.0001}),
            _carry(country="JP", tenor_years=5.0, **{"yield": 0.0005}),
            _carry(country="JP", tenor_years=10.0, duration=np.nan),
        ],
        ignore_index=True,
    )
    universe = _universe(pairs=(("US", "5"), ("US", "10"), ("JP", "5"), ("JP", "10")))
    out = sig.compute_signal(carry, universe, _cfg())
    per_month, per_country = sig.exclusion_rows(out)

    assert len(per_month) == 1
    row = per_month.iloc[0]
    assert int(row["n_below_floor"]) == 2
    assert int(row["n_missing_input"]) == 1
    assert int(row["n_eligible"]) == 1
    assert int(row["n_below_floor"]) == int((out["excluded_reason"] == "below_floor").sum())

    counts = dict(zip(per_country["country"], per_country["n_below_floor"], strict=True))
    assert counts == {"JP": 1, "US": 1}

    elig = sig.universe_eligible_rows(out).iloc[0]
    assert int(elig["n_eligible"]) == 1
    assert elig["eligible_buckets"] == "US:5"
    assert int(elig["n_universe"]) == 4


def test_floor_read_from_config_not_hardcoded() -> None:
    carry = _carry(**{"yield": 0.004})
    assert bool(sig.compute_signal(carry, _universe(), _cfg(floor=0.002)).loc[0, "eligible"])
    assert not bool(sig.compute_signal(carry, _universe(), _cfg(floor=0.005)).loc[0, "eligible"])


def test_universe_changes_are_entries_and_exits() -> None:
    """The first month is all entries; a bucket that stops being eligible leaves."""
    jan, feb, mar = (
        pd.Timestamp("2010-01-31"),
        pd.Timestamp("2010-02-28"),
        pd.Timestamp("2010-03-31"),
    )
    carry = pd.concat(
        [
            _carry(date=jan, country="US", tenor_years=5.0),
            _carry(date=jan, country="US", tenor_years=10.0),
            _carry(date=feb, country="US", tenor_years=5.0),
            _carry(date=mar, country="US", tenor_years=5.0),
            _carry(date=mar, country="GB", tenor_years=5.0),
        ],
        ignore_index=True,
    )
    universe = pd.concat(
        [
            _universe(pairs=(("US", "5"), ("US", "10")), date=jan),
            _universe(pairs=(("US", "5"),), date=feb),
            _universe(pairs=(("US", "5"), ("GB", "5")), date=mar),
        ],
        ignore_index=True,
    )
    changes = sig.universe_change_rows(sig.compute_signal(carry, universe, _cfg()))
    got = {(r["date"], r["country"], r["tenor_years"], r["change"]) for _, r in changes.iterrows()}
    assert got == {
        ("2010-01-31", "US", 5.0, "enters"),
        ("2010-01-31", "US", 10.0, "enters"),
        ("2010-02-28", "US", 10.0, "leaves"),
        ("2010-03-31", "GB", 5.0, "enters"),
    }
