"""Step 2.2: Nelson-Siegel on synthetic curves. No network, no data files."""

import numpy as np
import pandas as pd

from curvecarry import nelson_siegel as ns

TENORS = np.array([1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
GRID = (0.2, 1.5, 0.05)
CFG = {"nelson_siegel": {"ns_lambda_grid": list(GRID), "ns_lambda_fixed": 0.7, "min_tenors": 5}}


def _curve(beta, lam, tau=TENORS) -> np.ndarray:
    return ns.ns_loadings(tau, lam) @ np.asarray(beta, dtype="float64")


def test_recover_known_parameters() -> None:
    """Noiseless data from beta = (0.05, -0.02, 0.01), lambda = 0.6 is recovered to 1e-4."""
    beta, lam = (0.05, -0.02, 0.01), 0.6
    got = ns.fit(TENORS, _curve(beta, lam), GRID)
    assert abs(got.beta0 - beta[0]) < 1e-4
    assert abs(got.beta1 - beta[1]) < 1e-4
    assert abs(got.beta2 - beta[2]) < 1e-4
    assert abs(got.lam - lam) < 1e-4
    assert got.rmse_bp < 1e-6
    assert got.n_tenors == 8


def test_fixed_lambda_recovers_beta_when_lambda_true() -> None:
    """With lambda at its true value the OLS betas are exact to 1e-10."""
    beta, lam = (0.04, -0.015, 0.02), 0.7
    got, rmse = ns.fit_fixed_lambda(TENORS, _curve(beta, lam), lam)
    assert np.abs(got - np.array(beta)).max() < 1e-10
    assert rmse < 1e-12


def test_loadings_limits() -> None:
    """At tau -> 0 the loadings tend to [1, 1, 0]; at tau = 1e3 to [1, ~0, ~0]."""
    near_zero = ns.ns_loadings(np.array([1e-8]), 0.6)[0]
    assert abs(near_zero[0] - 1.0) < 1e-12
    assert abs(near_zero[1] - 1.0) < 1e-7
    assert abs(near_zero[2]) < 1e-7
    far = ns.ns_loadings(np.array([1e3]), 0.6)[0]
    assert far[0] == 1.0 and abs(far[1]) < 1e-2 and abs(far[2]) < 1e-2
    assert ns.ns_loadings(np.array([0.0]), 0.6)[0].tolist() == [1.0, 1.0, 0.0]


def test_grid_refinement_not_worse_than_grid() -> None:
    """The polished lambda never has a worse RMSE than the best grid point."""
    rng = np.random.default_rng(0)
    for _ in range(20):
        y = _curve((0.03, -0.01, 0.015), 0.43) + rng.normal(0, 2e-4, TENORS.size)
        best_grid = min(ns.fit_fixed_lambda(TENORS, y, lam)[1] for lam in ns.lambda_grid(GRID))
        got = ns.fit(TENORS, y, GRID)
        assert got.rmse_bp / 1e4 <= best_grid + 1e-15
        assert GRID[0] <= got.lam <= GRID[1]


def test_skips_below_min_tenors() -> None:
    """A month with 4 standard tenors is not fitted and is one row of fit_skipped."""
    dates = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
    rows = []
    for date, n in zip(dates, (8, 4), strict=True):
        tau = TENORS[:n]
        for t, y in zip(tau, _curve((0.03, -0.01, 0.01), 0.5, tau), strict=True):
            rows.append((date, "XX", float(t), float(y), True, False, False))
    panel = pd.DataFrame(
        rows,
        columns=[
            "date",
            "country",
            "tenor_years",
            "yield",
            "standard",
            "interpolated",
            "bootstrapped",
        ],
    )
    params, fitted = ns.fit_panel(panel, CFG)
    assert set(params["date"]) == {dates[0]}
    assert set(params["model"]) == {"ns_free", "ns_dl"}
    assert len(fitted) == 16
    skip = ns.skipped(panel, CFG)
    assert len(skip) == 1
    assert skip.loc[0, "date"] == dates[1] and skip.loc[0, "n_standard_tenors"] == 4


def test_holdout_points_split_by_country() -> None:
    """Amendment 3: GB/CA/JP contribute observed non-standard tenors, US/FR bootstrapped ones."""
    rows = []
    for country, interp, boot in (
        ("GB", False, False),
        ("GB", True, False),  # interpolated: excluded
        ("JP", False, True),
        ("US", True, True),  # bootstrapped: kept whatever the interpolated flag says
        ("DE", False, False),  # not in either list
    ):
        for t, std in ((4.0, False), (10.0, True), (0.5, False), (40.0, False)):
            rows.append((pd.Timestamp("2020-01-31"), country, t, 0.02, std, interp, boot))
    panel = pd.DataFrame(
        rows,
        columns=[
            "date",
            "country",
            "tenor_years",
            "yield",
            "standard",
            "interpolated",
            "bootstrapped",
        ],
    )
    pts = ns.holdout_points(panel)
    assert set(pts["country"]) == {"GB", "JP", "US"}
    assert set(pts["tenor_years"]) == {4.0}  # 10 is standard, 0.5 and 40 are outside [1, 30]
    assert len(pts[pts["country"] == "GB"]) == 1  # the interpolated GB row is gone
    assert dict(zip(pts["country"], pts["zero_kind"], strict=True)) == {
        "GB": "observed",
        "JP": "bootstrapped",
        "US": "bootstrapped",
    }


def test_holdout_error_is_zero_for_a_perfect_model() -> None:
    """Held-out error at an unfitted tenor is zero when the data really is a NS curve."""
    date = pd.Timestamp("2020-01-31")
    beta, lam = (0.03, -0.01, 0.012), 0.55
    tau_all = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0])
    std = np.isin(tau_all, TENORS)
    panel = pd.DataFrame(
        {
            "date": date,
            "country": "GB",
            "tenor_years": tau_all,
            "yield": _curve(beta, lam, tau_all),
            "standard": std,
            "interpolated": False,
            "bootstrapped": False,
        }
    )
    params, _ = ns.fit_panel(panel, CFG)
    hold = ns.holdout_errors(panel, params)
    assert set(hold["tenor_years"]) == {4.0, 15.0}
    assert hold[hold["model"] == "ns_free"]["error_bp"].abs().max() < 1e-4
    summary = ns.holdout_summary(hold, params)
    assert set(summary["model"]) == {"ns_free", "ns_dl"}
    assert summary.loc[summary["model"] == "ns_free", "holdout_rmse_median_bp"].iloc[0] < 1e-4
