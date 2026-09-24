"""Step 5.1: the carry signal, and the universe it is allowed to rank.

``signal = (carry + 12 * rolldown) / duration`` - carry is already per year
and rolldown is per horizon month, so the ``12`` puts both on a per-year
basis before dividing by ``D``. The units are return per year per year of
duration. Ranking is invariant to the scaling, so the brief's
``(Carry + Rolldown)/D`` with mixed units gives the same portfolio; the
annualised form is used because the number is then readable.

**Eligibility.** A bucket is eligible at ``(country, tenor, month)`` when

1. ``carry``, ``rolldown`` and ``duration`` are all finite and ``duration``
   is non-zero - otherwise ``missing_input``;
2. the bucket is in that month's row of ``data/checks/universe_by_month.csv``
   (step 4.2) - otherwise ``not_in_universe``;
3. its zero yield at the tenor is at least ``config.signal.yield_floor``
   (20 bp, brief 10) - otherwise ``below_floor``.

The reasons are tested in that order and one row carries one reason: a
bucket with no computable duration is ``missing_input`` whatever its yield.
Ineligible rows keep their signal - the number is still the number - and
carry ``eligible = False``.

**The universe join is session-5 amendment 3.** ``universe_by_month.csv`` is
the set of buckets the return engine of 4.2 can actually price from ``t`` to
``t + 1``. Joining to it here means the strategy can only rank what it could
have held, and a bucket that exists on the curve but has no computable
return is excluded with a reason rather than silently carried into 5.2 and
dropped there.

Three per-month check files, none of them a sample-wide aggregate:

- ``data/checks/signal_exclusions.csv`` - per month, the three counts and
  the eligible count; then a blank line and a second table of
  ``country, n_below_floor`` (Japan dominates it).
- ``data/checks/universe_eligible.csv`` - per month, the universe size, the
  eligible count, each exclusion count, and the eligible buckets themselves.
- ``data/checks/universe_changes.csv`` - every month a bucket enters or
  leaves the eligible set. The first month of the panel is all ``enters``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise

MONTHS_PER_YEAR = 12.0

SIGNAL_COLUMNS = [
    "date",
    "country",
    "tenor_years",
    "signal",
    "duration",
    "yield",
    "eligible",
    "excluded_reason",
]
EXCLUSION_COLUMNS = ["date", "n_below_floor", "n_missing_input", "n_eligible"]
EXCLUSION_BY_COUNTRY_COLUMNS = ["country", "n_below_floor"]
UNIVERSE_ELIGIBLE_COLUMNS = [
    "date",
    "n_universe",
    "n_eligible",
    "n_below_floor",
    "n_missing_input",
    "n_not_in_universe",
    "eligible_buckets",
]
UNIVERSE_CHANGE_COLUMNS = ["date", "country", "tenor_years", "change"]

REASON_NONE = ""
REASON_FLOOR = "below_floor"
REASON_MISSING = "missing_input"
REASON_NOT_IN_UNIVERSE = "not_in_universe"


def universe_pairs(universe: pd.DataFrame) -> dict[pd.Timestamp, set[tuple[str, float]]]:
    """``date -> {(country, tenor_years)}`` from ``universe_by_month.csv``."""
    out: dict[pd.Timestamp, set[tuple[str, float]]] = {}
    for date, country, tenors in zip(
        pd.to_datetime(universe["date"]), universe["country"], universe["tenors"], strict=True
    ):
        s = out.setdefault(pd.Timestamp(date), set())
        for t in str(tenors).split(";"):
            if t.strip():
                s.add((str(country), float(t)))
    return out


def compute_signal(carry: pd.DataFrame, universe: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``signal.parquet``: one row per bucket-month with its signal and eligibility."""
    floor = float(cfg["signal"]["yield_floor"])
    in_universe = universe_pairs(universe)
    df = carry[["date", "country", "tenor_years", "yield", "carry", "rolldown", "duration"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    with np.errstate(invalid="ignore", divide="ignore"):
        df["signal"] = (df["carry"] + MONTHS_PER_YEAR * df["rolldown"]) / df["duration"]

    finite = (
        np.isfinite(df["carry"])
        & np.isfinite(df["rolldown"])
        & np.isfinite(df["duration"])
        & (df["duration"] != 0.0)
    )
    present = np.array(
        [
            (c, float(t)) in in_universe.get(d, ())
            for d, c, t in zip(df["date"], df["country"], df["tenor_years"], strict=True)
        ]
    )
    above = df["yield"].to_numpy() >= floor

    reason = np.where(
        ~finite,
        REASON_MISSING,
        np.where(~present, REASON_NOT_IN_UNIVERSE, np.where(~above, REASON_FLOOR, REASON_NONE)),
    )
    df["eligible"] = reason == REASON_NONE
    df["excluded_reason"] = reason
    out = df[SIGNAL_COLUMNS].sort_values(["date", "country", "tenor_years"])
    return out.reset_index(drop=True)


def exclusion_rows(signal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The two tables of ``signal_exclusions.csv``: per month, then per country."""
    per_month = (
        signal.groupby("date")
        .apply(
            lambda g: pd.Series(
                {
                    "n_below_floor": int((g["excluded_reason"] == REASON_FLOOR).sum()),
                    "n_missing_input": int((g["excluded_reason"] == REASON_MISSING).sum()),
                    "n_eligible": int(g["eligible"].sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    per_country = (
        signal[signal["excluded_reason"] == REASON_FLOOR]
        .groupby("country")
        .size()
        .reindex(sorted(signal["country"].unique()), fill_value=0)
        .rename("n_below_floor")
        .reset_index()
    )
    return per_month[EXCLUSION_COLUMNS], per_country[EXCLUSION_BY_COUNTRY_COLUMNS]


def eligible_set(signal: pd.DataFrame) -> dict[pd.Timestamp, set[tuple[str, float]]]:
    """``date -> {(country, tenor)}`` of the eligible buckets."""
    e = signal[signal["eligible"]]
    out: dict[pd.Timestamp, set[tuple[str, float]]] = {d: set() for d in signal["date"].unique()}
    for d, c, t in zip(e["date"], e["country"], e["tenor_years"], strict=True):
        out[d].add((str(c), float(t)))
    return out


def _label(pair: tuple[str, float]) -> str:
    return f"{pair[0]}:{pair[1]:g}"


def universe_eligible_rows(signal: pd.DataFrame) -> pd.DataFrame:
    """``universe_eligible.csv`` - amendment 3, one row per month."""
    rows = []
    for date, g in signal.groupby("date", sort=True):
        reasons = g["excluded_reason"]
        held = sorted(
            (str(c), float(t))
            for c, t in zip(
                g.loc[g["eligible"], "country"], g.loc[g["eligible"], "tenor_years"], strict=True
            )
        )
        rows.append(
            {
                "date": pd.Timestamp(date).date().isoformat(),
                "n_universe": int((reasons != REASON_NOT_IN_UNIVERSE).sum()),
                "n_eligible": int(g["eligible"].sum()),
                "n_below_floor": int((reasons == REASON_FLOOR).sum()),
                "n_missing_input": int((reasons == REASON_MISSING).sum()),
                "n_not_in_universe": int((reasons == REASON_NOT_IN_UNIVERSE).sum()),
                "eligible_buckets": ";".join(_label(p) for p in held),
            }
        )
    return pd.DataFrame(rows, columns=UNIVERSE_ELIGIBLE_COLUMNS)


def universe_change_rows(signal: pd.DataFrame) -> pd.DataFrame:
    """``universe_changes.csv`` - every entry to and exit from the eligible set."""
    by_date = eligible_set(signal)
    dates = sorted(by_date)
    rows = []
    previous: set[tuple[str, float]] = set()
    for i, d in enumerate(dates):
        now = by_date[d]
        entering = now - previous if i else now
        leaving = previous - now
        for pair in sorted(entering):
            rows.append(
                {
                    "date": pd.Timestamp(d).date().isoformat(),
                    "country": pair[0],
                    "tenor_years": pair[1],
                    "change": "enters",
                }
            )
        for pair in sorted(leaving):
            rows.append(
                {
                    "date": pd.Timestamp(d).date().isoformat(),
                    "country": pair[0],
                    "tenor_years": pair[1],
                    "change": "leaves",
                }
            )
        previous = now
    return pd.DataFrame(rows, columns=UNIVERSE_CHANGE_COLUMNS)


def write_exclusions(
    per_month: pd.DataFrame, per_country: pd.DataFrame, path: Path = checks.SIGNAL_EXCLUSIONS
) -> Path:
    """Two tables in one file, separated by a blank line, as PLAN.md 5.1 describes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = per_month.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
    text = out.to_csv(index=False, lineterminator="\n")
    text += "\n" + per_country.to_csv(index=False, lineterminator="\n")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step signal``: ``signal.parquet`` and the three check files."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    carry = pd.read_parquet(p / "carry.parquet")
    universe = pd.read_csv(checks.UNIVERSE_BY_MONTH)
    signal = compute_signal(carry, universe, cfg)
    p.mkdir(parents=True, exist_ok=True)
    signal.to_parquet(p / "signal.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    per_month, per_country = exclusion_rows(signal)
    write_exclusions(per_month, per_country)
    universe_eligible_rows(signal).to_csv(
        checks.UNIVERSE_ELIGIBLE, index=False, lineterminator="\n"
    )
    universe_change_rows(signal).to_csv(checks.UNIVERSE_CHANGES, index=False, lineterminator="\n")
    return signal
