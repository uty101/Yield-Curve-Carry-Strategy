"""Report tables. Step 3.3 builds the first one; the full report is step 6.4.

``explained_table`` renders ``data/checks/pca_explained.csv`` as the markdown
table ``scope | PC1 | PC2 | PC3 | PC1-3``, in percent to one decimal place,
one row per scope. The rows are the six countries in ``config.countries``
order, then the primary pooled fit, then the secondary ``pooled_20y`` fit —
which is reported here and read by no step after 3.3 (issue #15 answer 5).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks

TABLE_COMPONENTS = [1, 2, 3]
HEADER = "| scope | n months | PC1 | PC2 | PC3 | PC1-3 |"
RULE = "|---|---:|---:|---:|---:|---:|"


def _scope_order(scopes: list[str], cfg: dict) -> list[str]:
    from curvecarry.pca import PRIMARY_POOLED, SECONDARY_POOLED

    order = [c for c in cfg["countries"] if c in scopes]
    return order + [s for s in (PRIMARY_POOLED, SECONDARY_POOLED) if s in scopes]


def explained_table(explained: pd.DataFrame, cfg: dict) -> str:
    """The markdown explained-variance table, percentages to 1 dp."""
    lines = [HEADER, RULE]
    for scope in _scope_order(list(explained["scope"].unique()), cfg):
        g = explained[explained["scope"] == scope].set_index("component")
        shares = [round(float(g.loc[k, "explained_share"]) * 100, 1) for k in TABLE_COMPONENTS]
        n = int(g["n_months"].iloc[0])
        cells = " | ".join(f"{v:.1f}" for v in shares)
        # the total is the sum of the **rounded** components, not the rounded sum,
        # so the printed row adds up: PLAN.md 3.3 asks for the PC1-3 column to equal
        # the sum of the three to 0.05 pp, and rounding the exact total instead can
        # put it 0.1 pp away from what the reader adds (US: 90.9 + 7.2 + 1.1 = 99.2,
        # while the exact 99.27 would print 99.3).
        lines.append(f"| {scope} | {n} | {cells} | {sum(shares):.1f} |")
    return "\n".join(lines) + "\n"


def write_explained_table(
    explained: pd.DataFrame, cfg: dict, path: Path = checks.PCA_EXPLAINED_TABLE
) -> Path:
    text = explained_table(explained, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


# ------------------------------------------------- step 5.5: the metrics table

METRICS_COLUMNS = [
    "variant",
    "window",
    "ann_return",
    "ann_vol",
    "sharpe",
    "max_dd",
    "dd_peak",
    "dd_trough",
    "turnover",
    "ret_2022",
    "dd_2022",
    "n_months",
    "ann_return_gross",
    "sharpe_gross",
    "sr_monthly",
    "skew",
    "kurtosis",
    "sr0",
    "dsr",
    "n_trials",
    "sr_var_trials",
]
METRICS_TABLE_HEADER = (
    "| variant | window | ann return | ann vol | Sharpe | max DD | DD peak | DD trough | "
    "turnover | 2022 | DD 2022 | n | gross return | gross Sharpe | DSR |"
)
METRICS_TABLE_RULE = "|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|"


def _variant_series(variant: str, processed: Path) -> pd.Series:
    """The monthly net return series of one run, indexed by date."""
    m = pd.read_parquet(processed / f"backtest_{variant}.parquet")
    return m.set_index("date")["r_net"].sort_index()


def metrics_table(cfg: dict, processed: Path | None = None, spec_path=None) -> pd.DataFrame:
    """Every logged variant, both windows, with the deflated Sharpe.

    ``N`` is ``speclog.count_runs()`` - the row count of
    ``reports/specifications.csv`` - and is never passed in. ``V[SR]`` is the
    variance of the **monthly** Sharpes across every run that has a
    ``metrics_<variant>.csv``, which is the set of trials whose results were
    actually looked at.
    """
    from curvecarry import harmonise, metrics, speclog

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    path = speclog.DEFAULT_PATH if spec_path is None else spec_path
    n_trials = speclog.count_runs(path)

    # "metrics_table.csv" is this function's own output, not a variant
    variants = sorted(
        name
        for name in (
            f.name[len("metrics_") : -len(".csv")] for f in checks.CHECKS.glob("metrics_*.csv")
        )
        if name != "table"
    )
    series = {v: _variant_series(v, p) for v in variants}
    sharpes = [metrics.monthly_sharpe(s) for s in series.values()]
    finite = [v for v in sharpes if pd.notna(v)]
    sr_var = float(pd.Series(finite).var(ddof=1)) if len(finite) > 1 else 0.0

    starts = {
        "full": pd.Timestamp(cfg["sample"]["strategy_start"]),
        "six": pd.Timestamp(cfg["sample"]["sample_full_start"]),
    }
    rows = []
    for variant in variants:
        table = pd.read_csv(checks.CHECKS / f"metrics_{variant}.csv")
        for window, start in starts.items():
            cell = table[table["window"] == window].set_index("metric")["value"]
            r = series[variant]
            r = r[r.index >= start]
            sr_monthly = metrics.monthly_sharpe(r)
            skew = float(r.skew())
            kurt = float(r.kurtosis()) + metrics.NORMAL_KURTOSIS  # pandas gives excess
            sr0, dsr = metrics.deflated_sharpe(sr_monthly, sr_var, n_trials, len(r), skew, kurt)
            row = {"variant": variant, "window": window}
            for key in METRICS_COLUMNS[2:14]:
                value = cell.get(key, "")
                row[key] = value if key in ("dd_peak", "dd_trough") else float(value)
            row |= {
                "sr_monthly": sr_monthly,
                "skew": skew,
                "kurtosis": kurt,
                "sr0": sr0,
                "dsr": dsr,
                "n_trials": n_trials,
                "sr_var_trials": sr_var,
            }
            rows.append(row)
    return pd.DataFrame(rows, columns=METRICS_COLUMNS)


def metrics_table_md(table: pd.DataFrame) -> str:
    """The same table as markdown, percentages to 2 dp."""
    lines = [METRICS_TABLE_HEADER, METRICS_TABLE_RULE]
    for _, r in table.iterrows():
        cells = [
            str(r["variant"]),
            str(r["window"]),
            f"{r['ann_return']:.2%}",
            f"{r['ann_vol']:.2%}",
            f"{r['sharpe']:.3f}",
            f"{r['max_dd']:.2%}",
            str(r["dd_peak"] or "inception"),
            str(r["dd_trough"]),
            f"{r['turnover']:.3f}",
            f"{r['ret_2022']:.2%}",
            f"{r['dd_2022']:.2%}",
            f"{r['n_months']:.0f}",
            f"{r['ann_return_gross']:.2%}",
            f"{r['sharpe_gross']:.3f}",
            f"{r['dsr']:.3f}",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    n = int(table["n_trials"].iloc[0])
    v = float(table["sr_var_trials"].iloc[0])
    lines.append("")
    sr0 = float(table["sr0"].iloc[0])
    lines.append(
        "**DSR is a probability, not a Sharpe**: the probability that the true Sharpe "
        f"exceeds the multiple-testing threshold, here SR0 = {sr0:.3f} monthly over "
        f"N = {n} trials. N is the row count of `reports/specifications.csv`, "
        f"V[SR] = {v:.6f} across the logged runs, monthly basis. A DSR below about "
        "0.95 does not clear the usual bar."
    )
    lines.append("")
    lines.append("Annualisation of every return and vol column: arithmetic, mean x 12.")
    return "\n".join(lines) + "\n"


def write_metrics_table(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """``data/checks/metrics_table.csv`` and ``metrics_table.md``."""
    table = metrics_table(cfg, processed)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    table.to_csv(checks.METRICS_TABLE, index=False, lineterminator="\n")
    checks.METRICS_TABLE_MD.write_text(metrics_table_md(table), encoding="utf-8")
    return table


# -------------------------------- session-5 fix 2: what the unhedged runs are

UNHEDGED_VARIANTS = ("carry_unhedged", "overlay_unhedged", "combined_unhedged")
FX_EXPOSURE_COLUMNS = ["variant", "date", "currency", "net_notional", "fx_return", "contribution"]
FX_REGRESSION_COLUMNS = [
    "variant",
    "n_months",
    "beta",
    "alpha_ann",
    "r_squared",
    "sd_book",
    "sd_fx_term",
    "mean_abs_net_notional",
    "max_abs_net_notional",
]


def fx_exposure_rows(positions: pd.DataFrame, returns: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Net notional per currency per month, and the FX return it was exposed to.

    The book is neutral in **duration**; it is not neutral in **notional**,
    and notional is what carries currency risk. A bucket's capital weight is
    an exposure to that country's currency, so the net exposure to a currency
    is the sum of the weights of every bucket in it (DE and FR share EUR).
    """
    currency = cfg["currency"]
    fx = returns[["date", "country", "tenor_years", "fx_return"]]
    p = positions.merge(fx, on=["date", "country", "tenor_years"], how="left")
    p["currency"] = p["country"].map(currency)
    p["contribution"] = p["weight"] * p["fx_return"]
    grouped = p.groupby(["date", "currency"], as_index=False).agg(
        net_notional=("weight", "sum"),
        contribution=("contribution", "sum"),
    )
    # the currency's own FX return, for reference: the contribution per unit of notional
    with np.errstate(invalid="ignore", divide="ignore"):
        grouped["fx_return"] = grouped["contribution"] / grouped["net_notional"].replace(
            0.0, np.nan
        )
    return grouped[FX_EXPOSURE_COLUMNS[1:]]


def fx_regression(exposure: pd.DataFrame, monthly: pd.DataFrame, base: str) -> dict:
    """Regress the book's monthly unhedged return on its own currency-weighted FX return."""
    term = exposure[exposure["currency"] != base].groupby("date")["contribution"].sum()
    r = monthly.set_index("date")["r_gross"].sort_index()
    # a month the book held nothing foreign has an FX term of exactly zero, not a
    # missing one; dropping those months would regress on the subsample where the
    # exposure was on, which is the subsample that flatters the hedged reading
    term = term.reindex(r.index).fillna(0.0)
    joined = pd.concat([r.rename("book"), term.rename("fx")], axis=1).dropna()
    if len(joined) < 3:
        return dict.fromkeys(FX_REGRESSION_COLUMNS[1:], float("nan")) | {"n_months": len(joined)}
    x = joined["fx"].to_numpy()
    y = joined["book"].to_numpy()
    beta, alpha = np.polyfit(x, y, 1)
    fitted = alpha + beta * x
    ss_res = float(((y - fitted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    net = (
        exposure[exposure["currency"] != base]
        .groupby("date")["net_notional"]
        .apply(lambda s: float(np.abs(s).sum()))
    )
    return {
        "n_months": len(joined),
        "beta": float(beta),
        "alpha_ann": float(alpha * 12),
        "r_squared": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "sd_book": float(joined["book"].std(ddof=1)),
        "sd_fx_term": float(joined["fx"].std(ddof=1)),
        "mean_abs_net_notional": float(net.mean()),
        "max_abs_net_notional": float(net.max()),
    }


def unhedged_fx_exposure(cfg: dict, processed: Path | None = None) -> tuple:
    """``data/checks/unhedged_fx_exposure.csv``: the per-month table, then the regressions."""
    from curvecarry import harmonise

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    returns = pd.read_parquet(p / "returns.parquet")
    base_currency = str(cfg["base_currency"])
    tables, summaries = [], []
    for variant in UNHEDGED_VARIANTS:
        positions = pd.read_parquet(checks.CHECKS / f"positions_{variant}.parquet")
        monthly = pd.read_parquet(p / f"backtest_{variant}.parquet")
        rows = fx_exposure_rows(positions, returns, cfg)
        rows.insert(0, "variant", variant)
        tables.append(rows)
        summaries.append({"variant": variant} | fx_regression(rows, monthly, base_currency))
    table = pd.concat(tables, ignore_index=True)[FX_EXPOSURE_COLUMNS]
    summary = pd.DataFrame(summaries, columns=FX_REGRESSION_COLUMNS)

    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    out = table.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
    text = out.to_csv(index=False, lineterminator="\n")
    text += "\n" + summary.to_csv(index=False, lineterminator="\n")
    checks.UNHEDGED_FX_EXPOSURE.write_text(text, encoding="utf-8")
    return table, summary


# ------------------------------- step 6.3: what carry does not tell you


def section_what_carry_does_not_tell_you(cfg: dict, checks_dir=None, decisions_dir=None) -> str:
    """PLAN.md 6.3's name for the section; the text and its facts live in ``caveats``.

    Session-6 deviation 5: the section is its own module. It reads eight check
    files and a decision document and holds a page of prose, and ``report.py``
    is already the metrics table, the explained-variance table and the FX
    regressions. The plan's entry point is kept here so nothing has to look
    for it.
    """
    from curvecarry import caveats

    return caveats.section(caveats.facts(cfg, checks_dir, decisions_dir))
