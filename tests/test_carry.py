"""Step 4.1: carry and rolldown, on synthetic curves.

Six tests, one per line of the plan's "Test" block. Nothing here reads a
file: every curve is written by hand so the expected number can be derived
in closed form.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import bondmath, carry
from curvecarry.curves import Curve

DT = carry.DT
TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]


def _curve(tenors, yields, country="US", date="2020-06-30") -> Curve:
    return Curve(
        np.array(tenors, float), np.array(yields, float), "zero", country, pd.Timestamp(date)
    )


def test_flat_curve_rolldown_zero() -> None:
    """A flat curve rolls down nowhere; carry is the yield over the funding rate."""
    c = _curve([0.5] + TENORS, [0.03] * 9)
    for tenor in TENORS:
        vals, flat = carry.bucket(c, tenor, freq=2, r_short=0.02)
        assert abs(vals["rolldown"]) < 1e-15
        assert vals["carry"] == pytest.approx(0.01, abs=1e-15)
        assert vals["expected_return_1m"] == pytest.approx(0.01 * DT, abs=1e-15)
        assert not flat


def test_linear_curve_rolldown() -> None:
    """y(t) = a + b*t makes the rolldown exactly b * dt * D at every tenor."""
    a, b = 0.02, 0.001
    grid = [0.5] + TENORS
    c = _curve(grid, [a + b * t for t in grid])
    for tenor in TENORS:
        vals, _ = carry.bucket(c, tenor, freq=2, r_short=0.01)
        assert vals["rolldown"] == pytest.approx(b * DT * vals["duration"], abs=1e-12)


def test_one_year_rolldown_uses_observed_short_end_else_flat() -> None:
    """With 0.5 observed the 1-year rolls between 0.5 and 1; with nothing below 1 it does not."""
    grid = [0.5] + TENORS
    with_short = _curve(grid, [0.02 + 0.001 * t for t in grid])
    vals, flat = carry.bucket(with_short, 1.0, freq=2, r_short=0.01)
    y_roll = with_short.at(1.0 - DT)
    assert y_roll == pytest.approx(0.02 + 0.001 * (1.0 - DT), abs=1e-15)
    assert vals["rolldown"] > 0 and not flat

    no_short = _curve(TENORS, [0.02 + 0.001 * t for t in TENORS], country="JP")
    vals, flat = carry.bucket(no_short, 1.0, freq=2, r_short=0.01)
    assert no_short.at(1.0 - DT) == no_short.yields[0]
    assert vals["rolldown"] == 0.0
    assert flat

    # and the flat month is counted, not silently absorbed
    zero = _panel(no_short, standard=TENORS)
    funding = _funding([("JP", "2020-06-30", 0.01)])
    cfg = _cfg(country="JP")
    out, miss = carry.build_carry(zero, funding, cfg)
    row = miss[miss["tenor_years"] == 1.0].iloc[0]
    assert int(row["n_flat_short_end"]) == 1 and int(row["n_missing"]) == 0
    assert miss[miss["tenor_years"] == 2.0].iloc[0]["n_flat_short_end"] == 0


def test_r_short_from_funding_table_not_curve() -> None:
    """Moving the curve leaves r_short alone; moving the funding row moves carry one for one."""
    grid = [0.5] + TENORS
    low = _curve(grid, [0.02 + 0.001 * t for t in grid])
    high = _curve(grid, [0.05 + 0.001 * t for t in grid])
    a, _ = carry.bucket(low, 5.0, freq=2, r_short=0.03)
    b, _ = carry.bucket(high, 5.0, freq=2, r_short=0.03)
    assert a["r_short"] == b["r_short"] == 0.03
    c, _ = carry.bucket(low, 5.0, freq=2, r_short=0.04)
    assert c["carry"] == pytest.approx(a["carry"] - 0.01, abs=1e-15)
    assert c["rolldown"] == pytest.approx(a["rolldown"], abs=1e-15)


def test_duration_is_par_bond_risk() -> None:
    """The duration column is bondmath.par_bond_risk and nothing else."""
    grid = [0.5] + TENORS
    c = _curve(grid, [0.02 + 0.0008 * t for t in grid])
    for tenor in TENORS:
        for freq in (1, 2):
            vals, _ = carry.bucket(c, tenor, freq, r_short=0.01)
            par, d, cx = bondmath.par_bond_risk(c, tenor, freq)
            assert vals["duration"] == d and vals["convexity"] == cx and vals["par_yield"] == par


def test_missing_input_is_counted_not_filled() -> None:
    """No funding row that month, and a tenor beyond the curve: both dropped and counted."""
    short = _curve([1.0, 2.0, 3.0, 5.0, 7.0, 10.0], [0.02 + 0.001 * t for t in [1, 2, 3, 5, 7, 10]])
    zero = _panel(short, standard=TENORS[:6])
    # a second month with no funding row at all
    second = _panel(short, standard=TENORS[:6], date="2020-07-31")
    zero = pd.concat([zero, second], ignore_index=True)
    funding = _funding([("US", "2020-06-30", 0.01)])
    out, miss = carry.build_carry(zero, funding, _cfg())
    assert set(out["date"].dt.date.astype(str)) == {"2020-06-30"}
    assert len(out) == 6  # only the six standard tenors the curve reaches
    assert miss["n_missing"].sum() == 6  # the six buckets of the funding-less month
    assert not out[["carry", "rolldown", "duration"]].isna().any().any()
    assert 20.0 not in set(out["tenor_years"])


# ------------------------------------------------------------- fixtures


def _panel(c: Curve, standard: list[float], date: str | None = None) -> pd.DataFrame:
    d = pd.Timestamp(date) if date is not None else c.date
    return pd.DataFrame(
        {
            "date": d,
            "country": c.country,
            "tenor_years": c.tenors,
            "yield": c.yields,
            "curve_type": "zero",
            "source": "test",
            "interpolated": False,
            "standard": [t in set(standard) for t in c.tenors],
            "bootstrapped": False,
        }
    )


def _funding(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(d),
                "country": c,
                "currency": "XXX",
                "rate": r,
                "kind": "policy",
                "source": "bis",
            }
            for c, d, r in rows
        ]
    )


def _cfg(country: str = "US") -> dict:
    return {
        "tenors": TENORS,
        "coupon_frequency": {country: 2},
        "hedge": {"funding_rate": "policy"},
    }
