"""Step 5.5: the deflated Sharpe, and the N it is deflated by."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest, checks, metrics, report, speclog


def test_deflated_sharpe_known_values() -> None:
    """The two closed forms of Bailey & Lopez de Prado (2014)."""
    from scipy.stats import norm

    # N = 1: no selection to deflate, so SR0 = 0 and DSR is the plain
    # probability that the Sharpe is positive.
    sr0, dsr = metrics.deflated_sharpe(0.3, 0.01, 1, 121, 0.0, 3.0)
    assert sr0 == 0.0
    expected = float(norm.cdf(0.3 * math.sqrt(120) / math.sqrt(1.0 + (3.0 - 1.0) / 4.0 * 0.09)))
    assert dsr == pytest.approx(expected, abs=1e-12)

    # N = 100, V = 0.01, SR = 0.3, T = 121, skew 0, kurt 3 (normal), by hand:
    #   g   = 0.5772156649015329
    #   z1  = Phi^-1(1 - 1/100)        = 2.3263478740408408
    #   z2  = Phi^-1(1 - 1/(100 e))    = Phi^-1(0.99632120558828559)
    #   SR0 = sqrt(0.01) * [(1 - g) z1 + g z2]                 = 0.253060289320...
    #   den = 1 - 0 * 0.3 + (3 - 1)/4 * 0.3^2 = 1.045
    #   DSR = Phi((0.3 - SR0) sqrt(120) / sqrt(1.045))         = 0.692519859437...
    sr0, dsr = metrics.deflated_sharpe(0.3, 0.01, 100, 121, 0.0, 3.0)
    assert sr0 == pytest.approx(0.2530602893201685, abs=1e-6)
    assert dsr == pytest.approx(0.6925198594379562, abs=1e-6)

    # and the pieces, so the test fails on the right line if the formula moves
    g = metrics.EULER_GAMMA
    z1 = float(norm.ppf(1.0 - 1.0 / 100.0))
    z2 = float(norm.ppf(1.0 - 1.0 / (100.0 * math.e)))
    assert sr0 == pytest.approx(0.1 * ((1.0 - g) * z1 + g * z2), abs=1e-12)
    assert dsr == pytest.approx(
        float(norm.cdf((0.3 - sr0) * math.sqrt(120) / math.sqrt(1.045))), abs=1e-12
    )

    # V = 0 also means nothing to deflate
    assert metrics.deflated_sharpe(0.3, 0.0, 100, 121, 0.0, 3.0)[0] == 0.0


def test_deflated_sharpe_deflates_more_with_more_trials() -> None:
    dsrs = [metrics.deflated_sharpe(0.2, 0.01, n, 240, 0.0, 3.0)[1] for n in (1, 10, 100, 1000)]
    assert dsrs == sorted(dsrs, reverse=True)
    sr0s = [metrics.deflated_sharpe(0.2, 0.01, n, 240, 0.0, 3.0)[0] for n in (10, 100, 1000)]
    assert sr0s == sorted(sr0s)


def _fake_run(tmp_checks: Path, processed: Path, variant: str, r: pd.Series) -> None:
    """Write the two files ``metrics_table`` reads for one variant."""
    pd.DataFrame({"date": r.index, "r_net": r.to_numpy(), "turnover": 0.5}).to_parquet(
        processed / f"backtest_{variant}.parquet", index=False
    )
    block = metrics.summary(r, pd.Series(0.5, index=r.index))
    rows = []
    for window in ("full", "six"):
        for name, value in block.items():
            rows.append(
                {
                    "run_id": "x",
                    "variant": variant,
                    "window": window,
                    "metric": name,
                    "value": value,
                }
            )
        for name, value in block.items():
            rows.append(
                {
                    "run_id": "x",
                    "variant": variant,
                    "window": window,
                    "metric": f"{name}_gross",
                    "value": value,
                }
            )
    pd.DataFrame(rows).to_csv(tmp_checks / f"metrics_{variant}.csv", index=False)


def test_n_is_read_from_speclog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A spec log of 7 rows makes the table report N = 7 - it is never an argument."""
    tmp_checks = tmp_path / "checks"
    tmp_checks.mkdir()
    processed = tmp_path / "processed"
    processed.mkdir()
    monkeypatch.setattr(checks, "CHECKS", tmp_checks)

    idx = pd.date_range("2000-01-31", periods=60, freq="ME")
    rng = np.random.default_rng(11)
    _fake_run(tmp_checks, processed, "a", pd.Series(rng.normal(0.002, 0.01, 60), index=idx))
    _fake_run(tmp_checks, processed, "b", pd.Series(rng.normal(0.001, 0.01, 60), index=idx))

    spec = tmp_path / "specifications.csv"
    for i in range(7):
        speclog.log_run({"k": i}, label=f"run{i}", path=spec)
    assert speclog.count_runs(spec) == 7

    cfg = {"sample": {"strategy_start": idx[0], "sample_full_start": idx[30]}}
    table = report.metrics_table(cfg, processed=processed, spec_path=spec)
    assert set(table["n_trials"]) == {7}
    assert table["variant"].nunique() == 2
    assert set(table["window"]) == {"full", "six"}
    # V[SR] is the variance of the monthly Sharpes across the runs that were looked at
    assert float(table["sr_var_trials"].iloc[0]) > 0.0


def test_variant_override_is_in_note_and_hash() -> None:
    """A robustness run differs from the base in its config hash, and says how in its note."""
    from curvecarry import config

    cfg = config.load()
    base = backtest.merge_overrides(cfg, {})
    for name in (
        "carry_hedged_country_scope",
        "carry_hedged_interbank_3m",
        "carry_hedged_cost0",
        "carry_hedged_cost2x",
    ):
        spec = backtest.VARIANTS[name]
        run_cfg = backtest.merge_overrides(cfg, spec.overrides)
        assert config.config_hash(run_cfg) != config.config_hash(base), name
        note = backtest.variant_note(spec, "")
        key = next(iter(next(iter(spec.overrides.values()))))
        assert key in note, (name, note)
        # and the base config on disk is untouched by the merge
        assert config.load() == cfg

    # the GB-30y run excludes a bucket rather than changing a knob, so its hash
    # is the base hash by design; the exclusion is in the note instead
    gb = backtest.VARIANTS["carry_hedged_no_gb30"]
    assert config.config_hash(backtest.merge_overrides(cfg, gb.overrides)) == config.config_hash(
        base
    )
    assert "exclude_buckets" in backtest.variant_note(gb, "")
    assert "GB" in backtest.variant_note(gb, "")


# ------------------------- session-5 fix 2: the unhedged runs are currency books


def _fx_frames() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    idx = pd.date_range("2010-01-31", periods=6, freq="ME")
    rng = np.random.default_rng(5)
    rows, ret = [], []
    for date in idx:
        for country, weight in (("DE", 0.5), ("FR", 0.25), ("JP", -0.75), ("US", 1.0)):
            fx = 0.0 if country == "US" else float(rng.normal(0, 0.02))
            rows.append(
                {
                    "date": date,
                    "country": country,
                    "tenor_years": 5.0,
                    "leg": "long" if weight > 0 else "short",
                    "duration": 5.0,
                    "weight": weight,
                    "wd": weight * 5.0,
                    "r": 0.0,
                }
            )
            ret.append({"date": date, "country": country, "tenor_years": 5.0, "fx_return": fx})
    cfg = {
        "base_currency": "USD",
        "countries": ["US", "DE", "JP", "FR"],
        "currency": {"US": "USD", "DE": "EUR", "JP": "JPY", "FR": "EUR"},
    }
    return pd.DataFrame(rows), pd.DataFrame(ret), cfg


def test_net_notional_is_summed_per_currency_not_per_country() -> None:
    """DE and FR are one exposure, because they are one currency."""
    positions, returns, cfg = _fx_frames()
    table = report.fx_exposure_rows(positions, returns, cfg)
    first = table[table["date"] == table["date"].min()].set_index("currency")
    assert set(first.index) == {"EUR", "JPY", "USD"}
    assert first.loc["EUR", "net_notional"] == pytest.approx(0.75)  # 0.5 DE + 0.25 FR
    assert first.loc["JPY", "net_notional"] == pytest.approx(-0.75)
    assert first.loc["USD", "net_notional"] == pytest.approx(1.0)
    # the contribution is the notional times the currency's own move
    de_fx = returns[(returns["country"] == "DE") & (returns["date"] == table["date"].min())]
    fr_fx = returns[(returns["country"] == "FR") & (returns["date"] == table["date"].min())]
    expected = 0.5 * float(de_fx["fx_return"].iloc[0]) + 0.25 * float(fr_fx["fx_return"].iloc[0])
    assert first.loc["EUR", "contribution"] == pytest.approx(expected)


def test_a_book_that_is_only_fx_regresses_to_r_squared_one() -> None:
    """The regression recovers the FX term when the book is nothing else."""
    positions, returns, cfg = _fx_frames()
    table = report.fx_exposure_rows(positions, returns, cfg)
    term = table[table["currency"] != "USD"].groupby("date")["contribution"].sum()
    monthly = pd.DataFrame({"date": term.index, "r_gross": term.to_numpy() + 0.001})

    out = report.fx_regression(table, monthly, "USD")
    assert out["r_squared"] == pytest.approx(1.0, abs=1e-12)
    assert out["beta"] == pytest.approx(1.0, abs=1e-12)
    assert out["alpha_ann"] == pytest.approx(0.012, abs=1e-12)
    assert out["n_months"] == 6

    # a book with no currency exposure at all has none of its variance explained
    flat = pd.DataFrame({"date": term.index, "r_gross": [0.001, -0.002] * 3})
    assert report.fx_regression(table, flat, "USD")["r_squared"] < 0.9


def test_months_with_no_foreign_exposure_are_zero_not_missing() -> None:
    """Dropping them would regress on the subsample where the exposure was on."""
    positions, returns, cfg = _fx_frames()
    table = report.fx_exposure_rows(positions, returns, cfg)
    dates = sorted(table["date"].unique())
    # the book covers two months the exposure table never mentions
    extra = list(pd.date_range(dates[-1], periods=3, freq="ME"))[1:]
    monthly = pd.DataFrame(
        {"date": list(dates) + extra, "r_gross": [0.001] * (len(dates) + len(extra))}
    )
    out = report.fx_regression(table, monthly, "USD")
    assert out["n_months"] == len(dates) + len(extra)
