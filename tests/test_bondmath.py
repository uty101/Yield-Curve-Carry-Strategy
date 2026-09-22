"""Step 2.1: bond maths against closed forms. No network, no data files."""

import numpy as np
import pandas as pd
import pytest

from curvecarry import bondmath
from curvecarry.curves import Curve

D = pd.Timestamp("2020-01-31")
STANDARD = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
SLOPED = [0.010, 0.014, 0.017, 0.022, 0.025, 0.028, 0.032, 0.033]


def _zero(tenors, yields) -> Curve:
    return Curve(np.asarray(tenors, float), np.asarray(yields, float), "zero", "XX", D)


def _flat(z: float, tenors=None) -> Curve:
    t = STANDARD if tenors is None else tenors
    return _zero(t, [z] * len(t))


def test_zero_coupon_bond_price() -> None:
    """A zero-coupon bond off a flat curve is 100 (1+z)^-T to 1e-12."""
    curve = _flat(0.03)
    for freq in (1, 2):
        for t in (1.0, 2.0, 5.0, 10.0, 30.0):
            want = 100.0 * (1.03) ** (-t)
            assert abs(bondmath.price_from_zero(curve, t, 0.0, freq) - want) < 1e-12


def test_flat_curve_par_yield() -> None:
    """Flat z: c = f((1+z)^(1/f) - 1); for f = 1, c = z."""
    for z in (0.01, 0.03, 0.07):
        curve = _flat(z)
        for freq in (1, 2, 4):
            want = freq * ((1.0 + z) ** (1.0 / freq) - 1.0)
            for t in (1.0, 5.0, 30.0):
                assert abs(bondmath.par_yield_from_zero(curve, t, freq) - want) < 1e-12
        assert abs(bondmath.par_yield_from_zero(curve, 10.0, 1) - z) < 1e-12


def test_par_bond_prices_at_100() -> None:
    """The par coupon prices its own bond at exactly 100 on a sloped curve."""
    curve = _zero(STANDARD, SLOPED)
    for freq in (1, 2):
        for t in (1.0, 2.0, 5.0, 10.0, 30.0):
            c = bondmath.par_yield_from_zero(curve, t, freq)
            assert abs(bondmath.price_from_zero(curve, t, c, freq) - 100.0) < 1e-9


def test_yield_from_price_round_trip() -> None:
    """yield_from_price(price_from_zero(...)) returns the par yield to 1e-10."""
    curve = _zero(STANDARD, SLOPED)
    for freq in (1, 2):
        for t in (1.0, 3.0, 7.0, 30.0):
            c = bondmath.par_yield_from_zero(curve, t, freq)
            p = bondmath.price_from_zero(curve, t, c, freq)
            assert abs(bondmath.yield_from_price(p, t, c, freq) - c) < 1e-10


def test_zero_coupon_duration_and_convexity() -> None:
    """Coupon 0: D = T/(1+y/f) and C = T(T + 1/f)/(1+y/f)^2 to 1e-10."""
    for freq in (1, 2):
        for y in (0.01, 0.05):
            for t in (1.0, 5.0, 30.0):
                d = bondmath.modified_duration(y, t, 0.0, freq)
                c = bondmath.convexity(y, t, 0.0, freq)
                assert abs(d - t / (1.0 + y / freq)) < 1e-10
                assert abs(c - t * (t + 1.0 / freq) / (1.0 + y / freq) ** 2) < 1e-10


def test_duration_matches_finite_difference() -> None:
    """-(P(y+h) - P(y-h)) / (2 h P) matches modified duration to 1e-6, h = 1e-6."""
    h = 1e-6
    for freq in (1, 2):
        for t, coupon, y in ((2.0, 0.03, 0.02), (10.0, 0.05, 0.04), (30.0, 0.02, 0.06)):
            p = bondmath.price_from_yield(y, t, coupon, freq)
            up = bondmath.price_from_yield(y + h, t, coupon, freq)
            dn = bondmath.price_from_yield(y - h, t, coupon, freq)
            fd = -(up - dn) / (2.0 * h * p)
            assert abs(fd - bondmath.modified_duration(y, t, coupon, freq)) < 1e-6


def test_curve_type_asserted() -> None:
    """Every function that takes a curve rejects a par curve (rule 3)."""
    par = Curve(np.asarray(STANDARD), np.asarray(SLOPED), "par", "XX", D)
    with pytest.raises(AssertionError):
        bondmath.price_from_zero(par, 10.0, 0.03, 2)
    with pytest.raises(AssertionError):
        bondmath.par_yield_from_zero(par, 10.0, 2)
    with pytest.raises(AssertionError):
        bondmath.par_bond_risk(par, 10.0, 2)


def test_short_end_is_flat_not_nan() -> None:
    """Flat below the shortest observed tenor, NaN above the longest, interpolated inside."""
    from_1y = _zero(STANDARD, SLOPED)
    assert from_1y.at(0.5) == from_1y.at(1.0) == SLOPED[0]
    assert np.isfinite(from_1y.at(0.5))
    assert np.isnan(from_1y.at(31.0))
    from_3m = _zero([0.25, *STANDARD], [0.008, *SLOPED])
    assert abs(from_3m.at(0.5) - (0.008 + (0.010 - 0.008) * 0.25 / 0.75)) < 1e-12
    # a seasoned bond's short stub prices off the flat short end rather than raising
    assert bondmath.price_from_zero(from_1y, 2.5, 0.03, 2) > 0
    with pytest.raises(ValueError):
        bondmath.price_from_zero(from_1y, 31.0, 0.03, 2)


def test_cashflow_times_stub_and_grid() -> None:
    """Coupon dates count back from maturity; the stub is first and everything is positive."""
    assert bondmath.cashflow_times(3.0, 1).tolist() == [1.0, 2.0, 3.0]
    assert bondmath.cashflow_times(2.0, 2).tolist() == [0.5, 1.0, 1.5, 2.0]
    stub = bondmath.cashflow_times(2.3, 2)
    assert stub.tolist() == pytest.approx([0.3, 0.8, 1.3, 1.8, 2.3])
    assert (stub > 0).all() and stub[-1] == 2.3


def test_par_bond_risk_is_one_function() -> None:
    """par_bond_risk returns the par coupon and its duration and convexity at ytm = coupon."""
    curve = _zero(STANDARD, SLOPED)
    c, d, cx = bondmath.par_bond_risk(curve, 10.0, 2)
    assert abs(c - bondmath.par_yield_from_zero(curve, 10.0, 2)) < 1e-15
    assert abs(d - bondmath.modified_duration(c, 10.0, c, 2)) < 1e-15
    assert abs(cx - bondmath.convexity(c, 10.0, c, 2)) < 1e-15
    assert abs(c - 0.027207805094634257) < 1e-15 and abs(d - 8.70363301265138) < 1e-12


def test_par_reprice_recovers_the_bootstrap() -> None:
    """A bootstrapped month reprices its own observed par nodes to float noise."""
    from curvecarry import bootstrap

    par = Curve(np.asarray(STANDARD), np.asarray(SLOPED), "par", "US", D)
    zc = bootstrap.bootstrap_par_to_zero(par, 2, STANDARD)
    panel = pd.DataFrame(
        {
            "date": D,
            "country": "US",
            "tenor_years": STANDARD,
            "yield": SLOPED,
            "curve_type": "par",
            "source": "test",
            "interpolated": False,
            "standard": True,
        }
    )
    zero = pd.DataFrame(
        {
            "date": D,
            "country": "US",
            "tenor_years": zc.tenors,
            "yield": zc.yields,
            "curve_type": "zero",
            "source": "test",
            "interpolated": False,
            "standard": np.isin(zc.tenors, STANDARD),
            "bootstrapped": True,
        }
    )
    cfg = {"coupon_frequency": {"US": 2}}
    out = bondmath.par_reprice(panel, zero, cfg)
    assert set(out["status"]) == {"ok"}
    assert out["diff_bp"].abs().max() < 1e-8
