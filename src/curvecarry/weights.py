"""Step 5.2: duration-neutral weights from the 5.1 signal.

Each month, the eligible buckets are ranked by ``signal`` descending; the top
third is the long leg and the bottom third the short leg. Ties are broken by
``(country, tenor_years)`` so two runs of the same data give the same book.

The book is sized in **duration**, not in capital. Every bucket in the long
leg carries ``wd = +B/k`` years of duration per unit capital and every bucket
in the short leg ``wd = -B/k``, with ``B = config.weights.long_duration_budget``
and ``k`` the leg size; the capital weight is ``weight = wd / duration``. So
``sum_j wd_j = 0`` by construction, not by a fitted hedge ratio, and the long
leg carries exactly ``B``.

**The duration is the one from 4.1 and 4.2.** ``signal.parquet`` carries the
``duration`` column that ``carry.parquet`` got from ``bondmath.par_bond_risk``;
nothing here recomputes it. Session-5 amendment 4 tests that on the real
panel against ``returns.parquet``.

**Two scopes.**

- ``scope = "book"`` (the default, and the headline): one ranking across
  every eligible bucket in every country. ``n`` eligible, ``k = n // 3``.
- ``scope = "country"``: the same rule inside each country, ``k_c = n_c // 3``,
  with the budget split ``B_c = B / n_countries_that_month``. A country with
  fewer than 3 eligible tenors has ``k_c = 0`` and holds nothing, so
  ``n_countries_that_month`` counts the countries that **trade** that month -
  the reading that keeps the book's long leg at exactly ``B`` in both scopes,
  which is what amendment 4 asserts every month.

**The minimum is pre-registered** (session-5 amendment 3). If fewer than
``config.weights.min_eligible_buckets`` (9) buckets are eligible, the book is
**flat that month** and the month is written to
``data/checks/weights_empty_months.csv``. The minimum is counted book-wide in
both scopes: no single country ever has 9 eligible tenors, so a per-country
reading would flatten the country book for the whole sample.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from curvecarry import checks, harmonise

SCOPE_BOOK = "book"
SCOPE_COUNTRY = "country"
LEG_LONG = "long"
LEG_SHORT = "short"

WEIGHT_COLUMNS = [
    "date",
    "country",
    "tenor_years",
    "leg",
    "signal",
    "duration",
    "weight",
    "wd",
]
EMPTY_MONTH_COLUMNS = ["date", "n_eligible", "min_eligible_buckets", "reason"]

REASON_BELOW_MIN = "below min_eligible_buckets"
REASON_NO_LEGS = "fewer than 3 eligible buckets in every scope group"


def _ranked(month: pd.DataFrame) -> pd.DataFrame:
    """Eligible rows of one month, best signal first, ties by (country, tenor)."""
    return month.sort_values(
        ["signal", "country", "tenor_years"], ascending=[False, True, True], kind="mergesort"
    )


def _leg_rows(ranked: pd.DataFrame, k: int, budget: float) -> list[dict]:
    """Top ``k`` long and bottom ``k`` short, each carrying ``budget / k`` of duration."""
    if k < 1:
        return []
    per = budget / k
    rows = []
    for leg, part, sign in (
        (LEG_LONG, ranked.head(k), 1.0),
        (LEG_SHORT, ranked.tail(k), -1.0),
    ):
        for _, r in part.iterrows():
            wd = sign * per
            rows.append(
                {
                    "date": r["date"],
                    "country": r["country"],
                    "tenor_years": float(r["tenor_years"]),
                    "leg": leg,
                    "signal": float(r["signal"]),
                    "duration": float(r["duration"]),
                    "weight": wd / float(r["duration"]),
                    "wd": wd,
                }
            )
    return rows


def month_weights(month: pd.DataFrame, cfg: dict) -> list[dict]:
    """The held rows of one month, or ``[]`` if the month is flat."""
    scope = cfg["weights"]["duration_neutral_scope"]
    budget = float(cfg["weights"]["long_duration_budget"])
    eligible = month[month["eligible"]]
    if len(eligible) < int(cfg["weights"]["min_eligible_buckets"]):
        return []
    if scope == SCOPE_BOOK:
        return _leg_rows(_ranked(eligible), len(eligible) // 3, budget)
    if scope != SCOPE_COUNTRY:
        raise ValueError(f"unknown duration_neutral_scope {scope!r}")
    groups = [(c, g) for c, g in eligible.groupby("country", sort=True) if len(g) // 3 >= 1]
    if not groups:
        return []
    per_country = budget / len(groups)
    rows: list[dict] = []
    for _, g in groups:
        rows.extend(_leg_rows(_ranked(g), len(g) // 3, per_country))
    return rows


def duration_neutral_weights(signal: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(weights.parquet frame, weights_empty_months.csv frame)``."""
    minimum = int(cfg["weights"]["min_eligible_buckets"])
    held: list[dict] = []
    empty: list[dict] = []
    for date, month in signal.groupby("date", sort=True):
        n_eligible = int(month["eligible"].sum())
        rows = month_weights(month, cfg)
        if rows:
            held.extend(rows)
            continue
        empty.append(
            {
                "date": pd.Timestamp(date).date().isoformat(),
                "n_eligible": n_eligible,
                "min_eligible_buckets": minimum,
                "reason": REASON_BELOW_MIN if n_eligible < minimum else REASON_NO_LEGS,
            }
        )
    weights = pd.DataFrame(held, columns=WEIGHT_COLUMNS)
    if len(weights):
        weights = weights.sort_values(["date", "leg", "country", "tenor_years"]).reset_index(
            drop=True
        )
    return weights, pd.DataFrame(empty, columns=EMPTY_MONTH_COLUMNS)


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step weights``: ``weights.parquet`` and ``weights_empty_months.csv``."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    signal = pd.read_parquet(p / "signal.parquet")
    weights, empty = duration_neutral_weights(signal, cfg)
    p.mkdir(parents=True, exist_ok=True)
    weights.to_parquet(p / "weights.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    empty.to_csv(checks.WEIGHTS_EMPTY_MONTHS, index=False, lineterminator="\n")
    return weights
