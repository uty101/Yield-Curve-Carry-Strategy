"""Step 6.3: the caveats section is built from files, never from typed numbers."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from curvecarry import caveats, checks, report

CFG = {
    "sample": {
        "strategy_start": "1997-08-31",
        "sample_full_start": "2004-11-30",
        "strategy_end": "2026-08-31",
        "sample_max_tenor": 10,
    }
}


def _numeric_constants(fn) -> list:
    """Every int/float constant in ``fn``'s source that is not a format spec."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    inside_format: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FormattedValue):
            inside_format |= {id(n) for n in ast.walk(node)}
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int | float)
        and not isinstance(node.value, bool)
        and id(node) not in inside_format
    ]


def test_section_6_3_has_no_hardcoded_numbers():
    """No number reaches the page except through ``facts``, which reads it from a file."""
    assert _numeric_constants(caveats.section) == []


def test_the_guard_would_catch_a_typed_number():
    """The AST guard is not vacuous: a function with a literal fails it."""

    def typed() -> str:
        n = 722
        return f"the overlay lost {n} bp"

    assert _numeric_constants(typed) == [722]


# ------------------------------------------------- synthetic end-to-end render


def _write_synthetic(tmp_path: Path) -> tuple[Path, Path]:
    c = tmp_path / "checks"
    d = tmp_path / "decisions"
    c.mkdir()
    d.mkdir()

    pd.DataFrame(
        [
            {"variant": "carry_hedged", "window": w, "piece": p, "cumulative": v, "share": 0.0}
            for w, rows in {
                "full": {
                    "carry_earned": 0.11,
                    "yield_change_pnl": -0.22,
                    "funding": 0.0,
                    "fx": 0.0,
                    "cost": -0.033,
                    "r_net": -0.143,
                },
                "1990s": {"r_net": -0.044},
                "2000s": {"r_net": 0.055},
            }.items()
            for p, v in rows.items()
        ]
    ).to_csv(c / "decomposition_shares.csv", index=False)

    months = pd.date_range("2022-01-31", periods=12, freq="ME")
    pd.DataFrame(
        {
            "date": months.date.astype(str),
            "country": "ALL",
            "leg": "both",
            "carry_earned": 0.001,
            "yield_change_pnl": -0.006,
            "hedge": 0.0,
            "cost": -0.0002,
            "total": -0.0052,
        }
    ).to_csv(c / "attribution_2022_carry_hedged.csv", index=False)

    pd.DataFrame(
        {
            "country": ["GB", "CA", "FR", "JP", "US", "DE"],
            "entry_date": ["2008-09-30"] * 6,
            "exit_date": ["2008-11-30"] * 6,
            "direction": ["flattener"] * 6,
            "pnl_bp": [-171.0, -129.0, -146.0, -106.0, -1.0, 2.0],
            "cost_bp": [4.0] * 6,
            "pnl_net_bp": [-175.0, -133.0, -150.0, -110.0, -5.0, -2.0],
            "in_sample": [True] * 6,
        }
    ).to_csv(c / "overlay_trades.csv", index=False)

    (c / "unhedged_fx_exposure.csv").write_text(
        "variant,date,currency,net_notional,fx_return,contribution\n"
        "carry_unhedged,2020-01-31,GBP,1.0,0.0,0.0\n"
        "\n"
        "variant,n_months,beta,alpha_ann,r_squared,sd_book,sd_fx_term,"
        "mean_abs_net_notional,max_abs_net_notional\n"
        "carry_unhedged,348,0.9564,-0.0056,0.9527,0.0320,0.0326,1.8602,3.3908\n",
        encoding="utf-8",
    )

    pd.DataFrame(
        {
            "country": ["JP", "US"],
            "first": ["1999-03-31", ""],
            "last": ["2000-07-31", ""],
            "months_filled": [17, 0],
        }
    ).to_csv(c / "funding_fill.csv", index=False)

    pd.DataFrame(
        [
            {
                "variant": v,
                "window": "full",
                "ann_return": r,
                "sharpe": sh,
                "max_dd": dd,
                "ret_2022": y22,
                "dsr": dsr,
                "n_trials": 19,
            }
            for v, r, sh, dd, y22, dsr in [
                ("carry_hedged", 0.0059, 0.2645, -0.1037, -0.0441, 0.573),
                ("carry_hedged_interbank_3m", 0.0064, 0.2838, -0.0955, -0.0468, 0.615),
                ("carry_hedged_country_scope", 0.0019, 0.1196, -0.0894, -0.0218, 0.281),
                ("carry_hedged_no_gb30", 0.0063, 0.2799, -0.1035, -0.0449, 0.606),
                ("carry_hedged_cost0", 0.0077, 0.3442, -0.0969, -0.0415, 0.727),
                ("carry_hedged_cost2x", 0.0041, 0.1851, -0.1104, -0.0467, 0.408),
                ("carry_hedged_ratesvol", 0.0059, 0.2645, -0.1037, -0.0441, 0.573),
                ("carry_hedged_ratesvol_rolling", 0.0058, 0.2848, -0.0863, -0.0143, 0.614),
            ]
        ]
    ).to_csv(c / "metrics_table.csv", index=False)

    pd.DataFrame(
        {
            "country": ["CA", "FR"],
            "months": [488, 262],
            "share_at_bound": [0.3463, 0.0458],
            "share_at_lower": [0.3156, 0.0458],
            "share_at_upper": [0.0307, 0.0],
        }
    ).to_csv(c / "ns_lambda_bound.csv", index=False)

    pd.DataFrame(
        {
            "date": ["2000-01-31", "2000-02-29"],
            "tenor_years": [10.0, 10.0],
            "par_cmt": [0.06, 0.06],
            "par_gsw": [0.0608, 0.0608],
            "diff_bp": [-7.0, -9.0],
            "interpolated": [False, False],
        }
    ).to_csv(c / "us_par_vs_gsw.csv", index=False)

    pd.DataFrame(
        {
            "date": ["1999-04-30", "1999-06-30", "2010-01-31"],
            "country": ["JP", "JP", "DE"],
            "tenor_years": [1.0, 1.0, 30.0],
            "change": ["leaves", "enters", "leaves"],
        }
    ).to_csv(c / "universe_changes.csv", index=False)

    pd.DataFrame(
        {
            "tenor_years": [1.0, 30.0],
            "n": [3145, 2000],
            "mean_bp": [-0.63, -1.42],
            "std_bp": [2.89, 9.0],
            "max_abs_bp": [36.0, 121.0],
        }
    ).to_csv(c / "return_approx_gap.csv", index=False)

    (d / "basis.md").write_text(
        "the basis runs **20 to 50 bp in stress periods** for the major pairs\n",
        encoding="utf-8",
    )
    return c, d


def test_section_6_3_renders_from_synthetic_inputs(tmp_path: Path):
    """Every synthetic input value appears, formatted, in the rendered section."""
    c, d = _write_synthetic(tmp_path)
    f = caveats.facts(CFG, c, d)
    text = caveats.section(f)
    for key, value in f.items():
        assert value in text, key
    # the values themselves, formatted the way the section formats them
    for expected in (
        "11.00%",  # carry earned
        "22.00%",  # the yield-change PnL, size only: the prose carries the sign
        "573 bp",  # the overlay worst five, summed, size only
        "95.3%",  # the FX R-squared
        "20 to 50 bp",  # the basis range, lifted from decisions/basis.md
        "34.6%",  # the worst lambda-on-bound share
        "-8.0 bp",  # the on-the-run mean at 10 years
        "1990s",  # the losing decade
        "19",  # the number of logged runs, in the selection caveat
        "0.614",  # the rolling control's own deflated Sharpe
    ):
        assert expected in text, expected


def test_section_6_3_covers_every_amendment_4_topic(tmp_path: Path):
    """The seven topics session-6 amendment 4 names are each in the text."""
    c, d = _write_synthetic(tmp_path)
    text = caveats.section(caveats.facts(CFG, c, d))
    for phrase in (
        "slope overlay is flat gross",
        "Duration neutrality is not currency neutrality",
        "policy rate used as a three-month anchor",
        "cross-currency basis",
        "Nelson-Siegel lambda is unidentified",
        "on-the-run",
        "enter and leave mid-sample",
        "one risk control that helped is not a result",
        "logged runs",
        "chosen after a result was seen",
        "never the headline",
    ):
        assert phrase in text, phrase


def test_plan_entry_point_is_the_same_text(tmp_path: Path):
    """``report.section_what_carry_does_not_tell_you`` is PLAN.md 6.3's name for it."""
    c, d = _write_synthetic(tmp_path)
    assert report.section_what_carry_does_not_tell_you(CFG, c, d) == caveats.section(
        caveats.facts(CFG, c, d)
    )


def test_ns_lambda_bound_rows_counts_only_the_free_fits():
    """The fixed-lambda model is never on a bound and is not in the table."""
    params = pd.DataFrame(
        {
            "country": ["US"] * 4,
            "model": ["ns_free", "ns_free", "ns_dl", "ns_dl"],
            "lam": [0.05, 0.7, 0.7, 0.7],
            "lam_at_bound": [True, False, False, False],
        }
    )
    table = caveats.ns_lambda_bound_rows(params)
    assert list(table["country"]) == ["US"]
    assert int(table["months"].iloc[0]) == 2
    assert float(table["share_at_bound"].iloc[0]) == pytest.approx(0.5)


def test_section_file_path_is_the_one_the_plan_names():
    assert checks.SECTION_6_3.name == "section_6_3.md"
