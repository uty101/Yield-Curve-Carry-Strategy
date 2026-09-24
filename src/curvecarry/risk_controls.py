"""Step 6.2: the four pre-registered risk controls, and the 2022 attribution.

**All four are logged before any result is looked at, and all four are
reported whether they help or not** (global rule 6, session-6 amendments 2 and
9). The parameters of (a) to (c) were fixed in `config.toml [risk]` in session
1 and (d)'s window was added to the same file, in its own commit, before the
run that uses it existed. None of them may change the headline definition,
whatever the numbers say: each is a
transform of a **base** variant's held positions into a new logged variant,
and the base variants are `config.risk.risk_control_base_variants`.

Each control is a function of information dated **strictly before** the month
it sizes. That is the one thing a risk control can get wrong and still look
good, so each has its own no-lookahead test.

- **(a) `vol_target`** — `scale_t = min(target_vol / vol_{t-12..t-1},
  max_leverage)` with `vol` the annualised standard deviation (ddof 1) of the
  base's `r_net` over the 12 returns **dated `t-12 … t-1`**. A return dated
  `t` is earned over `t -> t+1` (4.2) and is not known at `t`, so it cannot be
  in the window that sizes `t` (amendment C). `scale_t = 1` until 12 such
  returns exist. `weight` and `wd` are both multiplied by `scale_t`, so the
  book stays duration-neutral: scaling a neutral book by a scalar leaves
  `sum wd = 0`.

- **(b) `dd_stop`** — the drawdown of the base's wealth index **through
  `r_{t-1}`**, `prod_{s <= t-1} (1 + r_s)` against its running peak. When that
  drawdown is below `-dd_stop` the book is **flat for months `t+1 …
  t+dd_reentry_months`** and re-enters at the base's positions afterwards. A
  flat month is a month with no position rows at all, which is the same thing
  as zero positions for every number the backtest computes and keeps the
  turnover of closing last month's book, charged in that month's cost.

- **(c) `rates_vol_filter`** — the pooled PC1 score by the **expanding**
  method of 5.4 (scope `pooled`, component 1, `pca_min_months`), then
  `v_t` = the standard deviation of the 12 scores ending at `t`, and the book
  is flat for `t -> t+1` when `v_t` exceeds the **expanding**
  `rates_vol_pct` quantile of `v` up to and including `t`.

- **(d) `rates_vol_filter_rolling`** — session-6 amendment 9, pre-registered
  2026-09-24 before the run. Identical to (c) in every respect except that the
  `rates_vol_pct` percentile is computed on a **rolling
  `risk.rates_vol_window_months` window of `v`** instead of expanding from the
  first available month. Same score, same `v_t`, same arming rule (a threshold
  has to exist), same removal of that month's positions.

  It exists because (c) never fires inside the strategy sample: its expanding
  threshold is anchored on 1967-1985, when pooled PC1 vol ran two to three
  times its post-1997 level, and the largest in-sample ratio of `v` to the
  threshold in force is 0.68. **That is a null about the threshold, not about
  the idea.** (c) is the dead threshold and (d) is the live test of the same
  idea; both are logged, both are reported, and (c) is not withdrawn - rule 6
  does not let a logged run be taken back because it did nothing.

  **The pooled score is defined here** (session-6 deviation 3): `fit_pooled`
  stacks every country's changes, so a pooled fit has one loading vector and
  one score per country-month, not one score per month. The pooled PC1 score
  at `t` is the **mean across the countries with a change row at `t`** of that
  country's own score, `(change_{c,t} - mean_c) @ loadings[:, 0]`. A level
  shock is common across curves, so the cross-country mean of the PC1 score is
  the level move the pooled fit is measuring; the alternative — one country
  standing for the pool — would make the filter a US filter.

The 2022 attribution is the same decomposition (6.1) cut by country and leg
over the twelve months of 2022, plus a `country = ALL` row per month. The
month's cost is **allocated pro rata to `|wd|`**, so each row's `total` is the
part of `r_net` that country-leg is responsible for and the `ALL` row is
`r_net` exactly (`test_attribution_2022_rows_sum_to_total`).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from curvecarry import checks, decomposition, harmonise, pca

VOL_TARGET = "vol_target"
DD_STOP = "dd_stop"
RATES_VOL = "rates_vol_filter"
RATES_VOL_ROLLING = "rates_vol_filter_rolling"
CONTROLS = [VOL_TARGET, DD_STOP, RATES_VOL, RATES_VOL_ROLLING]
CONTROL_SUFFIX = {
    VOL_TARGET: "voltarget",
    DD_STOP: "ddstop",
    RATES_VOL: "ratesvol",
    RATES_VOL_ROLLING: "ratesvol_rolling",
}
EXPANDING = "expanding"
ROLLING = "rolling"
METHOD = {RATES_VOL: EXPANDING, RATES_VOL_ROLLING: ROLLING}
POOLED_SCORE_COLUMNS = ["date", "n_countries", "score"]

MONTHS = 12
PC1 = 0  # zero-based index of the first component

ATTRIBUTION_COLUMNS = [
    "date",
    "country",
    "leg",
    "carry_earned",
    "yield_change_pnl",
    "hedge",
    "cost",
    "total",
]
ALL_COUNTRIES = "ALL"
ALL_LEGS = "both"
ATTRIBUTION_YEAR = 2022

RATES_VOL_COLUMNS = [
    "method",
    "date",
    "n_countries",
    "score",
    "vol",
    "threshold",
    "ratio",
    "armed",
    "triggers",
]
RISK_CONTROL_COLUMNS = [
    "base",
    "variant",
    "control",
    "window",
    "ann_return",
    "ann_vol",
    "sharpe",
    "max_dd",
    "ret_2022",
    "turnover",
    "months_flat",
]


def variant_name(base: str, control: str) -> str:
    return f"{base}_{CONTROL_SUFFIX[control]}"


# ------------------------------------------------------------ (a) vol target


def vol_target_scale(r_net: pd.Series, cfg: dict) -> pd.Series:
    """``scale_t`` from the 12 returns dated ``t-12 … t-1``; 1 until there are 12."""
    risk = cfg["risk"]
    window = int(risk["vol_window_months"])
    target = float(risk["target_vol"])
    cap = float(risk["max_leverage"])
    r = r_net.sort_index()
    # shift(1) drops the return dated t out of the window that sizes t
    vol = r.shift(1).rolling(window, min_periods=window).std(ddof=1) * math.sqrt(MONTHS)
    scale = (target / vol).clip(upper=cap)
    return scale.where(vol.notna() & (vol > 0.0), 1.0)


# ------------------------------------------------------------- (b) dd stop


def dd_stop_flat_months(r_net: pd.Series, cfg: dict) -> pd.Series:
    """``date -> True`` where the book is flat, from the drawdown through ``r_{t-1}``."""
    risk = cfg["risk"]
    limit = float(risk["dd_stop"])
    reentry = int(risk["dd_reentry_months"])
    r = r_net.sort_index()
    wealth = (1.0 + r).cumprod()
    peak = np.maximum(wealth.cummax(), 1.0)
    drawdown = (wealth / peak - 1.0).shift(1)  # the drawdown *through t-1*, seen at t
    breached = (drawdown < -limit).fillna(False).to_numpy()
    flat = np.zeros(len(r), dtype=bool)
    for i, hit in enumerate(breached):
        if hit:
            flat[i + 1 : i + 1 + reentry] = True
    return pd.Series(flat, index=r.index)


# ------------------------------------------------- (c) pooled PC1 vol filter


def pooled_pc1_scores(changes_by_country: dict[str, pd.DataFrame], cfg: dict) -> pd.DataFrame:
    """``date, n_countries, score`` — the expanding pooled PC1 score, month by month.

    At each month end the fit uses every country change row dated on or before
    that month, on the pooled tenor set, each country demeaned by its own
    column means — the 3.1 pooled recipe, refitted from scratch each month.
    ``pca_min_months`` counts **months of history**, as it does in 5.4, not
    stacked rows: three countries do not make a 20-month panel a 60-month one.
    """
    minimum = int(cfg["pca"]["pca_min_months"])
    tenors = sorted(set.intersection(*(set(c.columns) for c in changes_by_country.values())))
    frames = {k: v[tenors].sort_index() for k, v in changes_by_country.items()}
    dates = sorted(set().union(*(set(f.index) for f in frames.values())))
    rows = []
    for n_months, date in enumerate(dates, start=1):
        blocks, current = [], []
        for _country, f in sorted(frames.items()):
            past = f[f.index <= date]
            if past.empty:
                continue
            x = past.to_numpy(dtype="float64")
            mean = x.mean(axis=0)
            blocks.append(x - mean)
            if past.index[-1] == date:
                current.append(x[-1] - mean)
        if not current or n_months < minimum:
            rows.append({"date": date, "n_countries": len(current), "score": np.nan})
            continue
        res = pca.pca(np.vstack(blocks), np.array(tenors, dtype="float64"))
        loading = res.loadings[:, PC1]
        score = float(np.mean([c @ loading for c in current]))
        rows.append({"date": date, "n_countries": len(current), "score": score})
    return pd.DataFrame(rows, columns=POOLED_SCORE_COLUMNS)


def rates_vol_flags(scores: pd.DataFrame, cfg: dict, method: str = EXPANDING) -> pd.DataFrame:
    """``v_t``, the percentile in force, and the flag that flattens ``t -> t+1``.

    ``armed`` is "there is enough history for a decision": 12 non-null scores,
    which needs ``pca_min_months`` of panel before the first one exists.
    ``triggers`` is the decision itself. ``ratio`` is ``vol / threshold`` and
    is written out so that a month that does not trigger can be read as a
    distance rather than as a bare ``False`` - a filter that never fires and a
    filter that is never consulted look identical without it (session-6 fix 1).

    The expanding quantile includes the current month, which is PLAN.md 6.2's
    wording ("up to and including ``t``"). That does **not** make exceedance
    impossible: at ``n`` observations the linear-interpolated 90th percentile
    sits at position ``0.9 (n - 1)`` and a new maximum sits at ``n - 1``, so a
    new high in ``v`` clears it whenever ``n > 1``.
    """
    window = int(cfg["risk"]["vol_window_months"])
    pct = float(cfg["risk"]["rates_vol_pct"])
    out = scores.sort_values("date").reset_index(drop=True).copy()
    s = out["score"]
    out["vol"] = s.rolling(window, min_periods=window).std(ddof=1)
    if method == EXPANDING:
        out["threshold"] = out["vol"].expanding().quantile(pct)
    elif method == ROLLING:
        span = int(cfg["risk"]["rates_vol_window_months"])
        out["threshold"] = out["vol"].rolling(span, min_periods=span).quantile(pct)
    else:
        raise KeyError(f"unknown percentile method {method!r}; known: {EXPANDING}, {ROLLING}")
    out["method"] = method
    out["ratio"] = out["vol"] / out["threshold"]
    out["armed"] = out["vol"].notna() & out["threshold"].notna()
    out["triggers"] = (out["vol"] > out["threshold"]).fillna(False)
    return out[RATES_VOL_COLUMNS]


def rates_vol_flat_months(
    cfg: dict, processed: Path | None = None, method: str = EXPANDING
) -> tuple[pd.Series, pd.DataFrame]:
    """``(date -> flat, the check table)``; the flag at ``t`` flattens the book **at** ``t``.

    "Flat for ``t -> t+1``" is the holding period of the positions dated
    ``t``, so the flagged month is the month whose positions are removed.
    """
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    changes = pca.monthly_changes_bp(zero, cfg)
    table = rates_vol_flags(pooled_pc1_scores(changes, cfg), cfg, method)
    flat = pd.Series(table["triggers"].to_numpy(dtype=bool), index=pd.DatetimeIndex(table["date"]))
    return flat, table


# ---------------------------------------------------------- applying them


def apply_control(
    control: str,
    positions: pd.DataFrame,
    base_monthly: pd.DataFrame,
    cfg: dict,
    processed: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(transformed positions, the control's own per-month table)``."""
    r = base_monthly.set_index("date")["r_net"].sort_index()
    out = positions.copy()
    if control == VOL_TARGET:
        scale = vol_target_scale(r, cfg)
        factor = out["date"].map(scale).fillna(1.0)
        out["weight"] = out["weight"] * factor
        out["wd"] = out["wd"] * factor
        table = scale.rename("scale").reset_index()
        return out, table
    if control == DD_STOP:
        flat = dd_stop_flat_months(r, cfg)
        keep = ~out["date"].map(flat).fillna(False).to_numpy(dtype=bool)
        return out[keep].reset_index(drop=True), flat.rename("flat").reset_index()
    if control in METHOD:
        flat, table = rates_vol_flat_months(cfg, processed, METHOD[control])
        keep = ~out["date"].map(flat).fillna(False).to_numpy(dtype=bool)
        return out[keep].reset_index(drop=True), table
    raise KeyError(f"unknown risk control {control!r}; known: {CONTROLS}")


# ------------------------------------------------------ the 2022 attribution


def attribution_rows(
    pieces: pd.DataFrame, monthly: pd.DataFrame, year: int = ATTRIBUTION_YEAR
) -> pd.DataFrame:
    """Per month of ``year``: one row per country and leg, plus a ``country = ALL`` row.

    ``hedge`` is the ``funding + fx`` pair, which is identically zero on a
    hedged variant and is the whole currency story on an unhedged one. The
    month's cost is allocated pro rata to ``|wd|``; a month whose book is
    empty carries its cost on the ``ALL`` row alone.
    """
    p = pieces.copy()
    p["date"] = pd.to_datetime(p["date"])
    p = p[p["date"].dt.year == year]
    m = monthly.copy()
    m["date"] = pd.to_datetime(m["date"])
    m = m[m["date"].dt.year == year]
    weight = p.merge(m[["date", "cost", "r_net"]], on="date", how="left", suffixes=("", "_month"))
    # the pieces frame has no wd; |weight| * duration is wd up to sign, and the
    # allocation only needs a non-negative size, so |weight| is used directly
    size = weight["weight"].abs()
    total_size = weight.groupby("date")["weight"].transform(lambda s: s.abs().sum())
    weight["cost_alloc"] = np.where(total_size > 0, -weight["cost"] * size / total_size, 0.0)
    weight["hedge"] = weight["funding"] + weight["fx"]

    grouped = weight.groupby(["date", "country", "leg"], as_index=False).agg(
        carry_earned=("carry_earned", "sum"),
        yield_change_pnl=("yield_change_pnl", "sum"),
        hedge=("hedge", "sum"),
        cost=("cost_alloc", "sum"),
    )
    rows = [grouped]
    allocated = weight.groupby("date", as_index=False)["cost_alloc"].sum()
    every = m[["date", "cost", "r_net"]].merge(allocated, on="date", how="left")
    every["cost_alloc"] = every["cost_alloc"].fillna(0.0)
    totals = weight.groupby("date", as_index=False).agg(
        carry_earned=("carry_earned", "sum"),
        yield_change_pnl=("yield_change_pnl", "sum"),
        hedge=("hedge", "sum"),
    )
    every = every.merge(totals, on="date", how="left").fillna(
        {"carry_earned": 0.0, "yield_change_pnl": 0.0, "hedge": 0.0}
    )
    every["country"] = ALL_COUNTRIES
    every["leg"] = ALL_LEGS
    # the ALL row carries the whole month's cost, allocated or not
    every["cost"] = -every["cost"]
    rows.append(every[["date", "country", "leg", *ATTRIBUTION_COLUMNS[3:6], "cost"]])

    out = pd.concat(rows, ignore_index=True)
    out["total"] = out[ATTRIBUTION_COLUMNS[3:7]].sum(axis=1)
    out = out.sort_values(["date", "country", "leg"]).reset_index(drop=True)
    return out[ATTRIBUTION_COLUMNS]


def attribution_2022(
    cfg: dict, variant: str, processed: Path | None = None, checks_dir: Path | None = None
) -> pd.DataFrame:
    """``data/checks/attribution_2022_<variant>.csv`` from the 6.1 pieces."""
    from curvecarry import backtest

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    cdir = Path(checks_dir) if checks_dir is not None else checks.CHECKS
    spec = backtest.VARIANTS[variant]
    positions = pd.read_parquet(cdir / f"positions_{variant}.parquet")
    monthly = pd.read_parquet(p / f"backtest_{variant}.parquet")
    returns = pd.read_parquet(p / "returns.parquet")
    carry = pd.read_parquet(p / "carry.parquet")
    pieces = decomposition.position_pieces(positions, returns, carry, spec.returns_column)
    table = attribution_rows(pieces, monthly)
    cdir.mkdir(parents=True, exist_ok=True)
    out = table.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
    out.to_csv(cdir / f"attribution_2022_{variant}.csv", index=False, lineterminator="\n")
    return table


# ------------------------------------------- the runs, and the summary table


def run_risk_controls(cfg: dict, note: str = "", **kwargs) -> list:
    """Every control on every base variant, each as its own logged run."""
    from curvecarry import backtest

    out = []
    for base in cfg["risk"]["risk_control_base_variants"]:
        for control in CONTROLS:
            out.append(backtest.run(cfg, variant_name(base, control), note=note, **kwargs))
    return out


def summary_table(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """Each control against its base, on the columns session-6 amendment 2 names."""
    from curvecarry import metrics

    p = Path(processed) if processed is not None else harmonise.PROCESSED
    starts = {
        "full": pd.Timestamp(cfg["sample"]["strategy_start"]),
        "six": pd.Timestamp(cfg["sample"]["sample_full_start"]),
    }
    rows = []
    for base in cfg["risk"]["risk_control_base_variants"]:
        for name, control in [(base, "")] + [(variant_name(base, c), c) for c in CONTROLS]:
            path = p / f"backtest_{name}.parquet"
            if not path.exists():
                continue
            m = pd.read_parquet(path).set_index("date").sort_index()
            for window, start in starts.items():
                part = m[m.index >= start]
                dd = metrics.max_drawdown(part["r_net"])
                year = part[part.index.year == ATTRIBUTION_YEAR]["r_net"]
                rows.append(
                    {
                        "base": base,
                        "variant": name,
                        "control": control or "(base)",
                        "window": window,
                        "ann_return": metrics.annualised_return(part["r_net"]),
                        "ann_vol": metrics.annualised_vol(part["r_net"]),
                        "sharpe": metrics.sharpe(part["r_net"]),
                        "max_dd": dd.depth,
                        "ret_2022": metrics.annualised_return(year),
                        "turnover": metrics.turnover_mean(part["turnover"]),
                        "months_flat": int((part["n_long"] + part["n_short"] == 0).sum()),
                    }
                )
    return pd.DataFrame(rows, columns=RISK_CONTROL_COLUMNS)


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step risk_controls``: the 2022 attributions and the summary."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    for variant in cfg["risk"]["risk_control_base_variants"]:
        attribution_2022(cfg, variant, p)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    # both percentile methods, side by side, so the dead threshold and the live
    # one can be read against each other in one file (session-6 amendment 9)
    out = pd.concat(
        [rates_vol_flat_months(cfg, p, method)[1] for method in (EXPANDING, ROLLING)],
        ignore_index=True,
    )
    out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
    out.to_csv(checks.RATES_VOL_FILTER, index=False, lineterminator="\n")
    table = summary_table(cfg, p)
    table.to_csv(checks.RISK_CONTROLS, index=False, lineterminator="\n")
    return table
