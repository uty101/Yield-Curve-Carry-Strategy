"""Step 2.1: bond maths on a zero curve.

Every function that takes a ``Curve`` asserts ``curve.curve_type == "zero"``
(rule 3: ``par`` and ``zero`` are never mixed in one calculation). Zero yields
are annually compounded decimals, so ``DF(t) = (1 + z(t))^(-t)``; yields to
maturity, durations and convexities are quoted at the bond's own coupon
frequency ``f`` (``decisions/compounding.md``).

``Curve.at`` supplies the yield at each cashflow date: interpolated between
observed tenors, flat below the shortest observed tenor
(``config.short_end = "flat"``), NaN above the longest (rule 13). A seasoned
bond's short stub therefore always prices; a bond maturing beyond the longest
observed tenor does not, and ``price_from_zero`` raises ``ValueError`` rather
than inventing a discount factor.

``par_bond_risk`` is **the one duration function** in the project: steps 4.1,
4.2, 5.1, 5.2 and 6.1 call it and nothing else computes a duration.

Amendment 1 of the session-2 instructions (``instructions/session-2.md``)
adds ``par_reprice`` and ``write_par_reprice``: for every US, JP and FR month
and every observed par node, the observed par yield against
``par_yield_from_zero`` off the bootstrapped zero curve of the same month.
The bootstrap is exactly invertible at a coupon-grid node, so the difference
is float noise; the check is what proves it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from curvecarry import checks
from curvecarry.curves import Curve

YTM_BRACKET = (-0.05, 1.0)
YTM_XTOL = 1e-12
REPRICE_COUNTRIES = ("US", "JP", "FR")
REPRICE_COLUMNS = [
    "country",
    "date",
    "tenor_years",
    "par_observed",
    "par_from_zero",
    "diff_bp",
    "status",
]


def _assert_zero(curve: Curve) -> None:
    assert curve.curve_type == "zero", f"needs a zero curve, got {curve.curve_type!r}"


def _curve_yields(curve: Curve, times: np.ndarray) -> np.ndarray:
    """``curve.at(times)``, raising if any cashflow falls above the longest observed tenor."""
    z = np.asarray(curve.at(times), dtype="float64")
    if not np.isfinite(z).all():
        bad = times[~np.isfinite(z)]
        raise ValueError(
            f"{curve.country} {curve.date.date()}: no zero yield at {bad.tolist()} "
            f"(longest observed tenor {curve.tenors[-1]})"
        )
    return z


def discount_factor(z: float | np.ndarray, t: float | np.ndarray) -> float | np.ndarray:
    """``(1 + z)^(-t)``: annual compounding, the convention of every zero curve here."""
    return (1.0 + np.asarray(z, dtype="float64")) ** (-np.asarray(t, dtype="float64"))


def cashflow_times(tenor: float, freq: int) -> np.ndarray:
    """Coupon dates of a bond maturing at ``tenor``, counted back from maturity.

    ``tenor - k/freq`` for ``k = n-1 ... 0`` with ``n = ceil(tenor * freq - 1e-9)``;
    ascending, all strictly positive, the last one exactly ``tenor``. For a
    seasoned bond (``tenor`` not a multiple of ``1/freq``) the first entry is
    the short stub.
    """
    assert freq in (1, 2, 4, 12), f"coupon frequency {freq}"
    assert tenor > 0, f"tenor must be positive, got {tenor}"
    n = int(np.ceil(tenor * freq - 1e-9))
    times = tenor - np.arange(n - 1, -1, -1) / float(freq)
    assert (times > 0).all(), f"non-positive cashflow time for tenor {tenor}, freq {freq}"
    return times


def price_from_zero(curve: Curve, tenor: float, coupon: float, freq: int) -> float:
    """Dirty price per 100 of a ``coupon`` bond maturing at ``tenor``, off the zero curve.

    ``sum (100*coupon/freq)*DF(t_j) + 100*DF(T)``. Raises ``ValueError`` if the
    curve has no yield at some cashflow date (above the longest observed tenor).
    """
    _assert_zero(curve)
    times = cashflow_times(tenor, freq)
    dfs = discount_factor(_curve_yields(curve, times), times)
    return float(100.0 * (coupon / freq) * dfs.sum() + 100.0 * dfs[-1])


def par_yield_from_zero(curve: Curve, tenor: float, freq: int) -> float:
    """Coupon that prices the ``tenor`` bond at 100: ``freq*(1 - DF(T)) / sum DF(t_j)``."""
    _assert_zero(curve)
    times = cashflow_times(tenor, freq)
    dfs = discount_factor(_curve_yields(curve, times), times)
    return float(freq * (1.0 - dfs[-1]) / dfs.sum())


def price_from_yield(ytm: float, tenor: float, coupon: float, freq: int) -> float:
    """Dirty price per 100 at yield ``ytm``, compounded ``freq`` times a year."""
    times = cashflow_times(tenor, freq)
    v = (1.0 + ytm / freq) ** (-freq * times)
    return float(100.0 * (coupon / freq) * v.sum() + 100.0 * v[-1])


def yield_from_price(price: float, tenor: float, coupon: float, freq: int) -> float:
    """Yield to maturity (``freq``-compounded) of a bond at ``price`` per 100, by brentq."""
    return float(
        brentq(
            lambda y: price_from_yield(y, tenor, coupon, freq) - price,
            YTM_BRACKET[0],
            YTM_BRACKET[1],
            xtol=YTM_XTOL,
        )
    )


def _pv_terms(ytm: float, tenor: float, coupon: float, freq: int) -> tuple[np.ndarray, np.ndarray]:
    """``(cashflow times, present values)`` per 100 face at yield ``ytm``."""
    times = cashflow_times(tenor, freq)
    v = (1.0 + ytm / freq) ** (-freq * times)
    cf = np.full(times.shape, 100.0 * coupon / freq)
    cf[-1] += 100.0
    return times, cf * v


def modified_duration(ytm: float, tenor: float, coupon: float, freq: int) -> float:
    """``Mac / (1 + ytm/freq)`` with ``Mac = sum t_j CF_j v_j / P``, in years."""
    times, pv = _pv_terms(ytm, tenor, coupon, freq)
    mac = float((times * pv).sum() / pv.sum())
    return mac / (1.0 + ytm / freq)


def convexity(ytm: float, tenor: float, coupon: float, freq: int) -> float:
    """``sum t_j (t_j + 1/freq) CF_j v_j / (P (1 + ytm/freq)^2)``, in years squared."""
    times, pv = _pv_terms(ytm, tenor, coupon, freq)
    num = float((times * (times + 1.0 / freq) * pv).sum())
    return num / (pv.sum() * (1.0 + ytm / freq) ** 2)


def par_bond_risk(curve: Curve, tenor: float, freq: int) -> tuple[float, float, float]:
    """``(coupon, modified duration, convexity)`` of the par bond at ``tenor`` off ``curve``.

    The one duration function (PLAN.md 2.1): the coupon is
    ``par_yield_from_zero``, and ``D`` and ``C`` are evaluated at ``ytm = coupon``
    because a par bond's yield is its coupon.
    """
    _assert_zero(curve)
    c = par_yield_from_zero(curve, tenor, freq)
    return c, modified_duration(c, tenor, coupon=c, freq=freq), convexity(c, tenor, c, freq)


def par_reprice(panel: pd.DataFrame, zero: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Amendment 1: observed par yield vs ``par_yield_from_zero`` at every observed par node.

    One row per (country, date, observed par tenor) for the bootstrapped
    countries in ``REPRICE_COUNTRIES``. ``status``:

    - ``ok`` - the node is on the coupon grid and inside the zero curve;
      ``diff_bp`` is the repricing error and is expected to be float noise.
    - ``money_market`` - an observed par node below the first coupon date
      (the US 0.25 bill), whose zero was set from the simple-interest
      identity ``P = 1/(1 + c*t)`` and not from the coupon bootstrap, so
      ``par_yield_from_zero`` (a one-coupon stub) is a different quantity.
    - ``dropped`` - the node is beyond the zero curve that month (the
      node-gap or zero-vs-par rule of 1.9 removed it); no reprice.
    """
    zc_all = zero[zero["country"].isin(REPRICE_COUNTRIES)]
    par = panel[(panel["curve_type"] == "par") & panel["country"].isin(REPRICE_COUNTRIES)]
    par = par[~par["interpolated"].astype(bool)]
    rows: list[tuple] = []
    for country, g in par.groupby("country", sort=True):
        freq = int(cfg["coupon_frequency"][country])
        by_date = dict(tuple(zc_all[zc_all["country"] == country].groupby("date", sort=False)))
        for date, m in g.groupby("date", sort=True):
            zm = by_date.get(date)
            if zm is None or zm.empty:
                continue
            curve = Curve(
                zm["tenor_years"].to_numpy(), zm["yield"].to_numpy(), "zero", country, date
            )
            for tenor, y in zip(m["tenor_years"], m["yield"], strict=True):
                t, obs = float(tenor), float(y)
                if t * freq < 1 - 1e-9:
                    rows.append((country, date, t, obs, np.nan, np.nan, "money_market"))
                    continue
                try:
                    c = par_yield_from_zero(curve, t, freq)
                except ValueError:
                    rows.append((country, date, t, obs, np.nan, np.nan, "dropped"))
                    continue
                rows.append((country, date, t, obs, c, (c - obs) * 1e4, "ok"))
    out = pd.DataFrame(rows, columns=REPRICE_COLUMNS)
    return out.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)


def write_par_reprice(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """Build ``data/checks/par_reprice.csv`` from the processed panels."""
    from curvecarry import harmonise

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    panel = pd.read_parquet(p / "curves.parquet")
    zero = pd.read_parquet(p / "curves_zero.parquet")
    out = par_reprice(panel, zero, cfg)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    out.to_csv(checks.PAR_REPRICE, index=False, lineterminator="\n")
    return out
