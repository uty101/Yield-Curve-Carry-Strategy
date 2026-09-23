"""Session-5 amendment 4: the 5.2 invariants walked over every month of the real panel.

The synthetic tests in ``tests/test_weights.py`` show the rule is right. This
one shows the rule held on the data actually used, month by month, in both
scopes - including that the duration the weights are sized with is the
``bondmath.par_bond_risk`` duration steps 4.1 and 4.2 used, and not a second
one computed here.

No network, no fetch: it reads the built ``data/processed`` panels and skips
with a message if they are absent.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import config
from curvecarry import weights as wt

PROCESSED = Path("data/processed")
SIGNAL = PROCESSED / "signal.parquet"
RETURNS = PROCESSED / "returns.parquet"

pytestmark = pytest.mark.skipif(
    not (SIGNAL.exists() and RETURNS.exists()),
    reason=f"{SIGNAL} or {RETURNS} not built; run `curvecarry build --step signal`",
)


@pytest.fixture(scope="module")
def cfg() -> dict:
    return config.load()


@pytest.fixture(scope="module")
def signal(cfg: dict) -> pd.DataFrame:
    """The real signal panel, from ``strategy_start`` on."""
    s = pd.read_parquet(SIGNAL)
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])
    return s[(s["date"] >= start) & (s["date"] <= end)].reset_index(drop=True)


@pytest.fixture(scope="module")
def book(signal: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    return wt.duration_neutral_weights(signal, cfg)


@pytest.fixture(scope="module")
def country_book(signal: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    c = {**cfg, "weights": {**cfg["weights"], "duration_neutral_scope": "country"}}
    return wt.duration_neutral_weights(signal, c)


def test_panel_is_the_whole_strategy_window(
    signal: pd.DataFrame, book: tuple[pd.DataFrame, pd.DataFrame], cfg: dict
) -> None:
    """The walk below is not vacuous: it covers every month of the sample."""
    held, empty = book
    months = set(signal["date"].unique())
    covered = set(held["date"].unique()) | set(pd.to_datetime(empty["date"]))
    assert covered == months
    assert len(months) > 300, len(months)


def test_book_is_duration_neutral_every_month(book: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    held, _ = book
    worst = held.groupby("date")["wd"].sum().abs().max()
    assert worst < 1e-10, worst


def test_country_scope_is_neutral_within_every_country_every_month(
    country_book: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    held, _ = country_book
    worst = held.groupby(["date", "country"])["wd"].sum().abs().max()
    assert worst < 1e-10, worst


def test_no_bucket_is_in_both_legs_in_any_month(book: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    held, _ = book
    key = held[["date", "country", "tenor_years"]]
    assert not key.duplicated().any()
    for date, g in held.groupby("date"):
        long = set(
            zip(g[g["leg"] == "long"]["country"], g[g["leg"] == "long"]["tenor_years"], strict=True)
        )
        short = set(
            zip(
                g[g["leg"] == "short"]["country"],
                g[g["leg"] == "short"]["tenor_years"],
                strict=True,
            )
        )
        assert long & short == set(), date


def test_long_leg_is_the_budget_and_the_legs_are_equal(
    book: tuple[pd.DataFrame, pd.DataFrame], cfg: dict
) -> None:
    held, _ = book
    budget = float(cfg["weights"]["long_duration_budget"])
    by_date = held.groupby(["date", "leg"])["wd"].sum().unstack()
    assert (by_date["long"] - budget).abs().max() < 1e-10
    assert (by_date["short"] + budget).abs().max() < 1e-10
    sizes = held.groupby(["date", "leg"]).size().unstack()
    assert (sizes["long"] == sizes["short"]).all()


def test_weight_times_duration_is_wd_every_month(book: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    held, _ = book
    assert np.abs(held["weight"] * held["duration"] - held["wd"]).max() < 1e-12


def test_duration_is_the_same_function_as_4_1_and_4_2(
    book: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """The sizing duration is ``returns.parquet``'s, i.e. ``bondmath.par_bond_risk``."""
    held, _ = book
    r = pd.read_parquet(RETURNS)[["date", "country", "tenor_years", "duration"]]
    merged = held.merge(r, on=["date", "country", "tenor_years"], how="left", suffixes=("", "_ret"))
    assert merged["duration_ret"].notna().all(), "a held bucket has no row in returns.parquet"
    assert np.abs(merged["duration"] - merged["duration_ret"]).max() == 0.0


def test_flat_months_hold_nothing_and_are_logged(
    book: tuple[pd.DataFrame, pd.DataFrame], signal: pd.DataFrame, cfg: dict
) -> None:
    held, empty = book
    minimum = int(cfg["weights"]["min_eligible_buckets"])
    eligible = signal.groupby("date")["eligible"].sum()
    thin = set(eligible[eligible < minimum].index)
    logged = set(pd.to_datetime(empty["date"]))
    assert thin == logged
    assert thin & set(held["date"].unique()) == set()
