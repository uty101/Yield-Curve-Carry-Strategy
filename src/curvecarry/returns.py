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
and is diagnostic only; ``gap_bp`` is the difference and its whole distribution
is in ``data/checks/return_approx_gap.csv``. ``dy`` is the change in the bond's
**own yield to maturity** (issue #17 answer 1), so ``gap_bp`` measures Taylor
truncation plus the known ``dy/12`` ageing term - about 4 bp for a 50 bp move -
and nothing else.

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
APPROX_WORST_COLUMNS = ["date", "country", "tenor_years", "coupon", "duration", "dy", "gap_bp"]
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
    "mean_duration",
    "mean_dy_ann",
    "trend_bp",
    "trend_residual_bp",
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
    """One bucket's month: full repricing, the approximation, and whether it closed.

    The pair is ``(values, closed)``. A closed bucket keeps its coupon,
    duration and convexity - they are known at ``t`` - and has
    ``r_local = 0.0`` with the rest NaN.

    ``dy`` is **the change in the bond's own yield to maturity**,
    ``yield_from_price(P, n - 1/12, c, freq) - c`` (issue #17 answer 1). It is
    not the par yield at the aged tenor, which is what PLAN.md 4.2 said before
    the ruling: that quantity is not comparable to the par yield at ``n``,
    because the aged bond's first coupon is a five-month stub while it still
    pays a full half-coupon, so its par rate is tens of basis points lower **on
    a curve that has not moved at all**, and the approximation came out biased
    by about 30 bp a month at every tenor.

    ``gap_bp`` is therefore pure Taylor truncation plus one known term: ``(D, C)``
    are taken at ``t`` on the un-aged bond, so a month of ageing leaves about
    ``dy / 12`` of error - roughly 4 bp for a 50 bp move - whatever ``dy`` is.
    That is the floor of the tolerance, not a fault (PLAN.md 4.2).
    """
    c, d, cx = bondmath.par_bond_risk(curve_t, tenor, freq)
    base = {"coupon": c, "duration": d, "convexity": cx}
    aged = tenor - DT
    nan_cols = ["dy", "r_local_full", "r_local_approx", "gap_bp"]
    try:
        price = bondmath.price_from_zero(curve_next, aged, c, freq)
    except ValueError:
        return ({**base, **dict.fromkeys(nan_cols, np.nan), "r_local": 0.0}, True)
    full = price / 100.0 - 1.0
    dy = bondmath.yield_from_price(price, aged, c, freq) - c
    approx = taylor(c, d, cx, dy)
    return (
        {
            **base,
            "dy": dy,
            "r_local_full": full,
            "r_local_approx": approx,
            "gap_bp": (full - approx) * 1e4,
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


def approx_gap_rows(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(distribution by tenor, the N_WORST_GAPS largest |gap_bp| rows)``."""
    g = returns[~returns["closed"] & returns["gap_bp"].notna()]
    rows = []
    for tenor, h in g.groupby("tenor_years", sort=True):
        x = h["gap_bp"].to_numpy()
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
    worst = g.reindex(g["gap_bp"].abs().sort_values(ascending=False).index)
    return dist, worst.head(N_WORST_GAPS)[APPROX_WORST_COLUMNS].reset_index(drop=True)


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


def constant_maturity_dy(carry: pd.DataFrame) -> pd.DataFrame:
    """``carry`` with ``dy_cm``: next month's zero yield at the **same** tenor, minus this one's.

    The constant-maturity yield change, which is what a trend in yields means
    for a bucket that is rebought at tenor ``n`` every month. The last month of
    each bucket has no successor and gets NaN.
    """
    d = carry.sort_values(["country", "tenor_years", "date"]).copy()
    key = ["country", "tenor_years"]
    nxt = d.groupby(key, sort=False)["date"].shift(-1)
    d["dy_cm"] = d.groupby(key, sort=False)["yield"].shift(-1) - d["yield"]
    d.loc[nxt != d["date"].map(next_month), "dy_cm"] = np.nan
    return d


def identity_rows(returns: pd.DataFrame, carry: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """The long-run identity, per country, tenor and window.

    ``yield_rolldown_ann`` is ``12 x mean(yield/12 + rolldown)`` - the expected
    **total** return of carrying and rolling down. ``carry_rolldown_ann`` is the
    same net of funding, ``12 x mean(carry/12 + rolldown)``, using this
    project's ``carry = y_n - r_short``. The two differ by ``r_short_ann`` by
    construction; ``flagged`` is set on the first (see PLAN.md 4.2).

    **The trend columns** (session-4 fix round, issue #18): if ``diff_bp`` is
    the sample's yield trend and nothing else, then it should equal minus the
    bucket's duration times the mean annual change in that tenor's yield.
    ``mean_dy_ann`` is ``12 x mean(dy_cm)`` at constant maturity,
    ``trend_bp = -mean_duration x mean_dy_ann x 1e4``, and
    ``trend_residual_bp = diff_bp - trend_bp`` is what the trend does not
    explain. A first-order comparison, so a residual of a few bp on a long
    bucket is the convexity and the cross term, not a discrepancy.
    """
    flag_bp = float(cfg["checks"]["identity_gap_flag_bp_per_year"])
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    key = ["country", "tenor_years", "date"]
    df = returns[~returns["closed"]].merge(
        constant_maturity_dy(carry)[
            ["country", "tenor_years", "date", "yield", "carry", "rolldown", "r_short", "dy_cm"]
        ],
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
            mean_d = float(g["duration"].mean())
            dy_ann = _ann(g["dy_cm"].dropna()) if g["dy_cm"].notna().any() else np.nan
            trend_bp = -mean_d * dy_ann * 1e4
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
                    "mean_duration": mean_d,
                    "mean_dy_ann": dy_ann,
                    "trend_bp": trend_bp,
                    "trend_residual_bp": diff_bp - trend_bp,
                }
            )
    return pd.DataFrame(rows, columns=IDENTITY_COLUMNS)


# -------------------------------------- step 4.3: hedged and unhedged returns


FX_COLUMNS = [
    "r_short_base",
    "fx_return",
    "r_hedged",
    "r_unhedged",
    "hedge_carry",
    "r_hedged_interbank_3m",
    "r_unhedged_interbank_3m",
    "hedge_carry_interbank_3m",
]
COVERAGE_COLUMNS = [
    "date",
    "country",
    "n_buckets",
    "has_r_local",
    "has_r_hedged",
    "has_r_unhedged",
    "reason",
    "funding_kind",
    "funding_source",
    "funding_area",
    "fx_currency",
]
NO_FX = "no_fx"


def base_country(cfg: dict) -> str:
    """The country whose currency is ``config.base_currency`` (the US)."""
    for country, currency in cfg["currency"].items():
        if currency == cfg["base_currency"]:
            return country
    raise KeyError(f"no country has currency {cfg['base_currency']!r}")


def fx_log_change(fx: pd.DataFrame, currency: str) -> dict[pd.Timestamp, float]:
    """``date t -> ln(S_{t+1}) - ln(S_t)`` for one currency; ``S`` is base per foreign."""
    g = fx[fx["currency"] == currency].sort_values("date")
    spot = dict(zip(g["date"], g["spot"], strict=True))
    out = {}
    for date, s in spot.items():
        nxt = spot.get(next_month(date))
        if nxt is not None and s > 0 and nxt > 0:
            out[pd.Timestamp(date)] = float(np.log(nxt) - np.log(s))
    return out


def add_fx(returns: pd.DataFrame, funding: pd.DataFrame, fx: pd.DataFrame, cfg: dict):
    """Step 4.3: the hedged and unhedged excess returns, and the no-FX log rows.

    ``r_hedged = r_excess_local``: under covered interest parity the FX-hedged
    excess return in the base currency **is** the local excess return, so no FX
    series enters it (``decisions/basis.md``). ``r_unhedged`` converts the local
    return at spot and finances it in the base currency.
    """
    home = base_country(cfg)
    out = returns.copy()
    changes = {c: fx_log_change(fx, cfg["currency"][c]) for c in out["country"].unique()}
    out["fx_return"] = [
        0.0 if c == home else changes[c].get(pd.Timestamp(d), np.nan)
        for c, d in zip(out["country"], out["date"], strict=True)
    ]
    home_rows = out["country"] == home
    for kind, suffix in (
        (cfg["hedge"]["funding_rate"], ""),
        (cfg["hedge"]["funding_rate_robustness"], "_interbank_3m"),
    ):
        rates = carry_mod.funding_lookup(funding, kind)
        base_rate = out["date"].map(lambda d, r=rates: r.get((home, pd.Timestamp(d)), np.nan))
        if suffix == "":
            out["r_short_base"] = base_rate
        out[f"r_hedged{suffix}"] = out[f"r_excess_local{suffix}"]
        out[f"r_unhedged{suffix}"] = out["r_local"] + out["fx_return"] - base_rate / 12.0
        out[f"hedge_carry{suffix}"] = (base_rate - out[f"r_short_local{suffix}"]) / 12.0
        out.loc[home_rows, f"hedge_carry{suffix}"] = 0.0
        out.loc[home_rows, f"r_unhedged{suffix}"] = out.loc[home_rows, f"r_excess_local{suffix}"]
    no_fx = out[out["r_unhedged"].isna() & ~out["closed"]].copy()
    no_fx["reason"] = NO_FX
    return out, no_fx[CLOSED_COLUMNS].reset_index(drop=True)


def funding_area(country: str, date: pd.Timestamp, cfg: dict) -> str:
    """The BIS area the funding rate came from: the legacy euro code before the splice."""
    if cfg["currency"][country] != "EUR":
        return country
    before = pd.Timestamp(date) < pd.Timestamp(cfg["hedge"]["eur_splice"])
    return cfg["hedge"]["eur_legacy"][country] if before else "XM"


def coverage_rows(returns: pd.DataFrame, funding: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Amendment 3: per country and month, which of the three returns exist and why not."""
    kind = cfg["hedge"]["funding_rate"]
    src = {
        (c, pd.Timestamp(d)): s
        for c, d, s in zip(
            *[funding[funding["kind"] == kind][k] for k in ("country", "date", "source")],
            strict=True,
        )
    }
    home = base_country(cfg)
    rows = []
    for (date, country), g in returns.groupby(["date", "country"], sort=True):
        live = g[~g["closed"]]
        has_local = bool(len(live))
        has_hedged = bool(live["r_hedged"].notna().any())
        has_unhedged = bool(live["r_unhedged"].notna().any())
        if not has_local:
            reason = "no_bucket"
        elif not has_hedged:
            reason = "no_funding_local"
        elif not has_unhedged:
            reason = NO_FX if live["fx_return"].isna().all() else "no_funding_base"
        else:
            reason = ""
        rows.append(
            {
                "date": date,
                "country": country,
                "n_buckets": int(len(live)),
                "has_r_local": has_local,
                "has_r_hedged": has_hedged,
                "has_r_unhedged": has_unhedged,
                "reason": reason,
                "funding_kind": kind,
                "funding_source": src.get((country, pd.Timestamp(date)), ""),
                "funding_area": funding_area(country, date, cfg),
                "fx_currency": "" if country == home else cfg["currency"][country],
            }
        )
    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def build_fx(cfg: dict, processed: Path | None = None, interim: Path | None = None):
    """CLI ``build --step fx``: the 4.3 columns on ``returns.parquet`` and its two checks."""
    from curvecarry.loaders import base

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    i = Path(interim) if interim is not None else base.INTERIM
    out = pd.read_parquet(p / "returns.parquet")
    funding = pd.read_parquet(i / "funding.parquet")
    fx = pd.read_parquet(i / "fx.parquet")
    out, no_fx = add_fx(out, funding, fx, cfg)
    out.to_parquet(p / "returns.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    pd.concat([closed_rows(out), no_fx], ignore_index=True).sort_values(
        ["country", "date", "tenor_years"]
    ).to_csv(checks.CLOSED_BUCKETS, index=False, lineterminator="\n")
    coverage_rows(out, funding, cfg).to_csv(
        checks.RETURN_COVERAGE, index=False, lineterminator="\n"
    )
    return out


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
    dist, worst = approx_gap_rows(out)
    with open(checks.RETURN_APPROX_GAP, "w", encoding="utf-8", newline="") as fh:
        dist.to_csv(fh, index=False, lineterminator="\n")
        fh.write(f"\n# the {N_WORST_GAPS} largest |gap_bp| rows\n")
        worst.to_csv(fh, index=False, lineterminator="\n")
    universe_rows(out).to_csv(checks.UNIVERSE_BY_MONTH, index=False, lineterminator="\n")
    carry = pd.read_parquet(p / "carry.parquet")
    identity_rows(out, carry, cfg).to_csv(checks.RETURN_IDENTITY, index=False, lineterminator="\n")
    return out
