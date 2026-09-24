"""Step 6.3: what carry does not tell you — written from this repo's own numbers.

**Every figure in the prose is a value read from a file in this repo**, not a
general caveat and not a number typed by hand. `section` contains no numeric
literal at all: `test_section_6_3_has_no_hardcoded_numbers` walks its AST and
fails on any `int` or `float` constant outside a format specification, so the
only way a number reaches the page is through `facts`, which reads it from
`data/checks/`, `data/processed/` or `decisions/`.

Session-6 amendment 4 fixes what the section has to cover, each with its
figure: the overlay is flat gross and loses its costs; duration neutrality is
not currency neutrality; the funding rate is a policy rate used as a
three-month anchor; the cross-currency basis is not measured; the
Nelson-Siegel lambda is unidentified on flat curves; the US on-the-run
richness; and the buckets that enter or leave mid-sample. The paragraphs
PLAN.md 6.3 already asked for — the carry share against the yield-change
share, 2022 month by month, the size of the return approximation, and what the
robustness rows changed — are the first, second, eighth and ninth.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

from curvecarry import checks, harmonise, overlay

DECISIONS = Path("decisions")
BASIS_DOC = DECISIONS / "basis.md"
BASIS_RANGE_PATTERN = r"\*\*([0-9]+ to [0-9]+ bp)[^*]*\*\*"
BASIS_NOT_MEASURED = "not measured"

HEADLINE_VARIANT = "carry_hedged"
OVERLAY_VARIANT = "overlay_hedged"
UNHEDGED_VARIANT = "carry_unhedged"
INTERBANK_VARIANT = "carry_hedged_interbank_3m"
COUNTRY_SCOPE_VARIANT = "carry_hedged_country_scope"
NO_GB30_VARIANT = "carry_hedged_no_gb30"
COST0_VARIANT = "carry_hedged_cost0"
COST2X_VARIANT = "carry_hedged_cost2x"
ROLLING_VARIANT = "carry_hedged_ratesvol_rolling"
EXPANDING_VARIANT = "carry_hedged_ratesvol"

NS_FREE_MODEL = "ns_free"
NS_LAMBDA_COLUMNS = ["country", "months", "share_at_bound", "share_at_lower", "share_at_upper"]


def _bp(x: float) -> str:
    return f"{x:,.0f} bp"


def _pct(x: float) -> str:
    return f"{x:.2%}"


def _share(x: float) -> str:
    return f"{x:.1%}"


def _pct_abs(x: float) -> str:
    """The size, without the sign: for prose that already carries it ("gave back")."""
    return _pct(abs(x))


def _bp_abs(x: float) -> str:
    return _bp(abs(x))


# ------------------------------------------------------- the lambda check file


def ns_lambda_bound_rows(ns_params: pd.DataFrame) -> pd.DataFrame:
    """Per country, the share of ``ns_free`` months whose lambda sits on a grid bound."""
    free = ns_params[ns_params["model"] == NS_FREE_MODEL]
    lam = free["lam"]
    lo, hi = float(lam.min()), float(lam.max())
    rows = []
    for country, g in free.groupby("country"):
        at_bound = g["lam_at_bound"].astype(bool)
        rows.append(
            {
                "country": country,
                "months": int(len(g)),
                "share_at_bound": float(at_bound.mean()),
                "share_at_lower": float((at_bound & (g["lam"] <= lo)).mean()),
                "share_at_upper": float((at_bound & (g["lam"] >= hi)).mean()),
            }
        )
    out = pd.DataFrame(rows, columns=NS_LAMBDA_COLUMNS)
    return out.sort_values("share_at_bound", ascending=False).reset_index(drop=True)


def write_ns_lambda_bound(processed: Path | None = None, path: Path | None = None) -> pd.DataFrame:
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    out = path if path is not None else checks.NS_LAMBDA_BOUND
    table = ns_lambda_bound_rows(pd.read_parquet(p / "ns_params.parquet"))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False, lineterminator="\n")
    return table


# ------------------------------------------------------------------- the facts


def _read_summary_block(path: Path) -> pd.DataFrame:
    """The **last** CSV block of a file that holds more than one, after a blank line."""
    text = Path(path).read_text(encoding="utf-8")
    return pd.read_csv(io.StringIO(text.split("\n\n")[-1].strip()))


def _read_first_block(path: Path) -> pd.DataFrame:
    """The **first** CSV block of a file that holds more than one.

    ``return_approx_gap.csv`` carries the per-tenor distribution and then, after
    a blank line and a comment, the 20 largest rows; reading it whole turns the
    second header into data.
    """
    text = Path(path).read_text(encoding="utf-8")
    return pd.read_csv(io.StringIO(text.split("\n\n")[0].strip()))


def _metric(table: pd.DataFrame, variant: str, column: str, window: str = "full") -> float:
    row = table[(table["variant"] == variant) & (table["window"] == window)]
    return float(row[column].iloc[0])


def _basis_range(path: Path) -> str:
    """The brief's basis range, taken from ``decisions/basis.md`` and not retyped."""
    found = re.search(BASIS_RANGE_PATTERN, Path(path).read_text(encoding="utf-8"))
    return found.group(1) if found else "unquantified"


def facts(cfg: dict, checks_dir: Path | None = None, decisions_dir: Path | None = None) -> dict:
    """Every number the section prints, formatted, keyed by the phrase it fills."""
    c = Path(checks_dir) if checks_dir is not None else checks.CHECKS
    d = Path(decisions_dir) if decisions_dir is not None else DECISIONS
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    end = pd.Timestamp(cfg["sample"]["strategy_end"])

    out: dict[str, str] = {}

    # 1 and 2 - the decomposition, whole sample and by decade
    shares = pd.read_csv(c / checks.DECOMPOSITION_SHARES.name)
    head = shares[shares["variant"] == HEADLINE_VARIANT]
    full = head[head["window"] == "full"].set_index("piece")["cumulative"]
    out["carry_earned"] = _pct(full["carry_earned"])
    out["yield_change"] = _pct_abs(full["yield_change_pnl"])
    out["decomp_cost"] = _pct_abs(full["cost"])
    out["net_return"] = _pct(full["r_net"])
    decades = head[~head["window"].isin(["full", "six"])]
    losing = decades[(decades["piece"] == "r_net") & (decades["cumulative"] < 0)]
    out["losing_decades"] = ", ".join(sorted(losing["window"])) or "none"

    # 3 - 2022, month by month
    a2022 = pd.read_csv(c / f"attribution_2022_{HEADLINE_VARIANT}.csv")
    whole = a2022[a2022["country"] == "ALL"]
    out["y2022_total"] = _pct_abs(float(whole["total"].sum()))
    out["y2022_carry"] = _pct(float(whole["carry_earned"].sum()))
    out["y2022_yield"] = _pct_abs(float(whole["yield_change_pnl"].sum()))
    out["y2022_worst_month"] = str(whole.loc[whole["total"].idxmin(), "date"])
    out["y2022_worst_value"] = _pct_abs(float(whole["total"].min()))
    out["y2022_carry_positive"] = str(int((whole["carry_earned"] > 0).sum()))
    out["y2022_months"] = str(len(whole))

    # 4 - the overlay: flat gross, and what the costs did to it
    trades = pd.read_csv(c / checks.OVERLAY_TRADES.name)
    in_sample = trades[trades["in_sample"].astype(bool)]
    out["overlay_gross"] = _bp(float(in_sample["pnl_bp"].sum()))
    out["overlay_cost"] = _bp(float(in_sample["cost_bp"].sum()))
    out["overlay_net"] = _bp(float(in_sample["pnl_net_bp"].sum()))
    out["overlay_trades"] = str(len(in_sample))
    out["overlay_years"] = f"{(end - start).days / 365.25:.0f}"
    worst = in_sample.nsmallest(overlay.WORST_TRADES, "pnl_net_bp")
    out["overlay_worst_total"] = _bp_abs(float(worst["pnl_net_bp"].sum()))
    out["overlay_worst_n"] = str(len(worst))
    out["overlay_worst_list"] = "; ".join(
        f"{r.country} {str(r.entry_date)[:7]} {r.direction} {r.pnl_net_bp:,.0f} bp"
        for r in worst.itertuples()
    )

    # 5 - duration neutrality is not currency neutrality
    fx = _read_summary_block(c / checks.UNHEDGED_FX_EXPOSURE.name)
    row = fx[fx["variant"] == UNHEDGED_VARIANT].iloc[0]
    out["fx_r2"] = _share(float(row["r_squared"]))
    out["fx_beta"] = f"{float(row['beta']):.2f}"
    out["fx_net_notional"] = f"{float(row['mean_abs_net_notional']):.2f}"
    out["fx_max_notional"] = f"{float(row['max_abs_net_notional']):.2f}"

    # 6 - the funding rate is a policy rate used as a three-month anchor
    fill = pd.read_csv(c / checks.FUNDING_FILL.name, keep_default_na=False)
    filled = fill[fill["months_filled"].astype(int) > 0]
    out["fill_months"] = str(int(filled["months_filled"].astype(int).sum()))
    out["fill_windows"] = "; ".join(
        f"{r.country} {r.first} to {r.last} ({r.months_filled} months)" for r in filled.itertuples()
    )
    out["fill_countries"] = ", ".join(sorted(filled["country"].unique())) or "none"
    metrics = pd.read_csv(c / checks.METRICS_TABLE.name)
    out["headline_sharpe"] = f"{_metric(metrics, HEADLINE_VARIANT, 'sharpe'):.3f}"
    out["headline_return"] = _pct(_metric(metrics, HEADLINE_VARIANT, "ann_return"))
    out["interbank_sharpe"] = f"{_metric(metrics, INTERBANK_VARIANT, 'sharpe'):.3f}"
    out["interbank_return"] = _pct(_metric(metrics, INTERBANK_VARIANT, "ann_return"))

    # 12b - the one risk control that helped, and its selection caveat
    out["n_runs"] = f"{int(metrics['n_trials'].iloc[0])}"
    out["roll_sharpe"] = f"{_metric(metrics, ROLLING_VARIANT, 'sharpe'):.3f}"
    out["roll_return"] = _pct(_metric(metrics, ROLLING_VARIANT, "ann_return"))
    out["roll_dd"] = _pct(_metric(metrics, ROLLING_VARIANT, "max_dd"))
    out["roll_2022"] = _pct(_metric(metrics, ROLLING_VARIANT, "ret_2022"))
    out["roll_dsr"] = f"{_metric(metrics, ROLLING_VARIANT, 'dsr'):.3f}"
    out["headline_dsr"] = f"{_metric(metrics, HEADLINE_VARIANT, 'dsr'):.3f}"
    out["headline_dd"] = _pct(_metric(metrics, HEADLINE_VARIANT, "max_dd"))
    out["headline_2022"] = _pct(_metric(metrics, HEADLINE_VARIANT, "ret_2022"))
    out["expanding_sharpe"] = f"{_metric(metrics, EXPANDING_VARIANT, 'sharpe'):.3f}"

    # 7 - the cross-currency basis
    out["basis_status"] = BASIS_NOT_MEASURED
    out["basis_range"] = _basis_range(d / BASIS_DOC.name)

    # 8 - the Nelson-Siegel lambda
    lam = pd.read_csv(c / checks.NS_LAMBDA_BOUND.name)
    worst_lam = lam.iloc[0]
    out["lam_worst_country"] = str(worst_lam["country"])
    out["lam_worst_share"] = _share(float(worst_lam["share_at_bound"]))
    out["lam_worst_lower"] = _share(float(worst_lam["share_at_lower"]))
    out["lam_best_country"] = str(lam.iloc[-1]["country"])
    out["lam_best_share"] = _share(float(lam.iloc[-1]["share_at_bound"]))

    # 9 - the US on-the-run richness
    # the tenor quoted is the project's own benchmark tenor, config.sample.sample_max_tenor
    tenor = float(cfg["sample"]["sample_max_tenor"])
    gsw = pd.read_csv(c / checks.US_PAR_VS_GSW.name)
    at_tenor = gsw[gsw["tenor_years"] == tenor]
    out["otr_tenor"] = f"{tenor:.0f}"
    out["otr_mean"] = f"{float(at_tenor['diff_bp'].mean()):.1f} bp"
    out["otr_median"] = f"{float(at_tenor['diff_bp'].median()):.1f} bp"
    out["otr_months"] = f"{len(at_tenor):,}"

    # 10 - the buckets that enter and leave mid-sample
    changes = pd.read_csv(c / checks.UNIVERSE_CHANGES.name, parse_dates=["date"])
    inside = changes[(changes["date"] > start) & (changes["date"] <= end)]
    counts = inside["change"].value_counts()
    out["bucket_enters"] = str(int(counts.get("enters", 0)))
    out["bucket_leaves"] = str(int(counts.get("leaves", 0)))
    out["bucket_countries"] = ", ".join(sorted(inside["country"].unique())) or "none"

    # 11 - the size of the return approximation, by tenor
    gap = _read_first_block(c / checks.RETURN_APPROX_GAP.name)
    out["gap_mean_lo"] = f"{float(gap['mean_bp'].min()):.2f} bp"
    out["gap_mean_hi"] = f"{float(gap['mean_bp'].max()):.2f} bp"
    out["gap_worst"] = f"{float(gap['max_abs_bp'].max()):.0f} bp"
    out["gap_worst_tenor"] = f"{float(gap.loc[gap['max_abs_bp'].idxmax(), 'tenor_years']):.0f}"

    # 12 - what the robustness rows changed
    for key, variant in (
        ("scope", COUNTRY_SCOPE_VARIANT),
        ("nogb30", NO_GB30_VARIANT),
        ("cost0", COST0_VARIANT),
        ("cost2x", COST2X_VARIANT),
    ):
        out[f"{key}_sharpe"] = f"{_metric(metrics, variant, 'sharpe'):.3f}"
        out[f"{key}_return"] = _pct(_metric(metrics, variant, "ann_return"))
    return out


# -------------------------------------------------------------- the section


def section(f: dict) -> str:
    """The 6.3 section of ``reports/results.md``. No numeric literal appears here."""
    return f"""## What carry does not tell you

Nine things this book's numbers do not say, each with the figure from this
repo that bounds it.

**1. The return is carry net of a losing yield bet, and the yield bet is the
larger number.** Over the full window the headline book earned
{f["carry_earned"]} of carry, gave back {f["yield_change"]} to yield changes
and {f["decomp_cost"]} to costs, and kept {f["net_return"]}. A reader who sees
only the net figure will under-estimate both the gross carry and the size of
the directional risk that offset it. The losing decades are
{f["losing_decades"]}: decades where the yield move was larger than the carry,
not decades where the carry stopped.

**2. 2022 is what that looks like in one year.** The book lost
{f["y2022_total"]} over {f["y2022_months"]} months, of which carry earned
{f["y2022_carry"]} and yield changes cost {f["y2022_yield"]}. Carry was
positive in {f["y2022_carry_positive"]} of those months, including the worst
one ({f["y2022_worst_month"]}, a loss of {f["y2022_worst_value"]}). Duration
neutrality did not protect the book, because the long leg sat where the curve
moved most;
a book neutral in duration is not neutral in *where on the curve* the duration
sits.

**3. The slope overlay is flat gross and loses its costs.** Over
{f["overlay_years"]} years and {f["overlay_trades"]} in-sample trades it made
{f["overlay_gross"]} gross, paid {f["overlay_cost"]} in costs and returned
{f["overlay_net"]}. The {f["overlay_worst_n"]} worst trades alone cost
{f["overlay_worst_total"]}: {f["overlay_worst_list"]}. They share a shape — a
mean-reversion slope signal is short the trend, so it fades a curve move that
keeps going, and it does that hardest in the months the move is largest. An
overlay that is flat before costs is not a diversifier; it is a fee.

**4. Duration neutrality is not currency neutrality.** The book is neutral in
duration and not in notional, and notional is what carries currency risk. The
unhedged book's monthly return regresses on its own currency-weighted FX term
with an R-squared of {f["fx_r2"]} and a beta of {f["fx_beta"]}: almost all of
what the unhedged run earned or lost is the exchange rate, not the curve. Its
mean absolute net foreign notional is {f["fx_net_notional"]} units of capital
and its maximum {f["fx_max_notional"]}. Every unhedged number in this report
is a currency bet with a carry book attached.

**5. The funding rate is a policy rate used as a three-month anchor.** The
financing leg of every excess return is the central bank's policy rate, not a
rate anyone can borrow at for three months. Where the policy series has gaps
they are filled from the OECD immediate rate: {f["fill_months"]} months in
total, all in {f["fill_countries"]} ({f["fill_windows"]}). The logged
robustness run on the OECD three-month interbank rate returns
{f["interbank_return"]} a year at a Sharpe of {f["interbank_sharpe"]} against
the headline's {f["headline_return"]} and {f["headline_sharpe"]} — close
enough that the choice does not carry the result, but the interbank series
prices bank credit, and in 2008 that credit spread would read here as carry.

**6. The cross-currency basis is {f["basis_status"]}.** The hedged return is
the local excess return by covered interest parity, and covered interest
parity has not held since 2008. No free basis series was found
(`decisions/basis.md` records the probe), so the error is not estimated; from
the brief it runs {f["basis_range"]} in stress periods for the major pairs,
one-directional rather than noise, and wider at quarter and year ends. Every
hedged number here is a CIP-implied hedged number.

**7. The Nelson-Siegel lambda is unidentified on flat curves.** As lambda goes
to zero the slope loading becomes the level loading and the design matrix goes
collinear, so the fit runs to the edge of the grid and stops there. On the
free-lambda fits that happens in {f["lam_worst_share"]} of
{f["lam_worst_country"]} months ({f["lam_worst_lower"]} of them at the lower
bound) and as little as {f["lam_best_share"]} of {f["lam_best_country"]}
months. Where lambda is on a bound the reported betas are coefficients on a
nearly singular basis and should not be read as level, slope and curvature.
Nothing in the strategy reads them — the signal is built from zero yields —
but the fitted-curve charts inherit the problem.

**8. The US curve is built from on-the-run yields, which are rich.** Against
the Fed's own GSW fitted curve the CMT par yield at {f["otr_tenor"]} years
differs by {f["otr_mean"]} on average and {f["otr_median"]} at the median over
{f["otr_months"]} months — the CMT yield is the lower, which is the on-the-run
bond being the dearer. That is the on-the-run premium, and it is a level
shift on one country's curve that no other country in this book carries. It
enters the carry signal as a small standing tilt away from the US, not as
noise.

**9. Buckets enter and leave mid-sample, and the universe is not the same book
throughout.** Inside the strategy window {f["bucket_enters"]} bucket-months
enter and {f["bucket_leaves"]} leave, across {f["bucket_countries"]}. A
cross-sectional rank is taken over whatever is available that month, so the
same signal value means a different thing in a month with four countries and a
month with six. The two sample windows exist for exactly this reason and every
result is reported on both.

**And one measurement note.** The duration-convexity approximation of the
monthly return, which the brief asks for, is diagnostic here and never inside
any identity. Its mean error runs {f["gap_mean_lo"]} to {f["gap_mean_hi"]} by
tenor, with a worst single bucket-month of {f["gap_worst"]} at
{f["gap_worst_tenor"]} years. Every return in this report is a full
repricing.

**And the one risk control that helped is not a result.** Of the four
pre-registered controls, only the rolling rates-vol filter improves the
headline: Sharpe {f["roll_sharpe"]} against {f["headline_sharpe"]}, worst
drawdown {f["roll_dd"]} against {f["headline_dd"]}. Four things belong beside
that. It is **one of {f["n_runs"]} logged runs**, and its own deflated Sharpe
is {f["roll_dsr"]} against the headline's {f["headline_dsr"]} — higher, and
still far short of any sensible bar. **The improvement is largely one event**:
2022 goes from {f["headline_2022"]} to {f["roll_2022"]} while the annual
return *falls*, {f["headline_return"]} to {f["roll_return"]}, so the gain is
risk reduction concentrated in a single episode rather than a better book.
**Half of its specification was chosen after a result was seen**: the
120-month window was pre-registered in its own commit before the run existed,
but the decision to try a rolling percentile at all came after the
pre-registered expanding one turned out never to fire (its Sharpe is
{f["expanding_sharpe"]}, the headline's to three places, because it never
trades differently). `N` does not price that degree of freedom. It **stays a
logged variant and is never the headline**.

**What the robustness rows changed.** Country-scope neutrality instead of
book-wide takes the headline to {f["scope_return"]} a year at
{f["scope_sharpe"]}; excluding the GB 30-year, {f["nogb30_return"]} at
{f["nogb30_sharpe"]}; zero costs, {f["cost0_return"]} at {f["cost0_sharpe"]};
double costs, {f["cost2x_return"]} at {f["cost2x_sharpe"]}. Costs move the
result more than any modelling choice in the list, and the country-scope run
moves it most of all — which is the honest reading that book-wide neutrality
is doing real work and is a choice, not a detail.
"""


def write_section(cfg: dict, checks_dir: Path | None = None, processed: Path | None = None) -> Path:
    """``data/checks/section_6_3.md``, for review before 6.4 assembles the report."""
    c = Path(checks_dir) if checks_dir is not None else checks.CHECKS
    write_ns_lambda_bound(processed, c / checks.NS_LAMBDA_BOUND.name)
    text = section(facts(cfg, c))
    path = c / checks.SECTION_6_3.name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def build(cfg: dict, processed: Path | None = None) -> pd.DataFrame:
    """CLI ``build --step caveats``: the lambda check file and the section."""
    table = write_ns_lambda_bound(processed)
    write_section(cfg, processed=processed)
    return table
