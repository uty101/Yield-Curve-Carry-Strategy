"""Step 5.4: the expanding PC2 score, its z-score, the state machine and the pair."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import overlay

TENORS = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0]


def _cfg(
    min_months: int = 60, window: int = 36, entry: float = 1.5, exit_level: float = 0.0
) -> dict:
    return {
        "pca": {"pca_min_months": min_months, "pca_z_window": window},
        "overlay": {
            "z_entry": entry,
            "z_exit": exit_level,
            "overlay_duration_budget": 2.0,
            "overlay_tenors": [2, 10],
        },
    }


def _changes(n: int, seed: int = 3) -> pd.DataFrame:
    """A synthetic bp-change panel with a level factor, a slope factor and noise."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1990-01-31", periods=n, freq="ME")
    level = rng.normal(0, 20, n)[:, None] * np.ones(len(TENORS))
    slope = rng.normal(0, 8, n)[:, None] * (np.array(TENORS) - 5.0)
    noise = rng.normal(0, 2, (n, len(TENORS)))
    return pd.DataFrame(level + slope + noise, index=idx, columns=TENORS)


def test_score_at_t_unchanged_when_future_appended() -> None:
    """Rule 7 on the loadings themselves: 24 more months do not move a past score."""
    full = _changes(120)
    cut = 84
    early = overlay.expanding_pc2_scores({"US": full.iloc[:cut]}, _cfg())
    late = overlay.expanding_pc2_scores({"US": full}, _cfg())
    late = late[late["date"].isin(early["date"])]
    a = early.sort_values("date")["score"].to_numpy()
    b = late.sort_values("date")["score"].to_numpy()
    both = np.isfinite(a) & np.isfinite(b)
    assert both.sum() >= 20
    assert np.isfinite(a).tolist() == np.isfinite(b).tolist()
    assert np.abs(a[both] - b[both]).max() < 1e-12


def test_no_score_before_min_months() -> None:
    scores = overlay.expanding_pc2_scores({"US": _changes(80)}, _cfg()).sort_values("date")
    assert int(scores.iloc[58]["n_months"]) == 59
    assert not np.isfinite(scores.iloc[58]["score"])
    assert int(scores.iloc[59]["n_months"]) == 60
    assert np.isfinite(scores.iloc[59]["score"])


def test_state_machine_sequences() -> None:
    cfg = _cfg()

    def run(values):
        idx = pd.date_range("2000-01-31", periods=len(values), freq="ME")
        return list(overlay.states(pd.Series(values, index=idx), cfg))

    assert run([-1.6, -0.5, 0.1, -1.6]) == ["steepener", "steepener", "flat", "steepener"]
    assert run([-1.6, -1.0, -1.7]) == ["steepener", "steepener", "steepener"]
    assert run([1.6, 0.5, -0.2, 1.6]) == ["flattener", "flattener", "flat", "flattener"]
    assert run([-1.6, np.nan, -1.6]) == ["steepener", "flat", "flat"]


def test_pair_is_duration_neutral_and_sized() -> None:
    cfg = _cfg()
    date = pd.Timestamp("2010-01-31")
    durations = {2.0: 1.95, 10.0: 8.4}
    steep = pd.DataFrame(overlay.pair_rows(date, "US", "steepener", -1.9, durations, cfg))
    assert steep["wd"].sum() == pytest.approx(0.0, abs=1e-15)
    long = steep[steep["leg"] == "long"]
    assert long["tenor_years"].iloc[0] == 2.0
    assert long["wd"].iloc[0] == pytest.approx(2.0)
    assert np.allclose(steep["weight"] * steep["duration"], steep["wd"])

    flat = pd.DataFrame(overlay.pair_rows(date, "US", "flattener", 1.9, durations, cfg))
    assert flat["wd"].sum() == pytest.approx(0.0, abs=1e-15)
    assert flat[flat["leg"] == "long"]["tenor_years"].iloc[0] == 10.0

    assert overlay.pair_rows(date, "US", "flat", 0.0, durations, cfg) == []


def test_zscore_window_and_ddof() -> None:
    idx = pd.date_range("2000-01-31", periods=40, freq="ME")
    s = pd.Series(np.arange(40, dtype="float64"), index=idx)
    z = overlay.zscore(s, 36)
    assert z.iloc[:35].isna().all()
    window = s.iloc[:36]
    expected = (window.iloc[-1] - window.mean()) / window.std(ddof=1)
    assert z.iloc[35] == pytest.approx(expected, rel=1e-12)
    # ddof 0 would give a different number, so the test is not vacuous
    assert z.iloc[35] != pytest.approx((window.iloc[-1] - window.mean()) / window.std(ddof=0))


def test_zscore_at_t_unchanged_when_future_appended() -> None:
    """Session-5 amendment 5: the rolling mean and sd on top of the score do not look ahead."""
    full = _changes(140)
    cut = 100
    cfg = _cfg()
    early = overlay.expanding_pc2_scores({"US": full.iloc[:cut]}, cfg)
    late = overlay.expanding_pc2_scores({"US": full}, cfg)
    za = overlay.zscore(early.set_index("date")["score"], cfg["pca"]["pca_z_window"])
    zb = overlay.zscore(late.set_index("date")["score"], cfg["pca"]["pca_z_window"])
    zb = zb.loc[za.index]
    both = za.notna() & zb.notna()
    assert both.sum() >= 5
    assert np.abs(za[both] - zb[both]).max() < 1e-12
    assert za.notna().tolist() == zb.notna().tolist()


def test_states_are_per_country_and_positions_follow_them() -> None:
    """Two countries with opposite z paths hold opposite pairs in the same month."""
    cfg = _cfg(window=5)
    idx = pd.date_range("2010-01-31", periods=8, freq="ME")
    scores = pd.DataFrame(
        [
            {"country": c, "date": d, "score": s, "n_months": 60}
            for c, path in (
                ("US", [0.0, 0.0, 0.0, 0.0, 3.0, -1.0, -20.0, -20.0]),
                ("GB", [0.0, 0.0, 0.0, 0.0, -3.0, 1.0, 20.0, 20.0]),
            )
            for d, s in zip(idx, path, strict=True)
        ]
    )
    returns = pd.DataFrame(
        [
            {"date": d, "country": c, "tenor_years": t, "duration": t * 0.9}
            for d in idx
            for c in ("US", "GB")
            for t in (2.0, 10.0)
        ]
    )
    pos, detail, skipped = overlay.build_positions(scores, returns, cfg)
    assert len(skipped) == 0
    assert set(detail["state"]) <= {"flat", "steepener", "flattener"}
    last = pos[pos["date"] == idx[-1]]
    us = last[last["country"] == "US"]
    gb = last[last["country"] == "GB"]
    assert set(us["state"]) == {"steepener"}
    assert set(gb["state"]) == {"flattener"}
    assert us[us["leg"] == "long"]["tenor_years"].iloc[0] == 2.0
    assert gb[gb["leg"] == "long"]["tenor_years"].iloc[0] == 10.0
    for _, g in pos.groupby(["date", "country"]):
        assert g["wd"].sum() == pytest.approx(0.0, abs=1e-15)


def test_pair_without_a_leg_duration_is_skipped_whole() -> None:
    cfg = _cfg(window=5)
    idx = pd.date_range("2010-01-31", periods=8, freq="ME")
    scores = pd.DataFrame(
        [
            {"country": "US", "date": d, "score": s, "n_months": 60}
            for d, s in zip(idx, [0.0, 0.0, 0.0, 0.0, 3.0, -1.0, -20.0, -20.0], strict=True)
        ]
    )
    returns = pd.DataFrame(
        [
            {"date": d, "country": "US", "tenor_years": 2.0, "duration": 1.9}
            for d in idx  # the 10-year leg has no duration at all
        ]
    )
    pos, _detail, skipped = overlay.build_positions(scores, returns, cfg)
    assert len(pos) == 0
    assert len(skipped) >= 1
    assert set(skipped["reason"]) == {"no duration for a leg"}


def test_warm_up_nans_leave_the_overlay_disarmed_until_z_crosses() -> None:
    """The plan's NaN rule, applied to the warm-up window: the first signal is skipped.

    ``z`` is NaN until the rolling window is full, and a NaN clears both armed
    flags "until the next crossing". So a country whose very first finite
    ``z`` is already beyond the entry threshold does **not** enter: it waits
    for ``z`` to cross ``z_exit`` and arm it. This is the literal rule and it
    is deliberate - an entry on the first number a 36-month window ever
    produces would be an entry on a threshold the series has never been
    tested against.
    """
    cfg = _cfg(window=5)
    idx = pd.date_range("2010-01-31", periods=8, freq="ME")
    # z is +1.79 at index 4 (beyond entry, but disarmed), crosses zero at
    # index 5, and is -1.77 at index 6, which is the first trade.
    z = overlay.zscore(pd.Series([0.0, 0.0, 0.0, 0.0, 3.0, -1.0, -20.0, -20.0], index=idx), 5)
    assert z.iloc[4] > cfg["overlay"]["z_entry"]
    got = list(overlay.states(z, cfg))
    assert got[4] == "flat"
    assert got[6] == "steepener"


# ------------------------------------------- session-5 fix 1: trade anatomy


def _detail(country: str, states: list[str], zs: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2010-01-31", periods=len(states), freq="ME")
    return pd.DataFrame(
        {
            "country": country,
            "date": idx,
            "z": zs,
            "state": states,
            "armed_steep": True,
            "armed_flat": True,
            "signal_present": [abs(v) > 1.5 for v in zs],
            "blocked": False,
        }
    )


def _positions(country: str, dates, contributions) -> pd.DataFrame:
    """One leg per month carrying the whole contribution, so the PnL is known."""
    return pd.DataFrame(
        [
            {
                "date": d,
                "country": country,
                "tenor_years": 2.0,
                "leg": "long",
                "duration": 2.0,
                "weight": 1.0,
                "wd": 2.0,
                "r": c,
            }
            for d, c in zip(dates, contributions, strict=True)
        ]
    )


def _anatomy_cfg() -> dict:
    cfg = _cfg()
    cfg["overlay"]["overlay_duration_budget"] = 2.0
    cfg["costs"] = {"cost_bp_per_duration_year": 0.5}
    cfg["sample"] = {
        "strategy_start": pd.Timestamp("2010-01-31"),
        "strategy_end": pd.Timestamp("2011-12-31"),
    }
    return cfg


def test_a_trade_is_a_run_of_months_with_its_own_pnl() -> None:
    """Two separate trades, not one: the flat month between them splits the run."""
    detail = _detail(
        "US",
        ["flat", "steepener", "steepener", "flat", "flattener", "flat"],
        [0.1, -1.6, -1.0, 0.2, 1.7, -0.1],
    )
    dates = list(detail["date"])
    pos = _positions("US", [dates[1], dates[2], dates[4]], [0.001, 0.002, -0.004])
    trades, _stats = overlay.trade_anatomy(detail, pos, _anatomy_cfg())

    assert len(trades) == 2
    first, second = trades.iloc[0], trades.iloc[1]
    assert first["direction"] == "steepener"
    assert first["entry_date"] == dates[1].date().isoformat()
    assert first["exit_date"] == dates[3].date().isoformat()
    assert first["months_held"] == 2
    assert first["entry_z"] == pytest.approx(-1.6)
    assert first["exit_z"] == pytest.approx(0.2)
    assert first["pnl_bp"] == pytest.approx(30.0)  # (0.001 + 0.002) x 1e4
    assert first["cost_bp"] == pytest.approx(4.0)  # 0.5 bp x 2 x B_o, twice
    assert first["pnl_net_bp"] == pytest.approx(26.0)
    assert not first["still_open"]

    assert second["direction"] == "flattener"
    assert second["months_held"] == 1
    assert second["pnl_bp"] == pytest.approx(-40.0)


def test_a_trade_still_open_at_the_end_pays_only_the_entry() -> None:
    detail = _detail("US", ["flat", "steepener", "steepener"], [0.1, -1.6, -1.2])
    dates = list(detail["date"])
    pos = _positions("US", [dates[1], dates[2]], [0.001, 0.001])
    trades, _stats = overlay.trade_anatomy(detail, pos, _anatomy_cfg())

    assert len(trades) == 1
    row = trades.iloc[0]
    assert bool(row["still_open"])
    assert row["exit_date"] == ""
    assert row["cost_bp"] == pytest.approx(2.0)
    assert row["pnl_net_bp"] == pytest.approx(20.0 - 2.0)


def test_country_stats_count_the_market_and_the_hit_rate() -> None:
    detail = pd.concat(
        [
            _detail(
                "US",
                ["flat", "steepener", "steepener", "flat", "flattener", "flat"],
                [0.1, -1.6, -1.0, 0.2, 1.7, -0.1],
            ),
            _detail("GB", ["flat"] * 6, [0.1] * 6),
        ],
        ignore_index=True,
    )
    dates = sorted(detail["date"].unique())
    pos = _positions("US", [dates[1], dates[2], dates[4]], [0.001, 0.002, -0.004])
    _trades, stats = overlay.trade_anatomy(detail, pos, _anatomy_cfg())

    us = stats[stats["country"] == "US"].iloc[0]
    assert us["trades"] == 2
    assert us["months_in_market"] == 3
    assert us["months_in_sample"] == 6
    assert us["share_in_market"] == pytest.approx(0.5)
    assert us["hit_rate"] == pytest.approx(0.5)  # one winner, one loser
    assert us["total_pnl_net_bp"] == pytest.approx(26.0 - 44.0)

    gb = stats[stats["country"] == "GB"].iloc[0]
    assert gb["trades"] == 0
    assert gb["months_in_market"] == 0
    assert np.isnan(gb["hit_rate"])


def test_a_month_armed_but_not_traded_is_counted() -> None:
    """The warm-up disarm again, this time counted rather than only asserted."""
    cfg = _cfg(window=5)
    idx = pd.date_range("2010-01-31", periods=8, freq="ME")
    z = overlay.zscore(pd.Series([0.0, 0.0, 0.0, 0.0, 3.0, -1.0, -20.0, -20.0], index=idx), 5)
    detail = overlay.state_detail(z, cfg)
    # index 4 has |z| > 1.5 and stays flat because the warm-up NaNs disarmed it
    assert bool(detail.iloc[4]["signal_present"])
    assert detail.iloc[4]["state"] == "flat"
    assert bool(detail.iloc[4]["blocked"])
    # and a NaN month is not counted as blocked, because there was no signal
    assert not bool(detail.iloc[0]["blocked"])
    assert int(detail["blocked"].sum()) == 1


def test_trade_pnl_ties_out_to_the_run() -> None:
    """Every month of the run belongs to exactly one trade, so the sums must agree."""
    detail = _detail(
        "US",
        ["flat", "steepener", "steepener", "flat", "flattener", "flat"],
        [0.1, -1.6, -1.0, 0.2, 1.7, -0.1],
    )
    dates = list(detail["date"])
    held = [dates[1], dates[2], dates[4]]
    contributions = [0.001, 0.002, -0.004]
    pos = _positions("US", held, contributions)
    trades, _stats = overlay.trade_anatomy(detail, pos, _anatomy_cfg(), sample_months=set(dates))

    assert trades["pnl_bp"].sum() == pytest.approx(sum(contributions) * 1e4)
    # two round trips, all four legs inside the sample
    assert trades["cost_bp"].sum() == pytest.approx(8.0)

    # a leg outside the covered months is not charged, because the engine never charged it
    short = overlay.trade_anatomy(detail, pos, _anatomy_cfg(), sample_months=set(dates[:3]))[0]
    assert short["cost_bp"].sum() == pytest.approx(2.0)
