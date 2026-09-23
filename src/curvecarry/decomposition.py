"""Step 6.1: the decomposition - how much was carry earned, how much a yield bet.

**This is the deliverable, not the Sharpe** (CLAUDE.md). The brief asks how
much of a duration-neutral carry book's return was carry and how much was
paid for a directional yield bet, so the four pieces have to add up to the
reported return exactly, not approximately.

**The residual definition (issue #17, carried into PLAN.md 6.1).** The
yield-change PnL is ``r_local - carry - rolldown``, the **exact remainder**
of the full repricing. The duration-convexity approximation is reported
**beside** the identity and never inside it: a Taylor term cannot appear in
an identity that has to hold to 1e-10, which is the whole reason step 4.2's
approximation is diagnostic.

Per held bucket ``j`` at month ``t``, with ``c_j`` the par yield the bond was
bought at (``returns.coupon``, the same ``c`` the return was computed from),
``rolldown_j`` from 4.1 and ``w_j`` the capital weight:

- **hedged variants** - ``r_hedged = r_local - r_short_local/12`` (4.3), so

      carry_earned_j = w_j (c_j/12 - r_short_local,j/12 + rolldown_j)
      funding_j      = 0
      fx_j           = 0

- **unhedged variants** - ``r_unhedged = r_local + fx - r_short_base/12``, so

      carry_earned_j = w_j (c_j/12 + rolldown_j)
      funding_j      = -w_j r_short_base/12
      fx_j           = w_j fx_return_j

and in both cases the remainder is

      yield_change_pnl_j = w_j r_j - carry_earned_j - funding_j - fx_j
                         = w_j (r_local_full,j - c_j/12 - rolldown_j)

which is the plan's formula written so that the identity is exact by
construction rather than by cancellation. ``r_j`` is the variant's own return
column as the backtest used it, which is ``0.0`` for a **closed** bucket; a
closed bucket therefore contributes zero to every piece, because it earned
nothing.

**The Taylor form, and the one correction to the plan text (session-6
deviation 1).** PLAN.md 6.1 wrote the Taylor form of the yield-change PnL as
``sum_j w_j (-D_j dy_j + C_j dy_j^2 / 2)`` and in the same paragraph required
``taylor_residual`` to be "exactly the 4.2 ``gap_bp`` aggregated by the
weights". Those two sentences cannot both hold: the quantity being
approximated is ``r_local - c/12 - rolldown`` and the bare Taylor price term
approximates ``r_local - c/12``, so the difference of the two carries a
leftover ``-sum_j w_j rolldown_j``. The rolldown is subtracted inside the
Taylor bracket as well, which is the only reading under which the step's own
``test_taylor_residual_equals_weighted_gap`` can pass:

      yield_change_taylor_j = w_j (-D_j dy_j + C_j dy_j^2 / 2 - rolldown_j)
      taylor_residual_j     = yield_change_pnl_j - yield_change_taylor_j
                            = w_j (r_local_full,j - r_local_approx,j)
                            = w_j gap_j

``dy_j`` is the step-4.2 ``dy`` - the change in the bond's **own** yield to
maturity - as the #17 ruling requires; ``D_j`` and ``C_j`` are the 4.2
duration and convexity, taken at ``t`` on the un-aged bond. The bare Taylor
price term, for anyone who wants it, is
``yield_change_taylor + sum_j w_j rolldown_j``.

``cost_t`` is the backtest's cost with the sign it has in the return:
``cost_t = -cost``. A month the book held nothing still has a row: every
piece is zero and ``cost`` is the charge for coming out of last month's book,
so the identity reads ``-cost == r_net``, which is what that month earned.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise

PIECES = ["carry_earned", "yield_change_pnl", "funding", "fx", "cost"]
DECOMPOSITION_COLUMNS = [
    "date",
    "carry_earned",
    "yield_change_pnl",
    "yield_change_taylor",
    "taylor_residual",
    "funding",
    "fx",
    "cost",
    "r_net",
    "identity_gap",
]
SHARE_COLUMNS = ["variant", "window", "piece", "cumulative", "share"]
POSITION_PIECE_COLUMNS = [
    "date",
    "country",
    "tenor_years",
    "leg",
    "weight",
    "carry_earned",
    "yield_change_pnl",
    "yield_change_taylor",
    "taylor_residual",
    "funding",
    "fx",
]
PIECE_VALUE_COLUMNS = POSITION_PIECE_COLUMNS[5:]
IDENTITY_TOLERANCE = 1e-10
HEDGED_PREFIX = "r_hedged"
INTERBANK_SUFFIX = "_interbank_3m"
DECADE_MIN_MONTHS = 12  # a decade with fewer months of the sample gets no share row


class IdentityBroken(RuntimeError):
    """The pieces did not sum to the reported return."""


def is_hedged(returns_column: str) -> bool:
    return returns_column.startswith(HEDGED_PREFIX)


def funding_suffix(returns_column: str) -> str:
    """``"_interbank_3m"`` for the robustness funding column, else ``""``."""
    return INTERBANK_SUFFIX if returns_column.endswith(INTERBANK_SUFFIX) else ""


def decade_label(date: pd.Timestamp) -> str:
    return f"{(pd.Timestamp(date).year // 10) * 10}s"


def position_pieces(
    positions: pd.DataFrame, returns: pd.DataFrame, carry: pd.DataFrame, returns_column: str
) -> pd.DataFrame:
    """One row per held bucket-month, with every piece of its contribution.

    Raises when a held bucket has no 4.1 rolldown or no 4.2 row: a bucket the
    book held and the decomposition cannot explain is a hole in the identity,
    not a row to drop.
    """
    suffix = funding_suffix(returns_column)
    hedged = is_hedged(returns_column)
    key = ["date", "country", "tenor_years"]
    cols = [
        *key,
        "coupon",
        "duration",
        "convexity",
        "dy",
        "r_local_full",
        "r_local_approx",
        f"r_short_local{suffix}",
        "r_short_base",
        "fx_return",
    ]
    p = positions.merge(returns[cols], on=key, how="left", suffixes=("", "_ret"))
    p = p.merge(carry[[*key, "rolldown"]], on=key, how="left")
    missing = p[p["rolldown"].isna() | p["coupon"].isna()]
    if len(missing):
        raise RuntimeError(f"held bucket with no carry or return row:\n{missing.head(3)}")

    w = p["weight"].to_numpy(dtype="float64")
    c = p["coupon"].to_numpy(dtype="float64")
    rd = p["rolldown"].to_numpy(dtype="float64")
    r = p["r"].to_numpy(dtype="float64")
    open_ = ~p["closed"].to_numpy(dtype="bool")

    if hedged:
        rs = p[f"r_short_local{suffix}"].to_numpy(dtype="float64")
        carry_earned = w * (c / 12.0 - rs / 12.0 + rd)
        funding = np.zeros_like(w)
        fx = np.zeros_like(w)
    else:
        carry_earned = w * (c / 12.0 + rd)
        funding = -w * p["r_short_base"].to_numpy(dtype="float64") / 12.0
        fx = w * p["fx_return"].to_numpy(dtype="float64")

    # a closed bucket earned nothing, so it explains nothing
    carry_earned = np.where(open_, carry_earned, 0.0)
    funding = np.where(open_, funding, 0.0)
    fx = np.where(open_, fx, 0.0)
    yield_change = w * r - carry_earned - funding - fx

    # ``duration`` is in both frames; the merge suffixed the 4.2 one
    duration = p["duration_ret"] if "duration_ret" in p.columns else p["duration"]
    d = duration.to_numpy(dtype="float64")
    cx = p["convexity"].to_numpy(dtype="float64")
    dy = p["dy"].to_numpy(dtype="float64")
    taylor = np.where(open_, w * (-d * dy + 0.5 * cx * dy * dy - rd), 0.0)

    out = p[["date", "country", "tenor_years", "leg", "weight"]].copy()
    out["carry_earned"] = carry_earned
    out["yield_change_pnl"] = yield_change
    out["yield_change_taylor"] = taylor
    out["taylor_residual"] = yield_change - taylor
    out["funding"] = funding
    out["fx"] = fx
    return out[POSITION_PIECE_COLUMNS]


def monthly_decomposition(pieces: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    """Sum the per-bucket pieces to months, add the cost, and check the identity."""
    summed = pieces.groupby("date", as_index=False)[PIECE_VALUE_COLUMNS].sum()
    out = monthly[["date", "cost", "r_net"]].merge(summed, on="date", how="left")
    for column in PIECE_VALUE_COLUMNS:
        out[column] = out[column].fillna(0.0)
    out["cost"] = -out["cost"]
    out["identity_gap"] = out[PIECES].sum(axis=1) - out["r_net"]
    worst = float(out["identity_gap"].abs().max()) if len(out) else 0.0
    if worst > IDENTITY_TOLERANCE:
        row = out.loc[out["identity_gap"].abs().idxmax()]
        raise IdentityBroken(f"|identity_gap| = {worst:.3e} > {IDENTITY_TOLERANCE:.0e}\n{row}")
    return out[DECOMPOSITION_COLUMNS]


def share_rows(decomposition: pd.DataFrame, variant: str, cfg: dict) -> pd.DataFrame:
    """``variant, window, piece, cumulative, share`` for both windows and each decade.

    ``cumulative`` is the sum of the monthly piece over the window and
    ``share`` its fraction of the summed ``r_net``; the ``r_net`` row carries
    the total itself, so the file can be read without a second file. The
    decade rows are session-6 amendment 1's "cumulative and by decade" and use
    the same three columns, with the decade as the ``window``.
    """
    d = decomposition.copy()
    d["date"] = pd.to_datetime(d["date"])
    windows = {
        "full": d[d["date"] >= pd.Timestamp(cfg["sample"]["strategy_start"])],
        "six": d[d["date"] >= pd.Timestamp(cfg["sample"]["sample_full_start"])],
    }
    full = windows["full"]
    for decade, g in full.groupby(full["date"].map(decade_label)):
        if len(g) >= DECADE_MIN_MONTHS:
            windows[str(decade)] = g
    rows = []
    for window, part in windows.items():
        total = float(part["r_net"].sum())
        for piece in PIECES:
            value = float(part[piece].sum())
            rows.append(
                {
                    "variant": variant,
                    "window": window,
                    "piece": piece,
                    "cumulative": value,
                    "share": value / total if total != 0.0 else float("nan"),
                }
            )
        rows.append(
            {
                "variant": variant,
                "window": window,
                "piece": "r_net",
                "cumulative": total,
                "share": 1.0 if total != 0.0 else float("nan"),
            }
        )
    return pd.DataFrame(rows, columns=SHARE_COLUMNS)


def decompose(
    variant: str,
    cfg: dict,
    processed: Path | None = None,
    checks_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``(per-bucket pieces, monthly decomposition, share rows)`` for one logged run."""
    from curvecarry import backtest

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    cdir = Path(checks_dir) if checks_dir is not None else checks.CHECKS
    spec = backtest.VARIANTS[variant]
    positions = pd.read_parquet(cdir / f"positions_{variant}.parquet")
    monthly = pd.read_parquet(p / f"backtest_{variant}.parquet")
    returns = pd.read_parquet(p / "returns.parquet")
    carry = pd.read_parquet(p / "carry.parquet")
    pieces = position_pieces(positions, returns, carry, spec.returns_column)
    table = monthly_decomposition(pieces, monthly)
    return pieces, table, share_rows(table, variant, cfg)


def build(
    cfg: dict,
    processed: Path | None = None,
    checks_dir: Path | None = None,
    variants: list[str] | None = None,
) -> pd.DataFrame:
    """CLI ``build --step decomposition``: every logged run that has a positions file."""
    from curvecarry import backtest

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    cdir = Path(checks_dir) if checks_dir is not None else checks.CHECKS
    names = variants if variants is not None else list(backtest.VARIANTS)
    names = [v for v in names if (cdir / f"positions_{v}.parquet").exists()]
    if not names:
        raise RuntimeError(
            "no positions_<variant>.parquet in "
            f"{cdir}: run `curvecarry run --all` before `build --step decomposition`"
        )
    shares = []
    for variant in names:
        _pieces, table, rows = decompose(variant, cfg, p, cdir)
        table.to_parquet(p / f"decomposition_{variant}.parquet", index=False)
        shares.append(rows)
    out = pd.concat(shares, ignore_index=True)
    cdir.mkdir(parents=True, exist_ok=True)
    out.to_csv(cdir / checks.DECOMPOSITION_SHARES.name, index=False, lineterminator="\n")
    return out
