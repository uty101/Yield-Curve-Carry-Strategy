"""Step 3.2: decade loading stability. Synthetic panels only (rule 12)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import pca
from test_pca import TENORS, _panel, _three_factor


def _cfg(countries=("GB",), min_months=24, gap_bp=50.0) -> dict:
    return {
        "countries": list(countries),
        "tenors": list(TENORS),
        "pca": {
            "tenor_presence_min": 0.95,
            "stability_min_months": min_months,
            "us_borderline_gap_bp": gap_bp,
        },
        "sample": {"strategy_start": "1997-08-31"},
    }


def _levels_from_factors(n: int, seed: int) -> np.ndarray:
    """Yield levels whose monthly changes come from one fixed 3-factor model."""
    return np.cumsum(_three_factor(n, TENORS, seed=seed), axis=0) / 1e4 + 0.03


def test_self_correlation_is_one() -> None:
    """A single decade against a full sample that is that decade."""
    dates = pd.date_range("2000-01-31", periods=120, freq="ME")  # 2000-01 .. 2009-12
    panel = _panel("GB", dates, TENORS, _levels_from_factors(120, 11))
    cfg = _cfg()
    out = pca.stability(panel, cfg)
    row = out[(out["decade"] == "2000s") & (out["component"] == 1)]
    assert len(row) == 1
    assert abs(float(row["abs_cosine"].iloc[0]) - 1.0) < 1e-12
    assert abs(float(row["abs_corr"].iloc[0]) - 1.0) < 1e-12


def test_stable_factor_structure_scores_high() -> None:
    """Two decades drawn from the same 3-factor model agree with the full sample."""
    dates = pd.date_range("2000-01-31", periods=241, freq="ME")
    panel = _panel("GB", dates, TENORS, _levels_from_factors(241, 12))
    out = pca.stability(panel, _cfg())
    got = out[out["decade"].isin(["2000s", "2010s"]) & (out["component"] <= 3)]
    assert len(got) == 6
    assert (got["abs_cosine"] > 0.99).all()


def test_short_decade_is_nan_with_count() -> None:
    """A decade below ``stability_min_months`` keeps its count and gets NaN statistics."""
    dates = pd.date_range("1999-01-31", periods=133, freq="ME")  # 12 months in the 1990s
    panel = _panel("GB", dates, TENORS, _levels_from_factors(133, 13))
    out = pca.stability(panel, _cfg())
    short = out[out["decade"] == "1990s"]
    assert len(short) == 3
    assert (short["n_months"] == 11).all()  # 12 months, less the first (no predecessor)
    assert short["abs_cosine"].isna().all()
    assert short["abs_corr"].isna().all()
    assert short["explained_share_decade"].isna().all()


def test_us_written_twice_with_flag(tmp_path) -> None:
    """Amendment 4: the US carries both flag values; no other country does."""
    dates = pd.date_range("1990-01-31", periods=121, freq="ME")
    panel = pd.concat(
        [
            _panel("US", dates, TENORS, _levels_from_factors(121, 14)),
            _panel("GB", dates, TENORS, _levels_from_factors(121, 15)),
        ],
        ignore_index=True,
    )
    gap = tmp_path / "par_zero_gap.csv"
    pd.DataFrame(
        {
            "country": "US",
            "date": [d.date().isoformat() for d in dates[:6]],
            "tenor_years": 30.0,
            "par_yield": 0.05,
            "zero_yield": 0.06,
            "gap_bp": [120.0, 10.0, 90.0, 5.0, 75.0, 0.0],  # three above 50 bp
        }
    ).to_csv(gap, index=False)
    cfg = _cfg(("US", "GB"))
    assert len(pca.us_borderline_months(cfg, gap)) == 3

    out = pca.stability(panel, cfg)
    assert set(out[out["country"] == "US"]["us_borderline_excluded"]) == {True, False}
    assert set(out[out["country"] == "GB"]["us_borderline_excluded"]) == {False}


def test_borderline_months_are_pre_strategy_start_and_over_the_bp() -> None:
    """Only US, only 30y, only before ``strategy_start``, only above the config bp."""
    rows = [
        ("US", "1982-03-31", 30.0, 120.0),  # in
        ("US", "1982-04-30", 30.0, 49.0),  # under the threshold
        ("US", "1982-05-31", 10.0, 120.0),  # wrong tenor
        ("GB", "1982-06-30", 30.0, 120.0),  # wrong country
        ("US", "2005-03-31", 30.0, 120.0),  # after strategy_start
        ("US", "1984-08-31", 30.0, -80.0),  # in, on the absolute value
    ]
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "gap.csv"
        pd.DataFrame(rows, columns=["country", "date", "tenor_years", "gap_bp"]).to_csv(
            p, index=False
        )
        got = pca.us_borderline_months(_cfg(), p)
    assert [str(pd.Timestamp(x).date()) for x in got] == ["1982-03-31", "1984-08-31"]


def test_excluding_months_changes_only_the_affected_decades() -> None:
    """A decade with no borderline month has identical rows under both flags."""
    dates = pd.date_range("1990-01-31", periods=241, freq="ME")
    panel = _panel("US", dates, TENORS, _levels_from_factors(241, 16))
    cfg = _cfg(("US",))
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "gap.csv"
        pd.DataFrame(
            {
                "country": "US",
                "date": [d2.date().isoformat() for d2 in dates[:5]],  # all in the 1990s
                "tenor_years": 30.0,
                "gap_bp": 120.0,
            }
        ).to_csv(p, index=False)
        bad = pca.us_borderline_months(cfg, p)
    changes = pca.monthly_changes_bp(panel, cfg)["US"]
    a = pca._stability_rows(changes, "US", cfg, False)
    b = pca._stability_rows(changes[~changes.index.isin(bad)], "US", cfg, True)
    by_dec = {(r[1], r[2]): r for r in a}
    for r in b:
        ref = by_dec[(r[1], r[2])]
        if r[1] == "2000s":
            # untouched decade: same months, same decade-only PCA
            assert r[3] == ref[3]
            assert r[6] == pytest.approx(ref[6])
        if r[1] == "1990s":
            assert r[3] < ref[3]
    # both statistics may move in every decade, because the full-sample vector
    # they are measured against is refitted without the excluded months
    assert any(r[4] != by_dec[(r[1], r[2])][4] for r in b)


def test_abs_cosine_is_the_named_statistic_and_abs_corr_is_secondary() -> None:
    """Fix round: `abs_cosine` comes first in the file, `abs_corr` beside it.

    On a near-flat PC1 the two disagree by design — Pearson removes the mean,
    which for a level loading is nearly the whole vector — so the column order
    is what says which one answers "is it the same factor".
    """
    assert pca.STABILITY_COLUMNS.index("abs_cosine") < pca.STABILITY_COLUMNS.index("abs_corr")
    flat = np.array([0.40, 0.41, 0.42, 0.43, 0.44, 0.45])
    tilted = np.array([0.45, 0.44, 0.43, 0.42, 0.41, 0.40])
    flat, tilted = flat / np.linalg.norm(flat), tilted / np.linalg.norm(tilted)
    assert abs(float(flat @ tilted)) > 0.99  # the same level factor
    assert abs(float(np.corrcoef(flat, tilted)[0, 1]) + 1.0) < 1e-12  # Pearson says -1
