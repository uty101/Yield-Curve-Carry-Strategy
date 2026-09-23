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
    pos, trades, skipped = overlay.build_positions(scores, returns, cfg)
    assert len(skipped) == 0
    last = pos[pos["date"] == idx[-1]]
    us = last[last["country"] == "US"]
    gb = last[last["country"] == "GB"]
    assert set(us["state"]) == {"steepener"}
    assert set(gb["state"]) == {"flattener"}
    assert us[us["leg"] == "long"]["tenor_years"].iloc[0] == 2.0
    assert gb[gb["leg"] == "long"]["tenor_years"].iloc[0] == 10.0
    for _, g in pos.groupby(["date", "country"]):
        assert g["wd"].sum() == pytest.approx(0.0, abs=1e-15)
    assert set(trades["event"]) <= {"enter", "exit"}


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
    pos, _trades, skipped = overlay.build_positions(scores, returns, cfg)
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
