"""Step 6.1: the four pieces add up, and the Taylor form is only reported beside them."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest, decomposition

DATES = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])


def _returns(rows: list[dict]) -> pd.DataFrame:
    """A 4.2/4.3 returns frame with every column the decomposition reads."""
    out = pd.DataFrame(rows)
    out["r_local"] = out["r_local_full"]
    out["r_excess_local"] = out["r_local"] - out["r_short_local"] / 12.0
    out["r_hedged"] = out["r_excess_local"]
    out["r_unhedged"] = out["r_local"] + out["fx_return"] - out["r_short_base"] / 12.0
    out["gap_bp"] = (out["r_local_full"] - out["r_local_approx"]) * 1e4
    return out


def _synthetic(seed: int = 0, n_buckets: int = 4) -> tuple:
    """``(positions, returns, carry, monthly_hedged, monthly_unhedged)`` on a small book."""
    rng = np.random.default_rng(seed)
    countries = ["US", "GB", "DE", "JP"][:n_buckets]
    pos_rows, ret_rows, carry_rows = [], [], []
    for date in DATES:
        for i, country in enumerate(countries):
            tenor = float(2 * (i + 1))
            weight = float(rng.normal(0.0, 1.0))
            coupon = 0.01 + 0.005 * i
            r_short = 0.004 + 0.001 * i
            rolldown = 0.0004 - 0.0001 * i
            d = 0.9 * tenor
            cx = 0.8 * tenor * tenor
            dy = float(rng.normal(0.0, 0.002))
            approx = coupon / 12.0 - d * dy + 0.5 * cx * dy * dy
            full = approx + float(rng.normal(0.0, 5e-5))  # Taylor truncation
            fx = float(rng.normal(0.0, 0.01))
            r_short_base = 0.003
            pos_rows.append(
                {
                    "date": date,
                    "country": country,
                    "tenor_years": tenor,
                    "leg": "long" if weight > 0 else "short",
                    "signal": 0.0,
                    "duration": d,
                    "weight": weight,
                    "wd": weight * d,
                    "closed": False,
                }
            )
            ret_rows.append(
                {
                    "date": date,
                    "country": country,
                    "tenor_years": tenor,
                    "coupon": coupon,
                    "duration": d,
                    "convexity": cx,
                    "dy": dy,
                    "r_local_full": full,
                    "r_local_approx": approx,
                    "r_short_local": r_short,
                    "r_short_local_interbank_3m": r_short + 0.001,
                    "r_short_base": r_short_base,
                    "fx_return": 0.0 if country == "US" else fx,
                }
            )
            carry_rows.append(
                {
                    "date": date,
                    "country": country,
                    "tenor_years": tenor,
                    "rolldown": rolldown,
                }
            )
    positions = pd.DataFrame(pos_rows)
    returns = _returns(ret_rows)
    carry = pd.DataFrame(carry_rows)
    key = ["date", "country", "tenor_years"]
    out = []
    for column in ("r_hedged", "r_unhedged"):
        held = positions.merge(returns[[*key, column]], on=key, how="left")
        held["r"] = held[column]
        by_date = held.groupby("date", as_index=False).apply(
            lambda g: pd.Series({"r_gross": float((g["weight"] * g["r"]).sum())}),
            include_groups=False,
        )
        by_date["cost"] = 0.0002
        by_date["r_net"] = by_date["r_gross"] - by_date["cost"]
        out.append((held.drop(columns=[column]), by_date))
    return positions, returns, carry, out[0], out[1]


def _on_column(held: pd.DataFrame, monthly: pd.DataFrame, returns, column: str) -> tuple:
    """The same book earning the robustness funding column instead of the policy one."""
    key = ["date", "country", "tenor_years"]
    suffix = decomposition.funding_suffix(column)
    merged = held[key].merge(
        returns[[*key, "r_local", f"r_short_local{suffix}"]], on=key, how="left"
    )
    held = held.copy()
    held["r"] = (merged["r_local"] - merged[f"r_short_local{suffix}"] / 12.0).to_numpy()
    gross = held.assign(c=held["weight"] * held["r"]).groupby("date")["c"].sum()
    monthly = monthly.copy()
    monthly["r_gross"] = monthly["date"].map(gross)
    monthly["r_net"] = monthly["r_gross"] - monthly["cost"]
    return held, monthly


def _cfg() -> dict:
    return {"sample": {"strategy_start": "2020-01-31", "sample_full_start": "2020-02-29"}}


@pytest.mark.parametrize("column", ["r_hedged", "r_unhedged", "r_hedged_interbank_3m"])
def test_four_pieces_sum_to_reported_return(column):
    """``|identity_gap| < 1e-10`` every month, on every kind of variant."""
    _positions, returns, carry, hedged, unhedged = _synthetic()
    held, monthly = unhedged if column == "r_unhedged" else hedged
    if column == "r_hedged_interbank_3m":
        held, monthly = _on_column(held, monthly, returns, column)
    pieces = decomposition.position_pieces(held, returns, carry, column)
    table = decomposition.monthly_decomposition(pieces, monthly)
    assert table["identity_gap"].abs().max() < decomposition.IDENTITY_TOLERANCE
    assert len(table) == len(DATES)


def test_carry_earned_hand_computed():
    """The hedged and unhedged brackets of PLAN.md 6.1, on one bucket, by hand."""
    date = DATES[0]
    key = {"date": date, "country": "US", "tenor_years": 5.0}
    positions = pd.DataFrame(
        [
            {
                **key,
                "leg": "long",
                "signal": 0.0,
                "duration": 4.0,
                "weight": 2.0,
                "wd": 8.0,
                "closed": False,
                "r": 0.0,
            }
        ]
    )
    returns = _returns(
        [
            {
                **key,
                "coupon": 0.03,
                "duration": 4.0,
                "convexity": 20.0,
                "dy": 0.0,
                "r_local_full": 0.0,
                "r_local_approx": 0.03 / 12.0,
                "r_short_local": 0.012,
                "r_short_local_interbank_3m": 0.012,
                "r_short_base": 0.006,
                "fx_return": 0.0,
            }
        ]
    )
    carry = pd.DataFrame([{**key, "rolldown": 0.0005}])

    hedged = decomposition.position_pieces(positions, returns, carry, "r_hedged")
    assert hedged["carry_earned"].iloc[0] == pytest.approx(2 * (0.0025 - 0.001 + 0.0005))
    assert hedged["funding"].iloc[0] == 0.0
    assert hedged["fx"].iloc[0] == 0.0

    unhedged = decomposition.position_pieces(positions, returns, carry, "r_unhedged")
    assert unhedged["carry_earned"].iloc[0] == pytest.approx(2 * (0.0025 + 0.0005))
    assert unhedged["funding"].iloc[0] == pytest.approx(-2 * 0.006 / 12.0)


def test_taylor_residual_equals_weighted_gap():
    """``taylor_residual`` is the 4.2 ``gap_bp`` aggregated by the weights, to 1e-12."""
    _positions, returns, carry, (held, _monthly), _un = _synthetic(seed=3)
    pieces = decomposition.position_pieces(held, returns, carry, "r_hedged")
    key = ["date", "country", "tenor_years"]
    joined = pieces.merge(returns[[*key, "gap_bp"]], on=key, how="left")
    expected = joined["weight"] * joined["gap_bp"] * 1e-4
    assert (joined["taylor_residual"] - expected).abs().max() < 1e-12


def test_shares_sum_to_one():
    """The five piece shares add to the ``r_net`` share, which is 1, in every window."""
    _positions, returns, carry, (held, monthly), _un = _synthetic(seed=7)
    pieces = decomposition.position_pieces(held, returns, carry, "r_hedged")
    table = decomposition.monthly_decomposition(pieces, monthly)
    shares = decomposition.share_rows(table, "carry_hedged", _cfg())
    assert set(shares["piece"]) == {*decomposition.PIECES, "r_net"}
    for window, g in shares.groupby("window"):
        got = g[g["piece"] != "r_net"]["share"].sum()
        assert got == pytest.approx(1.0), window
        total = float(g[g["piece"] == "r_net"]["cumulative"].iloc[0])
        assert g[g["piece"] != "r_net"]["cumulative"].sum() == pytest.approx(total)


def test_closed_bucket_contributes_nothing():
    """A bucket closed at its last price explains nothing, so every piece is zero."""
    _positions, returns, carry, (held, monthly), _un = _synthetic(seed=11)
    held = held.copy()
    held.loc[held.index[0], "closed"] = True
    held.loc[held.index[0], "r"] = 0.0
    pieces = decomposition.position_pieces(held, returns, carry, "r_hedged")
    first = pieces.iloc[0]
    assert all(first[c] == 0.0 for c in decomposition.PIECE_VALUE_COLUMNS)
    monthly = monthly.copy()
    gross = held.assign(c=held["weight"] * held["r"]).groupby("date")["c"].sum()
    monthly["r_gross"] = monthly["date"].map(gross)
    monthly["r_net"] = monthly["r_gross"] - monthly["cost"]
    table = decomposition.monthly_decomposition(pieces, monthly)
    assert table["identity_gap"].abs().max() < decomposition.IDENTITY_TOLERANCE


def test_identity_break_raises():
    """A decomposition that does not add up stops; it is never written."""
    _positions, returns, carry, (held, monthly), _un = _synthetic(seed=13)
    pieces = decomposition.position_pieces(held, returns, carry, "r_hedged")
    broken = monthly.copy()
    broken.loc[broken.index[1], "r_net"] += 1e-6
    with pytest.raises(decomposition.IdentityBroken):
        decomposition.monthly_decomposition(pieces, broken)


def test_every_variant_has_a_funding_column():
    """Each logged variant's return column maps to a funding column that exists in 4.2."""
    from curvecarry import returns as returns_mod

    for spec in backtest.VARIANTS.values():
        suffix = decomposition.funding_suffix(spec.returns_column)
        assert f"r_short_local{suffix}" in returns_mod.RETURN_COLUMNS
