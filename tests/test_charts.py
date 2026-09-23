"""Step 2.4: Chart 1 and Chart 3 on synthetic frames in tmp_path. No network, no data files."""

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import charts

TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
DECADES = [1990, 2000, 2010, 2020]


def _fitted(dates: list[str], country: str = "XX") -> pd.DataFrame:
    rows = [(pd.Timestamp(d), country, "ns_free", t, 0.03) for d in dates for t in TENORS]
    return pd.DataFrame(rows, columns=["date", "country", "model", "tenor_years", "fitted"])


def test_chart1_dates_rule() -> None:
    """Last December with a fit per decade; the earliest fitted month for a missing decade."""
    # a country with Decembers in the 2000s and 2010s only, and a first month in 2003-07
    dates = ["2003-07-31", "2005-12-31", "2009-12-31", "2014-12-31", "2019-12-31", "2021-06-30"]
    got = charts.chart1_dates(_fitted(dates), DECADES).set_index("decade")["date"]
    assert got[2000] == pd.Timestamp("2009-12-31")  # the LAST December of the decade
    assert got[2010] == pd.Timestamp("2019-12-31")
    assert got[1990] == pd.Timestamp("2003-07-31")  # decade absent -> earliest fitted month
    assert got[2020] == pd.Timestamp("2003-07-31")  # 2021-06 is not a December -> same fallback

    # two countries get independent fallbacks
    two = pd.concat([_fitted(dates, "AA"), _fitted(["2015-12-31"], "BB")], ignore_index=True)
    out = charts.chart1_dates(two, DECADES)
    assert len(out) == len(DECADES) * 2
    bb = out[out["country"] == "BB"].set_index("decade")["date"]
    assert bb[2010] == pd.Timestamp("2015-12-31")
    assert bb[1990] == bb[2000] == bb[2020] == pd.Timestamp("2015-12-31")


def _panel_and_params(country: str = "XX") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """A two-month zero panel with ns_free, ns_dl and sv parameter rows."""
    dates = [pd.Timestamp("2019-12-31"), pd.Timestamp("2009-12-31")]
    zero = pd.DataFrame(
        [
            (d, country, t, 0.02 + 0.0005 * t, "zero", "test", False, True, False)
            for d in dates
            for t in TENORS
        ],
        columns=[
            "date",
            "country",
            "tenor_years",
            "yield",
            "curve_type",
            "source",
            "interpolated",
            "standard",
            "bootstrapped",
        ],
    )
    ns = pd.DataFrame(
        [
            (d, country, m, 0.04, -0.02, 0.01, lam, 3.0, 8, bound, bound)
            for d in dates
            for m, lam, bound in (("ns_free", 0.05, True), ("ns_dl", 0.7, False))
        ],
        columns=[
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
        ],
    )
    sv = pd.DataFrame(
        [(d, country, "sv", 0.04, -0.02, 0.01, 0.005, 0.4, 1.1, 0.7, 1.0, 8) for d in dates],
        columns=[
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
        ],
    )
    return zero, ns, sv


def test_chart_functions_write_files(tmp_path: Path) -> None:
    """Each chart function writes a non-empty png."""
    zero, ns, sv = _panel_and_params()
    params = pd.concat([ns, sv], ignore_index=True)
    dates = charts.chart1_dates(params, DECADES)
    paths = charts.chart1_fit(zero, params, dates, tmp_path)
    assert len(paths) == 1 and paths[0].name == "chart1_fit_xx.png"
    p2 = charts.chart1_rmse(params, tmp_path / "chart1_rmse.png")
    p3, excluded = charts.chart3_betas(
        ns, tmp_path / "chart3_betas.png", pd.Timestamp("1995-01-01")
    )
    for p in [*paths, p2, p3]:
        assert p.exists() and p.stat().st_size > 0
    assert len(excluded) == 2  # both ns_free months are degenerate in this fixture
    assert set(excluded["reason"]) == {"bound"}


def test_chart1_draws_the_model_not_a_polyline() -> None:
    """The fitted curve is evaluated off the parameters, so it is defined between the tenors."""
    _, ns, sv = _panel_and_params()
    params = pd.concat([ns, sv], ignore_index=True)
    tau = np.array([1.0, 4.0, 12.5, 30.0])  # 4 and 12.5 are not fitted tenors
    y = charts.fitted_curve(params, "XX", pd.Timestamp("2019-12-31"), "ns_free", tau)
    assert y is not None and np.isfinite(y).all() and y.shape == tau.shape
    assert charts.fitted_curve(params, "XX", pd.Timestamp("1970-01-31"), "ns_free", tau) is None
    sv_y = charts.fitted_curve(params, "XX", pd.Timestamp("2019-12-31"), "sv", tau)
    assert sv_y is not None and not np.allclose(sv_y, y)  # the 4-factor model is a different curve


def test_chart3_excludes_degenerate_months_as_gaps() -> None:
    """Session 2 fix: the gap criterion is ns_degenerate, and the reason is recorded.

    Not clipped, not interpolated, not forward-filled — the value is NaN, so the
    line breaks. The ns_dl series keeps every month. Three flavours of gap are
    covered: lambda on a bound only, a runaway beta only, and both.
    """
    dates = pd.date_range("2000-01-31", periods=5, freq="ME")
    rows = []
    for i, d in enumerate(dates):
        bound = i in (2, 4)  # 2 is bound-only, 4 is bound AND a runaway beta
        beta0 = 0.6 if i in (3, 4) else 0.04 + i / 100.0  # 3 is beta-only
        rows.append(
            (
                d,
                "XX",
                "ns_free",
                beta0,
                -0.02,
                0.01,
                0.05 if bound else 0.4,
                3.0,
                8,
                bound,
                bound or abs(beta0) > 0.5,
            )
        )
        rows.append((d, "XX", "ns_dl", 0.04 + i / 100.0, -0.02, 0.01, 0.7, 5.0, 8, False, False))
    ns = pd.DataFrame(
        rows,
        columns=[
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
        ],
    )
    d_free, y_free = charts.chart3_series(ns, "XX", "ns_free", "beta0")
    assert len(y_free) == 5  # the rows are kept, so the x axis is unbroken
    assert np.isnan(y_free[[2, 3, 4]]).all()  # ... but the values are gaps
    assert np.isfinite(y_free[[0, 1]]).all()
    assert y_free[0] == 0.04 and y_free[1] == 0.05  # neighbours untouched: no interpolation
    assert list(d_free) == list(dates)

    d_dl, y_dl = charts.chart3_series(ns, "XX", "ns_dl", "beta0")
    assert np.isfinite(y_dl).all() and len(y_dl) == 5  # fixed lambda: never gapped

    excluded = charts.chart3_excluded(ns, pd.Timestamp("1995-01-01"))
    assert list(excluded.columns) == charts.CHART3_EXCLUDED_COLUMNS
    assert len(excluded) == 3
    assert dict(zip(excluded["date"], excluded["reason"], strict=True)) == {
        dates[2]: "bound",
        dates[3]: "beta",
        dates[4]: "both",
    }
    assert excluded.set_index("date").loc[dates[2], "lam"] == 0.05
    assert set(excluded["model"]) == {"ns_free"}

    # the start date filters the excluded list too
    assert len(charts.chart3_excluded(ns, pd.Timestamp("2000-04-30"))) == 2
