"""Step 1.9: par to zero, the two sample windows, the US bootstrap check.

``bootstrap_par_to_zero(par, freq)`` (PLAN.md 1.9, as amended by the Session
2 fixes): coupon dates ``t_k = k / freq`` up to the longest observed par
tenor ``T_max``; the par yield at each ``t_k`` is ``par.at(t_k)`` — the one
interpolator between observed par tenors, and flat at the shortest observed
par yield below it (``config.short_end``, amendment B). ``DF_k = (1 − (c_k/f)
Σ_{j<k} DF_j) / (1 + c_k/f)`` and ``z_k = DF_k^(−1/t_k) − 1`` (annual
compounding); at ``t_1 = 1/f`` this is ``z = (1 + c/f)^f − 1``. Returned
(issue #10 A, answer a): **the zero at every coupon-grid point** inside
``[T_min, T_max]`` — the curve is then exactly invertible (any observed par
bond reprices to 1e-10 off it) — plus, for an observed par tenor **below
the first coupon date** (the US 0.25 bill with ``freq = 2``; #10 B, answer
a), the money-market identity ``z = (1 + c·t)^(1/t) − 1``: a bill's
bond-equivalent yield ``c`` is defined by ``P = 1 / (1 + c·t)``. Grid points
below ``T_min`` are not returned: the par is flat there by convention, so
the bootstrap zeros there all equal ``z(T_min)`` and ``Curve.at`` (flat below
the shortest tenor) reproduces them exactly. Nothing beyond ``T_max``
(rule 13). Par yields are quoted with the country's coupon frequency
(``decisions/compounding.md`` → "Par yields").

``build(cfg)`` → ``data/processed/curves_zero.parquet`` (the panel schema
plus ``bootstrapped``; a bootstrapped month carries its whole coupon grid,
``standard`` marks the 8 standard tenors and ``interpolated`` marks a tenor
that was not an observed par tenor); ``data/checks/par_zero_gap.csv`` (10y
and 30y, par countries); ``data/checks/us_zero_vs_gsw.csv`` (Session 2
amendment 3); ``data/checks/sample_window.txt`` and the two dates in
``config.toml``.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, harmonise
from curvecarry.curves import Curve
from curvecarry.loaders import base

PROCESSED = harmonise.PROCESSED
ZERO_COLUMNS = [*harmonise.PANEL_COLUMNS, "bootstrapped"]
GAP_TENORS = [10.0, 30.0]
GSW_TENORS = [2.0, 5.0, 10.0, 30.0]


def bootstrap_grid(par: Curve, freq: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The bootstrap itself: ``(grid, discount_factors, zero_yields)`` at every coupon date
    ``t_k = k / freq`` up to the longest observed par tenor."""
    assert par.curve_type == "par", f"bootstrap needs a par curve, got {par.curve_type!r}"
    assert freq in (1, 2, 4, 12), f"coupon frequency {freq}"
    f = float(freq)
    t_max = float(par.tenors.max())
    n = int(round(t_max * f))
    assert abs(n / f - t_max) < 1e-9, f"longest par tenor {t_max} is not on the {freq}/yr grid"
    grid = np.arange(1, n + 1) / f
    c = np.asarray(par.at(grid), dtype="float64")  # interpolated; flat below the shortest tenor
    assert np.isfinite(c).all()
    df = np.empty(n)
    acc = 0.0
    for k in range(n):
        df[k] = (1.0 - (c[k] / f) * acc) / (1.0 + c[k] / f)
        acc += df[k]
    z = df ** (-1.0 / grid) - 1.0
    return grid, df, z


def money_market_zero(c: float | np.ndarray, t: float | np.ndarray) -> float | np.ndarray:
    """Zero yield (annual compounding) of a single-cashflow tenor ``t`` below the first coupon
    date, from its bond-equivalent (simple-interest) yield ``c``: ``P = 1 / (1 + c·t)``, so
    ``z = (1 + c·t)^(1/t) − 1`` (#10 B). Not the coupon-frequency stub formula."""
    return (1.0 + np.asarray(c) * np.asarray(t)) ** (1.0 / np.asarray(t)) - 1.0


def bootstrap_par_to_zero(par: Curve, freq: int, standard: list[float] | None = None) -> Curve:
    """Par curve (coupon frequency ``freq``) -> zero curve at every coupon-grid point inside
    ``[T_min, T_max]`` plus the money-market zero of any observed tenor below ``1/freq``
    (PLAN.md 1.9 as amended; issue #10). ``standard`` is accepted for the plan's signature
    and ignored: the standard tenors are on the grid."""
    grid, _, z = bootstrap_grid(par, freq)
    t_min = float(par.tenors.min())
    keep = grid >= t_min - 1e-9
    bill = par.tenors * freq < 1 - 1e-9  # observed tenors before the first coupon date
    tenors = np.r_[par.tenors[bill], grid[keep]]
    zeros = np.r_[money_market_zero(par.yields[bill], par.tenors[bill]), z[keep]]
    return Curve(tenors, zeros, "zero", par.country, par.date)


def zero_panel(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``curves.parquet`` -> the zero panel: zero pass through, par bootstrapped."""
    std = harmonise.standard_tenors(cfg)
    out = []
    for country, g in panel.groupby("country", sort=False):
        ctype = g["curve_type"].unique()
        assert len(ctype) == 1, f"{country}: mixed curve types"
        if ctype[0] == "zero":
            h = g.copy()
            h["bootstrapped"] = False
            out.append(h)
            continue
        freq = int(cfg["coupon_frequency"][country])
        source = g["source"].iloc[0]
        rows = []
        for date, m in g.groupby("date", sort=True):
            obs = m[~m["interpolated"]]
            par = Curve(
                obs["tenor_years"].to_numpy(), obs["yield"].to_numpy(), "par", country, date
            )
            if par.tenors.size < 2:
                continue
            zc = bootstrap_par_to_zero(par, freq)
            observed = set(np.round(obs["tenor_years"].to_numpy(), 9))
            for t, y in zip(zc.tenors, zc.yields, strict=True):
                rows.append(
                    (
                        date,
                        country,
                        float(t),
                        float(y),
                        "zero",
                        source,
                        round(t, 9) not in observed,
                        round(t, 9) in {round(s, 9) for s in std},
                        True,
                    )
                )
        out.append(pd.DataFrame(rows, columns=ZERO_COLUMNS))
    z = pd.concat(out, ignore_index=True)
    z["interpolated"] = z["interpolated"].astype(bool)
    z["standard"] = z["standard"].astype(bool)
    z["bootstrapped"] = z["bootstrapped"].astype(bool)
    z = z.sort_values(["country", "date", "tenor_years"]).reset_index(drop=True)
    base.validate_curve(z[base.CURVE_COLUMNS])
    return z[ZERO_COLUMNS]


def par_zero_gap(panel: pd.DataFrame, zero: pd.DataFrame) -> pd.DataFrame:
    """``country, date, tenor_years, par_yield, zero_yield, gap_bp`` at 10y and 30y, par only."""
    p = panel[(panel["curve_type"] == "par") & panel["tenor_years"].isin(GAP_TENORS)]
    z = zero[zero["bootstrapped"] & zero["tenor_years"].isin(GAP_TENORS)]
    key = ["country", "date", "tenor_years"]
    m = p[[*key, "yield"]].merge(z[[*key, "yield"]], on=key, suffixes=("_par", "_zero"))
    m = m.rename(columns={"yield_par": "par_yield", "yield_zero": "zero_yield"})
    m["gap_bp"] = (m["zero_yield"] - m["par_yield"]) * 1e4
    return m.sort_values(key).reset_index(drop=True)


def us_zero_vs_gsw(zero: pd.DataFrame, gsw: pd.DataFrame) -> pd.DataFrame:
    """``date, tenor_years, zero_bootstrap, zero_gsw, diff_bp`` at 2, 5, 10, 30y, both present."""
    us = zero[(zero["country"] == "US") & zero["tenor_years"].isin(GSW_TENORS)]
    g = gsw[gsw["tenor_years"].isin(GSW_TENORS)]
    key = ["date", "tenor_years"]
    m = us[[*key, "yield"]].merge(g[[*key, "yield"]], on=key, suffixes=("_bootstrap", "_gsw"))
    m = m.rename(columns={"yield_bootstrap": "zero_bootstrap", "yield_gsw": "zero_gsw"})
    m["diff_bp"] = (m["zero_bootstrap"] - m["zero_gsw"]) * 1e4
    return m.sort_values(key).reset_index(drop=True)


def sample_window(zero: pd.DataFrame, cfg: dict) -> tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    """(strategy_start, sample_full_start, per-country first month with all tenors <= 10y).

    A country-month qualifies when it has a non-null zero yield at every
    standard tenor ``<= config.sample.sample_max_tenor``. ``strategy_start`` is
    the first month end where at least ``sample_min_countries`` of
    ``config.countries`` qualify; ``sample_full_start`` the first where all do.
    """
    max_t = float(cfg["sample"]["sample_max_tenor"])
    need = [t for t in harmonise.standard_tenors(cfg) if t <= max_t]
    countries = list(cfg["countries"])
    z = zero[
        zero["country"].isin(countries) & zero["tenor_years"].isin(need) & zero["yield"].notna()
    ]
    have = z.groupby(["country", "date"])["tenor_years"].nunique()
    ok = have[have == len(need)].reset_index()[["country", "date"]]
    per_month = ok.groupby("date")["country"].nunique().sort_index()
    first_by_country = ok.groupby("country")["date"].min().reindex(countries)
    k = int(cfg["sample"]["sample_min_countries"])
    start = per_month[per_month >= k].index.min()
    full = per_month[per_month >= len(countries)].index.min()
    if pd.isna(start) or pd.isna(full):
        raise ValueError("no month satisfies the sample window rule")
    table = first_by_country.rename("first_month_all_tenors_to_10y").reset_index()
    return pd.Timestamp(start), pd.Timestamp(full), table


def write_config_dates(
    start: pd.Timestamp, full: pd.Timestamp, path: Path = Path("config.toml")
) -> None:
    """Set ``[sample] strategy_start`` and ``sample_full_start`` in place (one edit after 0.1)."""
    text = path.read_text(encoding="utf-8")
    for key, value in (("strategy_start", start), ("sample_full_start", full)):
        pat = re.compile(rf'^({key}\s*=\s*)"[^"]*"', re.M)
        assert pat.search(text), f"{key} not in config.toml"
        text = pat.sub(rf'\g<1>"{value.date().isoformat()}"', text, count=1)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(cfg: dict, processed: Path = PROCESSED, interim: Path = base.INTERIM) -> pd.DataFrame:
    panel = pd.read_parquet(Path(processed) / "curves.parquet")
    zero = zero_panel(panel, cfg)
    zero.to_parquet(Path(processed) / "curves_zero.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    par_zero_gap(panel, zero).to_csv(checks.PAR_ZERO_GAP, index=False, lineterminator="\n")
    gsw_path = Path(interim) / "gsw_us.parquet"
    if not gsw_path.exists():
        raise FileNotFoundError(
            f"{gsw_path}: run `curvecarry fetch --source gsw; build --step gsw`"
        )
    us_zero_vs_gsw(zero, pd.read_parquet(gsw_path)).to_csv(
        checks.US_ZERO_VS_GSW, index=False, lineterminator="\n"
    )
    start, full, table = sample_window(zero, cfg)
    lines = [
        f"strategy_start={start.date().isoformat()}",
        f"sample_full_start={full.date().isoformat()}",
    ]
    checks.SAMPLE_WINDOW.write_text("\n".join(lines) + "\n", encoding="utf-8")
    table.to_csv(checks.SAMPLE_WINDOW_BY_COUNTRY, index=False, lineterminator="\n")
    write_config_dates(start, full)
    return zero
