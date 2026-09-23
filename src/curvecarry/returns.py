"""Step 4.2: the return engine - one month's total return of every bucket.

A bucket is a **constant-maturity par bond**. At month end ``t`` we buy the par
bond at tenor ``n`` off that month's zero curve: its coupon is
``par_yield_from_zero(curve_t, n, freq)`` and its price is 100 by construction.
One month later the same bond has tenor ``n - 1/12``; its dirty price off the
next month's zero curve is ``price_from_zero(curve_{t+1}, n - 1/12, c, freq)``
and ``r_local_full = P/100 - 1``. No coupon is paid inside one month for
``freq <= 2``, and the accrued coupon is inside the dirty price, so nothing is
reinvested and nothing is lost.

``r_local = r_local_full``. The **approximation**
``r_local_approx = c/12 - D dy + C dy^2 / 2`` (brief 6.3) is computed beside it
from curve yields alone and is diagnostic only; ``gap_bp`` is the difference
and its whole distribution is in ``data/checks/return_approx_gap.csv``.

Every later step works in **excess** returns:
``r_excess_local = r_local - r_short_local/12``, the bucket's return over its
own financing, with ``r_short_local`` read from ``funding.parquet`` at the
bucket's own country and at date ``t`` - not ``t+1``
(``decisions/short_anchor.md``). The ``interbank_3m`` columns are the same
quantities on the robustness funding rate and are NaN where that series does
not reach.

A bucket that exists at ``t`` but whose aged tenor cannot be priced at ``t+1``
is **closed at its last available price**: ``r_local = 0.0``, ``closed = True``,
and one row in ``data/checks/closed_buckets.csv``. It is never dropped
silently and never carried at a stale price.

Two check files the session-4 amendments add:

- ``data/checks/universe_by_month.csv`` (amendment 1) - the tenors with a
  computable return, per country and month, and the total across countries.
- ``data/checks/return_identity.csv`` (amendment 2) - per country and tenor,
  the annualised mean of ``r_local`` against the annualised mean of the
  expected return from carrying and rolling down, over the full sample and
  over the strategy window. A check, not a gate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import bondmath, checks, harmonise
from curvecarry import carry as carry_mod
from curvecarry.curves import Curve

DT = 1.0 / 12.0

RETURN_COLUMNS = [
    "date",
    "country",
    "tenor_years",
    "coupon",
    "duration",
    "convexity",
    "dy",
    "r_local_full",
    "r_local_approx",
    "gap_bp",
    "dy_ytm",
    "r_local_approx_ytm",
    "gap_bp_ytm",
    "dy_curve",
    "r_local_approx_curve",
    "gap_bp_curve",
    "r_local",
    "r_short_local",
    "r_excess_local",
    "r_short_local_interbank_3m",
    "r_excess_local_interbank_3m",
    "closed",
]
CLOSED_COLUMNS = ["date", "country", "tenor_years", "reason"]
APPROX_GAP_COLUMNS = [
    "tenor_years",
    "n",
    "mean_bp",
    "std_bp",
    "p01",
    "p05",
    "p50",
    "p95",
    "p99",
    "max_abs_bp",
]
APPROX_WORST_COLUMNS = ["date", "country", "tenor_years", "dy", "gap_bp"]
# the gap column of each reading of the plan's dy, and the dy column that produced it
DY_OF = {"gap_bp": "dy", "gap_bp_ytm": "dy_ytm", "gap_bp_curve": "dy_curve"}
GAP_TITLE = {
    "gap_bp": "the plan's dy: par yield at the aged tenor minus the coupon",
    "gap_bp_ytm": "candidate ytm: the change in the bond's own yield to maturity",
    "gap_bp_curve": "candidate curve: the par move at the same tenor, plus the 4.1 rolldown",
}
UNIVERSE_COLUMNS = ["date", "country", "n_tenors", "tenors", "n_total_all_countries"]
IDENTITY_COLUMNS = [
    "country",
    "tenor_years",
    "window",
    "n_months",
    "r_local_ann",
    "yield_rolldown_ann",
    "carry_rolldown_ann",
    "price_return_ann",
    "r_short_ann",
    "diff_bp",
    "diff_carry_bp",
    "flagged",
]
CLOSED_REASON = "aged tenor beyond next curve"
N_WORST_GAPS = 20  # the 20 largest |gap_bp| rows go beside the distribution


def next_month(date: pd.Timestamp) -> pd.Timestamp:
    """The next calendar month end."""
    return pd.Timestamp(date) + pd.offsets.MonthEnd(1)


def taylor(c: float, d: float, cx: float, dy: float) -> float:
    """``c/12 - D dy + C dy^2 / 2``: the duration-convexity return approximation."""
    return c / 12.0 - d * dy + 0.5 * cx * dy * dy


def bucket_return(
    curve_t: Curve, curve_next: Curve, tenor: float, freq: int
) -> tuple[dict[str, float], bool]:
    """One bucket's month: full repricing, the three approximations, and whether it closed.

    The pair is ``(values, closed)``. A closed bucket keeps its coupon,
    duration and convexity - they are known at ``t`` - and has
    ``r_local = 0.0`` with the rest NaN.

    ``r_local_approx`` and ``gap_bp`` are **the plan's formula as written**:
    ``dy = par_yield_from_zero(curve_next, n - 1/12, freq) - c``. That formula
    is biased (see ``PLAN.md`` 4.2 and the session-4 decision issue): the par
    yield at ``n - 1/12`` is not comparable to the par yield at ``n``, because
    the aged bond's first coupon is a five-month stub while it still pays a
    full half-coupon, so its par rate is tens of basis points lower **on a
    curve that has not moved at all**. The two candidate repairs are computed
    beside it and are what the decision issue asks the owner to choose between:

    - ``*_ytm``: ``dy`` is the change in the **bond's own yield to maturity**,
      ``yield_from_price(P, n - 1/12, c, freq) - c``. Pure Taylor truncation,
      but it reads the price ``P`` and so is not "from curve yields only".
    - ``*_curve``: ``dy`` is the curve's move at the **same** tenor,
      ``par_yield_from_zero(curve_next, n, freq) - c``, with the rolldown put
      back as ``D (z(n) - z(n - 1/12))`` exactly as step 4.1 computes it. Curve
      yields only, and it is the decomposition step 6.1 is built on.
    """
    c, d, cx = bondmath.par_bond_risk(curve_t, tenor, freq)
    base = {"coupon": c, "duration": d, "convexity": cx}
    aged = tenor - DT
    nan_cols = [
        "dy",
        "r_local_full",
        "r_local_approx",
        "gap_bp",
        "dy_ytm",
        "r_local_approx_ytm",
        "gap_bp_ytm",
        "dy_curve",
        "r_local_approx_curve",
        "gap_bp_curve",
    ]
    try:
        price = bondmath.price_from_zero(curve_next, aged, c, freq)
        y_next = bondmath.par_yield_from_zero(curve_next, aged, freq)
    except ValueError:
        return ({**base, **dict.fromkeys(nan_cols, np.nan), "r_local": 0.0}, True)
    full = price / 100.0 - 1.0

    dy = y_next - c
    dy_ytm = bondmath.yield_from_price(price, aged, c, freq) - c
    try:
        dy_curve = bondmath.par_yield_from_zero(curve_next, tenor, freq) - c
    except ValueError:
        dy_curve = np.nan
    roll = (float(curve_t.at(tenor)) - float(curve_t.at(aged))) * d
    approx_curve = taylor(c, d, cx, dy_curve) + roll
    return (
        {
            **base,
            "dy": dy,
            "r_local_full": full,
            "r_local_approx": taylor(c, d, cx, dy),
            "gap_bp": (full - taylor(c, d, cx, dy)) * 1e4,
            "dy_ytm": dy_ytm,
            "r_local_approx_ytm": taylor(c, d, cx, dy_ytm),
            "gap_bp_ytm": (full - taylor(c, d, cx, dy_ytm)) * 1e4,
            "dy_curve": dy_curve,
            "r_local_approx_curve": approx_curve,
            "gap_bp_curve": (full - approx_curve) * 1e4,
            "r_local": full,
        },
        False,
    )


def build_returns(zero: pd.DataFrame, funding: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``returns.parquet`` from the zero panel and the funding table."""
    policy = carry_mod.funding_lookup(funding, cfg["hedge"]["funding_rate"])
    robust = carry_mod.funding_lookup(funding, cfg["hedge"]["funding_rate_robustness"])
    tenors = [float(t) for t in cfg["tenors"]]
    std = zero[zero["standard"] & zero["tenor_years"].isin(tenors)]
    rows: list[dict] = []
    for country, g in std.groupby("country", sort=True):
        freq = int(cfg["coupon_frequency"][country])
        by_date = dict(tuple(zero[zero["country"] == country].groupby("date", sort=False)))
        curves = {d: Curve.from_panel(m, country, d) for d, m in by_date.items()}
        for date, m in g.groupby("date", sort=True):
            nxt = curves.get(next_month(date))
            if nxt is None:
                continue
            r_short = policy.get((country, pd.Timestamp(date)), np.nan)
            r_ib = robust.get((country, pd.Timestamp(date)), np.nan)
            for tenor in sorted(float(t) for t in m["tenor_years"]):
                vals, closed = bucket_return(curves[date], nxt, tenor, freq)
                rows.append(
                    {
                        "date": date,
                        "country": country,
                        "tenor_years": tenor,
                        **vals,
                        "r_short_local": r_short,
                        "r_excess_local": vals["r_local"] - r_short / 12.0,
                        "r_short_local_interbank_3m": r_ib,
                        "r_excess_local_interbank_3m": vals["r_local"] - r_ib / 12.0,
                        "closed": closed,
                    }
                )
    out = pd.DataFrame(rows, columns=RETURN_COLUMNS)
    return out.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)


def closed_rows(returns: pd.DataFrame, reason: str = CLOSED_REASON) -> pd.DataFrame:
    """``closed_buckets.csv`` rows for the buckets 4.2 closed."""
    g = returns[returns["closed"]].copy()
    g["reason"] = reason
    return g[CLOSED_COLUMNS].reset_index(drop=True)


def approx_gap_rows(
    returns: pd.DataFrame, column: str = "gap_bp"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(distribution by tenor, the N_WORST_GAPS largest |column| rows)``."""
    g = returns[~returns["closed"] & returns[column].notna()]
    rows = []
    for tenor, h in g.groupby("tenor_years", sort=True):
        x = h[column].to_numpy()
        rows.append(
            {
                "tenor_years": float(tenor),
                "n": int(x.size),
                "mean_bp": float(x.mean()),
                "std_bp": float(x.std(ddof=1)) if x.size > 1 else 0.0,
                "p01": float(np.percentile(x, 1)),
                "p05": float(np.percentile(x, 5)),
                "p50": float(np.percentile(x, 50)),
                "p95": float(np.percentile(x, 95)),
                "p99": float(np.percentile(x, 99)),
                "max_abs_bp": float(np.abs(x).max()),
            }
        )
    dist = pd.DataFrame(rows, columns=APPROX_GAP_COLUMNS)
    worst = g.reindex(g[column].abs().sort_values(ascending=False).index)
    cols = ["date", "country", "tenor_years", DY_OF[column], column]
    return dist, worst.head(N_WORST_GAPS)[cols].reset_index(drop=True)


# ------------------------------------------- session-4 amendment 1: universe


def universe_rows(returns: pd.DataFrame) -> pd.DataFrame:
    """Per month and country: the tenors with a computable return, and the month's total.

    A tenor is computable when it has a standard zero at ``t`` and the curve at
    ``t + 1`` reaches the aged tenor - exactly ``closed == False``.
    """
    live = returns[~returns["closed"]]
    rows = []
    for (date, country), g in live.groupby(["date", "country"], sort=True):
        ts = sorted(float(t) for t in g["tenor_years"])
        rows.append(
            {
                "date": date,
                "country": country,
                "n_tenors": len(ts),
                "tenors": ";".join(f"{t:g}" for t in ts),
                "n_total_all_countries": 0,
            }
        )
    out = pd.DataFrame(rows, columns=UNIVERSE_COLUMNS)
    if out.empty:
        return out
    totals = out.groupby("date")["n_tenors"].sum()
    out["n_total_all_countries"] = out["date"].map(totals).astype(int)
    return out.sort_values(["date", "country"]).reset_index(drop=True)


# ------------------------------------------ session-4 amendment 2: identity


def _ann(x: pd.Series) -> float:
    return float(x.mean() * 12.0)


def identity_rows(returns: pd.DataFrame, carry: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """The long-run identity, per country, tenor and window.

    ``yield_rolldown_ann`` is ``12 x mean(yield/12 + rolldown)`` - the expected
    **total** return of carrying and rolling down. ``carry_rolldown_ann`` is the
    same net of funding, ``12 x mean(carry/12 + rolldown)``, using this
    project's ``carry = y_n - r_short``. The two differ by ``r_short_ann`` by
    construction; ``flagged`` is set on the first (see PLAN.md 4.2).
    """
    flag_bp = float(cfg["checks"]["identity_gap_flag_bp_per_year"])
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    key = ["country", "tenor_years", "date"]
    df = returns[~returns["closed"]].merge(
        carry[["country", "tenor_years", "date", "yield", "carry", "rolldown", "r_short"]],
        on=key,
        how="inner",
    )
    df["yield_roll"] = df["yield"] / 12.0 + df["rolldown"]
    df["carry_roll"] = df["carry"] / 12.0 + df["rolldown"]
    df["price_return"] = df["r_local"] - df["coupon"] / 12.0
    rows = []
    for window, sub in (("full", df), ("strategy", df[df["date"] >= start])):
        for (country, tenor), g in sub.groupby(["country", "tenor_years"], sort=True):
            if g.empty:
                continue
            r_local_ann, yr_ann = _ann(g["r_local"]), _ann(g["yield_roll"])
            diff_bp = (r_local_ann - yr_ann) * 1e4
            cr_ann = _ann(g["carry_roll"])
            rows.append(
                {
                    "country": country,
                    "tenor_years": float(tenor),
                    "window": window,
                    "n_months": len(g),
                    "r_local_ann": r_local_ann,
                    "yield_rolldown_ann": yr_ann,
                    "carry_rolldown_ann": cr_ann,
                    "price_return_ann": _ann(g["price_return"]),
                    "r_short_ann": float(g["r_short"].mean()),
                    "diff_bp": diff_bp,
                    "diff_carry_bp": (r_local_ann - cr_ann) * 1e4,
                    "flagged": bool(abs(diff_bp) > flag_bp),
                }
            )
    return pd.DataFrame(rows, columns=IDENTITY_COLUMNS)


def build(cfg: dict, processed: Path | None = None, interim: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step returns``: ``returns.parquet`` and the four check files."""
    from curvecarry.loaders import base

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    i = Path(interim) if interim is not None else base.INTERIM
    zero = pd.read_parquet(p / "curves_zero.parquet")
    funding = pd.read_parquet(i / "funding.parquet")
    out = build_returns(zero, funding, cfg)
    p.mkdir(parents=True, exist_ok=True)
    out.to_parquet(p / "returns.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    closed_rows(out).to_csv(checks.CLOSED_BUCKETS, index=False, lineterminator="\n")
    with open(checks.RETURN_APPROX_GAP, "w", encoding="utf-8", newline="") as fh:
        for i, column in enumerate(DY_OF):
            dist, worst = approx_gap_rows(out, column)
            fh.write(f"{'' if i == 0 else chr(10)}# {column} - {GAP_TITLE[column]}\n")
            dist.to_csv(fh, index=False, lineterminator="\n")
            fh.write(f"\n# the {N_WORST_GAPS} largest |{column}| rows\n")
            worst.to_csv(fh, index=False, lineterminator="\n")
    universe_rows(out).to_csv(checks.UNIVERSE_BY_MONTH, index=False, lineterminator="\n")
    carry = pd.read_parquet(p / "carry.parquet")
    identity_rows(out, carry, cfg).to_csv(checks.RETURN_IDENTITY, index=False, lineterminator="\n")
    return out
