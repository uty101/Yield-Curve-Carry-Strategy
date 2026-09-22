"""Writers for ``data/checks/`` - the files the reviewer opens.

``coverage.csv``: one row per ``(country, tenor_years, curve_type, stage)``
with first and last date, months present, months missing between them and
the runs of two or more missing months. Rows for the same
``(country, curve_type, stage)`` are replaced on each write; every other row
is kept.

``sample_day_mismatch.csv`` (Session 1 fix, 2026-09-22): one row per
``(country, month)`` with the latest ``obs_date`` any tenor was sampled on
and the number of standard tenors (``config.tenors``) sampled on an earlier
day — the per-tenor sampling rule's footprint. Rows for a country are
replaced on each write. A check only; the sampling rule is unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CHECKS = Path("data/checks")
COVERAGE = CHECKS / "coverage.csv"
FUNDING_FILL = CHECKS / "funding_fill.csv"  # written by loaders.short_rates.load (Session 1 fix)
SAMPLE_DAY = CHECKS / "sample_day_mismatch.csv"  # written by every curve loader (Session 1 fix)
PAR_ZERO_GAP = CHECKS / "par_zero_gap.csv"  # step 1.9
US_ZERO_VS_GSW = CHECKS / "us_zero_vs_gsw.csv"  # step 1.9, Session 2 amendment 3
SAMPLE_WINDOW = CHECKS / "sample_window.txt"  # step 1.9
SAMPLE_WINDOW_BY_COUNTRY = CHECKS / "sample_window_by_country.csv"  # 1.9, per country
SAMPLE_DAY_COLUMNS = [
    "country",
    "date",
    "latest_obs_date",
    "n_standard_tenors",
    "n_earlier",
    "earlier_tenors",
]
COVERAGE_COLUMNS = [
    "country",
    "tenor_years",
    "curve_type",
    "stage",
    "first_date",
    "last_date",
    "months_present",
    "months_missing",
    "gaps",
]


def _gaps(present: pd.DatetimeIndex) -> tuple[int, str]:
    """(months missing between first and last, ';'-joined runs of >= 2 missing months)."""
    if len(present) == 0:
        return 0, ""
    full = pd.period_range(present.min(), present.max(), freq="M")
    have = set(present.to_period("M"))
    missing = [p for p in full if p not in have]
    runs, cur = [], []
    for p in missing:
        if cur and p != cur[-1] + 1:
            runs.append(cur)
            cur = []
        cur.append(p)
    if cur:
        runs.append(cur)
    text = ";".join(
        f"{r[0].strftime('%Y-%m')}..{r[-1].strftime('%Y-%m')}" for r in runs if len(r) >= 2
    )
    return len(missing), text


def coverage_rows(df: pd.DataFrame, stage: str) -> pd.DataFrame:
    rows = []
    for (country, tenor, ctype), g in df.groupby(["country", "tenor_years", "curve_type"]):
        idx = pd.DatetimeIndex(g["date"].unique()).sort_values()
        n_missing, gaps = _gaps(idx)
        rows.append(
            {
                "country": country,
                "tenor_years": float(tenor),
                "curve_type": ctype,
                "stage": stage,
                "first_date": idx.min().date().isoformat(),
                "last_date": idx.max().date().isoformat(),
                "months_present": len(idx),
                "months_missing": n_missing,
                "gaps": gaps,
            }
        )
    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def sample_day_rows(daily: pd.DataFrame, country: str, standard: list[float]) -> pd.DataFrame:
    """Per month: the latest ``obs_date`` any tenor was sampled on, and how many of the
    standard tenors were sampled on an earlier day (a tenor whose last print of the
    month is not the month's last print). ``daily`` has ``obs_date, tenor_years, yield``."""
    d = daily.dropna(subset=["yield"]).copy()
    d["obs_date"] = pd.to_datetime(d["obs_date"])
    d["date"] = (d["obs_date"] + pd.offsets.MonthEnd(0)).dt.normalize()
    sampled = d.groupby(["date", "tenor_years"], as_index=False)["obs_date"].max()
    rows = []
    for date, g in sampled.groupby("date"):
        latest = g["obs_date"].max()
        std = g[g["tenor_years"].isin([float(t) for t in standard])]
        earlier = std[std["obs_date"] < latest]
        rows.append(
            {
                "country": country,
                "date": date.date().isoformat(),
                "latest_obs_date": latest.date().isoformat(),
                "n_standard_tenors": len(std),
                "n_earlier": len(earlier),
                "earlier_tenors": ";".join(
                    f"{t:g}@{o.date().isoformat()}"
                    for t, o in zip(earlier["tenor_years"], earlier["obs_date"], strict=True)
                ),
            }
        )
    return pd.DataFrame(rows, columns=SAMPLE_DAY_COLUMNS)


def write_sample_day(
    daily: pd.DataFrame, country: str, standard: list[float], path: Path = SAMPLE_DAY
) -> pd.DataFrame:
    """Replace the rows for ``country`` in ``sample_day_mismatch.csv``; keep every other country."""
    new = sample_day_rows(daily, country, standard)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        out = pd.concat([old[old["country"] != country], new.astype(str)], ignore_index=True)
    else:
        out = new.astype(str)
    out = out.sort_values(["country", "date"]).reset_index(drop=True)
    out.to_csv(path, index=False, lineterminator="\n")
    return out


def write_coverage(df: pd.DataFrame, stage: str, path: Path = COVERAGE) -> pd.DataFrame:
    """Replace the rows for ``(country, curve_type, stage)`` present in ``df``; keep all others.

    The key includes ``curve_type`` so that the funding rows of step 1.7
    (``curve_type = funding_*``, keyed by country) never displace a country's
    curve rows.
    """
    new = coverage_rows(df, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        old = pd.read_csv(path, dtype={"gaps": str}, keep_default_na=False)
        drop = set(zip(new["country"], new["curve_type"], new["stage"], strict=True))
        keys = zip(old["country"], old["curve_type"], old["stage"], strict=True)
        keep = old[[k not in drop for k in keys]]
        out = pd.concat([keep, new], ignore_index=True)
    else:
        out = new
    out = out.sort_values(["stage", "country", "curve_type", "tenor_years"]).reset_index(drop=True)
    out.to_csv(path, index=False, lineterminator="\n")
    return out
