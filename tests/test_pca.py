"""Step 3.1: PCA on monthly zero-yield changes. Synthetic panels only (rule 12)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import pca

TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]


def _cfg(countries=("US", "GB"), presence=0.95) -> dict:
    return {
        "countries": list(countries),
        "tenors": list(TENORS),
        "pca": {"tenor_presence_min": presence, "stability_min_months": 24},
    }


def _panel(country: str, dates: pd.DatetimeIndex, tenors, values=None) -> pd.DataFrame:
    """A zero panel in the shape of ``curves_zero.parquet`` for one country."""
    rows = []
    rng = np.random.default_rng(abs(hash(country)) % 2**32)
    for i, d in enumerate(dates):
        for t in tenors:
            v = values[i, tenors.index(t)] if values is not None else 0.03 + rng.normal(0, 0.001)
            if np.isnan(v):
                continue
            rows.append((d, country, float(t), float(v), "zero", "syn", False, True, False))
    return pd.DataFrame(
        rows,
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


def _three_factor(n_months: int, tenors: list[float], seed: int = 0) -> np.ndarray:
    """Changes in bp generated from exactly three factors, no noise."""
    rng = np.random.default_rng(seed)
    t = np.array(tenors, dtype="float64")
    level = np.ones_like(t)
    slope = (t - t.mean()) / t.std()
    curve = -((t - t.mean()) ** 2)
    curve = (curve - curve.mean()) / curve.std()
    f = rng.normal(0, [20.0, 8.0, 3.0], size=(n_months, 3))
    return f @ np.vstack([level, slope, curve])


# ------------------------------------------------------------------ the PCA


def test_explained_sums_to_one() -> None:
    x = _three_factor(300, TENORS, seed=1) + np.random.default_rng(2).normal(0, 1, (300, 8))
    res = pca.pca(x, np.array(TENORS))
    assert abs(res.explained.sum() - 1.0) < 1e-12


def test_scores_reconstruct_changes() -> None:
    x = _three_factor(200, TENORS, seed=3) + np.random.default_rng(4).normal(0, 1, (200, 8))
    res = pca.pca(x, np.array(TENORS))
    assert np.max(np.abs(res.scores @ res.loadings.T + res.mean - x)) < 1e-10


def test_sign_rules() -> None:
    """On a set whose longest tenor is not 30 and whose middle tenor is not 10."""
    tenors = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
    x = _three_factor(300, tenors, seed=5)
    res = pca.pca(x, np.array(tenors))
    assert pca.middle_tenor(np.array(tenors)) == 3.0  # even set: the lower middle
    v = res.loadings
    assert pca.loading_at(v[:, 0], res.tenors, 10.0) > 0
    assert pca.loading_at(v[:, 1], res.tenors, 8.0) > 0  # longest - 2, interpolated
    assert pca.loading_at(v[:, 2], res.tenors, 3.0) > 0
    # flipping every eigenvector must give the same answer back
    flipped = pca.apply_signs(-v, res.tenors)
    assert np.allclose(flipped, v)


def test_pc2_sign_tenor_is_interpolated_not_a_member() -> None:
    """``longest - 2`` is in none of the real sets; the loading there comes from interp."""
    tenors = np.array([1.0, 2.0, 3.0, 5.0, 7.0, 10.0])
    loading = np.array([0.0, 0.0, 0.0, 0.0, -1.0, 2.0])  # 8y sits between 7 and 10
    assert 8.0 not in tenors
    assert pca.loading_at(loading, tenors, 8.0) == pytest.approx(-1.0 + (2.0 - -1.0) / 3.0)


def test_three_factor_data_gives_three_components() -> None:
    x = _three_factor(400, TENORS, seed=6)
    res = pca.pca(x, np.array(TENORS))
    assert res.explained[3:].sum() < 1e-10


# --------------------------------------------------------------- tenor sets


def test_tenor_set_is_the_95pct_set() -> None:
    """A tenor present in 94% of months is out; one at 96% is in."""
    dates = pd.date_range("2000-01-31", periods=100, freq="ME")
    vals = np.full((100, 8), 0.03)
    vals[:6, TENORS.index(30.0)] = np.nan  # 94% present
    vals[:4, TENORS.index(20.0)] = np.nan  # 96% present
    panel = _panel("US", dates, TENORS, vals)
    cfg = _cfg(("US",))
    wide = pca.standard_wide(panel, "US", cfg)
    assert pca.country_tenor_set(wide, cfg) == [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0]


def test_panel_start_is_the_first_10y_month() -> None:
    """Months before the country's first 10-year zero do not count towards presence."""
    dates = pd.date_range("2000-01-31", periods=100, freq="ME")
    vals = np.full((100, 8), 0.03)
    vals[:50, TENORS.index(10.0)] = np.nan
    vals[:50, TENORS.index(20.0)] = np.nan
    vals[:50, TENORS.index(30.0)] = np.nan
    panel = _panel("US", dates, TENORS, vals)
    cfg = _cfg(("US",))
    wide = pca.standard_wide(panel, "US", cfg)
    assert pca.panel_start(wide) == dates[50]
    # counted from month 50 the three long tenors are present in 100% of months
    assert pca.country_tenor_set(wide, cfg) == TENORS


def test_tenor_set_too_small_raises() -> None:
    """A pooled intersection of 5 tenors is amendment 1's stop condition."""
    dates = pd.date_range("2000-01-31", periods=100, freq="ME")
    us = _panel("US", dates, TENORS)
    gb_vals = np.full((100, 8), 0.03)
    for t in (1.0, 2.0, 3.0, 5.0):
        gb_vals[:40, TENORS.index(t)] = np.nan  # 60% present from GB's first 10y month
    gb = _panel("GB", dates, TENORS, gb_vals)
    # GB's own set is 7,10,20,30 -> 4 tenors, so the country trip fires first
    with pytest.raises(pca.TenorSetTooSmall, match="GB"):
        pca.tenor_sets(pd.concat([us, gb], ignore_index=True), _cfg())


def test_pooled_trip_fires_below_six() -> None:
    dates = pd.date_range("2000-01-31", periods=100, freq="ME")
    us_vals = np.full((100, 8), 0.03)
    us_vals[:, TENORS.index(1.0)] = np.nan  # US set 2,3,5,7,10,20,30
    gb_vals = np.full((100, 8), 0.03)
    for t in (20.0, 30.0):
        gb_vals[:, TENORS.index(t)] = np.nan  # GB set 1,2,3,5,7,10
    panel = pd.concat(
        [_panel("US", dates, TENORS, us_vals), _panel("GB", dates, TENORS, gb_vals)],
        ignore_index=True,
    )
    with pytest.raises(pca.TenorSetTooSmall, match="pooled"):  # intersection 2,3,5,7,10 = 5
        pca.tenor_sets(panel, _cfg())


# ----------------------------------------------------------------- changes


def test_missing_tenor_month_dropped_and_counted() -> None:
    dates = pd.date_range("2000-01-31", periods=100, freq="ME")
    vals = np.full((100, 8), 0.03) + np.random.default_rng(7).normal(0, 0.001, (100, 8))
    vals[60, TENORS.index(5.0)] = np.nan  # one month loses a tenor that is in the set
    panel = _panel("US", dates, TENORS, vals)
    cfg = _cfg(("US",))
    changes = pca.monthly_changes_bp(panel, cfg)["US"]
    assert dates[60] not in changes.index  # the month itself
    assert dates[61] not in changes.index  # and the month that would difference against it
    dropped = pca.dropped_rows(panel, cfg)
    assert int(dropped.loc[0, "n_dropped"]) == 3  # month 0, month 60, month 61
    assert "missing a set tenor (1)" in dropped.loc[0, "reason"]


def test_gap_month_is_not_a_multi_month_change() -> None:
    """Amendment 3: a hole in the panel never becomes a change row spanning it."""
    dates = pd.date_range("2000-01-31", periods=24, freq="ME")
    keep = dates.delete(12)  # 2001-01 is missing outright
    vals = np.full((23, 8), 0.03)
    vals[12:, :] = 0.05  # a 200 bp jump across the hole
    panel = _panel("US", keep, TENORS, vals)
    cfg = _cfg(("US",))
    changes = pca.monthly_changes_bp(panel, cfg)["US"]
    assert dates[13] not in changes.index, "the month after the gap must not difference across it"
    assert changes.to_numpy().max() == pytest.approx(0.0), "no 200 bp change survives"
    assert len(changes) == 21  # 23 months, less the first and less the one after the gap


def test_changes_are_basis_points() -> None:
    dates = pd.date_range("2000-01-31", periods=3, freq="ME")
    vals = np.vstack([np.full(8, 0.03), np.full(8, 0.0325), np.full(8, 0.0325)])
    panel = _panel("US", dates, TENORS, vals)
    changes = pca.monthly_changes_bp(panel, _cfg(("US",)))["US"]
    assert changes.loc[dates[1]].to_numpy() == pytest.approx(25.0)
    assert changes.loc[dates[2]].to_numpy() == pytest.approx(0.0)


# ------------------------------------------------------------------- fits


def _two_country_panel() -> tuple[pd.DataFrame, dict]:
    dates = pd.date_range("2000-01-31", periods=120, freq="ME")
    panels = []
    for i, c in enumerate(("US", "GB")):
        lvl = np.cumsum(_three_factor(120, TENORS, seed=10 + i), axis=0) / 1e4 + 0.03
        panels.append(_panel(c, dates, TENORS, lvl))
    return pd.concat(panels, ignore_index=True), _cfg()


def test_pooled_scores_are_per_country_month() -> None:
    panel, cfg = _two_country_panel()
    _, _, scores = pca.fit_all(panel, cfg)
    pooled = scores[scores["scope"] == "pooled"]
    assert not pooled.duplicated(["country", "date", "component"]).any()
    assert set(pooled["country"]) == {"US", "GB"}
    assert len(pooled) == 2 * 119 * 8


def test_secondary_pooled_is_a_separate_scope() -> None:
    panel, cfg = _two_country_panel()
    explained, loadings, _ = pca.fit_all(panel, cfg)
    scopes = set(explained["scope"])
    assert {"pooled", "pooled_20y"} <= scopes
    primary = sorted(loadings[loadings["scope"] == "pooled"]["tenor_years"].unique())
    secondary = sorted(loadings[loadings["scope"] == "pooled_20y"]["tenor_years"].unique())
    assert primary == TENORS  # both countries have all 8 here, so the intersection is all 8
    assert secondary == pca.SECONDARY_POOLED_TENORS
    assert primary != secondary


def test_explained_shares_sum_to_one_per_scope() -> None:
    panel, cfg = _two_country_panel()
    explained, _, _ = pca.fit_all(panel, cfg)
    for _, g in explained.groupby("scope"):
        assert abs(g["explained_share"].sum() - 1.0) < 1e-12
