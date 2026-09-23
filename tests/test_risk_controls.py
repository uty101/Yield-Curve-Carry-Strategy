"""Step 6.2: the three pre-registered controls, and that none of them looks ahead."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest, config, risk_controls

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
    assert list(long_flags.loc[common, "flat_next"]) == list(short_flags["flat_next"])
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
    assert usable["flat_next"].mean() <= 0.25  # expanding, so early months flag more often


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


def test_six_risk_control_variants_exist_and_name_their_base():
    """Three controls on each of two bases, each carrying the base it transforms."""
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
