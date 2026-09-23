"""Step 4.2: the return engine, on synthetic Nelson-Siegel curves.

Every curve here is generated, never read: ``rng = default_rng(0)``,
beta0 in [0.01, 0.08], beta1 in [-0.04, 0.02], beta2 in [-0.03, 0.03],
lambda in [0.3, 1.2], and month-to-month shocks of a parallel move uniform on
+/-50 bp and a slope move uniform on +/-25 bp (PLAN.md 4.2).

``test_approx_within_tolerance_on_200_draws`` is ``xfail(strict=True)``. It is
the plan's own tolerance on the plan's own formula, and the formula misses it
by more than an order of magnitude: see the module docstring of
``curvecarry.returns`` and the session-4 decision issue. What the three
readings of ``dy`` do achieve is measured in
``test_approx_candidate_gaps_are_small_and_the_plan_dy_is_not``, which passes.
The 2 bp half of the tolerance turns out not to be reachable by any of them,
for a reason that has nothing to do with ``dy``; that test says why.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import bondmath, returns
from curvecarry.curves import Curve

TENORS = [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
STANDARD = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
N_DRAWS = 200
TOL_SHORT_BP = 2.0  # tenors <= 10
TOL_LONG_BP = 10.0  # 20 and 30
DT = returns.DT


def ns(tenors: np.ndarray, b0: float, b1: float, b2: float, lam: float) -> np.ndarray:
    """Nelson-Siegel zero yields, the shape the fixtures are drawn from."""
    x = lam * tenors
    load1 = (1.0 - np.exp(-x)) / x
    return b0 + b1 * load1 + b2 * (load1 - np.exp(-x))


def _curve(yields, tenors=TENORS, country="US", date="2020-06-30") -> Curve:
    return Curve(
        np.array(tenors, float), np.array(yields, float), "zero", country, pd.Timestamp(date)
    )


def _draws(n: int = N_DRAWS):
    """``(curve_t, curve_next, tenor)`` triples; the shock is parallel plus slope."""
    rng = np.random.default_rng(0)
    t = np.array(TENORS, float)
    out = []
    for _ in range(n):
        b0 = rng.uniform(0.01, 0.08)
        b1 = rng.uniform(-0.04, 0.02)
        b2 = rng.uniform(-0.03, 0.03)
        lam = rng.uniform(0.3, 1.2)
        y0 = ns(t, b0, b1, b2, lam)
        parallel = rng.uniform(-0.005, 0.005)
        slope = rng.uniform(-0.0025, 0.0025)
        y1 = y0 + parallel + slope * (t - t.mean()) / (t.max() - t.mean())
        tenor = float(rng.choice(STANDARD))
        out.append((_curve(y0), _curve(y1, date="2020-07-31"), tenor))
    return out


def _tol(tenor: float) -> float:
    return TOL_SHORT_BP if tenor <= 10.0 else TOL_LONG_BP


@pytest.mark.xfail(
    strict=True,
    reason="the plan's dy compares par yields at tenors with different stub structure; "
    "session-4 decision issue",
)
def test_approx_within_tolerance_on_200_draws() -> None:
    """The plan's tolerance on the plan's formula. Recorded as a known failure, not hidden."""
    for curve_t, curve_next, tenor in _draws():
        vals, closed = returns.bucket_return(curve_t, curve_next, tenor, freq=2)
        assert not closed
        assert abs(vals["gap_bp"]) <= _tol(tenor), (tenor, vals["gap_bp"])


def test_approx_candidate_gaps_are_small_and_the_plan_dy_is_not() -> None:
    """What the three readings of dy actually achieve on the plan's own draws.

    The plan's 2 bp tolerance is not reached by any of them, for a reason that
    is not about dy at all: ``(D, C)`` are taken at ``t`` on the un-aged bond,
    and a month of aging shortens the duration by about ``1/12`` of a year, so
    a 50 bp move leaves ``(1/12) x 50 bp`` of error whatever dy is. Both
    candidates land inside 5 bp; the plan's dy is out by more than 50.
    """
    worst = {c: {} for c in ("gap_bp", "gap_bp_ytm", "gap_bp_curve")}
    for curve_t, curve_next, tenor in _draws():
        vals, closed = returns.bucket_return(curve_t, curve_next, tenor, freq=2)
        assert not closed
        for column, seen in worst.items():
            seen[tenor] = max(seen.get(tenor, 0.0), abs(vals[column]))
    for tenor in STANDARD:
        assert worst["gap_bp"][tenor] > 50.0, (tenor, worst["gap_bp"][tenor])
        assert worst["gap_bp_ytm"][tenor] <= 5.0, (tenor, worst["gap_bp_ytm"][tenor])
        # the curve reading holds at 5 bp out to 10 years and drifts beyond it
        limit = 5.0 if tenor <= 10.0 else 25.0
        assert worst["gap_bp_curve"][tenor] <= limit, (tenor, worst["gap_bp_curve"][tenor])
    # only the ytm reading meets the plan's 10 bp tolerance at 20 and 30 years
    assert max(worst["gap_bp_ytm"][t] for t in (20.0, 30.0)) <= TOL_LONG_BP
    assert max(worst["gap_bp_curve"][t] for t in (20.0, 30.0)) > TOL_LONG_BP


def test_unchanged_curve_return_equals_carry_plus_rolldown() -> None:
    """A curve that does not move returns its coupon accrual plus its rolldown."""
    t = np.array(TENORS, float)
    y = ns(t, 0.04, -0.02, 0.01, 0.6)
    curve = _curve(y)
    same = _curve(y, date="2020-07-31")
    for tenor in STANDARD:
        vals, _ = returns.bucket_return(curve, same, tenor, freq=2)
        c, d, _ = bondmath.par_bond_risk(curve, tenor, freq=2)
        roll = (float(curve.at(tenor)) - float(curve.at(tenor - DT))) * d
        assert vals["r_local_full"] == pytest.approx(c / 12.0 + roll, abs=1e-4)
        assert vals["r_local_approx_curve"] == pytest.approx(c / 12.0 + roll, abs=1e-5)
        assert vals["dy_curve"] == pytest.approx(0.0, abs=1e-15)


def test_parallel_shift_sign() -> None:
    """+100 bp is a loss at every tenor and -100 bp is a gain at every tenor."""
    t = np.array(TENORS, float)
    y = ns(t, 0.04, -0.02, 0.01, 0.6)
    up = _curve(y + 0.01, date="2020-07-31")
    down = _curve(y - 0.01, date="2020-07-31")
    curve = _curve(y)
    for tenor in STANDARD:
        assert returns.bucket_return(curve, up, tenor, 2)[0]["r_local_full"] < 0
        assert returns.bucket_return(curve, down, tenor, 2)[0]["r_local_full"] > 0


def test_closed_bucket_is_zero_and_logged() -> None:
    """A curve at t+1 that stops at 10 years closes the 20- and 30-year buckets."""
    t = np.array(TENORS, float)
    y = ns(t, 0.04, -0.02, 0.01, 0.6)
    short_t = [x for x in TENORS if x <= 10.0]
    nxt = _curve(ns(np.array(short_t, float), 0.04, -0.02, 0.01, 0.6), short_t, date="2020-07-31")
    curve = _curve(y)
    vals, closed = returns.bucket_return(curve, nxt, 30.0, freq=2)
    assert closed and vals["r_local"] == 0.0
    assert np.isnan(vals["r_local_full"]) and np.isnan(vals["gap_bp"])
    assert vals["duration"] > 0  # known at t, kept

    frame = pd.DataFrame(
        [
            {"date": curve.date, "country": "US", "tenor_years": 30.0, "closed": True},
            {"date": curve.date, "country": "US", "tenor_years": 10.0, "closed": False},
        ]
    )
    log = returns.closed_rows(frame)
    assert list(log.columns) == returns.CLOSED_COLUMNS
    assert len(log) == 1 and log.iloc[0]["tenor_years"] == 30.0
    assert log.iloc[0]["reason"] == returns.CLOSED_REASON


def test_full_repricing_uses_dirty_price() -> None:
    """The price at t+1 is the PV of the remaining cashflows, first stub 1/freq - 1/12."""
    t = np.array(TENORS, float)
    y = ns(t, 0.04, -0.02, 0.01, 0.6)
    curve, nxt = _curve(y), _curve(y + 0.002, date="2020-07-31")
    tenor, freq = 10.0, 2
    c, _, _ = bondmath.par_bond_risk(curve, tenor, freq)
    aged = tenor - DT
    times = bondmath.cashflow_times(aged, freq)
    assert times[0] == pytest.approx(1.0 / freq - DT, abs=1e-12)
    assert len(times) == tenor * freq  # no coupon has been paid inside the month
    dfs = bondmath.discount_factor(np.asarray(nxt.at(times), float), times)
    manual = 100.0 * (c / freq) * dfs.sum() + 100.0 * dfs[-1]
    vals, _ = returns.bucket_return(curve, nxt, tenor, freq)
    assert vals["r_local_full"] == pytest.approx(manual / 100.0 - 1.0, abs=1e-15)


def test_excess_return_subtracts_own_funding() -> None:
    """r_excess_local uses the bucket's own country at date t, never t+1."""
    t = np.array(TENORS, float)
    y = ns(t, 0.04, -0.02, 0.01, 0.6)
    zero = pd.concat(
        [_panel(_curve(y, date=d)) for d in ("2020-06-30", "2020-07-31", "2020-08-31")],
        ignore_index=True,
    )
    funding = pd.DataFrame(
        [
            {"date": pd.Timestamp(d), "country": "US", "currency": "USD", "rate": r, "kind": k}
            for d, r in (("2020-06-30", 0.048), ("2020-07-31", 0.010), ("2020-08-31", 0.010))
            for k in ("policy", "interbank_3m")
        ]
    )
    out = returns.build_returns(zero, funding, _cfg())
    june = out[(out["date"] == "2020-06-30") & (out["tenor_years"] == 10.0)].iloc[0]
    assert june["r_short_local"] == 0.048  # dated t, not t+1
    assert june["r_excess_local"] == pytest.approx(june["r_local"] - 0.048 / 12.0, abs=1e-15)
    july = out[(out["date"] == "2020-07-31") & (out["tenor_years"] == 10.0)].iloc[0]
    assert july["r_short_local"] == 0.010
    # August has no next month, so it produces no rows at all
    assert set(out["date"].astype(str)) == {"2020-06-30", "2020-07-31"}


def test_universe_and_identity_files() -> None:
    """Amendments 1 and 2: the universe log counts live buckets; the identity annualises by 12."""
    frame = pd.DataFrame(
        [
            ("2020-06-30", "US", 10.0, False),
            ("2020-06-30", "US", 30.0, True),
            ("2020-06-30", "GB", 10.0, False),
            ("2020-07-31", "US", 10.0, False),
        ],
        columns=["date", "country", "tenor_years", "closed"],
    )
    frame["date"] = pd.to_datetime(frame["date"])
    u = returns.universe_rows(frame)
    assert list(u.columns) == returns.UNIVERSE_COLUMNS
    june = u[u["date"] == "2020-06-30"]
    assert set(june["n_total_all_countries"]) == {2}  # the closed 30y is not in the universe
    assert june[june["country"] == "US"].iloc[0]["tenors"] == "10"
    assert u[u["date"] == "2020-07-31"].iloc[0]["n_total_all_countries"] == 1

    r = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-06-30", "2020-07-31"]),
            "country": "US",
            "tenor_years": 10.0,
            "closed": False,
            "r_local": [0.01, 0.02],
            "coupon": [0.06, 0.06],
        }
    )
    c = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-06-30", "2020-07-31"]),
            "country": "US",
            "tenor_years": 10.0,
            "yield": [0.06, 0.06],
            "carry": [0.02, 0.02],
            "rolldown": [0.001, 0.001],
            "r_short": [0.04, 0.04],
        }
    )
    ident = returns.identity_rows(r, c, _cfg())
    full = ident[ident["window"] == "full"].iloc[0]
    assert full["n_months"] == 2
    assert full["r_local_ann"] == pytest.approx(0.015 * 12)
    assert full["yield_rolldown_ann"] == pytest.approx((0.06 / 12 + 0.001) * 12)
    assert full["carry_rolldown_ann"] == pytest.approx((0.02 / 12 + 0.001) * 12)
    assert full["price_return_ann"] == pytest.approx((0.015 - 0.005) * 12)
    # the two readings differ by exactly the funding rate
    assert full["carry_rolldown_ann"] == pytest.approx(full["yield_rolldown_ann"] - 0.04)
    assert bool(full["flagged"]) is True  # 0.18 - 0.072 is far beyond 50 bp


# ------------------------------------------------------------- fixtures


def _panel(c: Curve) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": c.date,
            "country": c.country,
            "tenor_years": c.tenors,
            "yield": c.yields,
            "curve_type": "zero",
            "source": "test",
            "interpolated": False,
            "standard": [t in set(STANDARD) for t in c.tenors],
            "bootstrapped": False,
        }
    )


def _cfg() -> dict:
    return {
        "tenors": STANDARD,
        "coupon_frequency": {"US": 2, "GB": 2},
        "hedge": {"funding_rate": "policy", "funding_rate_robustness": "interbank_3m"},
        "sample": {"strategy_start": "1997-08-31"},
        "checks": {"identity_gap_flag_bp_per_year": 50},
    }
