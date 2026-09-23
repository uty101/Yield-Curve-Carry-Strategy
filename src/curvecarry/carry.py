"""Step 4.1: carry and rolldown per country-month-tenor.

Two numbers per bucket, both from the zero curve of that month and the
funding table of that month, and nothing else:

- **carry** ``= y_n - r_short``, per year. ``r_short`` is the funding rate of
  the bucket's own country and date, read from ``funding.parquet`` at
  ``kind = config.hedge.funding_rate`` — **never off the curve** (plan v2
  amendment B, ``decisions/short_anchor.md``).
- **rolldown** ``= (y_n - y(n - 1/12)) * D``, per horizon month, decimal. ``D``
  is the modified duration of the par bond at ``n``, from
  ``bondmath.par_bond_risk`` — the one duration function in the project.

``expected_return_1m = carry / 12 + rolldown`` is the bucket's expected
return over its own financing if the curve does not move.

``y(n - 1/12)`` goes through ``Curve.at``, so it is linear in tenor between
observed tenors and **flat below the shortest observed tenor**. For JP and FR,
whose shortest observed tenor is 1 year, the 1-year bucket's ``y_roll`` is
``y(1)`` exactly and its rolldown is exactly 0; ``n_flat_short_end`` in
``data/checks/carry_missing.csv`` counts those bucket-months so the size of it
is a number rather than a footnote (``decisions/short_anchor.md``).

The bucket universe is the **standard** zero rows of ``curves_zero.parquet``:
a bucket exists at ``(country, date, n)`` when that country-month has a
standard zero at ``n``. Rows with a missing input — no funding rate that
month, or a curve that cannot price the par bond at ``n`` — are dropped and
counted, never filled.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import bondmath, checks, harmonise
from curvecarry.curves import Curve

DT = 1.0 / 12.0  # the horizon, one month

CARRY_COLUMNS = [
    "date",
    "country",
    "tenor_years",
    "yield",
    "r_short",
    "carry",
    "rolldown",
    "duration",
    "convexity",
    "par_yield",
    "expected_return_1m",
]
CARRY_MISSING_COLUMNS = ["country", "tenor_years", "n_missing", "n_flat_short_end"]


def funding_lookup(funding: pd.DataFrame, kind: str) -> dict[tuple[str, pd.Timestamp], float]:
    """``(country, date) -> rate`` for one ``kind`` of funding rate."""
    f = funding[funding["kind"] == kind]
    return dict(zip(zip(f["country"], f["date"], strict=True), f["rate"], strict=True))


def _standard_tenors(cfg: dict) -> list[float]:
    return [float(t) for t in cfg["tenors"]]


def bucket(
    curve: Curve, tenor: float, freq: int, r_short: float
) -> tuple[dict[str, float], bool] | None:
    """Carry and rolldown of one bucket, or ``None`` if the curve cannot price it.

    The second element of the pair is ``True`` when ``n - 1/12`` fell below the
    shortest observed tenor and the flat short-end rule supplied ``y_roll``.
    """
    y_n = float(curve.at(tenor))
    if not np.isfinite(y_n):
        return None
    try:
        c, d, cx = bondmath.par_bond_risk(curve, tenor, freq)
    except ValueError:
        return None
    aged = tenor - DT
    flat = bool(aged < curve.tenors[0])
    y_roll = float(curve.at(aged))
    if not np.isfinite(y_roll):
        return None
    carry = y_n - r_short
    rolldown = (y_n - y_roll) * d
    return (
        {
            "yield": y_n,
            "r_short": r_short,
            "carry": carry,
            "rolldown": rolldown,
            "duration": d,
            "convexity": cx,
            "par_yield": c,
            "expected_return_1m": carry * DT + rolldown,
        },
        flat,
    )


def build_carry(zero: pd.DataFrame, funding: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, ...]:
    """``(carry.parquet frame, carry_missing.csv frame)`` from the zero panel and funding."""
    rates = funding_lookup(funding, cfg["hedge"]["funding_rate"])
    tenors = _standard_tenors(cfg)
    std = zero[zero["standard"] & zero["tenor_years"].isin(tenors)]
    rows: list[dict] = []
    missing: dict[tuple[str, float], int] = {}
    flats: dict[tuple[str, float], int] = {}
    for country, g in std.groupby("country", sort=True):
        freq = int(cfg["coupon_frequency"][country])
        by_date = dict(tuple(zero[zero["country"] == country].groupby("date", sort=False)))
        for date, m in g.groupby("date", sort=True):
            curve = Curve.from_panel(by_date[date], country, date)
            r_short = rates.get((country, pd.Timestamp(date)), np.nan)
            for tenor in sorted(float(t) for t in m["tenor_years"]):
                key = (country, tenor)
                flats.setdefault(key, 0)
                missing.setdefault(key, 0)
                out = None if not np.isfinite(r_short) else bucket(curve, tenor, freq, r_short)
                if out is None:
                    missing[key] += 1
                    continue
                vals, flat = out
                flats[key] += int(flat)
                rows.append({"date": date, "country": country, "tenor_years": tenor, **vals})
    carry = pd.DataFrame(rows, columns=CARRY_COLUMNS)
    carry = carry.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)
    miss = pd.DataFrame(
        [
            {
                "country": c,
                "tenor_years": t,
                "n_missing": missing[(c, t)],
                "n_flat_short_end": flats[(c, t)],
            }
            for (c, t) in sorted(missing)
        ],
        columns=CARRY_MISSING_COLUMNS,
    )
    return carry, miss


def build(cfg: dict, processed: Path | None = None, interim: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step carry``: ``carry.parquet`` and ``carry_missing.csv``."""
    from curvecarry.loaders import base

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    i = Path(interim) if interim is not None else base.INTERIM
    zero = pd.read_parquet(p / "curves_zero.parquet")
    funding = pd.read_parquet(i / "funding.parquet")
    carry, miss = build_carry(zero, funding, cfg)
    p.mkdir(parents=True, exist_ok=True)
    carry.to_parquet(p / "carry.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    miss.to_csv(checks.CARRY_MISSING, index=False, lineterminator="\n")
    return carry
