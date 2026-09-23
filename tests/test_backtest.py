"""Step 5.3: the backtest engine, on synthetic panels in ``tmp_path``.

The spec-log path is injected everywhere, so no test ever appends a row to
the real ``reports/specifications.csv`` - N for the deflated Sharpe would be
wrong if it did.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest, metrics, speclog
from curvecarry import weights as wt

COUNTRIES = ["US", "GB", "DE"]
TENORS = [2.0, 5.0, 10.0]
START = "2010-01-31"


def _months(n: int) -> list[pd.Timestamp]:
    return list(pd.date_range(START, periods=n, freq="ME"))


def _cfg(
    tmp_path: Path, months: list[pd.Timestamp], minimum: int = 9, cost_bp: float = 0.5
) -> dict:
    return {
        "sample": {
            "strategy_start": months[0],
            "sample_full_start": months[len(months) // 2],
            "strategy_end": months[-1],
        },
        "weights": {
            "duration_neutral_scope": "book",
            "long_duration_budget": 5.0,
            "min_eligible_buckets": minimum,
        },
        "costs": {"cost_bp_per_duration_year": cost_bp},
    }


def _panel(
    months: list[pd.Timestamp], signal_of=None, r_of=None, duration: float = 5.0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A synthetic (signal, returns) pair over ``months`` x 9 buckets."""
    sig_rows, ret_rows = [], []
    for i, date in enumerate(months):
        for country in COUNTRIES:
            for tenor in TENORS:
                s = signal_of(i, country, tenor) if signal_of else float(tenor) + len(country)
                r = r_of(i, country, tenor) if r_of else 0.0
                sig_rows.append(
                    {
                        "date": date,
                        "country": country,
                        "tenor_years": tenor,
                        "signal": s,
                        "duration": duration,
                        "yield": 0.03,
                        "eligible": True,
                        "excluded_reason": "",
                    }
                )
                ret_rows.append(
                    {
                        "date": date,
                        "country": country,
                        "tenor_years": tenor,
                        "r_hedged": r,
                        "r_unhedged": r,
                        "closed": False,
                    }
                )
    return pd.DataFrame(sig_rows), pd.DataFrame(ret_rows)


def _write(tmp_path: Path, signal: pd.DataFrame, returns: pd.DataFrame) -> Path:
    processed = tmp_path / "processed"
    processed.mkdir(exist_ok=True)
    signal.to_parquet(processed / "signal.parquet", index=False)
    returns.to_parquet(processed / "returns.parquet", index=False)
    return processed


def _run(tmp_path: Path, cfg: dict, signal, returns, variant: str = "carry_hedged"):
    processed = _write(tmp_path, signal, returns)
    spec = tmp_path / "specifications.csv"
    return backtest.run(cfg, variant, processed=processed, speclog_path=spec, write=False), spec


def test_run_logs_specification_before_computing(tmp_path: Path) -> None:
    months = _months(6)
    cfg = _cfg(tmp_path, months)
    signal, returns = _panel(months)
    res, spec = _run(tmp_path, cfg, signal, returns)

    assert speclog.count_runs(spec) == 1
    rows = pd.read_csv(spec)
    assert rows.loc[0, "run_id"] == res.run_id
    assert rows.loc[0, "label"] == "carry_hedged"

    # a computing function called with an unlogged run_id refuses to compute
    with pytest.raises(RuntimeError):
        backtest.monthly_returns(
            pd.DataFrame(columns=wt.WEIGHT_COLUMNS),
            returns,
            backtest.VARIANTS["carry_hedged"],
            cfg,
            "not-a-run-id",
            spec,
        )


def test_timing_signal_t_return_t_to_t_plus_1(tmp_path: Path) -> None:
    """The return of month t is earned by the weights formed at t, not at t-1."""
    months = _months(4)
    cfg = _cfg(tmp_path, months)

    # month 0 and 1 rank US highest; from month 2 the ranking flips to DE.
    def signal_of(i, country, tenor):
        best = "US" if i < 2 else "DE"
        return 10.0 if country == best else (1.0 if country == "GB" else 0.0)

    # only DE earns, and only in month 2
    def r_of(i, country, tenor):
        return 0.01 if (i == 2 and country == "DE") else 0.0

    signal, returns = _panel(months, signal_of=signal_of, r_of=r_of)
    res, _ = _run(tmp_path, cfg, signal, returns)
    m = res.monthly.set_index("date")["r_gross"]
    # at month 2 DE is the long leg, so the DE move is earned, not missed
    assert m.iloc[2] > 0
    # had the old (month-1) weights been used, DE would have been the short leg
    assert m.iloc[1] == pytest.approx(0.0, abs=1e-15)


def test_portfolio_return_hand_computed(tmp_path: Path) -> None:
    """Two legs of three buckets, known weights and returns -> r_gross exactly."""
    months = _months(1)
    cfg = _cfg(tmp_path, months, cost_bp=0.0)
    signal, returns = _panel(months, r_of=lambda i, c, t: 0.02 if c == "US" else -0.01)
    res, _ = _run(tmp_path, cfg, signal, returns)

    # signal = tenor + len(country) with duration 5 for all: the three highest are
    # the 10y buckets, the three lowest the 2y buckets; wd = +-5/3, weight = wd/5 = +-1/3.
    held = res.positions
    long = held[held["leg"] == "long"]
    short = held[held["leg"] == "short"]
    expected = float((long["weight"] * long["r"]).sum() + (short["weight"] * short["r"]).sum())
    assert res.monthly.loc[0, "r_gross"] == pytest.approx(expected, abs=1e-15)
    assert np.allclose(long["weight"], 1.0 / 3.0)
    assert np.allclose(short["weight"], -1.0 / 3.0)


def test_turnover_and_cost(tmp_path: Path) -> None:
    """wd {A: +2, B: -2} -> {A: +2, C: -2} is turnover 2 and cost 0.5e-4 x 4."""
    prev = {("US", 5.0): 2.0, ("GB", 5.0): -2.0}
    now = {("US", 5.0): 2.0, ("DE", 5.0): -2.0}
    traded = backtest._turnover(prev, now)
    assert traded == pytest.approx(4.0)
    assert 0.5 * traded == pytest.approx(2.0)
    assert 0.5e-4 * traded == pytest.approx(0.5 * 1e-4 * 4.0)

    # and the engine charges exactly that: the first month is a full entry of 2B
    months = _months(2)
    cfg = _cfg(tmp_path, months)
    signal, returns = _panel(months)
    res, _ = _run(tmp_path, cfg, signal, returns)
    first = res.monthly.iloc[0]
    assert first["turnover"] == pytest.approx(5.0)  # 0.5 x (5 long + 5 short)
    assert first["cost"] == pytest.approx(0.5 * 1e-4 * 10.0)
    assert first["r_net"] == pytest.approx(first["r_gross"] - first["cost"])
    # nothing changes in month 2, so nothing is traded and nothing is charged
    assert res.monthly.iloc[1]["turnover"] == pytest.approx(0.0)
    assert res.monthly.iloc[1]["cost"] == pytest.approx(0.0)


def test_missing_bucket_not_held_and_closed_is_zero(tmp_path: Path) -> None:
    months = _months(2)
    cfg = _cfg(tmp_path, months, minimum=8)
    signal, returns = _panel(months, r_of=lambda i, c, t: 0.05)
    # DE 10y has no unhedged return at all, and US 2y is closed in month 0
    returns.loc[(returns["country"] == "DE") & (returns["tenor_years"] == 10.0), "r_unhedged"] = (
        np.nan
    )
    returns.loc[
        (returns["date"] == months[0])
        & (returns["country"] == "US")
        & (returns["tenor_years"] == 2.0),
        "closed",
    ] = True

    res, _ = _run(tmp_path, cfg, signal, returns, variant="carry_unhedged")
    held = res.positions
    assert not ((held["country"] == "DE") & (held["tenor_years"] == 10.0)).any()
    # the book is still neutral after the drop, because the drop happened before sizing
    assert abs(held.groupby("date")["wd"].sum()).max() < 1e-10

    closed = held[(held["country"] == "US") & (held["tenor_years"] == 2.0)]
    assert (closed[closed["date"] == months[0]]["r"] == 0.0).all()
    assert res.monthly.loc[0, "n_closed"] >= 1


def test_net_notional_is_financed(tmp_path: Path) -> None:
    """Returns are excess returns, so a net long notional pays its own financing."""
    r_short = 0.04
    # zero price change: every bucket earns exactly minus its financing
    excess = -r_short / 12.0
    months = _months(1)
    cfg = _cfg(tmp_path, months, cost_bp=0.0)
    # durations differ so that the legs do not have equal notional: long D 2.5, short D 10
    signal, returns = _panel(months, r_of=lambda i, c, t: excess)
    signal["duration"] = np.where(signal["tenor_years"] == 10.0, 2.5, 10.0)
    res, _ = _run(tmp_path, cfg, signal, returns)
    notional = float(res.positions["weight"].sum())
    assert abs(notional) > 0.1, "the test needs a net notional to be meaningful"
    assert res.monthly.loc[0, "r_gross"] == pytest.approx(notional * excess, abs=1e-15)


def test_metrics_closed_forms() -> None:
    idx = pd.date_range("2010-01-31", periods=24, freq="ME")
    const = pd.Series(0.01, index=idx)
    assert metrics.annualised_return(const) == pytest.approx(0.12)
    assert metrics.annualised_vol(const) == pytest.approx(0.0)
    assert metrics.max_drawdown(const).depth == pytest.approx(0.0)

    r = pd.Series([-0.10, 0.05], index=idx[:2])
    dd = metrics.max_drawdown(r)
    assert dd.depth == pytest.approx(-0.10)
    assert dd.peak_date is None or dd.peak_date == idx[0]
    assert dd.trough_date == idx[0]

    down = pd.Series([0.0, -0.10, 0.05], index=idx[:3])
    dd2 = metrics.max_drawdown(down)
    assert dd2.depth == pytest.approx(-0.10)
    assert dd2.peak_date == idx[0]
    assert dd2.trough_date == idx[1]


def test_two_windows_reported(tmp_path: Path) -> None:
    months = _months(12)
    cfg = _cfg(tmp_path, months)
    signal, returns = _panel(months, r_of=lambda i, c, t: 0.001 * (i % 3 - 1))
    res, _ = _run(tmp_path, cfg, signal, returns)
    assert set(res.metrics["window"]) == {"full", "six"}
    full = res.metrics[(res.metrics["window"] == "full") & (res.metrics["metric"] == "n_months")]
    six = res.metrics[(res.metrics["window"] == "six") & (res.metrics["metric"] == "n_months")]
    assert float(full["value"].iloc[0]) == 12.0
    assert float(six["value"].iloc[0]) == 6.0
    # gross and net are both reported
    assert {"ann_return", "ann_return_gross"} <= set(res.metrics["metric"])


def test_appending_months_does_not_change_weights_at_t(tmp_path: Path) -> None:
    """Session-5 amendment 5: the weights at t do not move when the future arrives."""
    months = _months(36)
    cfg = _cfg(tmp_path, months)
    rng = np.random.default_rng(7)
    values = {(i, c, t): float(rng.normal()) for i in range(36) for c in COUNTRIES for t in TENORS}
    signal, _ = _panel(months, signal_of=lambda i, c, t: values[(i, c, t)])

    cut = months[11]
    short_panel = signal[signal["date"] <= cut]
    early, _ = wt.duration_neutral_weights(short_panel, cfg)
    late, _ = wt.duration_neutral_weights(signal, cfg)
    late = late[late["date"] <= cut]

    key = ["date", "country", "tenor_years"]
    a = early.sort_values(key).reset_index(drop=True)
    b = late.sort_values(key).reset_index(drop=True)
    assert list(zip(a["date"], a["country"], a["tenor_years"], a["leg"], strict=True)) == list(
        zip(b["date"], b["country"], b["tenor_years"], b["leg"], strict=True)
    )
    assert np.abs(a["wd"].to_numpy() - b["wd"].to_numpy()).max() < 1e-12


def test_extreme_months_names_the_legs(tmp_path: Path) -> None:
    """Amendment 2: the biggest months come with the buckets that drove them."""
    months = _months(6)
    cfg = _cfg(tmp_path, months, cost_bp=0.0)
    # month 3 is the only month anything moves, and only the US 10y bucket does
    signal, returns = _panel(
        months, r_of=lambda i, c, t: 0.05 if (c == "US" and t == 10.0 and i == 3) else 0.0
    )
    res, _ = _run(tmp_path, cfg, signal, returns)
    table = backtest.extreme_months(res.monthly, res.positions, n=2, legs=2)

    assert list(table.columns) == backtest.EXTREME_COLUMNS
    assert set(table["sign"]) == {"gain", "loss"}
    best = table[(table["sign"] == "gain") & (table["rank"] == 1)]
    assert best["date"].nunique() == 1
    assert best["date"].iloc[0] == months[3].date().isoformat()
    # the contribution column is weight x the bucket's own return, and the
    # biggest contributor that month is a US bucket
    assert best.iloc[0]["country"] == "US"
    assert best["contribution"].iloc[0] == pytest.approx(
        best["wd"].iloc[0] / 5.0 * best["r_bucket"].iloc[0], abs=1e-15
    )
