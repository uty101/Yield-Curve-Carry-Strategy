"""Step 1.9: par to zero, the two sample windows, the US bootstrap check.

``bootstrap_par_to_zero(par, freq)`` (PLAN.md 1.9, as amended by the
Session 1 part B fixes): coupon dates ``t_k = k / freq`` up to the longest observed par
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

**No bootstrap across a wide node gap** (Session 1 part B fix 2): the bootstrap
for a (country, date) runs only to the longest observed par tenor ``T``
such that no two consecutive observed par nodes up to ``T`` are more than
``config.bootstrap_max_node_gap_years`` (10) apart; tenors beyond it are
absent from the zero curve (rule 13), not interpolated. For the US this
removes the 20y and 30y zeros for 1987-01..1993-09, when DGS20 was not
published and the par curve was linear from 10 to 30 years
(``decisions/sources.md`` → "Bootstrap node-gap rule").

**Ill-conditioned long end** (Session 1 part B fix 3, **withdrawn**; replaced in
fix round 2): after bootstrapping each (country, date), if the zero yield
differs from the par yield by more than
``config.bootstrap_zero_par_tolerance_bp`` (100) at any standard tenor
``T >= ZERO_PAR_MIN_TENOR`` (10) that is **also an observed par node**, the
zeros at ``T`` and beyond are dropped for that month. The comparison is at
observed nodes only, so nothing the interpolator invented can trip it. The
1-year forward rule it replaces tripped on the forward-rate jumps that
linear par interpolation produces at every node
(``decisions/sources.md`` → "Bootstrap long-end rules").

``data/checks/bootstrap_dropped.csv``: one row per (country, date, reason)
that dropped tenors — ``reason`` is ``node_gap`` (fix 2) or ``zero_par``,
with the first tenor dropped and, for ``zero_par``, the zero, the par and
the gap in bp at the breaching node.

**GSW diagnostics, reported only** (Session 1 part B fix 4): ``us_par_vs_gsw.csv``
— the CMT par yield minus the GSW par yield (``SVENPY``, coupon-equivalent,
the same basis) at 2, 5, 10 and 30 years every month both exist, so the
input difference can be read apart from the bootstrap; ``bootstrap_on_gsw.csv``
— the GSW par curve (every integer tenor the fit reaches, ``freq = 2``)
put through ``bootstrap_grid`` and compared with the GSW zeros at the same
four tenors: the bootstrap's own error on a smooth curve it did not build.

``build(cfg)`` → ``data/processed/curves_zero.parquet`` (the panel schema
plus ``bootstrapped``; a bootstrapped month carries its whole coupon grid,
``standard`` marks the 8 standard tenors and ``interpolated`` marks a tenor
that was not an observed par tenor); ``data/checks/par_zero_gap.csv`` (10y
and 30y, par countries); ``data/checks/us_zero_vs_gsw.csv`` (Session 1 part B
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
ZERO_PAR_MIN_TENOR = 10.0  # the zero-vs-par check runs at standard tenors from here up
DROPPED_COLUMNS = ["country", "date", "reason", "first_tenor_dropped", "zero", "par", "gap_bp"]
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


def node_gap_cutoff(par: Curve, max_gap: float) -> float:
    """The longest observed par tenor ``T`` such that no two consecutive observed nodes up to
    ``T`` are more than ``max_gap`` years apart (Session 1 part B fix 2)."""
    wide = np.where(np.diff(par.tenors) > max_gap + 1e-9)[0]
    return float(par.tenors[wide[0]]) if wide.size else float(par.tenors[-1])


def truncate(par: Curve, t_max: float) -> Curve:
    keep = par.tenors <= t_max + 1e-9
    return Curve(par.tenors[keep], par.yields[keep], par.curve_type, par.country, par.date)


def zero_par_breach(
    par: Curve,
    grid: np.ndarray,
    z: np.ndarray,
    standard: list[float],
    tol_bp: float,
) -> tuple[float, float, float, float] | None:
    """The first standard tenor ``T >= ZERO_PAR_MIN_TENOR`` that is an observed par node and
    whose bootstrapped zero is more than ``tol_bp`` from the par yield there:
    ``(T, zero, par, gap_bp)``, or ``None``."""
    nodes = set(np.round(par.tenors, 9))
    for t in sorted(float(x) for x in standard):
        if t < ZERO_PAR_MIN_TENOR or round(t, 9) not in nodes:
            continue
        hit = np.isclose(grid, t, atol=1e-9)
        if not hit.any():
            continue
        zt, pt = float(z[hit][0]), float(par.at(t))
        gap_bp = (zt - pt) * 1e4
        if abs(gap_bp) > tol_bp:
            return t, zt, pt, gap_bp
    return None


def bootstrap_month(
    par: Curve,
    freq: int,
    max_node_gap: float | None = None,
    standard: list[float] | None = None,
    zero_par_tolerance_bp: float | None = None,
) -> tuple[Curve | None, list[dict]]:
    """One (country, date): ``(zero curve or None, rows for bootstrap_dropped.csv)``. The
    node-gap cut (fix 2) runs first, then the bootstrap, then the zero-vs-par check (fix
    round 2). ``None`` when nothing survives."""
    dropped = []
    t_max_obs = float(par.tenors.max())
    if max_node_gap is not None:
        t_gap = node_gap_cutoff(par, max_node_gap)
        if t_gap < t_max_obs - 1e-9:
            par = truncate(par, t_gap)
            dropped.append(
                {
                    "reason": "node_gap",
                    "first_tenor_dropped": t_gap + 1.0 / freq,
                    "zero": None,
                    "par": None,
                    "gap_bp": None,
                }
            )
    grid, _, z = bootstrap_grid(par, freq)
    cut = None
    if zero_par_tolerance_bp is not None and standard:
        breach = zero_par_breach(par, grid, z, standard, zero_par_tolerance_bp)
        if breach is not None:
            cut, zt, pt, gap_bp = breach
            dropped.append(
                {
                    "reason": "zero_par",
                    "first_tenor_dropped": cut,
                    "zero": zt,
                    "par": pt,
                    "gap_bp": gap_bp,
                }
            )
    keep = grid >= float(par.tenors.min()) - 1e-9
    if cut is not None:
        keep &= grid < cut - 1e-9
    bill = par.tenors * freq < 1 - 1e-9  # observed tenors before the first coupon date
    tenors = np.r_[par.tenors[bill], grid[keep]]
    zeros = np.r_[money_market_zero(par.yields[bill], par.tenors[bill]), z[keep]]
    curve = Curve(tenors, zeros, "zero", par.country, par.date) if tenors.size else None
    return curve, dropped


def bootstrap_par_to_zero(
    par: Curve,
    freq: int,
    standard: list[float] | None = None,
    max_node_gap: float | None = None,
    zero_par_tolerance_bp: float | None = None,
) -> Curve:
    """Par curve (coupon frequency ``freq``) -> zero curve at every coupon-grid point inside
    ``[T_min, T_max]`` plus the money-market zero of any observed tenor below ``1/freq``
    (PLAN.md 1.9 as amended; issue #10). ``max_node_gap`` (years, fix 2) and
    ``zero_par_tolerance_bp`` (fix round 2, with ``standard``) switch the two rules on;
    ``zero_panel`` passes ``config.bootstrap_max_node_gap_years`` and
    ``config.bootstrap_zero_par_tolerance_bp``. With no tolerance, ``standard`` is unused:
    the standard tenors are on the grid."""
    curve, _ = bootstrap_month(par, freq, max_node_gap, standard, zero_par_tolerance_bp)
    if curve is None:
        raise ValueError(f"{par.country} {par.date.date()}: no zero tenor survives")
    return curve


def zero_panel(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """``curves.parquet`` -> the zero panel: zero pass through, par bootstrapped."""
    return zero_panel_and_dropped(panel, cfg)[0]


def zero_panel_and_dropped(panel: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The zero panel and the ``bootstrap_dropped.csv`` table (one row per country-month and
    reason that dropped tenors: ``node_gap`` or ``zero_par``)."""
    std = harmonise.standard_tenors(cfg)
    max_gap = float(cfg["bootstrap_max_node_gap_years"])
    tol_bp = float(cfg["bootstrap_zero_par_tolerance_bp"])
    out, dropped = [], []
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
            zc, rows_dropped = bootstrap_month(par, freq, max_gap, std, tol_bp)
            dropped += [{"country": country, "date": date, **r} for r in rows_dropped]
            if zc is None:
                continue
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
    d = pd.DataFrame(dropped, columns=DROPPED_COLUMNS)
    d = d.sort_values(["country", "date", "reason"]).reset_index(drop=True)
    return z[ZERO_COLUMNS], d


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


def us_par_vs_gsw(panel: pd.DataFrame, gsw_par: pd.DataFrame) -> pd.DataFrame:
    """``date, tenor_years, par_cmt, par_gsw, diff_bp, interpolated`` at 2, 5, 10, 30y, both
    present (fix 4a). ``interpolated`` is the CMT panel's flag (US 2y before 1976-06)."""
    us = panel[
        (panel["country"] == "US")
        & (panel["curve_type"] == "par")
        & panel["tenor_years"].isin(GSW_TENORS)
    ]
    g = gsw_par[gsw_par["tenor_years"].isin(GSW_TENORS)].dropna(subset=["yield"])
    key = ["date", "tenor_years"]
    m = us[[*key, "yield", "interpolated"]].merge(
        g[[*key, "yield"]], on=key, suffixes=("_cmt", "_gsw")
    )
    m = m.rename(columns={"yield_cmt": "par_cmt", "yield_gsw": "par_gsw"})
    m["diff_bp"] = (m["par_cmt"] - m["par_gsw"]) * 1e4
    cols = [*key, "par_cmt", "par_gsw", "diff_bp", "interpolated"]
    return m[cols].sort_values(key).reset_index(drop=True)


def bootstrap_on_gsw(gsw_par: pd.DataFrame, gsw_zero: pd.DataFrame, freq: int) -> pd.DataFrame:
    """``date, tenor_years, zero_bootstrap_gsw, zero_gsw, diff_bp`` at 2, 5, 10, 30y (fix 4b):
    the GSW par curve — every integer tenor the fit reaches that month — through
    ``bootstrap_grid`` (no node-gap or forward rule), against the GSW zeros."""
    rows = []
    for date, m in gsw_par.dropna(subset=["yield"]).groupby("date", sort=True):
        m = m.sort_values("tenor_years")
        if len(m) < 2:
            continue
        par = Curve(m["tenor_years"].to_numpy(), m["yield"].to_numpy(), "par", "US", date)
        grid, _, z = bootstrap_grid(par, freq)
        for t in GSW_TENORS:
            hit = np.isclose(grid, t)
            if hit.any():
                rows.append((date, float(t), float(z[hit][0])))
    b = pd.DataFrame(rows, columns=["date", "tenor_years", "zero_bootstrap_gsw"])
    g = gsw_zero[gsw_zero["tenor_years"].isin(GSW_TENORS)].dropna(subset=["yield"])
    key = ["date", "tenor_years"]
    out = b.merge(g[[*key, "yield"]].rename(columns={"yield": "zero_gsw"}), on=key)
    out["diff_bp"] = (out["zero_bootstrap_gsw"] - out["zero_gsw"]) * 1e4
    return out.sort_values(key).reset_index(drop=True)


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
    zero, dropped = zero_panel_and_dropped(panel, cfg)
    zero.to_parquet(Path(processed) / "curves_zero.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    dropped.to_csv(checks.BOOTSTRAP_DROPPED, index=False, lineterminator="\n")
    par_zero_gap(panel, zero).to_csv(checks.PAR_ZERO_GAP, index=False, lineterminator="\n")
    gsw_path = Path(interim) / "gsw_us.parquet"
    if not gsw_path.exists():
        raise FileNotFoundError(
            f"{gsw_path}: run `curvecarry fetch --source gsw; build --step gsw`"
        )
    end = pd.Timestamp(cfg["sample"]["strategy_end"])  # the partial month stays in interim
    gsw_zero = pd.read_parquet(gsw_path)
    gsw_zero = gsw_zero[gsw_zero["date"] <= end]
    gsw_par = pd.read_parquet(Path(interim) / "gsw_us_par.parquet")
    gsw_par = gsw_par[gsw_par["date"] <= end]
    us_zero_vs_gsw(zero, gsw_zero).to_csv(checks.US_ZERO_VS_GSW, index=False, lineterminator="\n")
    us_par_vs_gsw(panel, gsw_par).to_csv(checks.US_PAR_VS_GSW, index=False, lineterminator="\n")
    bootstrap_on_gsw(gsw_par, gsw_zero, int(cfg["coupon_frequency"]["US"])).to_csv(
        checks.BOOTSTRAP_ON_GSW, index=False, lineterminator="\n"
    )
    start, full, table = sample_window(zero, cfg)
    lines = [
        f"strategy_start={start.date().isoformat()}",
        f"sample_full_start={full.date().isoformat()}",
    ]
    checks.SAMPLE_WINDOW.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    table.to_csv(checks.SAMPLE_WINDOW_BY_COUNTRY, index=False, lineterminator="\n")
    write_config_dates(start, full)
    return zero
