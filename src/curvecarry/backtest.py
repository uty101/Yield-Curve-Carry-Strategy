"""Step 5.3: the backtest engine - one logged run of one variant.

**Nothing computes before it is logged.** ``run`` calls
``speclog.log_run`` first and every computing function below takes the
``run_id`` and calls ``speclog.require_logged`` (global rule 6). A variant
with no row in ``reports/specifications.csv`` did not happen.

**The headline** (session-5 amendment 1, fixed before any result was seen)
is ``carry_hedged``, ``full`` window, ``r_net``: carry-only, hedged,
book-wide duration neutrality, net of costs, from ``strategy_start``
(1997-08-31) to ``strategy_end``, on the universe available each month.
Every other entry in ``VARIANTS`` is a logged variant and never the
headline.

**Timing.** Weights ``w_t`` come from the signal at month end ``t``; the
bucket return is the ``returns.parquet`` row **dated t**, which is the
return from ``t`` to ``t + 1`` (4.2). So the signal is formed on the curve
at ``t`` and earns the move that follows it, and the last usable ``t`` is
the last month with a ``t + 1`` return - 5.1's universe join empties the
final month by itself, without a special case here.

**Availability is applied before sizing, not after.** A bucket whose return
column is NaN for this variant (an unhedged run before its FX series
starts, say) is marked ineligible in the signal frame and then the weights
are built. Dropping it afterwards would leave ``sum wd != 0`` and quietly
break the one invariant the book is built on.

**Costs.** ``turnover_t = 0.5 * sum_j |wd_{j,t} - wd_{j,t-1}|`` over the
union of buckets held at ``t`` and ``t - 1``; the first month counts the
full entry. ``cost_t = cost_bp_per_duration_year * 1e-4 * sum_j |dwd|``,
which is ``2 * cost_bp * 1e-4 * turnover_t``. ``r_net = r_gross - cost``.

**Variant overrides.** A variant may override config keys; the override is
deep-merged into a copy of the config, so the run's ``config_hash`` differs
from the base and the overridden keys are recorded as JSON in the spec-log
``note``. ``config.toml`` itself is never edited. ``exclude_buckets`` is not
a config knob - it is part of the variant's definition in ``VARIANTS``, as
PLAN.md 5.5 names it - and it is recorded in the note the same way.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise, metrics, speclog
from curvecarry import weights as wt
from curvecarry.weights import LEG_LONG, LEG_SHORT

WINDOW_FULL = "full"
WINDOW_SIX = "six"

BACKTEST_COLUMNS = [
    "date",
    "r_gross",
    "cost",
    "r_net",
    "turnover",
    "n_long",
    "n_short",
    "n_closed",
    "run_id",
]
METRIC_COLUMNS = ["run_id", "variant", "window", "metric", "value"]


@dataclass(frozen=True)
class Variant:
    """One logged run: which book, which return column, and what it overrides."""

    book: str  # "carry"; "overlay" and "combined" arrive in 5.4 and 5.5
    returns_column: str  # "r_hedged" or "r_unhedged", or their interbank twins
    overrides: dict = field(default_factory=dict)
    exclude_buckets: tuple[tuple[str, float], ...] = ()


BOOK_CARRY = "carry"
BOOK_OVERLAY = "overlay"
BOOK_COMBINED = "combined"

# Steps 5.3 (the first two), 5.4 (the two overlay books) and 5.5 (the rest).
# Eleven logged runs in this session, and every one of them is reported.
VARIANTS: dict[str, Variant] = {
    "carry_hedged": Variant(book=BOOK_CARRY, returns_column="r_hedged"),
    "carry_unhedged": Variant(book=BOOK_CARRY, returns_column="r_unhedged"),
    "overlay_hedged": Variant(book=BOOK_OVERLAY, returns_column="r_hedged"),
    "overlay_unhedged": Variant(book=BOOK_OVERLAY, returns_column="r_unhedged"),
    "combined_hedged": Variant(book=BOOK_COMBINED, returns_column="r_hedged"),
    "combined_unhedged": Variant(book=BOOK_COMBINED, returns_column="r_unhedged"),
    # session-5 amendment 2: five robustness runs on the headline book,
    # fixed before any of their results were seen and all reported.
    "carry_hedged_country_scope": Variant(
        book=BOOK_CARRY,
        returns_column="r_hedged",
        overrides={"weights": {"duration_neutral_scope": "country"}},
    ),
    "carry_hedged_interbank_3m": Variant(
        book=BOOK_CARRY,
        returns_column="r_hedged_interbank_3m",
        overrides={"hedge": {"funding_rate": "interbank_3m"}},
    ),
    "carry_hedged_cost0": Variant(
        book=BOOK_CARRY,
        returns_column="r_hedged",
        overrides={"costs": {"cost_bp_per_duration_year": 0.0}},
    ),
    "carry_hedged_cost2x": Variant(
        book=BOOK_CARRY,
        returns_column="r_hedged",
        overrides={"costs": {"cost_bp_per_duration_year": 1.0}},
    ),
    "carry_hedged_no_gb30": Variant(
        book=BOOK_CARRY,
        returns_column="r_hedged",
        exclude_buckets=(("GB", 30.0),),
    ),
}

HEADLINE = "carry_hedged"


@dataclass(frozen=True)
class BacktestResult:
    run_id: str
    variant: str
    monthly: pd.DataFrame
    positions: pd.DataFrame
    metrics: pd.DataFrame


def merge_overrides(cfg: dict, overrides: dict) -> dict:
    """Deep-merge ``overrides`` into a copy of ``cfg``; the file on disk is untouched."""
    out = copy.deepcopy(cfg)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge_overrides(out[key], value)
        else:
            out[key] = value
    return out


def variant_note(variant: Variant, note: str) -> str:
    """The spec-log note: the owner's note plus the JSON of what this run overrode."""
    payload: dict = {}
    if variant.overrides:
        payload["overrides"] = variant.overrides
    if variant.exclude_buckets:
        payload["exclude_buckets"] = [[c, t] for c, t in variant.exclude_buckets]
    if not payload:
        return note
    text = json.dumps(payload, sort_keys=True)
    return f"{note} {text}".strip()


def available_signal(
    signal: pd.DataFrame,
    returns: pd.DataFrame,
    variant: Variant,
    run_id: str,
    spec_path: str | Path = speclog.DEFAULT_PATH,
) -> pd.DataFrame:
    """Mark ineligible every bucket this variant cannot hold, before the weights are sized."""
    speclog.require_logged(run_id, spec_path)
    col = variant.returns_column
    have = returns.loc[returns[col].notna(), ["date", "country", "tenor_years"]]
    have = set(zip(have["date"], have["country"], have["tenor_years"], strict=True))
    out = signal.copy()
    keep = np.array(
        [
            (d, c, t) in have
            for d, c, t in zip(out["date"], out["country"], out["tenor_years"], strict=True)
        ]
    )
    if variant.exclude_buckets:
        excluded = {(c, float(t)) for c, t in variant.exclude_buckets}
        keep &= np.array(
            [
                (c, float(t)) not in excluded
                for c, t in zip(out["country"], out["tenor_years"], strict=True)
            ]
        )
    out.loc[~keep, "eligible"] = False
    out.loc[~keep & (out["excluded_reason"] == ""), "excluded_reason"] = "unavailable_for_variant"
    return out


def overlay_book(
    positions: pd.DataFrame, returns: pd.DataFrame, variant: Variant, cfg: dict
) -> pd.DataFrame:
    """The 5.4 pairs, restricted to the sample and to pairs this variant can hold.

    A pair is dropped **whole** when either leg has no return for this
    variant: holding one side of a 2s10s pair would leave the overlay book
    with a naked duration position, which is the one thing it is built not
    to have.
    """
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    p = positions[(positions["date"] >= start) & (positions["date"] <= end)].copy()
    col = variant.returns_column
    have = returns.loc[returns[col].notna(), ["date", "country", "tenor_years"]]
    have = set(zip(have["date"], have["country"], have["tenor_years"], strict=True))
    ok = np.array(
        [
            (d, c, t) in have
            for d, c, t in zip(p["date"], p["country"], p["tenor_years"], strict=True)
        ]
    )
    p = p[ok]
    whole = p.groupby(["date", "country"])["tenor_years"].transform("size") == 2
    p = p[whole]
    p["signal"] = np.nan
    return p[wt.WEIGHT_COLUMNS].reset_index(drop=True)


def combine_books(carry: pd.DataFrame, overlay: pd.DataFrame) -> pd.DataFrame:
    """Sum the two books per ``(date, country, tenor)``; both are neutral, so the sum is."""
    both = pd.concat([carry, overlay], ignore_index=True)
    grouped = both.groupby(["date", "country", "tenor_years"], as_index=False).agg(
        signal=("signal", "first"),
        duration=("duration", "first"),
        weight=("weight", "sum"),
        wd=("wd", "sum"),
    )
    grouped = grouped[grouped["wd"] != 0.0]
    grouped["leg"] = np.where(grouped["wd"] > 0, LEG_LONG, LEG_SHORT)
    return (
        grouped[wt.WEIGHT_COLUMNS]
        .sort_values(["date", "country", "tenor_years"])
        .reset_index(drop=True)
    )


def bucket_returns(returns: pd.DataFrame, variant: Variant) -> pd.DataFrame:
    """``date, country, tenor_years, r, closed`` for this variant; a closed bucket earns 0."""
    col = variant.returns_column
    out = returns[["date", "country", "tenor_years", "closed"]].copy()
    out["r"] = np.where(returns["closed"], 0.0, returns[col])
    return out


def _turnover(prev: dict[tuple[str, float], float], now: dict[tuple[str, float], float]) -> float:
    """``sum_j |wd_j,t - wd_j,t-1|`` over the union; the caller halves it for turnover."""
    return sum(abs(now.get(k, 0.0) - prev.get(k, 0.0)) for k in set(prev) | set(now))


def monthly_returns(
    held: pd.DataFrame,
    returns: pd.DataFrame,
    variant: Variant,
    cfg: dict,
    run_id: str,
    spec_path: str | Path = speclog.DEFAULT_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(monthly frame, positions frame)`` - the whole backtest, month by month.

    Every month of the sample gets a row, including a month the 5.2 minimum
    left flat: it earns 0 and is charged the cost of coming out of last
    month's book, which is the honest accounting of a rule that flattens.
    """
    speclog.require_logged(run_id, spec_path)
    r = bucket_returns(returns, variant)
    joined = held.merge(r, on=["date", "country", "tenor_years"], how="left")
    if joined["r"].isna().any():
        missing = joined[joined["r"].isna()].head(3)
        raise RuntimeError(f"held bucket with no return for {variant.returns_column}:\n{missing}")
    cost_bp = float(cfg["costs"]["cost_bp_per_duration_year"])

    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    sample = sorted(d for d in set(returns["date"]) if start <= d <= end)
    by_date = dict(tuple(joined.groupby("date")))
    empty = joined.iloc[:0]

    rows = []
    prev: dict[tuple[str, float], float] = {}
    for date in sample:
        g = by_date.get(date, empty)
        now = {
            (c, float(t)): float(w)
            for c, t, w in zip(g["country"], g["tenor_years"], g["wd"], strict=True)
        }
        traded = _turnover(prev, now)
        r_gross = float((g["weight"] * g["r"]).sum())
        cost = cost_bp * 1e-4 * traded
        rows.append(
            {
                "date": pd.Timestamp(date),
                "r_gross": r_gross,
                "cost": cost,
                "r_net": r_gross - cost,
                "turnover": 0.5 * traded,
                "n_long": int((g["leg"] == "long").sum()),
                "n_short": int((g["leg"] == "short").sum()),
                "n_closed": int(g["closed"].sum()),
                "run_id": run_id,
            }
        )
        prev = now
    monthly = pd.DataFrame(rows, columns=BACKTEST_COLUMNS)
    return monthly, joined.reset_index(drop=True)


def metric_rows(
    monthly: pd.DataFrame,
    variant_name: str,
    cfg: dict,
    run_id: str,
    spec_path: str | Path = speclog.DEFAULT_PATH,
) -> pd.DataFrame:
    """Every metric on both windows, gross and net. ``value`` is text for the two dates."""
    speclog.require_logged(run_id, spec_path)
    m = monthly.set_index("date").sort_index()
    windows = {
        WINDOW_FULL: pd.Timestamp(cfg["sample"]["strategy_start"]),
        WINDOW_SIX: pd.Timestamp(cfg["sample"]["sample_full_start"]),
    }
    rows = []
    for window, start in windows.items():
        part = m[m.index >= start]
        for basis, column in (("net", "r_net"), ("gross", "r_gross")):
            block = metrics.summary(part[column], part["turnover"] if basis == "net" else None)
            for name, value in block.items():
                rows.append(
                    {
                        "run_id": run_id,
                        "variant": variant_name,
                        "window": window,
                        "metric": name if basis == "net" else f"{name}_gross",
                        "value": value,
                    }
                )
        rows.append(
            {
                "run_id": run_id,
                "variant": variant_name,
                "window": window,
                "metric": "annualisation",
                "value": metrics.ANNUALISATION,
            }
        )
    return pd.DataFrame(rows, columns=METRIC_COLUMNS)


EXTREME_COLUMNS = [
    "rank",
    "sign",
    "date",
    "r_net",
    "country",
    "tenor_years",
    "leg",
    "wd",
    "r_bucket",
    "contribution",
]
N_EXTREME = 10  # the 10 largest gains and the 10 largest losses
N_LEGS = 5  # the 5 largest contributions each way inside each of those months


def extreme_months(
    monthly: pd.DataFrame, positions: pd.DataFrame, n: int = N_EXTREME, legs: int = N_LEGS
) -> pd.DataFrame:
    """The biggest months, with the legs that drove them (session-5 amendment 2).

    A headline number nobody can trace to a curve move is a number taken on
    trust. For each of the ``n`` largest monthly gains and the ``n`` largest
    losses, this lists the ``legs`` largest positive and ``legs`` largest
    negative bucket contributions, ``contribution = weight * r``.
    """
    rows = []
    for sign, part in (
        ("gain", monthly.nlargest(n, "r_net")),
        ("loss", monthly.nsmallest(n, "r_net")),
    ):
        for rank, (_, month) in enumerate(part.iterrows(), start=1):
            g = positions[positions["date"] == month["date"]].copy()
            g["contribution"] = g["weight"] * g["r"]
            g = g.sort_values("contribution", ascending=False)
            chosen = pd.concat([g.head(legs), g.tail(legs)]).drop_duplicates(
                subset=["country", "tenor_years"]
            )
            for _, b in chosen.iterrows():
                rows.append(
                    {
                        "rank": rank,
                        "sign": sign,
                        "date": pd.Timestamp(month["date"]).date().isoformat(),
                        "r_net": float(month["r_net"]),
                        "country": b["country"],
                        "tenor_years": float(b["tenor_years"]),
                        "leg": b["leg"],
                        "wd": float(b["wd"]),
                        "r_bucket": float(b["r"]),
                        "contribution": float(b["contribution"]),
                    }
                )
    return pd.DataFrame(rows, columns=EXTREME_COLUMNS)


def variant_signal(spec: Variant, cfg_run: dict, processed: Path) -> pd.DataFrame:
    """The 5.1 signal frame this variant ranks on.

    A variant that overrides ``hedge.funding_rate`` cannot use the stored
    ``signal.parquet``: carry is ``y_n - r_short`` and ``r_short`` is the
    funding rate, so the whole signal changes with it. Its carry and signal
    are rebuilt in memory from ``curves_zero.parquet`` and
    ``funding.parquet`` under the overridden config, and ``config.toml`` is
    still not touched.
    """
    from curvecarry import carry as carry_mod
    from curvecarry import signal as signal_mod
    from curvecarry.loaders import base

    if "funding_rate" not in spec.overrides.get("hedge", {}):
        return pd.read_parquet(processed / "signal.parquet")
    zero = pd.read_parquet(processed / "curves_zero.parquet")
    funding = pd.read_parquet(base.INTERIM / "funding.parquet")
    carry, _missing = carry_mod.build_carry(zero, funding, cfg_run)
    universe = pd.read_csv(checks.UNIVERSE_BY_MONTH)
    return signal_mod.compute_signal(carry, universe, cfg_run)


def book_positions(
    spec: Variant,
    cfg_run: dict,
    returns: pd.DataFrame,
    run_id: str,
    processed: Path,
    spec_path: str | Path = speclog.DEFAULT_PATH,
) -> pd.DataFrame:
    """The held book of this variant: carry, overlay, or the sum of the two."""
    speclog.require_logged(run_id, spec_path)
    start = pd.Timestamp(cfg_run["sample"]["strategy_start"])
    end = pd.Timestamp(cfg_run["sample"]["strategy_end"])

    carry_held = pd.DataFrame(columns=wt.WEIGHT_COLUMNS)
    if spec.book in (BOOK_CARRY, BOOK_COMBINED):
        signal = variant_signal(spec, cfg_run, processed)
        signal = signal[(signal["date"] >= start) & (signal["date"] <= end)]
        usable = available_signal(signal, returns, spec, run_id, spec_path)
        carry_held, _empty = wt.duration_neutral_weights(usable, cfg_run)
    if spec.book == BOOK_CARRY:
        return carry_held

    overlay_held = overlay_book(
        pd.read_parquet(processed / "overlay_positions.parquet"), returns, spec, cfg_run
    )
    if spec.book == BOOK_OVERLAY:
        return overlay_held
    if spec.book != BOOK_COMBINED:
        raise ValueError(f"unknown book {spec.book!r}")
    return combine_books(carry_held, overlay_held)


def run(
    cfg: dict,
    variant: str,
    note: str = "",
    processed: Path | None = None,
    speclog_path: str | Path = speclog.DEFAULT_PATH,
    write: bool = True,
) -> BacktestResult:
    """Log the run, then compute it. The log row is written before anything else."""
    if variant not in VARIANTS:
        raise KeyError(f"unknown variant {variant!r}; known: {sorted(VARIANTS)}")
    spec = VARIANTS[variant]
    cfg_run = merge_overrides(cfg, spec.overrides)
    run_id = speclog.log_run(
        cfg_run, label=variant, note=variant_note(spec, note), path=speclog_path
    )

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    returns = pd.read_parquet(p / "returns.parquet")
    start = pd.Timestamp(cfg_run["sample"]["strategy_start"])
    end = pd.Timestamp(cfg_run["sample"]["strategy_end"])

    held = book_positions(spec, cfg_run, returns, run_id, p, speclog_path)
    held = held[(held["date"] >= start) & (held["date"] <= end)]
    monthly, positions = monthly_returns(held, returns, spec, cfg_run, run_id, speclog_path)
    table = metric_rows(monthly, variant, cfg_run, run_id, speclog_path)

    if write:
        p.mkdir(parents=True, exist_ok=True)
        monthly.to_parquet(p / f"backtest_{variant}.parquet", index=False)
        positions.to_parquet(checks.CHECKS / f"positions_{variant}.parquet", index=False)
        checks.CHECKS.mkdir(parents=True, exist_ok=True)
        table.to_csv(checks.CHECKS / f"metrics_{variant}.csv", index=False, lineterminator="\n")
        extreme_months(monthly, positions).to_csv(
            checks.CHECKS / f"extreme_months_{variant}.csv", index=False, lineterminator="\n"
        )
    return BacktestResult(run_id, variant, monthly, positions, table)


def run_all(cfg: dict, note: str = "", **kwargs) -> list[BacktestResult]:
    """Every variant built so far, each as its own logged row."""
    return [run(cfg, name, note=note, **kwargs) for name in VARIANTS]
