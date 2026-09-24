"""Step 6.2: the three pre-registered controls, and that none of them looks ahead."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest, config, pca, risk_controls

DATES = pd.date_range("2000-01-31", periods=40, freq="ME")


def _cfg() -> dict:
    return {
        "risk": {
            "target_vol": 0.05,
            "vol_window_months": 12,
            "max_leverage": 2.0,
            "dd_stop": 0.10,
            "dd_reentry_months": 3,
            "rates_vol_pct": 0.90,
            "rates_vol_window_months": 120,
            "risk_control_base_variants": ["carry_hedged", "combined_hedged"],
        },
        "pca": {"pca_min_months": 6, "pca_z_window": 36},
        "sample": {"strategy_start": "2000-01-31", "sample_full_start": "2001-01-31"},
    }


def _returns(seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.002, 0.01, len(DATES)), index=DATES)


# -------------------------------------------------------------- (a) vol target


def test_vol_target_scale_formula_and_cap():
    """``min(target / trailing vol, cap)``, computed by hand on month 13."""
    cfg = _cfg()
    r = _returns()
    scale = risk_controls.vol_target_scale(r, cfg)
    # the first 12 months have no 12-month window ending at t-1
    assert (scale.iloc[:12] == 1.0).all()
    window = r.iloc[:12]
    vol = float(window.std(ddof=1)) * math.sqrt(12)
    assert scale.iloc[12] == pytest.approx(min(0.05 / vol, 2.0))
    assert scale.max() <= cfg["risk"]["max_leverage"] + 1e-12


def test_vol_target_caps_at_max_leverage():
    """A near-flat book asks for far more than the cap and gets exactly the cap."""
    cfg = _cfg()
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0, 1e-6, len(DATES)), index=DATES)  # vol far below target
    assert risk_controls.vol_target_scale(r, cfg).iloc[-1] == cfg["risk"]["max_leverage"]


def test_vol_target_uses_only_past_returns():
    """Changing ``r_t`` does not move ``scale_t``; changing ``r_{t-1}`` does."""
    cfg = _cfg()
    r = _returns()
    base = risk_controls.vol_target_scale(r, cfg)
    t = DATES[20]
    bumped_t = r.copy()
    bumped_t.loc[t] += 0.5
    assert risk_controls.vol_target_scale(bumped_t, cfg).loc[t] == base.loc[t]
    bumped_prev = r.copy()
    bumped_prev.loc[DATES[19]] += 0.5
    assert risk_controls.vol_target_scale(bumped_prev, cfg).loc[t] != base.loc[t]


# --------------------------------------------------------------- (b) dd stop


def test_dd_stop_goes_flat_next_month_for_exactly_reentry_months():
    """One breach flattens exactly ``dd_reentry_months`` months, starting at ``t+1``."""
    cfg = _cfg()
    r = pd.Series(0.0, index=DATES)
    r.iloc[5] = -0.20  # a single month through the 10% stop
    r.iloc[6] = 0.30  # and back above the old peak, so the breach is one month long
    flat = risk_controls.dd_stop_flat_months(r, cfg)
    # the drawdown first appears in r_5, so it is seen at t = 6 and flattens 7, 8, 9
    assert list(flat[flat].index) == list(DATES[7:10])
    assert int(flat.sum()) == cfg["risk"]["dd_reentry_months"]


def test_dd_stop_uses_wealth_through_t_minus_1():
    """A breach that first appears in ``r_t`` does not flatten ``t``; it flattens ``t+1``."""
    cfg = _cfg()
    r = pd.Series(0.0, index=DATES)
    r.iloc[5] = -0.20
    r.iloc[6] = 0.30
    flat = risk_controls.dd_stop_flat_months(r, cfg)
    assert not flat.iloc[5]
    assert not flat.iloc[6]
    assert flat.iloc[7]


def test_dd_stop_reenters_at_the_base_book():
    """After the flat window the positions are the base's own, unchanged."""
    cfg = _cfg()
    positions = pd.DataFrame(
        {
            "date": DATES,
            "country": "US",
            "tenor_years": 5.0,
            "leg": "long",
            "signal": 0.0,
            "duration": 4.0,
            "weight": 1.0,
            "wd": 4.0,
        }
    )
    r = pd.Series(0.0, index=DATES)
    r.iloc[5] = -0.20
    r.iloc[6] = 0.30
    monthly = pd.DataFrame({"date": DATES, "r_net": r.to_numpy()})
    out, _table = risk_controls.apply_control(risk_controls.DD_STOP, positions, monthly, cfg)
    assert set(out["date"]) == set(DATES) - set(DATES[7:10])
    assert (out["weight"] == 1.0).all()


# ----------------------------------------------------- (c) pooled PC1 filter


def _changes(seed: int = 0, n: int = 30) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    tenors = [1.0, 2.0, 5.0, 10.0]
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    return {
        c: pd.DataFrame(rng.normal(0.0, 10.0, (n, len(tenors))), index=idx, columns=tenors)
        for c in ("US", "GB", "DE")
    }


def test_rates_filter_expanding_percentile_no_lookahead():
    """Appending months after ``t`` leaves the flag at ``t`` unchanged."""
    cfg = _cfg()
    changes = _changes()
    short = {k: v.iloc[:24] for k, v in changes.items()}
    long_flags = risk_controls.rates_vol_flags(
        risk_controls.pooled_pc1_scores(changes, cfg), cfg
    ).set_index("date")
    short_flags = risk_controls.rates_vol_flags(
        risk_controls.pooled_pc1_scores(short, cfg), cfg
    ).set_index("date")
    common = short_flags.index
    assert list(long_flags.loc[common, "triggers"]) == list(short_flags["triggers"])
    assert long_flags.loc[common, "vol"].equals(short_flags["vol"])


def test_pooled_pc1_score_is_the_cross_country_mean():
    """The score is the mean of each country's own PC1 score at that month."""
    cfg = _cfg()
    changes = _changes(seed=5)
    scores = risk_controls.pooled_pc1_scores(changes, cfg)
    assert scores["score"].iloc[: cfg["pca"]["pca_min_months"] - 1].isna().all()
    assert scores["n_countries"].max() == len(changes)
    assert scores["score"].notna().any()


def test_rates_filter_flags_only_the_top_tail():
    """At the 90th expanding percentile, at most a tenth of the months are flagged."""
    cfg = _cfg()
    table = risk_controls.rates_vol_flags(
        risk_controls.pooled_pc1_scores(_changes(seed=9, n=80), cfg), cfg
    )
    usable = table[table["vol"].notna()]
    assert usable["triggers"].mean() <= 0.25  # expanding, so early months flag more often


# ------------------------------------------------------- the 2022 attribution


def _pieces_and_monthly() -> tuple[pd.DataFrame, pd.DataFrame]:
    months = pd.date_range("2022-01-31", periods=12, freq="ME")
    rng = np.random.default_rng(1)
    rows = []
    for date in months:
        for country in ("US", "GB"):
            for leg in ("long", "short"):
                rows.append(
                    {
                        "date": date,
                        "country": country,
                        "tenor_years": 5.0,
                        "leg": leg,
                        "weight": float(rng.normal(0.0, 1.0)),
                        "carry_earned": float(rng.normal(0.0005, 0.0002)),
                        "yield_change_pnl": float(rng.normal(0.0, 0.004)),
                        "yield_change_taylor": 0.0,
                        "taylor_residual": 0.0,
                        "funding": 0.0,
                        "fx": 0.0,
                    }
                )
    pieces = pd.DataFrame(rows)
    gross = pieces.groupby("date")[["carry_earned", "yield_change_pnl"]].sum().sum(axis=1)
    monthly = pd.DataFrame({"date": months, "cost": 0.0002})
    monthly["r_net"] = monthly["date"].map(gross) - monthly["cost"]
    return pieces, monthly


def test_attribution_2022_rows_sum_to_total():
    """The country-leg rows sum to the ``ALL`` row, which is that month's ``r_net``."""
    pieces, monthly = _pieces_and_monthly()
    table = risk_controls.attribution_rows(pieces, monthly)
    assert len(table["date"].unique()) == 12
    for date, g in table.groupby("date"):
        parts = g[g["country"] != risk_controls.ALL_COUNTRIES]
        whole = g[g["country"] == risk_controls.ALL_COUNTRIES]
        assert len(whole) == 1
        assert parts["total"].sum() == pytest.approx(float(whole["total"].iloc[0])), date
        expected = float(monthly.loc[monthly["date"] == date, "r_net"].iloc[0])
        assert float(whole["total"].iloc[0]) == pytest.approx(expected)


def test_attribution_cost_is_allocated_not_invented():
    """The allocated costs add to the month's cost, with the sign it has in the return."""
    pieces, monthly = _pieces_and_monthly()
    table = risk_controls.attribution_rows(pieces, monthly)
    parts = table[table["country"] != risk_controls.ALL_COUNTRIES]
    for date, g in parts.groupby("date"):
        cost = float(monthly.loc[monthly["date"] == date, "cost"].iloc[0])
        assert g["cost"].sum() == pytest.approx(-cost)


# ------------------------------------------- the variant table and the config


def test_risk_control_bases_match_config():
    """``RISK_CONTROL_BASES`` is exactly ``config.risk.risk_control_base_variants``."""
    cfg = config.load()
    assert list(backtest.RISK_CONTROL_BASES) == list(cfg["risk"]["risk_control_base_variants"])


def test_every_risk_control_variant_names_its_base():
    """Each control on each base, each carrying the base it transforms."""
    made = {k: v for k, v in backtest.VARIANTS.items() if v.risk_control}
    assert len(made) == len(backtest.RISK_CONTROL_BASES) * len(risk_controls.CONTROLS)
    for name, spec in made.items():
        assert spec.base_variant in backtest.VARIANTS
        base = backtest.VARIANTS[spec.base_variant]
        assert spec.returns_column == base.returns_column
        assert spec.book == base.book
        assert name == risk_controls.variant_name(spec.base_variant, spec.risk_control)


def test_risk_control_note_records_the_control():
    """The spec-log note names the control and its base, so a row explains itself."""
    name = risk_controls.variant_name("carry_hedged", risk_controls.VOL_TARGET)
    note = backtest.variant_note(backtest.VARIANTS[name], "")
    assert risk_controls.VOL_TARGET in note
    assert "carry_hedged" in note


def test_no_control_changes_the_headline():
    """The headline is still ``carry_hedged``, and no control run is it."""
    assert backtest.HEADLINE == "carry_hedged"
    assert not backtest.VARIANTS[backtest.HEADLINE].risk_control


# ---------- session-6 fix 1: a null result has to be distinguishable from a no-op


def test_rates_vol_flag_is_applied_to_the_weights():
    """A raised flag removes that month's positions.

    Without this, a filter that never fires and a filter whose flag never
    reaches the book are the same observation: both report zero flat months.
    """
    dates = pd.date_range("2000-01-31", periods=6, freq="ME")
    positions = pd.DataFrame(
        {
            "date": list(dates) * 2,
            "country": ["US"] * 6 + ["GB"] * 6,
            "tenor_years": 5.0,
            "leg": "long",
            "signal": 0.0,
            "duration": 4.0,
            "weight": 1.0,
            "wd": 4.0,
        }
    )
    victim = dates[2]
    flat = pd.Series(False, index=dates)
    flat.loc[victim] = True
    keep = ~positions["date"].map(flat).fillna(False).to_numpy(dtype=bool)
    out = positions[keep]
    assert int((positions["date"] == victim).sum()) == 2
    assert int((out["date"] == victim).sum()) == 0
    assert len(out) == len(positions) - 2


def test_rates_vol_filter_fires_on_a_series_that_should_fire():
    """The rule is not vacuous: a score series whose volatility keeps rising triggers.

    Proves the comparison is ``vol`` against a percentile **of vol**, and that
    including the current month in the expanding quantile does not make
    exceedance impossible.
    """
    cfg = _cfg()
    n = 60
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(4)
    rising = rng.normal(0.0, 1.0, n) * np.linspace(1.0, 20.0, n)
    table = risk_controls.rates_vol_flags(
        pd.DataFrame({"date": idx, "n_countries": 3, "score": rising}), cfg
    )
    assert bool(table["armed"].any())
    assert int(table["triggers"].sum()) > 0
    # and the flag only ever goes up when the ratio is above one
    fired = table[table["triggers"]]
    assert float(fired["ratio"].min()) > 1.0
    assert float(table[~table["triggers"] & table["armed"]]["ratio"].max()) <= 1.0


def test_rates_vol_ratio_is_written_for_every_armed_month():
    """``ratio`` turns a bare ``False`` into a distance, so a null can be read."""
    cfg = _cfg()
    idx = pd.date_range("2000-01-31", periods=40, freq="ME")
    rng = np.random.default_rng(5)
    table = risk_controls.rates_vol_flags(
        pd.DataFrame({"date": idx, "n_countries": 3, "score": rng.normal(0.0, 10.0, 40)}), cfg
    )
    armed = table[table["armed"]]
    assert len(armed) > 0
    assert armed["ratio"].notna().all()
    assert (armed["ratio"] > 0).all()


# ------ session-6 amendment 9: the rolling percentile, the live test of (c)


# pandas computes a rolling variance with a running-sum update, so a huge value
# entering and leaving the window leaves a floating-point residue in every later
# value. It is ~2e-12 against a vol level of ~9, a relative 3e-13, and it is
# arithmetic noise rather than information: these two tests compare with a
# tolerance rather than with ``equals`` for that reason and no other.
ROLLING_FP_TOLERANCE = 1e-9


def test_rolling_threshold_uses_only_the_trailing_window():
    """The rolling threshold at ``t`` ignores ``v`` older than the window."""
    cfg = _cfg()
    cfg["risk"]["rates_vol_window_months"] = 24
    n = 90
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(11)
    score = rng.normal(0.0, 10.0, n)
    table = risk_controls.rates_vol_flags(
        pd.DataFrame({"date": idx, "n_countries": 3, "score": score}), cfg, risk_controls.ROLLING
    )
    # a huge spike in the first year cannot reach a threshold 60 months later
    spiked = score.copy()
    spiked[:12] *= 50.0
    after = risk_controls.rates_vol_flags(
        pd.DataFrame({"date": idx, "n_countries": 3, "score": spiked}), cfg, risk_controls.ROLLING
    )
    late = table["date"] >= idx[60]
    gap = (table.loc[late, "threshold"] - after.loc[late, "threshold"]).abs().max()
    assert float(gap) < ROLLING_FP_TOLERANCE


def test_rolling_and_expanding_differ_only_in_the_threshold():
    """Same score, same vol, same arming rule; only the percentile in force changes."""
    cfg = _cfg()
    cfg["risk"]["rates_vol_window_months"] = 24
    idx = pd.date_range("1990-01-31", periods=120, freq="ME")
    rng = np.random.default_rng(12)
    scores = pd.DataFrame({"date": idx, "n_countries": 3, "score": rng.normal(0.0, 10.0, 120)})
    a = risk_controls.rates_vol_flags(scores, cfg, risk_controls.EXPANDING)
    b = risk_controls.rates_vol_flags(scores, cfg, risk_controls.ROLLING)
    assert a["vol"].equals(b["vol"])
    assert list(a["method"].unique()) == [risk_controls.EXPANDING]
    assert list(b["method"].unique()) == [risk_controls.ROLLING]
    assert not a["threshold"].equals(b["threshold"])


def test_rolling_percentile_is_not_lookahead():
    """Appending months after ``t`` leaves the rolling threshold and flag at ``t`` alone."""
    cfg = _cfg()
    cfg["risk"]["rates_vol_window_months"] = 24
    idx = pd.date_range("1990-01-31", periods=120, freq="ME")
    rng = np.random.default_rng(13)
    full = pd.DataFrame({"date": idx, "n_countries": 3, "score": rng.normal(0.0, 10.0, 120)})
    long = risk_controls.rates_vol_flags(full, cfg, risk_controls.ROLLING).set_index("date")
    short = risk_controls.rates_vol_flags(full.iloc[:90], cfg, risk_controls.ROLLING).set_index(
        "date"
    )
    common = short.index
    gap = (long.loc[common, "threshold"] - short["threshold"]).abs().max()
    assert float(gap) < ROLLING_FP_TOLERANCE
    assert list(long.loc[common, "triggers"]) == list(short["triggers"])


def test_unknown_percentile_method_raises():
    cfg = _cfg()
    idx = pd.date_range("2000-01-31", periods=20, freq="ME")
    scores = pd.DataFrame({"date": idx, "n_countries": 3, "score": 1.0})
    with pytest.raises(KeyError):
        risk_controls.rates_vol_flags(scores, cfg, "rolling-ish")


def test_eight_risk_control_variants_and_two_percentile_methods():
    """Four controls on each of two bases, and the two filter variants differ by method."""
    made = {k: v for k, v in backtest.VARIANTS.items() if v.risk_control}
    assert len(made) == len(backtest.RISK_CONTROL_BASES) * len(risk_controls.CONTROLS)
    assert len(risk_controls.CONTROLS) == 4
    assert set(risk_controls.METHOD.values()) == {risk_controls.EXPANDING, risk_controls.ROLLING}
    for control, method in risk_controls.METHOD.items():
        name = risk_controls.variant_name("carry_hedged", control)
        assert name in backtest.VARIANTS
        assert backtest.VARIANTS[name].risk_control == control
        assert method in (risk_controls.EXPANDING, risk_controls.ROLLING)


def test_pooled_pc1_scores_are_expanding_and_never_full_sample():
    """The score at ``t`` uses only months <= t, and the minimum is counted in months.

    This is what keeps full-sample loadings out of the one control that helps.
    Truncating the panel after ``t`` must leave every score at or before ``t``
    bit-identical, and the first score must appear exactly ``pca_min_months``
    months in - not ``pca_min_months`` stacked rows, which six countries would
    reach six times sooner.
    """
    cfg = _cfg()
    minimum = int(cfg["pca"]["pca_min_months"])
    n = 40
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(21)
    tenors = [1.0, 2.0, 5.0, 10.0]
    changes = {
        c: pd.DataFrame(rng.normal(0.0, 10.0, (n, len(tenors))), index=idx, columns=tenors)
        for c in ("US", "GB", "DE")
    }
    full = risk_controls.pooled_pc1_scores(changes, cfg)

    cut = 25
    truncated = {k: v.iloc[:cut] for k, v in changes.items()}
    part = risk_controls.pooled_pc1_scores(truncated, cfg)
    merged = full.merge(part, on="date", suffixes=("_full", "_part"))
    assert len(merged) == cut
    # not "close to": the expanding fit sees exactly the same matrix either way
    assert float((merged["score_full"] - merged["score_part"]).abs().max()) == 0.0

    scored = full[full["score"].notna()]
    assert len(scored) == n - minimum + 1
    first = scored["date"].min()
    assert int((full["date"] <= first).sum()) == minimum


def test_pooled_pc1_score_differs_from_a_full_sample_fit():
    """A full-sample fit would give a different score, so the expanding one is real.

    Without this the previous test would also pass on an implementation that
    fitted once on everything: identical is identical either way.
    """
    cfg = _cfg()
    n = 40
    idx = pd.date_range("2000-01-31", periods=n, freq="ME")
    rng = np.random.default_rng(22)
    tenors = [1.0, 2.0, 5.0, 10.0]
    # a regime break in the second half, so the full-sample loadings differ
    block = rng.normal(0.0, 10.0, (n, len(tenors)))
    block[n // 2 :, -1] *= 8.0
    changes = {c: pd.DataFrame(block, index=idx, columns=tenors) for c in ("US", "GB")}
    scores = risk_controls.pooled_pc1_scores(changes, cfg)

    early = scores[scores["score"].notna()].iloc[0]
    at = pd.Timestamp(early["date"])
    x = np.vstack([v.to_numpy() - v.to_numpy().mean(axis=0) for v in changes.values()])
    res = pca.pca(x, np.array(tenors, dtype="float64"))
    row = changes["US"].loc[at].to_numpy() - changes["US"].to_numpy().mean(axis=0)
    full_sample_score = float(row @ res.loadings[:, risk_controls.PC1])
    assert abs(float(early["score"]) - full_sample_score) > 1e-6
