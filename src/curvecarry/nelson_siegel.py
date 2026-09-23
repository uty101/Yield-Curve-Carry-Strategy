"""Step 2.2: the Nelson-Siegel curve, fitted to the zero panel.

The brief's 6.1 form, with ``lambda`` per year (not the ``tau`` decay time of
the Bundesbank's Svensson files, ``lambda = 1/tau``):

    z(tau) = b0 + b1 (1 - e^{-l tau})/(l tau)
                + b2 [(1 - e^{-l tau})/(l tau) - e^{-l tau}]

For a fixed ``lambda`` the three betas are linear, so the fit is OLS; only
``lambda`` needs searching. ``fit`` walks the grid
``config.nelson_siegel.ns_lambda_grid`` (lo, hi, step), takes the best grid
point and polishes it with a bounded ``minimize_scalar`` inside one grid step.
``ns_dl`` is the Diebold-Li variant: ``lambda`` fixed at
``config.nelson_siegel.ns_lambda_fixed``, betas by OLS.

**All fits use the 8 standard tenors only** (``standard == True`` in
``curves_zero.parquet``), which is what makes the held-out check of
session-2 amendment 3 a held-out check. A country-month with fewer than
``config.nelson_siegel.min_tenors`` non-null standard tenors is not fitted
and is one row of ``data/checks/fit_skipped.csv``.

``holdout_errors`` (amendment 3) is here rather than in a module of its own
because 2.2 owns the fitted-yield-from-parameters path; ``svensson.build``
calls it again once ``sv`` rows exist, so ``fit_holdout.csv`` ends the
session with all three models in it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from curvecarry import checks, harmonise

PARAM_COLUMNS = [
    "date",
    "country",
    "model",
    "beta0",
    "beta1",
    "beta2",
    "lam",
    "rmse_bp",
    "n_tenors",
    "lam_at_bound",
    "ns_degenerate",
]
LAM_BOUND_ATOL = 1e-12  # issue #14 option K: lam counts as "at a bound" within this
# session 2 fix round: a level factor of -22% is not a level factor. 0.5 in decimal
# yield units is 50 percentage points.
BETA_DEGENERATE_MAX = 0.5
FITTED_COLUMNS = ["date", "country", "model", "tenor_years", "fitted"]
SKIPPED_COLUMNS = ["country", "date", "n_standard_tenors", "reason"]
HOLDOUT_COLUMNS = [
    "country",
    "date",
    "model",
    "tenor_years",
    "observed",
    "fitted",
    "error_bp",
    "zero_kind",
]
# amendment 3: where the held-out points come from, per country
HOLDOUT_OBSERVED = ("GB", "CA", "JP")  # non-standard tenors with interpolated == False
HOLDOUT_BOOTSTRAPPED = ("US", "FR")  # non-standard coupon-grid zeros of the bootstrap
HOLDOUT_MIN_TENOR, HOLDOUT_MAX_TENOR = 1.0, 30.0


@dataclass(frozen=True)
class NSFit:
    beta0: float
    beta1: float
    beta2: float
    lam: float
    rmse_bp: float
    n_tenors: int


def ns_loadings(tau: np.ndarray, lam: float) -> np.ndarray:
    """(n x 3) design matrix ``[1, slope, curvature]`` at maturities ``tau``, decay ``lam``."""
    t = np.asarray(tau, dtype="float64")
    assert lam > 0, f"lambda must be positive, got {lam}"
    x = lam * t
    slope = np.where(x == 0, 1.0, (1.0 - np.exp(-x)) / np.where(x == 0, 1.0, x))
    return np.column_stack([np.ones_like(t), slope, slope - np.exp(-x)])


def _rmse(y: np.ndarray, fit: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - fit) ** 2)))


def fit_fixed_lambda(tau: np.ndarray, y: np.ndarray, lam: float) -> tuple[np.ndarray, float]:
    """OLS betas at a given ``lam``, and the RMSE in **decimal** (not bp)."""
    x = ns_loadings(tau, lam)
    beta, *_ = np.linalg.lstsq(x, np.asarray(y, dtype="float64"), rcond=None)
    return beta, _rmse(np.asarray(y, dtype="float64"), x @ beta)


def lam_at_bound(lam: float | np.ndarray, grid: tuple[float, float, float]) -> bool | np.ndarray:
    """True where ``lam`` sits on either end of the grid (issue #14, option K).

    A bound hit is a constraint, not an estimate: the RMSE was still falling when
    the search ran out of grid. It is flagged rather than fixed because widening
    the grid does not remove it — lambda -> 0 is a degeneracy of Nelson-Siegel on
    a flat curve, where the slope loading tends to the level loading and the
    betas run away to cancel (``decisions/lambda_bound.md``). Chart 3 leaves
    these months as gaps in its NS-free panel.
    """
    lo, hi = float(grid[0]), float(grid[1])
    x = np.asarray(lam, dtype="float64")
    out = np.isclose(x, lo, rtol=0.0, atol=LAM_BOUND_ATOL) | np.isclose(
        x, hi, rtol=0.0, atol=LAM_BOUND_ATOL
    )
    return bool(out) if np.ndim(lam) == 0 else out


def beta_degenerate(
    beta0: float | np.ndarray, beta1: float | np.ndarray, beta2: float | np.ndarray
) -> bool | np.ndarray:
    """True where ``max(|beta0|, |beta1|, |beta2|)`` exceeds ``BETA_DEGENERATE_MAX``.

    The betas are decimal yields, so the threshold is 50 **percentage points**.
    A fit that reports a level of -22% cancelled by a slope of +22% is not
    reporting a level and a slope, whatever its RMSE.
    """
    b = np.maximum(np.maximum(np.abs(beta0), np.abs(beta1)), np.abs(beta2))
    out = np.asarray(b, dtype="float64") > BETA_DEGENERATE_MAX
    return bool(out) if np.ndim(b) == 0 else out


def ns_degenerate(
    lam_bound: bool | np.ndarray,
    beta0: float | np.ndarray,
    beta1: float | np.ndarray,
    beta2: float | np.ndarray,
) -> bool | np.ndarray:
    """``lam_at_bound`` **or** ``beta_degenerate``: the months Chart 3 leaves as gaps.

    ``lam_at_bound`` alone missed months whose lambda is just inside the bound
    and whose loadings are still nearly collinear — GB 2010-02-28 at
    lambda = 0.0539 fits to 3.19 bp with beta2 = +50.2%. Both criteria are kept
    as separate columns; ``decisions/lambda_bound.md`` refers to the first.
    """
    out = np.asarray(lam_bound, dtype=bool) | np.asarray(
        beta_degenerate(beta0, beta1, beta2), dtype=bool
    )
    return bool(out) if np.ndim(out) == 0 else out


def lambda_grid(grid: tuple[float, float, float]) -> np.ndarray:
    """``np.arange(lo, hi + step/2, step)`` - the grid the plan names, hi included."""
    lo, hi, step = (float(v) for v in grid)
    return np.arange(lo, hi + step / 2.0, step)


def fit(tau: np.ndarray, y: np.ndarray, grid: tuple[float, float, float]) -> NSFit:
    """Grid search on ``lambda``, then a bounded polish inside one grid step of the winner."""
    lo, hi, step = (float(v) for v in grid)
    lams = lambda_grid(grid)
    rmses = np.array([fit_fixed_lambda(tau, y, lam)[1] for lam in lams])
    best = float(lams[int(np.argmin(rmses))])
    a, b = max(lo, best - step), min(hi, best + step)
    if b > a:
        res = minimize_scalar(
            lambda lam: fit_fixed_lambda(tau, y, lam)[1],
            bounds=(a, b),
            method="bounded",
            options={"xatol": 1e-10},
        )
        if float(res.fun) <= float(rmses.min()):
            best = float(res.x)
    beta, rmse = fit_fixed_lambda(tau, y, best)
    return NSFit(*(float(v) for v in beta), best, rmse * 1e4, int(np.size(tau)))


def standard_points(zero_panel: pd.DataFrame) -> pd.DataFrame:
    """The 8 standard tenors with a non-null yield - the only points any fit sees."""
    z = zero_panel[zero_panel["standard"].astype(bool)]
    return z[z["yield"].notna()]


def skipped(zero_panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``fit_skipped.csv``: country-months with fewer than ``min_tenors`` standard tenors."""
    need = int(cfg["nelson_siegel"]["min_tenors"])
    months = zero_panel[["country", "date"]].drop_duplicates()
    idx = pd.MultiIndex.from_frame(months.sort_values(["country", "date"]))
    n = standard_points(zero_panel).groupby(["country", "date"]).size()
    n = n.reindex(idx, fill_value=0).rename("n")  # a month with no standard tenor at all counts
    bad = n[n < need].reset_index()
    bad["n_standard_tenors"] = bad["n"].astype(int)
    bad["reason"] = f"fewer than min_tenors ({need}) non-null standard tenors"
    out = bad[SKIPPED_COLUMNS]
    return out.sort_values(["country", "date"]).reset_index(drop=True)


def fit_panel(zero_panel: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(ns_params, ns_fitted)`` for both models over every fittable country-month."""
    need = int(cfg["nelson_siegel"]["min_tenors"])
    grid = tuple(cfg["nelson_siegel"]["ns_lambda_grid"])
    lam_dl = float(cfg["nelson_siegel"]["ns_lambda_fixed"])
    pts = standard_points(zero_panel)
    params: list[tuple] = []
    fitted: list[tuple] = []
    for (country, date), g in pts.groupby(["country", "date"], sort=True):
        g = g.sort_values("tenor_years")
        tau = g["tenor_years"].to_numpy(dtype="float64")
        y = g["yield"].to_numpy(dtype="float64")
        if tau.size < need:
            continue
        free = fit(tau, y, grid)
        beta_dl, rmse_dl = fit_fixed_lambda(tau, y, lam_dl)
        dl = NSFit(*(float(v) for v in beta_dl), lam_dl, rmse_dl * 1e4, int(tau.size))
        for model, f in (("ns_free", free), ("ns_dl", dl)):
            params.append(
                (
                    date,
                    country,
                    model,
                    f.beta0,
                    f.beta1,
                    f.beta2,
                    f.lam,
                    f.rmse_bp,
                    f.n_tenors,
                    lam_at_bound(f.lam, grid),
                    ns_degenerate(lam_at_bound(f.lam, grid), f.beta0, f.beta1, f.beta2),
                )
            )
            vals = ns_loadings(tau, f.lam) @ np.array([f.beta0, f.beta1, f.beta2])
            for t, v in zip(tau, vals, strict=True):
                fitted.append((date, country, model, float(t), float(v)))
    p = pd.DataFrame(params, columns=PARAM_COLUMNS)
    p["lam_at_bound"] = p["lam_at_bound"].astype(bool)
    p["ns_degenerate"] = p["ns_degenerate"].astype(bool)
    f = pd.DataFrame(fitted, columns=FITTED_COLUMNS)
    p = p.sort_values(["country", "date", "model"]).reset_index(drop=True)
    f = f.sort_values(["country", "date", "model", "tenor_years"]).reset_index(drop=True)
    return p, f


def fitted_at(params_row: pd.Series, tau: np.ndarray) -> np.ndarray:
    """Fitted yields at arbitrary maturities from one row of ``ns_params`` or ``sv_params``."""
    if "beta3" in params_row.index and pd.notna(params_row.get("beta3")):
        from curvecarry.svensson import sv_loadings

        x = sv_loadings(tau, float(params_row["lam1"]), float(params_row["lam2"]))
        beta = np.array([params_row[f"beta{i}"] for i in range(4)], dtype="float64")
    else:
        x = ns_loadings(tau, float(params_row["lam"]))
        beta = np.array([params_row[f"beta{i}"] for i in range(3)], dtype="float64")
    return x @ beta


def holdout_points(zero_panel: pd.DataFrame) -> pd.DataFrame:
    """Amendment 3: the non-standard zeros each country is tested on, with ``zero_kind``.

    ``GB, CA, JP`` - observed non-standard tenors (``interpolated == False``).
    ``US, FR`` - the bootstrapped non-standard coupon-grid zeros, labelled
    ``bootstrapped``. Both are restricted to ``[1, 30]`` years. DE is not in
    either list: its whole curve is reconstructed from the Bundesbank's own
    Svensson parameters, so a non-standard DE tenor is not an observation.
    """
    z = zero_panel[~zero_panel["standard"].astype(bool) & zero_panel["yield"].notna()]
    z = z[z["tenor_years"].between(HOLDOUT_MIN_TENOR, HOLDOUT_MAX_TENOR)]
    obs = z[z["country"].isin(HOLDOUT_OBSERVED) & ~z["interpolated"].astype(bool)].copy()
    obs["zero_kind"] = np.where(obs["bootstrapped"].astype(bool), "bootstrapped", "observed")
    boot = z[z["country"].isin(HOLDOUT_BOOTSTRAPPED)].copy()
    boot["zero_kind"] = "bootstrapped"
    out = pd.concat([obs, boot], ignore_index=True)
    return out.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)


def holdout_errors(zero_panel: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    """Every model in ``params`` evaluated at the held-out tenors of ``holdout_points``."""
    pts = holdout_points(zero_panel)
    by_key = {
        (c, d, m): row
        for (c, d, m), row in params.set_index(["country", "date", "model"]).iterrows()
    }
    models = sorted(params["model"].unique())
    rows: list[tuple] = []
    for (country, date), g in pts.groupby(["country", "date"], sort=True):
        tau = g["tenor_years"].to_numpy(dtype="float64")
        obs = g["yield"].to_numpy(dtype="float64")
        kind = g["zero_kind"].to_numpy()
        for model in models:
            row = by_key.get((country, date, model))
            if row is None:
                continue
            vals = fitted_at(row, tau)
            for t, o, v, k in zip(tau, obs, vals, kind, strict=True):
                rows.append((country, date, model, float(t), float(o), float(v), (v - o) * 1e4, k))
    out = pd.DataFrame(rows, columns=HOLDOUT_COLUMNS)
    return out.sort_values(["country", "date", "model", "tenor_years"]).reset_index(drop=True)


def holdout_summary(holdout: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    """Per country and model: median and p95 of the monthly held-out RMSE, next to in-sample."""
    h = holdout.copy()
    h["sq"] = h["error_bp"] ** 2
    monthly = h.groupby(["country", "model", "date"])["sq"].mean().pow(0.5).rename("rmse_bp")
    out = monthly.groupby(["country", "model"]).agg(
        holdout_rmse_median_bp="median",
        holdout_rmse_p95_bp=lambda s: s.quantile(0.95),
        months="size",
    )
    ins = params.groupby(["country", "model"])["rmse_bp"].agg(
        in_sample_rmse_median_bp="median",
        in_sample_rmse_p95_bp=lambda s: s.quantile(0.95),
    )
    out = out.join(ins, how="left")
    out["ratio_holdout_over_in_sample"] = (
        out["holdout_rmse_median_bp"] / out["in_sample_rmse_median_bp"]
    )
    return out.reset_index().sort_values(["country", "model"]).reset_index(drop=True)


def write_holdout(zero_panel: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    """Write ``data/checks/fit_holdout.csv`` for whatever models ``params`` holds."""
    out = holdout_errors(zero_panel, params)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    out.to_csv(checks.FIT_HOLDOUT, index=False, lineterminator="\n")
    return out


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step ns``: the two NS models over ``curves_zero.parquet``."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    params, fitted = fit_panel(zero, cfg)
    params.to_parquet(p / "ns_params.parquet", index=False)
    fitted.to_parquet(p / "ns_fitted.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    skipped(zero, cfg).to_csv(checks.FIT_SKIPPED, index=False, lineterminator="\n")
    write_holdout(zero, params)
    return params
