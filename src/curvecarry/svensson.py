"""The Svensson (1994) spot-rate function, and (step 2.3) the fit of it.

The Bundesbank's decay-time form, built in step 1.3:

    z(m) = b0 + b1 (1 - e^{-m/t1})/(m/t1)
              + b2 [(1 - e^{-m/t1})/(m/t1) - e^{-m/t1}]
              + b3 [(1 - e^{-m/t2})/(m/t2) - e^{-m/t2}]

with ``m`` the maturity in years and ``t1, t2`` decay *times* in years.
Deutsche Bundesbank, Monthly Report October 1997 and Discussion Paper 4/97
(Schich); the Bundesbank's z is an annually compounded spot rate
(``decisions/compounding.md``).

**Step 2.3** adds the lambda form (``lambda = 1/tau``) used everywhere else in
this package: ``sv_loadings``, ``fit`` (a grid over ordered pairs
``lam2 > lam1 + step`` from ``config.nelson_siegel.ns_lambda_grid``, then
Nelder-Mead), ``fit_panel`` and the Germany benchmark ``compare_bundesbank``.
Ordering the pair is what removes the label swap: ``(b2, lam1)`` and
``(b3, lam2)`` enter the *curvature* the same way, so the two are near
indistinguishable without an ordering. The exchange is not an exact symmetry:
``lam1`` also carries the slope loading (see ``bundesbank_to_lambda``).

**Session-2 amendment 2.** The Bundesbank publishes no such ordering, so
``bundesbank_to_lambda`` converts ``(tau1, tau2)`` to ``(1/tau1, 1/tau2)`` and,
where ``1/tau2 < 1/tau1``, swaps the labels **and** ``beta2`` with ``beta3``.
``swapped`` records it per month in ``data/checks/svensson_vs_bundesbank.csv``
and, after the issue #12 answer, the swap is used for the **lambda** comparison
only: ``beta_diff_max`` is computed against the original, unswapped betas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from curvecarry import checks, harmonise, nelson_siegel
from curvecarry.loaders import base

PARAM_COLUMNS = [
    "date",
    "country",
    "model",
    "beta0",
    "beta1",
    "beta2",
    "beta3",
    "lam1",
    "lam2",
    "lam_gap",
    "rmse_bp",
    "n_tenors",
]
BBK_COLUMNS = [
    "date",
    "rmse_ours_bp",
    "rmse_bbk_bp",
    "lam1_ours",
    "lam2_ours",
    "lam1_bbk",
    "lam2_bbk",
    "lam_gap_ours",
    "lam_gap_bbk",
    "beta_diff_max",
    "swapped",
    "bbk_lam_outside_grid",
]
MODEL = "sv"
DE = "DE"


def _term(m: np.ndarray, t: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = m / t
    slope = np.where(x == 0, 1.0, (1.0 - np.exp(-x)) / np.where(x == 0, 1.0, x))
    return slope, slope - np.exp(-x)


def svensson_yield(
    m: float | np.ndarray,
    beta0: float | np.ndarray,
    beta1: float | np.ndarray,
    beta2: float | np.ndarray,
    beta3: float | np.ndarray,
    tau1: float | np.ndarray,
    tau2: float | np.ndarray,
) -> np.ndarray:
    """Spot rate at maturity ``m`` (years); units follow the betas (decimal in, decimal out)."""
    m = np.asarray(m, dtype=float)
    s1, c1 = _term(m, np.asarray(tau1, dtype=float))
    _, c2 = _term(m, np.asarray(tau2, dtype=float))
    return beta0 + beta1 * s1 + beta2 * c1 + beta3 * c2


@dataclass(frozen=True)
class SVFit:
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    lam1: float
    lam2: float
    lam_gap: float
    rmse_bp: float
    n_tenors: int


def sv_loadings(tau: np.ndarray, lam1: float, lam2: float) -> np.ndarray:
    """(n x 4): the three NS loadings at ``lam1``, plus the second curvature at ``lam2``."""
    assert lam1 > 0 and lam2 > 0, f"lambdas must be positive, got {lam1}, {lam2}"
    t = np.asarray(tau, dtype="float64")
    ns = nelson_siegel.ns_loadings(t, lam1)
    x2 = lam2 * t
    slope2 = np.where(x2 == 0, 1.0, (1.0 - np.exp(-x2)) / np.where(x2 == 0, 1.0, x2))
    return np.column_stack([ns, slope2 - np.exp(-x2)])


def fit_fixed_lambdas(
    tau: np.ndarray, y: np.ndarray, lam1: float, lam2: float
) -> tuple[np.ndarray, float]:
    """OLS betas at a given ``(lam1, lam2)``, and the RMSE in **decimal**."""
    x = sv_loadings(tau, lam1, lam2)
    yy = np.asarray(y, dtype="float64")
    beta, *_ = np.linalg.lstsq(x, yy, rcond=None)
    return beta, float(np.sqrt(np.mean((yy - x @ beta) ** 2)))


def lambda_pairs(grid: tuple[float, float, float]) -> list[tuple[float, float]]:
    """Ordered pairs ``lam2 > lam1 + step`` from the shared lambda grid."""
    lams = nelson_siegel.lambda_grid(grid)
    step = float(grid[2])
    return [(float(a), float(b)) for a in lams for b in lams if b > a + step - 1e-12]


def _project(v: np.ndarray, lo: float, hi: float, step: float) -> tuple[float, float]:
    """The feasible pair nearest ``v``: inside ``[lo, hi]`` and ``lam2 >= lam1 + step``.

    Issue #12 answer Q2, option D. The grid already searches only ordered pairs
    with a full step between them; before the fix the Nelder-Mead polish was
    clipped to ``[lo, hi]`` alone and could drive ``lam2`` onto ``lam1``, which
    makes the two curvature columns of ``sv_loadings`` identical and blows the
    betas up to 1e11 as a difference of two large numbers. The separation is
    now the same in the polish as in the grid.
    """
    a, b = float(np.clip(v[0], lo, hi)), float(np.clip(v[1], lo, hi))
    if b < a:
        a, b = b, a
    if b < a + step:
        mid = 0.5 * (a + b)
        a, b = mid - step / 2.0, mid + step / 2.0
        if a < lo:
            a, b = lo, lo + step
        if b > hi:
            a, b = hi - step, hi
    return a, b


def fit(tau: np.ndarray, y: np.ndarray, grid: tuple[float, float, float]) -> SVFit:
    """Grid over ordered ``(lam1, lam2)`` pairs, then Nelder-Mead from the best pair.

    The polish honours the grid's own separation ``lam2 >= lam1 + step`` as well
    as ``[lo, hi]`` (issue #12 Q2, option D).
    """
    lo, hi, step = (float(v) for v in grid)
    assert hi - lo >= step, f"lambda grid {grid} is narrower than one step"
    pairs = lambda_pairs(grid)
    rmses = [fit_fixed_lambdas(tau, y, a, b)[1] for a, b in pairs]
    k = int(np.argmin(rmses))
    best, best_rmse = pairs[k], float(rmses[k])

    def objective(v: np.ndarray) -> float:
        return fit_fixed_lambdas(tau, y, *_project(v, lo, hi, step))[1]

    res = minimize(
        objective,
        np.array(best),
        method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-14},
    )
    lam1, lam2 = _project(res.x, lo, hi, step)
    if float(res.fun) > best_rmse or not np.isfinite(res.fun):
        lam1, lam2 = best
    beta, rmse = fit_fixed_lambdas(tau, y, lam1, lam2)
    return SVFit(
        *(float(v) for v in beta),
        lam1,
        lam2,
        abs(lam2 - lam1),
        rmse * 1e4,
        int(np.size(tau)),
    )


def fit_panel(zero_panel: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(sv_params, sv_fitted)`` over every country-month with enough standard tenors."""
    need = int(cfg["nelson_siegel"]["min_tenors"])
    grid = tuple(cfg["nelson_siegel"]["ns_lambda_grid"])
    pts = nelson_siegel.standard_points(zero_panel)
    params: list[tuple] = []
    fitted: list[tuple] = []
    for (country, date), g in pts.groupby(["country", "date"], sort=True):
        g = g.sort_values("tenor_years")
        tau = g["tenor_years"].to_numpy(dtype="float64")
        y = g["yield"].to_numpy(dtype="float64")
        if tau.size < need:
            continue
        f = fit(tau, y, grid)
        params.append(
            (
                date,
                country,
                MODEL,
                f.beta0,
                f.beta1,
                f.beta2,
                f.beta3,
                f.lam1,
                f.lam2,
                f.lam_gap,
                f.rmse_bp,
                f.n_tenors,
            )
        )
        vals = sv_loadings(tau, f.lam1, f.lam2) @ np.array([f.beta0, f.beta1, f.beta2, f.beta3])
        for t, v in zip(tau, vals, strict=True):
            fitted.append((date, country, MODEL, float(t), float(v)))
    p = pd.DataFrame(params, columns=PARAM_COLUMNS)
    f = pd.DataFrame(fitted, columns=nelson_siegel.FITTED_COLUMNS)
    p = p.sort_values(["country", "date"]).reset_index(drop=True)
    f = f.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)
    return p, f


def bundesbank_to_lambda(row: pd.Series) -> dict:
    """Amendment 2: ``(tau1, tau2)`` -> ordered ``(lam1, lam2)`` with the betas carried along.

    ``lambda = 1/tau``. Where ``1/tau2 < 1/tau1`` the two curvature terms are
    relabelled — ``lam1`` with ``lam2`` **and** ``beta2`` with ``beta3`` — so
    that both sides of the comparison use ``lam2 > lam1``.

    **This is a labelling convention, not an identity.** ``lam1`` drives the
    slope loading as well as the first curvature, so the swap leaves the curve
    unchanged only when ``beta1 = 0``; on a real month it moves the curve by
    tens of basis points. Use it to line the two parameter sets up for
    comparison, never to re-evaluate a curve.
    """
    lam1, lam2 = 1.0 / float(row["tau1"]), 1.0 / float(row["tau2"])
    beta2, beta3 = float(row["beta2"]), float(row["beta3"])
    swapped = lam2 < lam1
    if swapped:
        lam1, lam2 = lam2, lam1
        beta2, beta3 = beta3, beta2
    return {
        "beta0": float(row["beta0"]),
        "beta1": float(row["beta1"]),
        "beta2": beta2,
        "beta3": beta3,
        "lam1": lam1,
        "lam2": lam2,
        "swapped": bool(swapped),
    }


def compare_bundesbank(
    cfg: dict, processed: Path | None = None, interim: Path | None = None
) -> pd.DataFrame:
    """``data/checks/svensson_vs_bundesbank.csv``: our DE fit against the published parameters.

    ``rmse_bbk_bp`` is the Bundesbank's own parameters scored against the DE
    panel, **in their original labelling**. The panel *is* those parameters
    evaluated at the standard tenors (step 1.3), so it is zero by
    construction; it is in the file as the control that says the conversion
    and the sampling line up. It is deliberately not scored after the
    amendment-2 swap: the swap is a labelling convention for comparing
    parameters, **not** a curve-preserving transformation. ``lambda1`` carries
    the slope loading as well as the first curvature, so exchanging
    ``(beta2, lam1)`` with ``(beta3, lam2)`` leaves the curve unchanged only
    when ``beta1 = 0``; on a real month it moves the curve by tens of basis
    points. See ``review/2.3.md``.
    """
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    i = Path(interim) if interim is not None else base.INTERIM
    lo, hi = (
        float(cfg["nelson_siegel"]["ns_lambda_grid"][0]),
        float(cfg["nelson_siegel"]["ns_lambda_grid"][1]),
    )
    zero = pd.read_parquet(p / "curves_zero.parquet")
    zero = zero[zero["country"] == DE]
    ours = pd.read_parquet(p / "sv_params.parquet")
    ours = ours[ours["country"] == DE].set_index("date")
    bbk = pd.read_parquet(i / "svensson_params_de.parquet").set_index("date")
    pts = nelson_siegel.standard_points(zero)
    rows: list[tuple] = []
    for date, g in pts.groupby("date", sort=True):
        if date not in ours.index or date not in bbk.index:
            continue
        g = g.sort_values("tenor_years")
        tau = g["tenor_years"].to_numpy(dtype="float64")
        y = g["yield"].to_numpy(dtype="float64")
        o = ours.loc[date]
        raw = bbk.loc[date]
        b = bundesbank_to_lambda(raw)
        fit_b = svensson_yield(
            tau, raw["beta0"], raw["beta1"], raw["beta2"], raw["beta3"], raw["tau1"], raw["tau2"]
        )
        rmse_bbk = float(np.sqrt(np.mean((y - fit_b) ** 2))) * 1e4
        # issue #12: beta_diff_max is computed against the ORIGINAL, unswapped
        # betas. The swap is a labelling convention and not an identity once
        # beta1 != 0, so comparing across it compared a beta fitted against lam1
        # with one fitted against a different decay. `swapped` stays in the csv
        # and is used for the lambda comparison only.
        beta_diff = max(abs(float(o[f"beta{k}"]) - float(raw[f"beta{k}"])) for k in range(4))
        outside = not (lo <= b["lam1"] <= hi and lo <= b["lam2"] <= hi)
        rows.append(
            (
                date,
                float(o["rmse_bp"]),
                rmse_bbk,
                float(o["lam1"]),
                float(o["lam2"]),
                b["lam1"],
                b["lam2"],
                float(o["lam_gap"]),
                abs(b["lam2"] - b["lam1"]),
                beta_diff,
                b["swapped"],
                outside,
            )
        )
    out = pd.DataFrame(rows, columns=BBK_COLUMNS)
    return out.sort_values("date").reset_index(drop=True)


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step svensson``: the Svensson fits, the DE benchmark, the held-out file."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    params, fitted = fit_panel(zero, cfg)
    params.to_parquet(p / "sv_params.parquet", index=False)
    ns_fitted = pd.read_parquet(p / "ns_fitted.parquet")
    ns_fitted = ns_fitted[ns_fitted["model"] != MODEL]
    allfit = pd.concat([ns_fitted, fitted], ignore_index=True)
    allfit = allfit.sort_values(["country", "date", "model", "tenor_years"]).reset_index(drop=True)
    allfit.to_parquet(p / "ns_fitted.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    compare_bundesbank(cfg, processed=p).to_csv(
        checks.SVENSSON_VS_BUNDESBANK, index=False, lineterminator="\n"
    )
    # amendment 3: rewrite fit_holdout.csv with all three models in it
    ns_params = pd.read_parquet(p / "ns_params.parquet")
    both = pd.concat([ns_params, params], ignore_index=True)
    nelson_siegel.write_holdout(zero, both)
    return params
