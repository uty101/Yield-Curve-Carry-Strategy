"""Step 4.3: hedged and unhedged excess returns, on synthetic rows.

Nothing here reads a file. The point of the step is that ``r_hedged`` is
``r_excess_local`` and contains no exchange rate at all
(``decisions/basis.md``), so the first test changes the FX series and asserts
that ``r_hedged`` does not move.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from curvecarry import returns

BASE = "US"
DATES = ["2020-06-30", "2020-07-31", "2020-08-31"]


def _cfg() -> dict:
    return {
        "base_currency": "USD",
        "countries": ["US", "GB", "DE", "JP"],
        "currency": {"US": "USD", "GB": "GBP", "DE": "EUR", "JP": "JPY"},
        "hedge": {
            "funding_rate": "policy",
            "funding_rate_robustness": "interbank_3m",
            "eur_splice": "1999-01-31",
            "eur_legacy": {"DE": "DE", "FR": "FR"},
        },
    }


def _returns(countries=("US", "GB"), r_local=0.01, closed=False) -> pd.DataFrame:
    rows = []
    for country in countries:
        for date in DATES[:2]:
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "country": country,
                    "tenor_years": 10.0,
                    "r_local": r_local,
                    "r_short_local": 0.012,
                    "r_excess_local": r_local - 0.012 / 12.0,
                    "r_short_local_interbank_3m": 0.014,
                    "r_excess_local_interbank_3m": r_local - 0.014 / 12.0,
                    "closed": closed,
                }
            )
    return pd.DataFrame(rows)


def _funding(rate_us=0.048, ib_us=0.050) -> pd.DataFrame:
    rows = []
    for date in DATES:
        for country, pol, ib in (("US", rate_us, ib_us), ("GB", 0.012, 0.014), ("JP", 0.001, None)):
            rows.append((pd.Timestamp(date), country, pol, "policy", "bis"))
            if ib is not None:
                rows.append((pd.Timestamp(date), country, ib, "interbank_3m", "fred"))
    return pd.DataFrame(rows, columns=["date", "country", "rate", "kind", "source"])


def _fx(gbp=(1.20, 1.25, 1.25)) -> pd.DataFrame:
    rows = []
    for date, s in zip(DATES, gbp, strict=True):
        rows.append((pd.Timestamp(date), "GBP", s))
        rows.append((pd.Timestamp(date), "USD", 1.0))
        rows.append((pd.Timestamp(date), "JPY", 0.0093))
    return pd.DataFrame(rows, columns=["date", "currency", "spot"])


def test_hedged_is_local_excess_return() -> None:
    """r_hedged == r_local - r_short_local/12, and it does not move when FX moves."""
    cfg = _cfg()
    a, _ = returns.add_fx(_returns(), _funding(), _fx(), cfg)
    b, _ = returns.add_fx(_returns(), _funding(), _fx(gbp=(1.20, 0.90, 0.90)), cfg)
    for frame in (a, b):
        assert (
            frame["r_hedged"] - (frame["r_local"] - frame["r_short_local"] / 12.0)
        ).abs().max() < 1e-15
    assert (a["r_hedged"] - b["r_hedged"]).abs().max() == 0.0
    assert (a["r_unhedged"] - b["r_unhedged"]).abs().max() > 0.0  # but the unhedged one does


def test_cip_identity() -> None:
    """r_local + hedge_carry - r_short_base/12 == r_hedged on 1,000 random rows."""
    rng = np.random.default_rng(0)
    n = 1000
    frame = pd.DataFrame(
        {
            "date": pd.Timestamp(DATES[0]),
            "country": "GB",
            "tenor_years": 10.0,
            "r_local": rng.uniform(-0.05, 0.05, n),
            "r_short_local": rng.uniform(0.0, 0.15, n),
            "r_short_local_interbank_3m": rng.uniform(0.0, 0.15, n),
            "closed": False,
        }
    )
    frame["r_excess_local"] = frame["r_local"] - frame["r_short_local"] / 12.0
    frame["r_excess_local_interbank_3m"] = (
        frame["r_local"] - frame["r_short_local_interbank_3m"] / 12.0
    )
    out, _ = returns.add_fx(frame, _funding(), _fx(), _cfg())
    lhs = out["r_local"] + out["hedge_carry"] - out["r_short_base"] / 12.0
    assert (lhs - out["r_hedged"]).abs().max() < 1e-14


def test_base_country_columns_equal() -> None:
    """For the base currency the three returns coincide and both FX terms are zero."""
    out, _ = returns.add_fx(_returns(), _funding(), _fx(), _cfg())
    us = out[out["country"] == BASE]
    assert (us["r_hedged"] == us["r_excess_local"]).all()
    assert (us["r_unhedged"] == us["r_excess_local"]).all()
    assert (us["fx_return"] == 0.0).all() and (us["hedge_carry"] == 0.0).all()
    assert (us["hedge_carry_interbank_3m"] == 0.0).all()


def test_hedge_carry_sign_and_size() -> None:
    """Base 5%, foreign 1% -> the hedge earns +0.04/12 a month."""
    frame = _returns(countries=("GB",))
    frame["r_short_local"] = 0.01
    frame["r_excess_local"] = frame["r_local"] - 0.01 / 12.0
    out, _ = returns.add_fx(frame, _funding(rate_us=0.05), _fx(), _cfg())
    assert out["hedge_carry"].iloc[0] == pytest.approx(0.04 / 12.0, abs=1e-15)


def test_unhedged_uses_log_change_and_base_funding() -> None:
    """S 1.00 -> 1.02 with r_local 0 and r_short_base 4.8% gives ln(1.02) - 0.004."""
    frame = _returns(countries=("GB",), r_local=0.0)
    out, _ = returns.add_fx(frame, _funding(), _fx(gbp=(1.00, 1.02, 1.02)), _cfg())
    june = out[out["date"] == DATES[0]].iloc[0]
    assert june["fx_return"] == pytest.approx(np.log(1.02), abs=1e-15)
    assert june["r_unhedged"] == pytest.approx(np.log(1.02) - 0.048 / 12.0, abs=1e-15)
    # a foreign appreciation raises it
    up, _ = returns.add_fx(frame, _funding(), _fx(gbp=(1.00, 1.05, 1.05)), _cfg())
    assert up[up["date"] == DATES[0]].iloc[0]["r_unhedged"] > june["r_unhedged"]


def test_rates_dated_t_not_t_plus_1() -> None:
    """r_short_base is the base rate at t; changing t+1 alone changes nothing."""
    funding = _funding()
    out_a, _ = returns.add_fx(_returns(), funding, _fx(), _cfg())
    moved = funding.copy()
    july = (moved["date"] == pd.Timestamp(DATES[1])) & (moved["country"] == BASE)
    moved.loc[july & (moved["kind"] == "policy"), "rate"] = 0.20
    out_b, _ = returns.add_fx(_returns(), moved, _fx(), _cfg())
    june = out_a["date"] == pd.Timestamp(DATES[0])
    assert (out_a.loc[june, "r_short_base"] == out_b.loc[june, "r_short_base"]).all()
    assert out_a.loc[june, "r_short_base"].iloc[0] == 0.048
    assert out_b[out_b["date"] == pd.Timestamp(DATES[1])]["r_short_base"].iloc[0] == 0.20


def test_robustness_columns_present_and_nan_where_missing() -> None:
    """The interbank columns exist and are NaN where that series does not reach."""
    frame = _returns(countries=("US", "GB"))
    jp = _returns(countries=("JP",))
    jp["r_short_local_interbank_3m"] = np.nan
    jp["r_excess_local_interbank_3m"] = np.nan
    out, _ = returns.add_fx(pd.concat([frame, jp], ignore_index=True), _funding(), _fx(), _cfg())
    for column in returns.FX_COLUMNS:
        assert column in out.columns
    assert out[out["country"] == "JP"]["r_hedged_interbank_3m"].isna().all()
    assert out[out["country"] == "GB"]["r_hedged_interbank_3m"].notna().all()


def test_no_fx_means_unhedged_nan_and_logged() -> None:
    """A month with no spot gives r_unhedged NaN, a no_fx log row, and a live r_hedged."""
    frame = _returns(countries=("DE",))
    fx = _fx()  # has GBP, USD and JPY - no EUR at all
    out, no_fx = returns.add_fx(frame, _funding(), fx, _cfg())
    assert out["r_unhedged"].isna().all()
    assert out["r_hedged"].notna().all()  # the hedge needs no FX series
    assert len(no_fx) == len(frame)
    assert set(no_fx["reason"]) == {returns.NO_FX}
    assert list(no_fx.columns) == returns.CLOSED_COLUMNS

    cov = returns.coverage_rows(out, _funding(), _cfg())
    assert list(cov.columns) == returns.COVERAGE_COLUMNS
    assert (cov["reason"] == returns.NO_FX).all()
    assert cov["has_r_hedged"].all() and not cov["has_r_unhedged"].any()
    # DE is spliced: the legacy area before eur_splice, XM from it
    assert returns.funding_area("DE", pd.Timestamp("1998-12-31"), _cfg()) == "DE"
    assert returns.funding_area("DE", pd.Timestamp("1999-01-31"), _cfg()) == "XM"
    assert returns.funding_area("GB", pd.Timestamp("1998-12-31"), _cfg()) == "GB"
