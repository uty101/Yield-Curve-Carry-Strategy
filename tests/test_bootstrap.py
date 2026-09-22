"""Step 1.9: bootstrap, sample window and the GSW check on synthetic curves and fixtures."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry import bootstrap, config
from curvecarry.curves import Curve
from curvecarry.loaders import base, gsw

STANDARD = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
D = pd.Timestamp("2020-01-31")


def _price(zc: Curve, tenor: float, coupon: float, freq: int) -> float:
    """Dirty price per 100 of a par bond off a zero curve (local helper; bondmath is 2.1)."""
    ts = np.arange(1, int(round(tenor * freq)) + 1) / freq
    dfs = (1.0 + zc.at(ts)) ** (-ts)
    return 100.0 * ((coupon / freq) * dfs.sum() + dfs[-1])


def _par(tenors, yields) -> Curve:
    return Curve(np.asarray(tenors, float), np.asarray(yields, float), "par", "XX", D)


def test_flat_par_gives_flat_zero() -> None:
    for freq in (1, 2):
        par = _par(STANDARD, [0.04] * 8)
        zc = bootstrap.bootstrap_par_to_zero(par, freq, STANDARD)
        want = (1 + 0.04 / freq) ** freq - 1
        # the whole coupon grid from the shortest observed tenor (#10 A): 30 or 59 points
        grid = (np.arange(1, 30 * freq + 1) / freq).tolist()
        assert zc.curve_type == "zero" and zc.tenors.tolist() == [t for t in grid if t >= 1]
        assert set(STANDARD) <= set(zc.tenors)
        assert np.abs(zc.yields - want).max() < 1e-12
        if freq == 1:
            assert np.abs(zc.yields - 0.04).max() < 1e-12
        _, _, z = bootstrap.bootstrap_grid(par, freq)
        assert np.abs(z - want).max() < 1e-12  # every coupon date, not only the output tenors


def test_reprice_par_bonds_at_100() -> None:
    """The bootstrap is exact: each observed par bond prices at 100 off the returned zero
    curve, which carries every coupon-grid point (#10 A, answer a)."""
    t = np.array(STANDARD)
    y = 0.02 + 0.03 * (t - 1) / 29  # 2% at 1y to 5% at 30y
    for tenors, yields in ((t, y), (np.r_[0.25, 0.5, t], np.r_[0.018, 0.019, y])):
        for freq in (1, 2):
            par = _par(tenors, yields)
            zc = bootstrap.bootstrap_par_to_zero(par, freq, STANDARD)
            for tenor, c in zip(tenors, yields, strict=True):
                if tenor * freq < 1 - 1e-9:  # a tenor below the first coupon date is not a bond
                    continue
                assert abs(_price(zc, tenor, c, freq) - 100.0) < 1e-9, (freq, tenor)
            # and the returned curve is the grid itself (plus any bill tenor), not a subset
            grid, _, z = bootstrap.bootstrap_grid(par, freq)
            on_grid = zc.tenors[zc.tenors * freq >= 1 - 1e-9]
            assert on_grid.tolist() == grid[grid >= tenors.min() - 1e-9].tolist()
            for tt, zz in zip(zc.tenors, zc.yields, strict=True):
                if tt * freq >= 1 - 1e-9:
                    assert zz == pytest.approx(float(z[np.isclose(grid, tt)][0]), abs=1e-15)


def test_zero_source_passes_through(tmp_path: Path) -> None:
    cfg = config.load()
    rows = [
        (D, "GB", t, 0.01 + 0.001 * t, "zero", "boe", False, t in STANDARD)
        for t in [0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
    ]
    panel = pd.DataFrame(rows, columns=[*base.CURVE_COLUMNS, "interpolated", "standard"])
    out = bootstrap.zero_panel(panel, cfg)
    assert not out["bootstrapped"].any()
    pd.testing.assert_frame_equal(
        out[[*base.CURVE_COLUMNS, "interpolated", "standard"]].reset_index(drop=True),
        panel.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True),
        check_dtype=False,
    )


def test_par_assertion() -> None:
    zc = Curve(np.array(STANDARD), np.full(8, 0.03), "zero", "XX", D)
    with pytest.raises(AssertionError):
        bootstrap.bootstrap_par_to_zero(zc, 2)
    with pytest.raises(AssertionError):
        bootstrap.bootstrap_grid(zc, 2)


def test_no_tenor_beyond_longest_par() -> None:
    par = _par([1, 2, 3, 5, 7, 10], [0.02, 0.022, 0.024, 0.027, 0.029, 0.03])
    zc = bootstrap.bootstrap_par_to_zero(par, 2, STANDARD)
    assert zc.tenors.max() == 10.0 and not {20.0, 30.0} & set(zc.tenors)
    assert math.isnan(zc.at(20.0))
    # and none below the shortest observed par tenor (JP 1978-80: shortest is 4y)
    par = _par([4, 5, 7, 10], [0.06, 0.062, 0.065, 0.07])
    zc = bootstrap.bootstrap_par_to_zero(par, 2, STANDARD)
    assert zc.tenors.tolist() == (np.arange(8, 21) / 2).tolist()  # 4.0, 4.5, ..., 10.0
    # below the shortest observed tenor the flat par gives the same zero as Curve.at does
    grid, _, z = bootstrap.bootstrap_grid(par, 2)
    assert np.abs(z[grid < 4] - float(zc.at(0.5))).max() < 1e-12


def test_no_bootstrap_across_wide_node_gap() -> None:
    """Session 2 fix 2: the bootstrap stops before two consecutive observed par nodes more
    than config.bootstrap_max_node_gap_years (10) apart; nothing beyond is interpolated."""
    max_gap = float(config.load()["bootstrap_max_node_gap_years"])
    assert max_gap == 10.0
    y = [0.02, 0.022, 0.024, 0.027, 0.029, 0.03, 0.035, 0.04]
    with_gap = _par([1, 2, 3, 5, 7, 10, 30], y[:6] + y[7:])  # 10 -> 30 is a 20-year gap
    zc = bootstrap.bootstrap_par_to_zero(with_gap, 2, max_node_gap=max_gap)
    assert zc.tenors.max() == 10.0 and math.isnan(zc.at(20.0)) and math.isnan(zc.at(30.0))
    assert bootstrap.node_gap_cutoff(with_gap, max_gap) == 10.0
    full = _par([1, 2, 3, 5, 7, 10, 20, 30], y)
    zc = bootstrap.bootstrap_par_to_zero(full, 2, max_node_gap=max_gap)
    assert zc.tenors.max() == 30.0 and {20.0, 30.0} <= set(zc.tenors)
    assert bootstrap.node_gap_cutoff(full, max_gap) == 30.0
    # the zeros up to 10y are the same with and without the cut: the bootstrap is sequential
    a = bootstrap.bootstrap_par_to_zero(with_gap, 2)  # no rule: runs to 30 across the gap
    assert (
        np.abs(a.at(zc.tenors[zc.tenors <= 10]) - zc.at(zc.tenors[zc.tenors <= 10])).max() < 1e-15
    )
    # and a gap of exactly 10 years (20 -> 30) is allowed
    assert (
        bootstrap.node_gap_cutoff(_par([1, 10, 20, 30], [0.02, 0.03, 0.035, 0.04]), max_gap) == 30.0
    )


def test_ill_conditioned_long_end_is_dropped() -> None:
    """Session 2 fix 3: a 30 bp kink in the 20y par yield of a 15% curve sends the 1-year
    forwards beyond config.bootstrap_forward_tolerance_bp (300) from par; the zeros from the
    first breach on are dropped. The same curve without the kink keeps every tenor."""
    tol = float(config.load()["bootstrap_forward_tolerance_bp"])
    assert tol == 300.0
    flat = _par(STANDARD, [0.15] * 8)
    zc, diag = bootstrap.bootstrap_month(flat, 2, forward_tolerance_bp=tol)
    assert zc.tenors.max() == 30.0 and diag["first_tenor_dropped"] is None and not diag["dropped"]
    assert abs(diag["worst_diff_bp"]) < 100  # 56 bp: par 15% vs the annual-compounded forward
    kink = _par(STANDARD, [0.15] * 6 + [0.153, 0.15])
    zc, diag = bootstrap.bootstrap_month(kink, 2, forward_tolerance_bp=tol)
    first = diag["first_tenor_dropped"]
    assert diag["dropped"] and 10.0 < first <= 20.0
    assert zc.tenors.max() < first and not {20.0, 30.0} & set(zc.tenors)
    assert abs(diag["worst_diff_bp"]) > tol and diag["worst_tenor"] >= first
    assert diag["par_at_worst"] == pytest.approx(float(kink.at(diag["worst_tenor"])))
    # the zeros below the first breach are the bootstrap's own, untouched
    full = bootstrap.bootstrap_par_to_zero(kink, 2)
    assert np.abs(zc.yields - full.at(zc.tenors)).max() < 1e-15
    # the 200 bp report threshold is at or before the 300 bp cut, and never applied
    assert diag["first_tenor_dropped_200bp"] <= first
    assert bootstrap.bootstrap_par_to_zero(kink, 2, forward_tolerance_bp=tol).tenors.max() < first
    # the forward arithmetic: on a flat zero curve every 1-year forward equals the zero
    grid, df, z = bootstrap.bootstrap_grid(flat, 2)
    fwd = bootstrap.one_year_forwards(grid, df, 2)
    assert np.isnan(fwd[0]) and np.abs(fwd[1:] - z[1:]).max() < 1e-12


def test_short_stub_is_flat_at_shortest_par() -> None:
    # tenors from 1y, freq 2: the 0.5y discount factor is the one implied by the 1y par yield
    par = _par([1, 2, 5, 10], [0.03, 0.032, 0.035, 0.04])
    grid, df, _ = bootstrap.bootstrap_grid(par, 2)
    assert grid[0] == 0.5 and df[0] == pytest.approx(1 / (1 + 0.03 / 2), abs=1e-15)
    # with 0.5 observed at a different yield, the 0.5y discount factor follows the 0.5 par yield
    par = _par([0.5, 1, 2, 5, 10], [0.02, 0.03, 0.032, 0.035, 0.04])
    grid, df, _ = bootstrap.bootstrap_grid(par, 2)
    assert df[0] == pytest.approx(1 / (1 + 0.02 / 2), abs=1e-15)
    # an observed 0.25 tenor (off the semi-annual grid) is in the returned zero curve (#10 B)
    par = _par([0.25, 0.5, 1, 2, 5, 10], [0.018, 0.02, 0.03, 0.032, 0.035, 0.04])
    zc = bootstrap.bootstrap_par_to_zero(par, 2, STANDARD)
    assert 0.25 in set(zc.tenors) and 0.5 in set(zc.tenors)


def test_bill_zero_is_money_market_identity() -> None:
    """The US 0.25 point (a bill quoted bond-equivalent, P = 1/(1 + c·t)) gets
    z = (1 + c·0.25)^(1/0.25) − 1 (#10 B, answer a); nothing else moves."""
    c = 0.0512
    with_bill = _par([0.25, 0.5, 1, 2, 5, 10], [c, 0.05, 0.049, 0.048, 0.047, 0.046])
    without = _par([0.5, 1, 2, 5, 10], [0.05, 0.049, 0.048, 0.047, 0.046])
    a = bootstrap.bootstrap_par_to_zero(with_bill, 2)
    b = bootstrap.bootstrap_par_to_zero(without, 2)
    assert a.tenors[0] == 0.25
    assert a.yields[0] == pytest.approx((1 + c * 0.25) ** 4 - 1, abs=1e-15)
    assert a.yields[0] == pytest.approx(bootstrap.money_market_zero(c, 0.25), abs=1e-15)
    assert a.yields[0] != pytest.approx((1 + c / 2) ** 2 - 1, abs=1e-6)  # not the coupon stub
    assert a.tenors[1:].tolist() == b.tenors.tolist()
    assert np.abs(a.yields[1:] - b.yields).max() < 1e-15
    # and the bill's own price, discounted at its zero, is 1/(1 + c·t)
    assert (1 + a.yields[0]) ** -0.25 == pytest.approx(1 / (1 + c * 0.25), abs=1e-15)


def _zero_rows(country: str, months, tenors):
    return [
        (pd.Timestamp(m), country, float(t), 0.03, "zero", "s", False, True, True)
        for m in months
        for t in tenors
    ]


def test_sample_window_rule() -> None:
    cfg = config.load()
    to10 = [1, 2, 3, 5, 7, 10]
    months = pd.date_range("1996-01-31", "1998-12-31", freq="ME")
    rows = []
    rows += _zero_rows("US", months, to10 + [20, 30])
    rows += _zero_rows("GB", months, to10)
    rows += _zero_rows("JP", months, to10)
    rows += _zero_rows("CA", months, to10)
    rows += _zero_rows("DE", months[months >= "1997-08-31"], to10)  # fifth country from 1997-08
    rows += _zero_rows(
        "FR", months[months >= "1998-03-31"], [1, 2, 3, 5, 7]
    )  # no 10y: never counts
    rows += _zero_rows("FR", months[months >= "1998-06-30"], [10])  # complete from 1998-06
    zero = pd.DataFrame(rows, columns=bootstrap.ZERO_COLUMNS)
    start, full, table = bootstrap.sample_window(zero, cfg)
    assert start == pd.Timestamp("1997-08-31") and full == pd.Timestamp("1998-06-30")
    t = table.set_index("country")["first_month_all_tenors_to_10y"]
    assert t["DE"] == pd.Timestamp("1997-08-31") and t["FR"] == pd.Timestamp("1998-06-30")
    assert t["US"] == pd.Timestamp("1996-01-31")


def test_write_config_dates(tmp_path: Path) -> None:
    src = Path("config.toml").read_text(encoding="utf-8")
    p = tmp_path / "config.toml"
    p.write_text(src, encoding="utf-8")
    bootstrap.write_config_dates(pd.Timestamp("1999-01-31"), pd.Timestamp("2005-02-28"), p)
    cfg = config.load(p)
    assert cfg["sample"]["strategy_start"] == "1999-01-31"
    assert cfg["sample"]["sample_full_start"] == "2005-02-28"
    assert cfg["sample"]["strategy_end"] == pd.Timestamp(config.load()["sample"]["strategy_end"])


def test_gsw_units_and_compounding() -> None:
    daily = gsw.parse([Path("tests/fixtures/gsw/feds200628.csv")])
    assert daily["yield"].dropna().between(-0.05, 0.5).all() and daily["yield"].max() > 0.001
    raw = pd.read_csv("tests/fixtures/gsw/feds200628.csv", skiprows=9, na_values=["NA"]).iloc[0]
    got = daily[(daily["obs_date"] == pd.Timestamp(raw["Date"])) & (daily["tenor_years"] == 1.0)]
    assert got["yield"].item() == pytest.approx(math.exp(raw["SVENY01"] / 100.0) - 1, abs=1e-14)
    assert set(daily["tenor_years"]) == set(float(k) for k in range(1, 31))
    # 1961: the fit reaches 7 years only; longer tenors are NA, never zero
    first = daily[daily["obs_date"] == pd.Timestamp(raw["Date"])]
    assert first[first["tenor_years"] > 7]["yield"].isna().all() and not (daily["yield"] == 0).any()


def test_par_zero_gap_and_gsw_check_shapes() -> None:
    cfg = config.load()
    t = np.array(STANDARD)
    # upward sloping and flattening (2% -> 4%): a par curve rising 10 bp/yr for ever implies
    # 1-year forwards 1,200 bp above par at 30y, which the fix-3 rule would (rightly) drop
    y = 0.02 + 0.02 * (1 - np.exp(-t / 5))
    panel_rows = [
        (D, "US", tt, yy, "par", "fred", False, True) for tt, yy in zip(t, y, strict=True)
    ]
    panel = pd.DataFrame(panel_rows, columns=[*base.CURVE_COLUMNS, "interpolated", "standard"])
    zero, dropped = bootstrap.zero_panel_and_dropped(panel, cfg)
    assert list(dropped.columns) == bootstrap.DROPPED_COLUMNS and dropped.empty
    assert len(zero) == 59 and zero["standard"].sum() == 8  # the grid 1.0 .. 30.0, freq 2
    assert (zero["interpolated"] == ~zero["tenor_years"].isin(t)).all()
    assert Curve.from_panel(zero, "US", D).tenors.size == 59  # a zero curve is its grid
    gap = bootstrap.par_zero_gap(panel, zero)
    assert list(gap.columns) == [
        "country",
        "date",
        "tenor_years",
        "par_yield",
        "zero_yield",
        "gap_bp",
    ]
    assert set(gap["tenor_years"]) == {10.0, 30.0} and (gap["gap_bp"] > 0).all()  # upward sloping
    g = pd.DataFrame(
        {
            "date": [D] * 4,
            "tenor_years": [2.0, 5.0, 10.0, 30.0],
            "yield": [0.022, 0.025, 0.03, 0.05],
        }
    )
    chk = bootstrap.us_zero_vs_gsw(zero, g)
    assert list(chk.columns) == ["date", "tenor_years", "zero_bootstrap", "zero_gsw", "diff_bp"]
    assert len(chk) == 4 and np.allclose(
        chk["diff_bp"], (chk["zero_bootstrap"] - chk["zero_gsw"]) * 1e4
    )
