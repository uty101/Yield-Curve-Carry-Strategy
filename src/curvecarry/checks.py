"""Writers for ``data/checks/`` - the files the reviewer opens.

``coverage.csv``: one row per ``(country, tenor_years, curve_type, stage)``
with first and last date, months present, months missing between them and
the runs of two or more missing months. Rows for the same
``(country, curve_type, stage)`` are replaced on each write; every other row
is kept.

``sample_day_mismatch.csv`` (Session 1 part A fix, 2026-09-22): one row per
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
# written by loaders.short_rates.load (Session 1 part A fix)
FUNDING_FILL = CHECKS / "funding_fill.csv"
# written by every curve loader (Session 1 part A fix)
SAMPLE_DAY = CHECKS / "sample_day_mismatch.csv"
PAR_ZERO_GAP = CHECKS / "par_zero_gap.csv"  # step 1.9
US_ZERO_VS_GSW = CHECKS / "us_zero_vs_gsw.csv"  # step 1.9, Session 1 part B amendment 3
BOOTSTRAP_DROPPED = CHECKS / "bootstrap_dropped.csv"  # step 1.9, Session 1 part B fix 3
US_PAR_VS_GSW = CHECKS / "us_par_vs_gsw.csv"  # step 1.9, Session 1 part B fix 4a
BOOTSTRAP_ON_GSW = CHECKS / "bootstrap_on_gsw.csv"  # step 1.9, Session 1 part B fix 4b
SAMPLE_WINDOW = CHECKS / "sample_window.txt"  # step 1.9
SAMPLE_WINDOW_BY_COUNTRY = CHECKS / "sample_window_by_country.csv"  # 1.9, per country
PAR_REPRICE = CHECKS / "par_reprice.csv"  # step 2.1, session-2 amendment 1
FIT_SKIPPED = CHECKS / "fit_skipped.csv"  # steps 2.2 and 2.3 (PLAN.md, Phase 2 preamble)
FIT_HOLDOUT = CHECKS / "fit_holdout.csv"  # steps 2.2 and 2.3, session-2 amendment 3
SVENSSON_VS_BUNDESBANK = CHECKS / "svensson_vs_bundesbank.csv"  # step 2.3
CHART1_DATES = CHECKS / "chart1_dates.csv"  # step 2.4
CHART3_EXCLUDED = CHECKS / "chart3_excluded.csv"  # step 2.4, issue #14 option K
PCA_TENOR_SETS = CHECKS / "pca_tenor_sets.csv"  # step 3.1, session-3 amendment 1
PCA_DROPPED = CHECKS / "pca_dropped.csv"  # step 3.1
PCA_EXPLAINED = CHECKS / "pca_explained.csv"  # step 3.1
PCA_STABILITY = CHECKS / "pca_stability.csv"  # step 3.2
PCA_CHANGE_VOL = CHECKS / "pca_change_vol.csv"  # step 3.2, session-3 fix round
PCA_EXPLAINED_TABLE = CHECKS / "pca_explained_table.md"  # step 3.3
CARRY_MISSING = CHECKS / "carry_missing.csv"  # step 4.1
RETURN_APPROX_GAP = CHECKS / "return_approx_gap.csv"  # step 4.2
CLOSED_BUCKETS = CHECKS / "closed_buckets.csv"  # steps 4.2 and 4.3
UNIVERSE_BY_MONTH = CHECKS / "universe_by_month.csv"  # step 4.2, session-4 amendment 1
RETURN_IDENTITY = CHECKS / "return_identity.csv"  # step 4.2, session-4 amendment 2
RETURN_COVERAGE = CHECKS / "return_coverage.csv"  # step 4.3, session-4 amendment 3
XCCY_BASIS = CHECKS / "xccy_basis.csv"  # step 4.3, if a basis series is found
SIGNAL_EXCLUSIONS = CHECKS / "signal_exclusions.csv"  # step 5.1
UNIVERSE_ELIGIBLE = CHECKS / "universe_eligible.csv"  # step 5.1, session-5 amendment 3
UNIVERSE_CHANGES = CHECKS / "universe_changes.csv"  # step 5.1, session-5 amendment 3
WEIGHTS_EMPTY_MONTHS = CHECKS / "weights_empty_months.csv"  # step 5.2
OVERLAY_TRADES = CHECKS / "overlay_trades.csv"  # step 5.4, one row per trade (session-5 fix 1)
OVERLAY_COUNTRY_STATS = CHECKS / "overlay_country_stats.csv"  # session-5 fix 1
OVERLAY_SKIPPED = CHECKS / "overlay_skipped.csv"  # step 5.4, a country-month with no leg duration
METRICS_TABLE = CHECKS / "metrics_table.csv"  # step 5.5
METRICS_TABLE_MD = CHECKS / "metrics_table.md"  # step 5.5
UNHEDGED_FX_EXPOSURE = CHECKS / "unhedged_fx_exposure.csv"  # session-5 fix 2
DECOMPOSITION_SHARES = CHECKS / "decomposition_shares.csv"  # step 6.1
ATTRIBUTION_2022 = CHECKS / "attribution_2022"  # step 6.2, one file per variant (suffix added)
RISK_CONTROLS = CHECKS / "risk_controls.csv"  # step 6.2, each control against its base
RATES_VOL_FILTER = CHECKS / "rates_vol_filter.csv"  # step 6.2, the pooled PC1 vol and its flag
NS_LAMBDA_BOUND = CHECKS / "ns_lambda_bound.csv"  # step 6.3, the share of months lambda is pinned
SECTION_6_3 = CHECKS / "section_6_3.md"  # step 6.3
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
