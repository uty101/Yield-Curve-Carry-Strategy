"""Step 2.3: Svensson on synthetic curves and on real Bundesbank parameter rows (fixture)."""

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import svensson as sv
from curvecarry.loaders import de

TENORS = np.array([1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
GRID = (0.2, 1.5, 0.05)
FIX = Path("tests/fixtures/bundesbank")
# fixture rows chosen by their converted lambdas (amendment 2)
INSIDE_GRID = pd.Timestamp("1997-08-07")  # 1/tau1 = 0.4068, 1/tau2 = 0.6460, no swap
SWAPPED_INSIDE = pd.Timestamp("1997-09-02")  # 1/tau1 = 0.6265 > 1/tau2 = 0.3627, swapped
OUTSIDE_GRID = pd.Timestamp("1997-09-19")  # 1/tau2 = 10000, far above the grid's 1.5


def _params() -> pd.DataFrame:
    return de.parse_params([FIX / f"{p}.csv" for p in de.PARAMS]).set_index("obs_date")


def _bbk_curve(row: pd.Series, tau: np.ndarray = TENORS) -> np.ndarray:
    return sv.svensson_yield(
        tau, row["beta0"], row["beta1"], row["beta2"], row["beta3"], row["tau1"], row["tau2"]
    )


def test_recover_known_curve() -> None:
    """beta = (0.05, -0.02, 0.01, 0.015), lam = (0.5, 1.2): the fitted curve is exact to 1e-7."""
    beta = np.array([0.05, -0.02, 0.01, 0.015])
    y = sv.sv_loadings(TENORS, 0.5, 1.2) @ beta
    f = sv.fit(TENORS, y, GRID)
    got = sv.sv_loadings(TENORS, f.lam1, f.lam2) @ np.array([f.beta0, f.beta1, f.beta2, f.beta3])
    assert np.abs(got - y).max() < 1e-7
    assert f.n_tenors == 8


def test_nested_ns_case() -> None:
    """Data with beta3 = 0 is a Nelson-Siegel curve and Svensson fits it to nothing."""
    beta = np.array([0.04, -0.018, 0.012, 0.0])
    y = sv.sv_loadings(TENORS, 0.6, 1.3) @ beta
    assert sv.fit(TENORS, y, GRID).rmse_bp < 1e-6


def test_lambda_gap_recorded_and_positive() -> None:
    """lam_gap is |lam1 - lam2|, lam2 >= lam1, and both stay inside the grid."""
    rng = np.random.default_rng(1)
    for _ in range(10):
        y = sv.sv_loadings(TENORS, 0.4, 1.1) @ np.array([0.03, -0.01, 0.01, 0.008]) + rng.normal(
            0, 2e-4, TENORS.size
        )
        f = sv.fit(TENORS, y, GRID)
        assert f.lam2 >= f.lam1
        assert abs(f.lam_gap - abs(f.lam2 - f.lam1)) < 1e-15
        assert GRID[0] <= f.lam1 <= GRID[1] and GRID[0] <= f.lam2 <= GRID[1]


def test_bundesbank_form_equals_lambda_form() -> None:
    """svensson_yield(tau, ..., tau1, tau2) == sv_loadings(tau, 1/tau1, 1/tau2) @ beta to 1e-14."""
    beta = np.array([0.05, -0.02, 0.01, 0.015])
    for tau1, tau2 in ((2.0, 0.8), (5.0, 1.5), (1.0, 1.0)):
        want = sv.svensson_yield(TENORS, *beta, tau1, tau2)
        got = sv.sv_loadings(TENORS, 1.0 / tau1, 1.0 / tau2) @ beta
        assert np.abs(got - want).max() < 1e-14


def test_de_fit_recovers_bundesbank_curve() -> None:
    """Amendment 2: on a fixture row whose lambdas lie inside the grid, our RMSE is under 0.1 bp."""
    row = _params().loc[INSIDE_GRID]
    b = sv.bundesbank_to_lambda(row)
    assert not b["swapped"]
    assert GRID[0] <= b["lam1"] <= GRID[1] and GRID[0] <= b["lam2"] <= GRID[1]
    f = sv.fit(TENORS, _bbk_curve(row), GRID)
    assert f.rmse_bp < 0.1
    # the lambdas themselves are recovered, not only the curve
    assert abs(f.lam1 - b["lam1"]) < 1e-3 and abs(f.lam2 - b["lam2"]) < 1e-3


def test_de_fit_for_a_row_outside_the_grid() -> None:
    """Amendment 2: what happens when a Bundesbank lambda lies outside config's grid.

    1997-09-19 has ``tau2 = 1e-4``, so ``1/tau2 = 10,000`` — four orders of
    magnitude above the grid's upper bound of 1.5. The fourth loading
    ``(1 - e^{-lam2 tau})/(lam2 tau) - e^{-lam2 tau}`` is then within 1e-4 of
    zero at every tenor from 1 year up, so that term contributes nothing the
    fit has to reproduce: our in-grid fit still recovers the **curve** to well
    under 0.1 bp, and only the reported ``lam2`` differs. The grid is a
    constraint on the parameters, not on the curves they can produce.
    """
    row = _params().loc[OUTSIDE_GRID]
    b = sv.bundesbank_to_lambda(row)
    assert b["lam2"] > GRID[1]  # outside the grid
    loading = sv.sv_loadings(TENORS, b["lam1"], b["lam2"])[:, 3]
    assert np.abs(loading).max() <= 1e-4  # the fourth factor is dead at these tenors
    f = sv.fit(TENORS, _bbk_curve(row), GRID)
    assert f.rmse_bp < 0.1
    assert f.lam2 <= GRID[1]  # our lam2 cannot leave the grid, and does not need to


def test_bundesbank_to_lambda_swaps_labels_and_betas() -> None:
    """The swap relabels lam1/lam2 and beta2/beta3 together; it does not preserve the curve."""
    row = _params().loc[SWAPPED_INSIDE]
    b = sv.bundesbank_to_lambda(row)
    assert b["swapped"] and b["lam2"] > b["lam1"]
    assert abs(b["lam1"] - 1.0 / row["tau2"]) < 1e-12
    assert b["beta2"] == row["beta3"] and b["beta3"] == row["beta2"]
    unswapped = sv.bundesbank_to_lambda(_params().loc[INSIDE_GRID])
    assert not unswapped["swapped"]
    # the swap is a labelling convention, NOT a curve-preserving transformation:
    # lam1 carries the slope loading too, so the relabelled parameters describe
    # a different curve unless beta1 == 0.
    swapped_curve = sv.sv_loadings(TENORS, b["lam1"], b["lam2"]) @ np.array(
        [b["beta0"], b["beta1"], b["beta2"], b["beta3"]]
    )
    moved_bp = np.abs(swapped_curve - _bbk_curve(row)).max() * 1e4
    assert moved_bp > 10.0  # 65.7 bp on this row
    zero_slope = sv.sv_loadings(TENORS, b["lam1"], b["lam2"]) @ np.array(
        [b["beta0"], 0.0, b["beta2"], b["beta3"]]
    )
    zero_slope_raw = sv.svensson_yield(
        TENORS, row["beta0"], 0.0, row["beta2"], row["beta3"], row["tau1"], row["tau2"]
    )
    assert np.abs(zero_slope - zero_slope_raw).max() < 1e-15  # exact once beta1 = 0


def test_polish_keeps_the_grid_separation() -> None:
    """Issue #12 Q2 option D: the polished pair never collapses, and the betas stay small.

    Before the fix the Nelder-Mead polish was clipped to [lo, hi] only and could
    drive lam2 onto lam1, making the two curvature columns identical and the
    betas 1e11 as a difference of two large numbers.
    """
    step = GRID[2]
    rng = np.random.default_rng(7)
    for _ in range(30):
        # a near-Nelson-Siegel curve: the second curvature is barely identified,
        # which is exactly where the pair used to collapse
        y = sv.sv_loadings(TENORS, 0.4, 0.45) @ np.array([0.03, -0.01, 0.01, 0.0005]) + rng.normal(
            0, 1e-5, TENORS.size
        )
        f = sv.fit(TENORS, y, GRID)
        assert f.lam2 >= f.lam1 + step - 1e-9, (f.lam1, f.lam2)
        assert f.lam_gap >= step - 1e-9
        assert max(abs(f.beta2), abs(f.beta3)) < 1e6


def test_project_is_the_nearest_feasible_pair() -> None:
    """_project keeps [lo, hi] and the one-step separation, and orders the pair."""
    lo, hi, step = GRID
    assert sv._project(np.array([0.5, 0.5]), lo, hi, step) == (0.475, 0.525)
    assert sv._project(np.array([0.9, 0.4]), lo, hi, step) == (0.4, 0.9)  # crossed: ordered
    a, b = sv._project(np.array([lo, lo]), lo, hi, step)
    assert (a, b) == (lo, lo + step)  # pushed up, not below the floor
    a, b = sv._project(np.array([hi, hi]), lo, hi, step)
    assert (a, b) == (hi - step, hi)  # pushed down, not above the ceiling
    a, b = sv._project(np.array([-5.0, 99.0]), lo, hi, step)
    assert (a, b) == (lo, hi)


def test_fit_panel_and_holdout_shapes() -> None:
    """fit_panel emits one sv row per fittable month, and the params join the holdout file."""
    from curvecarry import nelson_siegel as ns

    cfg = {"nelson_siegel": {"ns_lambda_grid": list(GRID), "ns_lambda_fixed": 0.7, "min_tenors": 5}}
    tau_all = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0, 30.0])
    std = np.isin(tau_all, TENORS)
    y = sv.sv_loadings(tau_all, 0.45, 1.1) @ np.array([0.03, -0.012, 0.01, 0.009])
    panel = pd.DataFrame(
        {
            "date": pd.Timestamp("2020-01-31"),
            "country": "GB",
            "tenor_years": tau_all,
            "yield": y,
            "standard": std,
            "interpolated": False,
            "bootstrapped": False,
        }
    )
    params, fitted = sv.fit_panel(panel, cfg)
    assert len(params) == 1 and set(params["model"]) == {"sv"}
    assert len(fitted) == 8  # the 8 standard tenors, not the held-out 4y
    hold = ns.holdout_errors(panel, params)
    assert set(hold["tenor_years"]) == {4.0}
    assert hold["error_bp"].abs().max() < 1e-4
