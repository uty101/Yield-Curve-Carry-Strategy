"""Step 2.4: Chart 1 and Chart 3 on synthetic frames in tmp_path. No network, no data files."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import charts

TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
DECADES = [1990, 2000, 2010, 2020]


def _fitted(dates: list[str], country: str = "XX") -> pd.DataFrame:
    rows = [(pd.Timestamp(d), country, "ns_free", t, 0.03) for d in dates for t in TENORS]
    return pd.DataFrame(rows, columns=["date", "country", "model", "tenor_years", "fitted"])


def test_chart1_dates_rule() -> None:
    """Last December with a fit per decade; no row at all for a decade the country misses."""
    # Decembers in the 2000s and 2010s; a 2020s month that is not a December; nothing in the 1990s
    dates = ["2003-07-31", "2005-12-31", "2009-12-31", "2014-12-31", "2019-12-31", "2021-06-30"]
    out = charts.chart1_dates(_fitted(dates), DECADES)
    got = out.set_index("decade")["date"]
    assert got[2000] == pd.Timestamp("2009-12-31")  # the LAST December of the decade
    assert got[2010] == pd.Timestamp("2019-12-31")
    assert 1990 not in got.index  # no fitted month in the decade -> no row (fix round)
    assert got[2020] == pd.Timestamp("2021-06-30")  # months but no December -> last month of it
    assert len(out) == 3
    assert out["date"].notna().all()  # the file holds only real dates

    # two countries, each with its own missing decades
    two = pd.concat([_fitted(dates, "AA"), _fitted(["2015-12-31"], "BB")], ignore_index=True)
    both = charts.chart1_dates(two, DECADES)
    bb = both[both["country"] == "BB"].set_index("decade")["date"]
    assert bb.index.tolist() == [2010] and bb[2010] == pd.Timestamp("2015-12-31")
    assert len(both) == 4


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
    assert sorted(dates["decade"]) == [2000, 2010]  # the fixture has no 1990s or 2020s month
    paths = charts.chart1_fit(zero, params, dates, DECADES, tmp_path)
    assert len(paths) == 1 and paths[0].name == "chart1_fit_xx.png"
    p2 = charts.chart1_rmse(params, tmp_path / "chart1_rmse.png")
    p3, excluded = charts.chart3_betas(
        ns, tmp_path / "chart3_betas.png", pd.Timestamp("1995-01-01")
    )
    for p in [*paths, p2, p3]:
        assert p.exists() and p.stat().st_size > 0
    assert len(excluded) == 2  # both ns_free months are degenerate in this fixture
    assert set(excluded["reason"]) == {"bound"}


def test_chart1_empty_panel_for_a_missing_decade(tmp_path: Path) -> None:
    """A decade with no fitted month gets an empty panel, not another decade's curve.

    The figure still has one panel per configured decade, so the six countries
    stay comparable side by side (session 2 fix round).
    """
    zero, ns, sv = _panel_and_params()
    params = pd.concat([ns, sv], ignore_index=True)
    dates = charts.chart1_dates(params, DECADES)
    assert 1990 not in set(dates["decade"]) and 2020 not in set(dates["decade"])
    paths = charts.chart1_fit(zero, params, dates, DECADES, tmp_path)
    assert len(paths) == 1 and paths[0].stat().st_size > 0
    # a country with no fitted month in ANY configured decade has nothing to draw
    far = charts.chart1_dates(params, [1950])
    assert far.empty
    assert charts.chart1_fit(zero, params, far, [1950], tmp_path / "empty") == []
    assert charts.NO_FIT_TEXT.count(chr(10)) == 1  # two lines of centred grey text


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


def _loadings() -> pd.DataFrame:
    """Two countries on different tenor sets, plus both pooled scopes."""
    rows = []
    sets = {
        "US": [1.0, 2.0, 3.0, 5.0, 7.0, 10.0],
        "DE": [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0],
        "pooled": [1.0, 2.0, 3.0, 5.0, 7.0, 10.0],
        "pooled_20y": [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0],
    }
    for scope, tenors in sets.items():
        for k in (1, 2, 3):
            for i, t in enumerate(tenors):
                rows.append((scope, k, t, 0.4 - 0.02 * k * i))
    return pd.DataFrame(rows, columns=["scope", "component", "tenor_years", "loading"])


def test_chart2_writes_file(tmp_path: Path) -> None:
    p = charts.chart2_loadings(_loadings(), tmp_path / "chart2_loadings.png")
    assert p.exists() and p.stat().st_size > 0


def test_chart2_draws_countries_and_pooled_but_not_the_secondary() -> None:
    """The secondary pooled fit is reported, never drawn beside the six countries."""
    assert charts.chart2_country_scopes(_loadings()) == ["US", "DE"]


# ---------------------------------------------------- step 4.4: Chart 4


def _carry() -> pd.DataFrame:
    """Two countries on different tenor sets, over four months, one bucket absent."""
    rows = []
    for country, tenors in (("US", [1.0, 10.0, 30.0]), ("JP", [1.0, 10.0])):
        for i, date in enumerate(pd.date_range("2020-01-31", periods=4, freq="ME")):
            for t in tenors:
                if country == "US" and t == 30.0 and i < 2:
                    continue  # the bucket enters halfway through
                rows.append((date, country, t, 0.001 * (i - 1) * t, max(t * 0.9, 1.0)))
    return pd.DataFrame(rows, columns=["date", "country", "tenor_years", "carry", "duration"])


def test_chart4_writes_files(tmp_path: Path) -> None:
    paths = charts.chart4_carry_heatmap(_carry(), tmp_path / "chart4_carry_per_duration.png")
    assert [p.name for p in paths] == [
        "chart4_carry_per_duration.png",
        "chart4_us.png",
        "chart4_jp.png",
    ]
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)


def test_chart4_rows_are_grouped_by_country_and_absent_buckets_are_nan() -> None:
    """Rows follow CHART4_COUNTRY_ORDER then ascending tenor; a month with no bucket is NaN."""
    wide = charts.carry_per_duration(_carry())
    assert list(wide.index) == ["US-1y", "US-10y", "US-30y", "JP-1y", "JP-10y"]
    assert wide.loc["US-30y"].isna().sum() == 2  # the two months before it enters
    assert wide.loc["US-10y"].notna().all()
    # the value is carry/duration in bp, not a decimal
    assert wide.loc["US-10y"].iloc[2] == pytest.approx(0.001 * 10.0 / 9.0 * 1e4)
