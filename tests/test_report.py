"""Step 6.4: the report is written from the checks files, and its N is the final N."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from curvecarry import backtest, results, speclog

RESULTS = Path("reports/results.md")
CFG = {
    "sample": {
        "strategy_start": "2000-01-31",
        "sample_full_start": "2001-01-31",
        "strategy_end": "2002-12-31",
    }
}


def _table(n_trials: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variant": backtest.HEADLINE,
                "window": w,
                "ann_return": 0.0059,
                "ann_vol": 0.0223,
                "sharpe": 0.2645,
                "max_dd": -0.1037,
                "dd_peak": "2019-12-31",
                "dd_trough": "2022-12-31",
                "turnover": 1.473,
                "ret_2022": -0.0441,
                "dd_2022": -0.0469,
                "n_months": 348.0,
                "ann_return_gross": 0.0077,
                "sharpe_gross": 0.3442,
                "sr_monthly": 0.0764,
                "skew": -0.2,
                "kurtosis": 4.0,
                "sr0": 0.067,
                "dsr": dsr,
                "n_trials": n_trials,
                "sr_var_trials": 0.0017,
            }
            for w, dsr in (("full", 0.567), ("six", 0.512))
        ]
    )


def _years() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2000, 2001],
            "n_months": [12, 12],
            "r_net": [0.01, -0.02],
            "carry_earned": [0.03, 0.03],
            "yield_change_pnl": [-0.018, -0.048],
            "cost": [-0.002, -0.002],
        }
    )


def _speclog(tmp_path: Path, n: int) -> Path:
    path = tmp_path / "specifications.csv"
    rows = [
        {
            "run_id": f"r{i}",
            "timestamp_utc": "2026-09-23T17:15:19+00:00",
            "git_commit": "abc1234",
            "config_hash": "68b55883b46e",
            "label": f"variant_{i}",
            "note": "",
        }
        for i in range(n)
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


# ------------------------------------------------------------- the year table


def test_year_rows_sum_to_the_reported_total():
    """Each year's pieces add to its net return, and the years add to the sample."""
    dates = pd.date_range("2000-01-31", periods=24, freq="ME")
    decomposition = pd.DataFrame(
        {
            "date": dates,
            "carry_earned": 0.003,
            "yield_change_pnl": -0.002,
            "funding": 0.0,
            "fx": 0.0,
            "cost": -0.0002,
        }
    )
    monthly = pd.DataFrame({"date": dates, "r_net": 0.0008})
    years = results.year_rows(monthly, decomposition, CFG)
    assert list(years["year"]) == [2000, 2001]
    assert (years["n_months"] == 12).all()
    pieces = years["carry_earned"] + years["yield_change_pnl"] + years["cost"]
    assert (pieces - years["r_net"]).abs().max() < 1e-12
    assert float(years["r_net"].sum()) == pytest.approx(float(monthly["r_net"].sum()))


def test_year_table_md_has_a_total_row():
    text = results.year_table_md(_years())
    assert text.startswith(results.YEAR_HEADER)
    assert "| **all** |" in text
    assert text.count("\n") == len(_years()) + 3  # header, rule, rows, total


# --------------------------------------------------------------------- the DSR


def test_report_writes_from_synthetic_checks(tmp_path: Path):
    """The block renders from a synthetic metrics table, year table and spec log."""
    table = _table(n_trials=17)
    block = results.results_block(CFG, table, _years(), _speclog(tmp_path, 17))
    assert "carry_hedged" in block
    assert "0.59% a year" in block
    assert "N = 17" in block
    assert results.YEAR_HEADER in block
    assert results.RUNS_HEADER in block
    assert "variant_0" in block


def test_dsr_is_reported_as_a_probability_with_its_threshold_and_n():
    text = results.dsr_sentences(_table(n_trials=17), backtest.HEADLINE)
    assert "a probability, not a Sharpe ratio" in text
    assert "SR0 = 0.067" in text
    assert "17 trials across 17 logged runs" in text
    assert "distinct run labels" in text


def test_dsr_below_the_bar_gets_its_own_sentence():
    """Session-6 amendment 3: not a footnote, a sentence of its own."""
    text = results.dsr_sentences(_table(n_trials=17), backtest.HEADLINE)
    assert "**That does not clear the usual bar.**" in text


def test_dsr_above_the_bar_says_so():
    """The other branch is reachable, so the sentence is a verdict and not a constant."""
    table = _table(n_trials=17)
    table["dsr"] = 0.99
    text = results.dsr_sentences(table, backtest.HEADLINE)
    assert "clears the usual bar" in text
    assert "does not clear" not in text


# ------------------------------------------------- the report on disk, N and all


def test_report_n_equals_the_distinct_label_count():
    """The N printed in ``reports/results.md`` is ``speclog.count_runs()``, not a smaller one.

    Since the 2026-09-24 ruling that is the count of **distinct labels**; the
    append-only row count is printed beside it and is never N.
    """
    text = RESULTS.read_text(encoding="utf-8")
    printed = {int(n) for n in re.findall(r"N = (\d+)", text)}
    assert printed == {speclog.count_runs()}


def test_report_prints_the_row_count_beside_n():
    """Both figures appear, because they answer different questions."""
    text = RESULTS.read_text(encoding="utf-8")
    assert f"holds {speclog.count_rows()} rows" in text
    assert f"{speclog.count_runs()} trials across {speclog.count_runs()} logged runs" in text
    assert "a trial is a specification, not an execution" in text


def test_report_n_is_at_least_what_phase_5_left_behind():
    """A DSR quoted from an earlier session's smaller N flatters the result."""
    assert speclog.count_runs() >= results.PHASE_5_RUNS


def test_report_n_matches_the_metrics_table():
    """The table and the prose cannot disagree about how many trials there were."""
    table = pd.read_csv("data/checks/metrics_table.csv")
    assert set(table["n_trials"]) == {speclog.count_runs()}


def test_every_logged_run_is_in_the_report():
    """Rule 6 from the other side: a run that happened is reported."""
    text = RESULTS.read_text(encoding="utf-8")
    for label in pd.read_csv(speclog.DEFAULT_PATH)["label"]:
        assert f"`{label}`" in text, label


def test_report_has_every_section_the_plan_names():
    text = RESULTS.read_text(encoding="utf-8")
    for heading in (
        "## The decomposition",
        "## 2022, month by month",
        "## The three pre-registered risk controls",
        "## PCA: explained variance",
        "## PCA: loading stability by decade",
        "## What carry does not tell you",
        "## Charts",
    ):
        assert heading in text, heading


def test_report_lists_the_five_charts():
    text = RESULTS.read_text(encoding="utf-8")
    for stem in ("chart1_", "chart2_", "chart3_", "chart4_", "chart5_"):
        assert stem in text, stem


def test_replace_block_is_idempotent():
    text = RESULTS.read_text(encoding="utf-8")
    block = results.read_block(text)
    assert results.replace_block(text, block) == text
