"""Step 3.1: PCA on monthly zero-yield changes, per country and pooled.

**The tenor set is chosen, not fixed** (session-3 amendment 1, as answered in
issue #15). A standard tenor is in a country's set if it is present in at
least ``config.pca.tenor_presence_min`` (0.95) of that country's months
counted **from the first month the country has a 10-year zero** — a country
enters the panel when it enters with a curve rather than a stub. That last
clause is the owner's ruling of 2026-09-23 and replaces the instruction's
"from the first month it enters the panel": read that way JP entered in
1974-09 with a curve stopping at 7 years, its 10-year point was present in
77.2% of its months, and the pooled intersection came out at 5 tenors, which
tripped the amendment's own stop condition. The stop condition is kept for a
re-run on changed data: fewer than 5 tenors for a country, or fewer than 6
pooled, raises ``TenorSetTooSmall``.

**The input is the zero panel** ``curves_zero.parquet`` in basis points of
monthly change — never the Phase 2 fitted yields (amendment 3). A month
enters only if **it and the previous calendar month** are both complete on
the set, so a gap is never bridged into a multi-month change reported as a
one-month one.

**Signs** (amendment 2, restated for a variable set): PC1 loading at 10
years > 0; PC2 at ``longest − 2`` years > 0; PC3 at the middle tenor of the
set > 0 (the lower of the two middles when the set is even); PC4+ first
non-zero element positive. 10 years is in all seven scopes, so no rule needs
a fallback.

**Two pooled fits** (issue #15 answer 5). ``pooled`` is the primary fit, on
the intersection of the six country sets; **it is the only pooled fit any
later step reads** — 5.4's PC2 z-score and 6.2's PC1 vol control take
``scope == "pooled"``. ``pooled_20y`` is a secondary fit on
``1, 2, 3, 5, 7, 10, 20`` over the months every country has complete on it,
reported beside the primary one and read by nothing after 3.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise
from curvecarry.interp import interpolate_yield

SIGN_PC1_TENOR = 10.0  # amendment 2: PC1 loading positive at 10 years
SIGN_PC2_OFFSET = 2.0  # PC2 positive at (longest tenor in the set) - 2 years
MIN_COUNTRY_TENORS = 5  # stop condition, amendment 1
MIN_POOLED_TENORS = 6
SECONDARY_POOLED_TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0]  # issue #15 answer 5
PRIMARY_POOLED = "pooled"
SECONDARY_POOLED = "pooled_20y"

TENOR_SET_COLUMNS = [
    "country",
    "tenors_used",
    "tenors_excluded",
    "months_available",
    "months_dropped_missing_tenor",
]
DROPPED_COLUMNS = ["country", "n_months_total", "n_dropped", "reason"]
EXPLAINED_COLUMNS = ["scope", "component", "eigenvalue", "explained_share", "n_months"]
LOADING_COLUMNS = ["scope", "component", "tenor_years", "loading"]
SCORE_COLUMNS = ["scope", "country", "date", "component", "score"]


class TenorSetTooSmall(RuntimeError):
    """Amendment 1's stop condition: a country set below 5, or a pooled set below 6."""


@dataclass(frozen=True)
class PCAResult:
    """One PCA. ``loadings`` is ``n x n``, column ``k`` the ``k``-th eigenvector."""

    tenors: np.ndarray
    loadings: np.ndarray
    eigenvalues: np.ndarray
    explained: np.ndarray
    mean: np.ndarray
    scores: np.ndarray


# --------------------------------------------------------------- tenor sets


def standard_wide(zero_panel: pd.DataFrame, country: str, cfg: dict) -> pd.DataFrame:
    """That country's standard zero yields, wide: index ``date``, columns ``config.tenors``."""
    std = harmonise.standard_tenors(cfg)
    z = zero_panel
    z = z[(z["country"] == country) & z["standard"].astype(bool) & z["yield"].notna()]
    wide = z.pivot_table(index="date", columns="tenor_years", values="yield")
    return wide.reindex(columns=std).sort_index()


def panel_start(wide: pd.DataFrame) -> pd.Timestamp | None:
    """The first month the country has a 10-year zero (issue #15, option C)."""
    if SIGN_PC1_TENOR not in wide.columns:
        return None
    return wide[SIGN_PC1_TENOR].first_valid_index()


def country_tenor_set(wide: pd.DataFrame, cfg: dict) -> list[float]:
    """Standard tenors present in >= ``pca.tenor_presence_min`` of months from ``panel_start``."""
    start = panel_start(wide)
    if start is None:
        return []
    window = wide[wide.index >= start]
    floor = float(cfg["pca"]["tenor_presence_min"])
    present = window.notna().mean()
    return [float(t) for t in wide.columns if present[t] >= floor]


def tenor_sets(zero_panel: pd.DataFrame, cfg: dict) -> dict[str, list[float]]:
    """Per-country sets plus ``pooled`` (their intersection) and ``pooled_20y``.

    Raises ``TenorSetTooSmall`` when amendment 1's stop condition fires.
    """
    sets: dict[str, list[float]] = {}
    for country in cfg["countries"]:
        wide = standard_wide(zero_panel, country, cfg)
        chosen = country_tenor_set(wide, cfg)
        if len(chosen) < MIN_COUNTRY_TENORS:
            raise TenorSetTooSmall(
                f"{country}: {len(chosen)} tenors {chosen}, fewer than {MIN_COUNTRY_TENORS}"
            )
        sets[country] = chosen
    pooled = sorted(set.intersection(*(set(v) for v in sets.values())))
    if len(pooled) < MIN_POOLED_TENORS:
        raise TenorSetTooSmall(
            f"pooled: {len(pooled)} tenors {pooled}, fewer than {MIN_POOLED_TENORS}"
        )
    sets[PRIMARY_POOLED] = pooled
    sets[SECONDARY_POOLED] = list(SECONDARY_POOLED_TENORS)
    return sets


def tenor_set_rows(zero_panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``data/checks/pca_tenor_sets.csv``: the choice, the exclusions and the month counts."""
    sets = tenor_sets(zero_panel, cfg)
    std = harmonise.standard_tenors(cfg)
    rows = []
    for country in cfg["countries"]:
        wide = standard_wide(zero_panel, country, cfg)
        chosen = sets[country]
        window = wide[wide.index >= panel_start(wide)]
        complete = window[chosen].notna().all(axis=1)
        rows.append(
            {
                "country": country,
                "tenors_used": ";".join(f"{t:g}" for t in chosen),
                "tenors_excluded": ";".join(f"{t:g}" for t in std if t not in chosen),
                "months_available": int(complete.sum()),
                "months_dropped_missing_tenor": int((~complete).sum()),
            }
        )
    return pd.DataFrame(rows, columns=TENOR_SET_COLUMNS)


# ----------------------------------------------------------------- changes


def monthly_changes_bp(
    zero_panel: pd.DataFrame, cfg: dict, sets: dict[str, list[float]] | None = None
) -> dict[str, pd.DataFrame]:
    """Per country: ``(y_t - y_{t-1}) * 1e4`` on that country's tenor set.

    A row is produced only where ``t`` and the **previous calendar month end**
    are both complete on the set, so a gap in the panel never becomes a
    multi-month change wearing a one-month label (amendment 3).
    """
    sets = tenor_sets(zero_panel, cfg) if sets is None else sets
    out: dict[str, pd.DataFrame] = {}
    for country in cfg["countries"]:
        out[country] = changes_on(standard_wide(zero_panel, country, cfg), sets[country])
    return out


def changes_on(wide: pd.DataFrame, tenors: list[float]) -> pd.DataFrame:
    """``wide`` restricted to ``tenors`` -> bp changes against the previous calendar month."""
    sub = wide[tenors].dropna(how="any")
    prev = sub.reindex(sub.index + pd.offsets.MonthEnd(-1))
    have_prev = prev.index.isin(sub.index)
    diff = (sub.to_numpy() - prev.to_numpy()) * 1e4
    out = pd.DataFrame(diff, index=sub.index, columns=tenors)
    return out[have_prev]


def dropped_rows(
    zero_panel: pd.DataFrame, cfg: dict, sets: dict[str, list[float]] | None = None
) -> pd.DataFrame:
    """``data/checks/pca_dropped.csv``: months of the panel that produce no change row, and why."""
    sets = tenor_sets(zero_panel, cfg) if sets is None else sets
    rows = []
    for country in cfg["countries"]:
        wide = standard_wide(zero_panel, country, cfg)
        chosen = sets[country]
        total = len(wide)
        start = panel_start(wide)
        before = int((wide.index < start).sum())
        window = wide[wide.index >= start]
        incomplete = int((~window[chosen].notna().all(axis=1)).sum())
        kept = len(changes_on(wide, chosen))
        rows.append(
            {
                "country": country,
                "n_months_total": total,
                "n_dropped": total - kept,
                "reason": (
                    f"before first 10y month ({before}); "
                    f"missing a set tenor ({incomplete}); "
                    f"no complete previous month ({total - before - incomplete - kept})"
                ),
            }
        )
    return pd.DataFrame(rows, columns=DROPPED_COLUMNS)


# --------------------------------------------------------------------- PCA


def middle_tenor(tenors: np.ndarray) -> float:
    """The middle entry of the sorted set; the lower of the two middles when it is even."""
    return float(np.asarray(tenors)[(len(tenors) - 1) // 2])


def _sign_targets(tenors: np.ndarray) -> list[float]:
    """The tenor each of PC1, PC2, PC3 is signed at (amendment 2)."""
    return [SIGN_PC1_TENOR, float(np.max(tenors)) - SIGN_PC2_OFFSET, middle_tenor(tenors)]


def loading_at(loadings_k: np.ndarray, tenors: np.ndarray, target: float) -> float:
    """One component's loading at ``target``, through the package's one interpolation function.

    PC1 and PC3 are signed at tenors that are always set members, so this is
    exact for them. PC2's tenor, ``longest - 2``, is **never** a member of any
    of the seven sets (10-2=8, 20-2=18, 30-2=28), so the loading there is read
    off the loading curve by ``interp.interpolate_yield`` — linear in tenor
    between the two adjacent set tenors, never extrapolated (rule 13). The
    alternative readings (the nearest set tenor at or below, or the longest
    tenor itself) give the same sign for every component of every scope; the
    check is in ``review/3.1.md``.
    """
    where = np.flatnonzero(np.isclose(tenors, target))
    if where.size:
        return float(loadings_k[where[0]])
    return float(interpolate_yield(tenors, loadings_k, target))


def apply_signs(loadings: np.ndarray, tenors: np.ndarray) -> np.ndarray:
    """PC1-3 signed at their named tenors; PC4+ by their first non-zero element."""
    tenors = np.asarray(tenors, dtype="float64")
    out = loadings.copy()
    for k in range(out.shape[1]):
        if k < 3:
            ref = loading_at(out[:, k], tenors, _sign_targets(tenors)[k])
        else:
            nz = np.flatnonzero(~np.isclose(out[:, k], 0.0))
            ref = out[nz[0], k] if nz.size else 1.0
        if ref < 0:
            out[:, k] = -out[:, k]
    return out


def pca(changes: np.ndarray, tenors: np.ndarray) -> PCAResult:
    """Covariance PCA of ``changes`` (rows = months, columns = ``tenors``), signs normalised."""
    x = np.asarray(changes, dtype="float64")
    tenors = np.asarray(tenors, dtype="float64")
    mean = x.mean(axis=0)
    centred = x - mean
    cov = np.cov(centred, rowvar=False, ddof=1)
    w, v = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    w, v = w[order], v[:, order]
    v = apply_signs(v, tenors)
    return PCAResult(
        tenors=tenors,
        loadings=v,
        eigenvalues=w,
        explained=w / w.sum(),
        mean=mean,
        scores=centred @ v,
    )


# ------------------------------------------------------------------- fits


def _frames(res: PCAResult, scope: str, dates: dict[str, pd.DatetimeIndex]) -> tuple:
    """``(explained rows, loading rows, score rows)`` for one fit."""
    n_months = sum(len(d) for d in dates.values())
    exp = pd.DataFrame(
        {
            "scope": scope,
            "component": np.arange(1, len(res.eigenvalues) + 1),
            "eigenvalue": res.eigenvalues,
            "explained_share": res.explained,
            "n_months": n_months,
        }
    )
    load = pd.DataFrame(
        [
            (scope, k + 1, float(t), float(res.loadings[i, k]))
            for k in range(res.loadings.shape[1])
            for i, t in enumerate(res.tenors)
        ],
        columns=LOADING_COLUMNS,
    )
    rows = []
    at = 0
    for country, idx in dates.items():
        block = res.scores[at : at + len(idx)]
        at += len(idx)
        for d, row in zip(idx, block, strict=True):
            for k, s in enumerate(row):
                rows.append((scope, country, d, k + 1, float(s)))
    return exp, load, pd.DataFrame(rows, columns=SCORE_COLUMNS)


def fit_country(changes: dict[str, pd.DataFrame], country: str) -> tuple:
    """One country's own PCA, on its own tenor set."""
    c = changes[country]
    res = pca(c.to_numpy(), np.array(c.columns, dtype="float64"))
    return (*_frames(res, country, {country: c.index}), res)


def fit_pooled(changes: dict[str, pd.DataFrame], tenors: list[float], scope: str) -> tuple:
    """Every country's changes on ``tenors``, each demeaned by its own column means, stacked.

    ``scope = "pooled"`` is the primary fit and the only pooled fit any step
    after 3.3 reads; ``scope = "pooled_20y"`` is the secondary one, on the
    months every country has complete on the 20-year set (issue #15 answer 5).
    """
    blocks, dates = [], {}
    for country, c in changes.items():
        if not set(tenors) <= set(c.columns):
            continue
        sub = c[tenors].dropna(how="any")
        if sub.empty:
            continue
        blocks.append(sub.to_numpy() - sub.to_numpy().mean(axis=0))
        dates[country] = sub.index
    stacked = np.vstack(blocks)
    # each block is already demeaned by its own column means, so the stacked
    # matrix has an exactly zero column mean and ``pca`` demeans a second time
    # for nothing; that is the plan's "demeaned by its own column means".
    res = pca(stacked, np.array(tenors, dtype="float64"))
    return (*_frames(res, scope, dates), res)


def secondary_changes(
    zero_panel: pd.DataFrame, cfg: dict, sets: dict[str, list[float]]
) -> dict[str, pd.DataFrame]:
    """Changes on the 20-year set, restricted to months **every** country has complete."""
    per = {}
    for country in cfg["countries"]:
        wide = standard_wide(zero_panel, country, cfg)
        per[country] = changes_on(wide, SECONDARY_POOLED_TENORS)
    common = sorted(set.intersection(*(set(c.index) for c in per.values())))
    return {k: v.loc[common] for k, v in per.items()}


def fit_all(zero_panel: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``(explained, loadings, scores)`` for the six countries and both pooled fits."""
    sets = tenor_sets(zero_panel, cfg)
    changes = monthly_changes_bp(zero_panel, cfg, sets)
    exp, load, score = [], [], []
    for country in cfg["countries"]:
        e, ld, sc, _ = fit_country(changes, country)
        exp.append(e)
        load.append(ld)
        score.append(sc)
    e, ld, sc, _ = fit_pooled(changes, sets[PRIMARY_POOLED], PRIMARY_POOLED)
    exp.append(e)
    load.append(ld)
    score.append(sc)
    e, ld, sc, _ = fit_pooled(
        secondary_changes(zero_panel, cfg, sets), SECONDARY_POOLED_TENORS, SECONDARY_POOLED
    )
    exp.append(e)
    load.append(ld)
    score.append(sc)
    return (
        pd.concat(exp, ignore_index=True)[EXPLAINED_COLUMNS],
        pd.concat(load, ignore_index=True)[LOADING_COLUMNS],
        pd.concat(score, ignore_index=True)[SCORE_COLUMNS],
    )


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step pca``: the tenor sets, both pooled fits and the six country fits."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    tenor_set_rows(zero, cfg).to_csv(checks.PCA_TENOR_SETS, index=False, lineterminator="\n")
    dropped_rows(zero, cfg).to_csv(checks.PCA_DROPPED, index=False, lineterminator="\n")
    explained, loadings, scores = fit_all(zero, cfg)
    explained.to_csv(checks.PCA_EXPLAINED, index=False, lineterminator="\n")
    loadings.to_parquet(p / "pca_loadings.parquet", index=False)
    scores.to_parquet(p / "pca_scores.parquet", index=False)
    return scores
