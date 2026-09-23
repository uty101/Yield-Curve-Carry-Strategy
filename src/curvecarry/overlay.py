"""Step 5.4: the slope overlay - an expanding-window PC2 z-score, and a 2s10s pair.

**The PCA is per country and expanding** (issue #19, answered 2026-09-23).
For country ``c`` and month ``t`` the fit uses **country ``c``'s own change
rows dated at or before ``t``**, on country ``c``'s own tenor set from 3.1,
with 3.1's sign convention, and produces a score only once there are
``config.pca.pca_min_months`` (60) of them. Never a full-sample loading, and
never the pooled vector: the overlay trades a national 2s10s pair, so ``v2``
has to describe that country's slope, and the pooled set stops at 10 years,
which would drop the long end out of the slope measure for DE, JP, CA and FR.
6.2's volatility control is the step that takes the pooled PC1.

``score_t = (dy_t - mean_{<=t}) @ v2^{(<=t)}``, in basis points, where
``mean_{<=t}`` is the column mean of the same expanding window. Both the
loading and the mean are re-estimated every month from data dated at or
before ``t``, which is what makes the score honest at ``t`` (rule 7) and is
what ``test_score_at_t_unchanged_when_future_appended`` asserts.

**The z-score** is ``(s_t - mean of the last 36 scores) / sd of the last 36``
(``config.pca.pca_z_window``, ddof 1, the window ending at and including
``t``), NaN until 36 scores exist.

**The state machine**, per country, with two armed flags that both start
True:

- ``flat -> steepener`` when ``z < -z_entry`` and ``armed_steep``;
  ``flat -> flattener`` when ``z > +z_entry`` and ``armed_flat``. Entering
  clears that side's flag, so one signal is one trade.
- ``steepener -> flat`` when ``z >= z_exit``; ``flattener -> flat`` when
  ``z <= z_exit``.
- A flag is re-armed when ``z`` crosses ``z_exit`` between two consecutive
  months (a sign change of ``z - z_exit``).
- A NaN ``z`` forces ``flat`` and clears both flags until the next crossing.
  This applies to the **warm-up** too: ``z`` is NaN until 36 scores exist, so
  a country whose first finite ``z`` is already beyond the entry threshold
  does not trade on it and waits for a crossing to arm it. That is the rule
  as PLAN.md 5.4 writes it, and it is the conservative side: an entry on the
  first number a 36-month window ever produces would be an entry on a
  threshold the series has never been tested against
  (``test_warm_up_nans_leave_the_overlay_disarmed_until_z_crosses``).

PC2 is signed positive at ``longest - 2`` years (3.1), so a **positive**
score is the long end selling off relative to the short end - a steepening
month - and a large negative ``z`` is a sharp flattening. The overlay is
therefore a mean-reversion rule: it enters a **steepener after a flattening**
and a **flattener after a steepening**.

**The pair.** In ``steepener``: long ``config.overlay.overlay_tenors[0]``
(2y) at ``wd = +B_o`` and short ``overlay_tenors[1]`` (10y) at ``wd = -B_o``,
``B_o = config.overlay.overlay_duration_budget``; ``flattener`` is the
reverse. ``weight = wd / duration`` with the duration of 4.1 and 4.2 - the
same ``bondmath.par_bond_risk`` output the carry book is sized with. A
country-month missing either leg's duration holds no pair and is counted.
``sum wd = 0`` inside every country by construction, so the overlay book is
duration-neutral on its own and the combined book of 5.5 is neutral because
both of its parts are.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise, pca

STATE_FLAT = "flat"
STATE_STEEP = "steepener"
STATE_FLAT_ENER = "flattener"

SCORE_COLUMNS = ["country", "date", "score", "n_months"]
POSITION_COLUMNS = [
    "date",
    "country",
    "state",
    "z",
    "tenor_years",
    "leg",
    "duration",
    "weight",
    "wd",
]
TRADE_COLUMNS = [
    "country",
    "entry_date",
    "exit_date",
    "direction",
    "entry_z",
    "exit_z",
    "months_held",
    "pnl_bp",
    "cost_bp",
    "pnl_net_bp",
    "still_open",
    "in_sample",
]
COUNTRY_STAT_COLUMNS = [
    "country",
    "trades",
    "months_in_market",
    "months_in_sample",
    "share_in_market",
    "hit_rate",
    "mean_pnl_bp",
    "median_pnl_bp",
    "total_pnl_net_bp",
    "months_armed_not_traded",
    "months_no_score_under_min",
    "months_no_z_short_window",
]
STATE_DETAIL_COLUMNS = [
    "date",
    "z",
    "state",
    "armed_steep",
    "armed_flat",
    "signal_present",
    "blocked",
]
SKIPPED_COLUMNS = ["date", "country", "state", "reason"]

PC2 = 1  # zero-based index of the second component


def expanding_pc2_scores(changes_by_country: dict[str, pd.DataFrame], cfg: dict) -> pd.DataFrame:
    """``country, date, score, n_months`` - the expanding-window PC2 score of each month."""
    minimum = int(cfg["pca"]["pca_min_months"])
    rows = []
    for country in sorted(changes_by_country):
        c = changes_by_country[country].sort_index()
        tenors = np.array(c.columns, dtype="float64")
        x = c.to_numpy(dtype="float64")
        for i, date in enumerate(c.index):
            n = i + 1
            if n < minimum:
                rows.append({"country": country, "date": date, "score": np.nan, "n_months": n})
                continue
            window = x[:n]
            res = pca.pca(window, tenors)
            score = float((window[-1] - res.mean) @ res.loadings[:, PC2])
            rows.append({"country": country, "date": date, "score": score, "n_months": n})
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


def zscore(scores: pd.Series, window: int) -> pd.Series:
    """``(s_t - mean) / sd`` over the ``window`` scores ending at ``t``, ddof 1, NaN until full."""
    s = scores.astype("float64")
    mean = s.rolling(window, min_periods=window).mean()
    sd = s.rolling(window, min_periods=window).std(ddof=1)
    return (s - mean) / sd


def state_detail(z: pd.Series, cfg: dict) -> pd.DataFrame:
    """The state machine month by month, with the two armed flags and why nothing traded.

    ``signal_present`` is a month whose ``|z|`` is beyond ``z_entry``;
    ``blocked`` is such a month that stayed flat anyway because the relevant
    flag was disarmed. Both are recorded so that "the overlay did nothing"
    can be told apart from "the overlay was not allowed to do anything"
    (session-5 fix 1).
    """
    entry = float(cfg["overlay"]["z_entry"])
    exit_level = float(cfg["overlay"]["z_exit"])
    state = STATE_FLAT
    armed_steep = armed_flat = True
    rows = []
    previous = np.nan
    for date, value in z.astype("float64").items():
        if np.isfinite(previous) and np.isfinite(value):
            if np.sign(previous - exit_level) != np.sign(value - exit_level):
                armed_steep = armed_flat = True
        if not np.isfinite(value):
            state = STATE_FLAT
            armed_steep = armed_flat = False
            rows.append((date, value, state, armed_steep, armed_flat, False, False))
            previous = value
            continue
        if state == STATE_STEEP and value >= exit_level:
            state = STATE_FLAT
        elif state == STATE_FLAT_ENER and value <= exit_level:
            state = STATE_FLAT
        signal_present = abs(value) > entry
        blocked = False
        if state == STATE_FLAT:
            if value < -entry and armed_steep:
                state = STATE_STEEP
                armed_steep = False
            elif value > entry and armed_flat:
                state = STATE_FLAT_ENER
                armed_flat = False
            elif signal_present:
                blocked = True
        rows.append((date, value, state, armed_steep, armed_flat, signal_present, blocked))
        previous = value
    return pd.DataFrame(rows, columns=STATE_DETAIL_COLUMNS).set_index("date")


def states(z: pd.Series, cfg: dict) -> pd.Series:
    """The state machine of the module docstring, over one country's z-score series."""
    return state_detail(z, cfg)["state"].rename("state")


def pair_rows(
    date: pd.Timestamp,
    country: str,
    state: str,
    z: float,
    durations: dict[float, float],
    cfg: dict,
) -> list[dict]:
    """The two legs of one country-month, or ``[]`` when the state is flat."""
    if state == STATE_FLAT:
        return []
    short_tenor, long_tenor = (float(t) for t in cfg["overlay"]["overlay_tenors"])
    budget = float(cfg["overlay"]["overlay_duration_budget"])
    sign = 1.0 if state == STATE_STEEP else -1.0
    rows = []
    for tenor, wd in ((short_tenor, sign * budget), (long_tenor, -sign * budget)):
        duration = durations[tenor]
        rows.append(
            {
                "date": date,
                "country": country,
                "state": state,
                "z": z,
                "tenor_years": tenor,
                "leg": "long" if wd > 0 else "short",
                "duration": duration,
                "weight": wd / duration,
                "wd": wd,
            }
        )
    return rows


def _durations(returns: pd.DataFrame, cfg: dict) -> dict[tuple[pd.Timestamp, str, float], float]:
    tenors = {float(t) for t in cfg["overlay"]["overlay_tenors"]}
    r = returns[returns["tenor_years"].isin(tenors)]
    return {
        (d, c, float(t)): float(v)
        for d, c, t, v in zip(r["date"], r["country"], r["tenor_years"], r["duration"], strict=True)
    }


def build_positions(
    scores: pd.DataFrame, returns: pd.DataFrame, cfg: dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``(positions, state detail, skipped)`` from the expanding scores.

    The second frame is one row per country-month - ``z``, the state and the
    armed flags - and is what the trade anatomy of ``trade_anatomy`` is cut
    from. The per-trade file is written after a run, because a trade's PnL
    only exists once the returns have been earned.
    """
    window = int(cfg["pca"]["pca_z_window"])
    overlay_tenors = [float(t) for t in cfg["overlay"]["overlay_tenors"]]
    durations = _durations(returns, cfg)
    positions, details, skipped = [], [], []
    for country, g in scores.groupby("country", sort=True):
        g = g.sort_values("date")
        z = zscore(g.set_index("date")["score"], window)
        detail = state_detail(z, cfg)
        detail.insert(0, "country", country)
        details.append(detail.reset_index())
        for date, s in detail["state"].items():
            value = float(z.loc[date])
            if s == STATE_FLAT:
                continue
            have = {t: durations.get((date, country, t)) for t in overlay_tenors}
            if any(v is None or not np.isfinite(v) for v in have.values()):
                skipped.append(
                    {
                        "date": date,
                        "country": country,
                        "state": s,
                        "reason": "no duration for a leg",
                    }
                )
                continue
            positions.extend(pair_rows(date, country, s, value, have, cfg))
    pos = pd.DataFrame(positions, columns=POSITION_COLUMNS)
    if len(pos):
        pos = pos.sort_values(["date", "country", "tenor_years"]).reset_index(drop=True)
    detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return pos, detail, pd.DataFrame(skipped, columns=SKIPPED_COLUMNS)


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step overlay``: the scores, the positions and the trade log."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    returns = pd.read_parquet(p / "returns.parquet")
    changes = pca.monthly_changes_bp(zero, cfg)
    scores = expanding_pc2_scores(changes, cfg)
    positions, detail, skipped = build_positions(scores, returns, cfg)
    p.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(p / "pc2_expanding.parquet", index=False)
    positions.to_parquet(p / "overlay_positions.parquet", index=False)
    detail.to_parquet(p / "overlay_states.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    skipped.to_csv(checks.OVERLAY_SKIPPED, index=False, lineterminator="\n")
    return positions


# ------------------------------------------------- session-5 fix 1: anatomy

WORST_TRADES = 5  # the worst trades listed in the review


def monthly_pnl_bp(positions: pd.DataFrame) -> pd.Series:
    """``(country, date) -> bp`` the overlay earned that month, gross of costs.

    ``positions`` is a run's ``positions_<variant>.parquet``: the pairs that
    were actually held, with the return each leg earned.
    """
    p = positions.copy()
    p["contribution"] = p["weight"] * p["r"]
    return p.groupby(["country", "date"])["contribution"].sum() * 1e4


def trade_anatomy(
    detail: pd.DataFrame,
    positions: pd.DataFrame,
    cfg: dict,
    sample_months: set | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(one row per trade, one row per country)``.

    A **trade** is a maximal run of consecutive months in a non-flat state
    for one country. Its PnL is the sum of that country's monthly overlay
    contributions over the months held, in bp of book. Its cost is the
    overlay's own round trip at ``config.costs.cost_bp_per_duration_year``:
    entering moves two legs by ``B_o`` each, so ``sum |d(wD)| = 2 B_o``, and
    leaving does the same. A trade still open at the end of the sample is
    charged the entry only, and is marked ``still_open``.

    ``sample_months`` is the set of months the run actually covered. A leg
    whose month is outside it was never charged by the engine and is not
    charged here either, so the per-trade costs sum to the run's own cost to
    the last decimal (``test_trade_pnl_ties_out_to_the_run``).
    """
    budget = float(cfg["overlay"]["overlay_duration_budget"])
    cost_bp_per_year = float(cfg["costs"]["cost_bp_per_duration_year"])
    leg_cost_bp = cost_bp_per_year * 2.0 * budget  # one side of the round trip, in bp
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    pnl = monthly_pnl_bp(positions)

    trades = []
    for country, g in detail.groupby("country", sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        run: list[int] = []
        for i in range(len(g) + 1):
            in_state = i < len(g) and g.loc[i, "state"] != STATE_FLAT
            if in_state and (not run or g.loc[run[-1], "state"] == g.loc[i, "state"]):
                run.append(i)
                continue
            if run:
                first = g.loc[run[0]]
                exits = i < len(g)
                dates = [pd.Timestamp(g.loc[k, "date"]) for k in run]
                earned = float(sum(pnl.get((country, d), 0.0) for d in dates))
                exit_date = pd.Timestamp(g.loc[i, "date"]) if exits else None

                def charged(month: pd.Timestamp) -> float:
                    if sample_months is None:
                        return leg_cost_bp
                    return leg_cost_bp if month in sample_months else 0.0

                cost = charged(pd.Timestamp(first["date"]))
                if exits:
                    cost += charged(exit_date)
                trades.append(
                    {
                        "country": country,
                        "entry_date": pd.Timestamp(first["date"]).date().isoformat(),
                        "exit_date": exit_date.date().isoformat() if exits else "",
                        "direction": first["state"],
                        "entry_z": float(first["z"]),
                        "exit_z": float(g.loc[i, "z"]) if exits else float("nan"),
                        "months_held": len(run),
                        "pnl_bp": earned,
                        "cost_bp": cost,
                        "pnl_net_bp": earned - cost,
                        "still_open": not exits,
                        "in_sample": bool(
                            pd.Timestamp(first["date"]) >= start
                            and pd.Timestamp(first["date"]) <= end
                        ),
                    }
                )
                run = []
            if in_state:
                run = [i]
    trade_frame = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    return trade_frame, country_stats(trade_frame, detail, cfg)


def country_stats(trades: pd.DataFrame, detail: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per country, over the strategy window: how often it traded and how it did."""
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    d = detail.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d[(d["date"] >= start) & (d["date"] <= end)]
    live = trades[trades["in_sample"]] if len(trades) else trades

    rows = []
    for country in sorted(d["country"].unique()):
        g = d[d["country"] == country]
        t = live[live["country"] == country] if len(live) else live
        closed = t[~t["still_open"]] if len(t) else t
        months = int((g["state"] != STATE_FLAT).sum())
        no_score = int(g["z"].isna().sum())
        rows.append(
            {
                "country": country,
                "trades": int(len(t)),
                "months_in_market": months,
                "months_in_sample": int(len(g)),
                "share_in_market": months / len(g) if len(g) else float("nan"),
                "hit_rate": (
                    float((closed["pnl_net_bp"] > 0).mean()) if len(closed) else float("nan")
                ),
                "mean_pnl_bp": float(t["pnl_net_bp"].mean()) if len(t) else float("nan"),
                "median_pnl_bp": float(t["pnl_net_bp"].median()) if len(t) else float("nan"),
                "total_pnl_net_bp": float(t["pnl_net_bp"].sum()) if len(t) else 0.0,
                "months_armed_not_traded": int(g["blocked"].sum()),
                "months_no_score_under_min": no_score,
                "months_no_z_short_window": 0,
            }
        )
    out = pd.DataFrame(rows, columns=COUNTRY_STAT_COLUMNS)
    return out


def split_no_z(detail: pd.DataFrame, scores: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Split the NaN-z months into "no score yet" and "score, but fewer than 36 of them".

    ``z`` is NaN for two different reasons and they mean different things: the
    expanding PCA has not reached ``pca_min_months`` rows, or it has but the
    rolling z window has not yet filled. The country table reports them apart.
    """
    minimum = int(cfg["pca"]["pca_min_months"])
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    s = scores.copy()
    s["date"] = pd.to_datetime(s["date"])
    s = s[(s["date"] >= start) & (s["date"] <= end)]
    d = detail.copy()
    d["date"] = pd.to_datetime(d["date"])
    merged = d.merge(s[["country", "date", "n_months"]], on=["country", "date"], how="left")
    merged = merged[(merged["date"] >= start) & (merged["date"] <= end)]
    no_z = merged[merged["z"].isna()]
    rows = []
    for country in sorted(merged["country"].unique()):
        g = no_z[no_z["country"] == country]
        rows.append(
            {
                "country": country,
                "months_no_score_under_min": int((g["n_months"] < minimum).sum()),
                "months_no_z_short_window": int((g["n_months"] >= minimum).sum()),
            }
        )
    return pd.DataFrame(rows)


def build_trades(
    cfg: dict, variant: str = "overlay_hedged", processed: Path | None = None
) -> pd.DataFrame:
    """CLI ``build --step overlay_trades``: the per-trade file and the country table.

    It runs **after** ``run --variant overlay_hedged``, because a trade has no
    PnL until the run has earned it. It logs nothing and computes no new
    strategy: it reads the saved positions of a run that is already in
    ``reports/specifications.csv``.
    """
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    detail = pd.read_parquet(p / "overlay_states.parquet")
    scores = pd.read_parquet(p / "pc2_expanding.parquet")
    positions = pd.read_parquet(checks.CHECKS / f"positions_{variant}.parquet")
    monthly = pd.read_parquet(p / f"backtest_{variant}.parquet")
    months = set(pd.to_datetime(monthly["date"]))
    trades, stats = trade_anatomy(detail, positions, cfg, sample_months=months)
    split = split_no_z(detail, scores, cfg)
    stats = stats.drop(columns=["months_no_score_under_min", "months_no_z_short_window"]).merge(
        split, on="country", how="left"
    )
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    trades.to_csv(checks.OVERLAY_TRADES, index=False, lineterminator="\n")
    stats.to_csv(checks.OVERLAY_COUNTRY_STATS, index=False, lineterminator="\n")
    return trades
