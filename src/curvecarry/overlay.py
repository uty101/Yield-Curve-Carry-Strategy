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
TRADE_COLUMNS = ["date", "country", "event", "state", "z"]
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


def states(z: pd.Series, cfg: dict) -> pd.Series:
    """The state machine of the module docstring, over one country's z-score series."""
    entry = float(cfg["overlay"]["z_entry"])
    exit_level = float(cfg["overlay"]["z_exit"])
    state = STATE_FLAT
    armed_steep = armed_flat = True
    out = []
    previous = np.nan
    for value in z.astype("float64"):
        if np.isfinite(previous) and np.isfinite(value):
            crossed = np.sign(previous - exit_level) != np.sign(value - exit_level)
            if crossed:
                armed_steep = armed_flat = True
        if not np.isfinite(value):
            state = STATE_FLAT
            armed_steep = armed_flat = False
            out.append(state)
            previous = value
            continue
        if state == STATE_STEEP and value >= exit_level:
            state = STATE_FLAT
        elif state == STATE_FLAT_ENER and value <= exit_level:
            state = STATE_FLAT
        if state == STATE_FLAT:
            if value < -entry and armed_steep:
                state = STATE_STEEP
                armed_steep = False
            elif value > entry and armed_flat:
                state = STATE_FLAT_ENER
                armed_flat = False
        out.append(state)
        previous = value
    return pd.Series(out, index=z.index, name="state")


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
    """``(positions, trades, skipped)`` from the expanding scores."""
    window = int(cfg["pca"]["pca_z_window"])
    overlay_tenors = [float(t) for t in cfg["overlay"]["overlay_tenors"]]
    durations = _durations(returns, cfg)
    positions, trades, skipped = [], [], []
    for country, g in scores.groupby("country", sort=True):
        g = g.sort_values("date")
        z = zscore(g.set_index("date")["score"], window)
        state = states(z, cfg)
        previous = STATE_FLAT
        for date, s in state.items():
            value = float(z.loc[date])
            if s != previous:
                event = "exit" if s == STATE_FLAT else "enter"
                trades.append(
                    {"date": date, "country": country, "event": event, "state": s, "z": value}
                )
            previous = s
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
    return (
        pos,
        pd.DataFrame(trades, columns=TRADE_COLUMNS),
        pd.DataFrame(skipped, columns=SKIPPED_COLUMNS),
    )


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step overlay``: the scores, the positions and the trade log."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    returns = pd.read_parquet(p / "returns.parquet")
    changes = pca.monthly_changes_bp(zero, cfg)
    scores = expanding_pc2_scores(changes, cfg)
    positions, trades, skipped = build_positions(scores, returns, cfg)
    p.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(p / "pc2_expanding.parquet", index=False)
    positions.to_parquet(p / "overlay_positions.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    trades.to_csv(checks.OVERLAY_TRADES, index=False, lineterminator="\n")
    skipped.to_csv(checks.OVERLAY_SKIPPED, index=False, lineterminator="\n")
    return positions
