"""Step 5.5: the combined book is the sum of the two, and it is still neutral."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import backtest
from curvecarry import weights as wt

DATE = pd.Timestamp("2010-01-31")


def _rows(spec: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    """``(country, tenor, duration, wd)`` -> a weights frame."""
    return pd.DataFrame(
        [
            {
                "date": DATE,
                "country": c,
                "tenor_years": t,
                "leg": "long" if wd > 0 else "short",
                "signal": np.nan,
                "duration": d,
                "weight": wd / d,
                "wd": wd,
            }
            for c, t, d, wd in spec
        ],
        columns=wt.WEIGHT_COLUMNS,
    )


def test_combined_weights_are_sum_and_neutral() -> None:
    carry = _rows(
        [
            ("US", 5.0, 4.7, 2.5),
            ("GB", 10.0, 8.4, 2.5),
            ("DE", 2.0, 1.9, -2.5),
            ("JP", 30.0, 22.0, -2.5),
        ]
    )
    overlay = _rows([("US", 2.0, 1.9, 2.0), ("US", 10.0, 8.5, -2.0)])
    combined = backtest.combine_books(carry, overlay)

    assert abs(combined["wd"].sum()) < 1e-12
    assert list(combined.columns) == wt.WEIGHT_COLUMNS
    # every bucket of either book is in the sum, once
    keys = set(zip(combined["country"], combined["tenor_years"], strict=True))
    assert keys == {("US", 5.0), ("GB", 10.0), ("DE", 2.0), ("JP", 30.0), ("US", 2.0), ("US", 10.0)}
    assert not combined[["country", "tenor_years"]].duplicated().any()
    # weight x duration is still wd for every row
    assert np.abs(combined["weight"] * combined["duration"] - combined["wd"]).max() < 1e-12
    assert (combined["leg"] == np.where(combined["wd"] > 0, "long", "short")).all()


def test_combined_sums_a_bucket_both_books_hold() -> None:
    carry = _rows([("US", 2.0, 1.9, 2.5), ("DE", 2.0, 1.9, -2.5)])
    overlay = _rows([("US", 2.0, 1.9, 2.0), ("US", 10.0, 8.5, -2.0)])
    combined = backtest.combine_books(carry, overlay)

    us2 = combined[(combined["country"] == "US") & (combined["tenor_years"] == 2.0)]
    assert len(us2) == 1
    assert us2["wd"].iloc[0] == pytest.approx(4.5)
    assert us2["weight"].iloc[0] == pytest.approx(4.5 / 1.9)
    assert abs(combined["wd"].sum()) < 1e-12


def test_combined_drops_a_bucket_the_two_books_cancel() -> None:
    """A carry long exactly offset by an overlay short is not a position."""
    carry = _rows([("US", 2.0, 1.9, 2.0), ("DE", 2.0, 1.9, -2.0)])
    overlay = _rows([("US", 2.0, 1.9, -2.0), ("US", 10.0, 8.5, 2.0)])
    combined = backtest.combine_books(carry, overlay)

    keys = set(zip(combined["country"], combined["tenor_years"], strict=True))
    assert ("US", 2.0) not in keys
    assert keys == {("DE", 2.0), ("US", 10.0)}
    assert abs(combined["wd"].sum()) < 1e-12


def test_overlay_pair_is_dropped_whole_when_a_leg_has_no_return() -> None:
    """Half a 2s10s pair would be a naked duration position, so neither leg is held."""
    positions = pd.concat(
        [
            _rows([("US", 2.0, 1.9, 2.0), ("US", 10.0, 8.5, -2.0)]),
            _rows([("GB", 2.0, 1.9, 2.0), ("GB", 10.0, 8.4, -2.0)]),
        ],
        ignore_index=True,
    )
    returns = pd.DataFrame(
        [
            {"date": DATE, "country": c, "tenor_years": t, "r_hedged": r}
            for c, t, r in (
                ("US", 2.0, 0.001),
                ("US", 10.0, np.nan),  # the US pair loses a leg
                ("GB", 2.0, 0.001),
                ("GB", 10.0, 0.002),
            )
        ]
    )
    cfg = {"sample": {"strategy_start": DATE, "strategy_end": DATE}}
    spec = backtest.VARIANTS["overlay_hedged"]
    held = backtest.overlay_book(positions, returns, spec, cfg)

    assert set(held["country"]) == {"GB"}
    assert len(held) == 2
    assert abs(held["wd"].sum()) < 1e-12
