"""Step 6.4: ``reports/results.md``, and the block that is pasted into the README.

**No number in `README.md` is typed by hand** (global rule 8). The block
between `<!-- results:begin -->` and `<!-- results:end -->` in the README is
character for character the block between the same two markers in
`reports/results.md`, and `test_readme_results_equal_results_md` asserts it.
`write` produces both files from the same string, so they cannot drift.

**The deflated Sharpe is recomputed with the final `N`** (session-6 amendment
3). `metrics_table` takes `N` from `speclog.count_runs()` at the moment the
report is written, so every Phase 6 run — the six risk controls above all — is
in it. A DSR quoted from an earlier session's smaller `N` flatters the result,
and quoting one is a reporting error, not a rounding difference.
`tests/test_report.py` asserts the `N` printed here equals
`speclog.count_runs()` and is at least the count Phase 5 left behind.

**It is a probability, not a Sharpe** (session-5 fix 3), and where the
headline does not clear the usual bar the README says so **in its own
sentence** and not in a footnote (session-6 amendment 3).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

from curvecarry import backtest, caveats, checks, harmonise, report, speclog

RESULTS = Path("reports/results.md")
README = Path("README.md")
BEGIN = "<!-- results:begin -->"
END = "<!-- results:end -->"

DSR_BAR = 0.95  # the conventional bar; a DSR below it does not clear it
PHASE_5_RUNS = 11  # the runs session 5 left behind; N may never be smaller

YEAR_COLUMNS = ["year", "n_months", "r_net", "carry_earned", "yield_change_pnl", "cost"]
YEAR_HEADER = "| year | months | net return | carry earned | yield-change PnL | cost |"
YEAR_RULE = "|---|---:|---:|---:|---:|---:|"
RUNS_HEADER = "| # | label | logged at (UTC) | config hash | what it overrides |"
RUNS_RULE = "|---|---|---|---|---|"


def git_commit() -> str:
    """The short commit the report was written at, or ``unknown`` outside a checkout."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


# ------------------------------------------------- the per-year headline table


def year_rows(monthly: pd.DataFrame, decomposition: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One row per calendar year of the headline book, with the 6.1 pieces beside it.

    The year figure is the **sum** of the monthly returns, not a compounded
    one, so that it adds up with the decomposition pieces printed next to it -
    the same arithmetic basis every other return in this report uses.
    """
    start = pd.Timestamp(cfg["sample"]["strategy_start"])
    m = monthly.copy()
    m["date"] = pd.to_datetime(m["date"])
    m = m[m["date"] >= start]
    d = decomposition.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] >= start]
    joined = m[["date", "r_net"]].merge(
        d[["date", "carry_earned", "yield_change_pnl", "cost"]], on="date", how="left"
    )
    joined["year"] = joined["date"].dt.year
    out = joined.groupby("year", as_index=False).agg(
        n_months=("date", "size"),
        r_net=("r_net", "sum"),
        carry_earned=("carry_earned", "sum"),
        yield_change_pnl=("yield_change_pnl", "sum"),
        cost=("cost", "sum"),
    )
    return out[YEAR_COLUMNS]


def year_table_md(years: pd.DataFrame) -> str:
    lines = [YEAR_HEADER, YEAR_RULE]
    for _, r in years.iterrows():
        lines.append(
            f"| {int(r['year'])} | {int(r['n_months'])} | {r['r_net']:.2%} | "
            f"{r['carry_earned']:.2%} | {r['yield_change_pnl']:.2%} | {r['cost']:.2%} |"
        )
    total = years[["r_net", "carry_earned", "yield_change_pnl", "cost"]].sum()
    lines.append(
        f"| **all** | **{int(years['n_months'].sum())}** | **{total['r_net']:.2%}** | "
        f"**{total['carry_earned']:.2%}** | **{total['yield_change_pnl']:.2%}** | "
        f"**{total['cost']:.2%}** |"
    )
    return "\n".join(lines) + "\n"


# ------------------------------------------------------- the logged-run table


def runs_table_md(spec_path: Path | None = None) -> str:
    """Every row of ``reports/specifications.csv``, in the order it was logged."""
    path = Path(spec_path) if spec_path is not None else Path(speclog.DEFAULT_PATH)
    rows = pd.read_csv(path, keep_default_na=False)
    lines = [RUNS_HEADER, RUNS_RULE]
    for i, r in enumerate(rows.itertuples(), start=1):
        note = str(r.note).replace("|", "\\|") or "(the base definition)"
        lines.append(
            f"| {i} | `{r.label}` | {str(r.timestamp_utc)[:19]} | `{r.config_hash}` | {note} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the block


def dsr_sentences(table: pd.DataFrame, headline: str) -> str:
    """The DSR in words: what it is, its threshold, its N, and whether it clears the bar."""
    row = table[(table["variant"] == headline) & (table["window"] == "full")].iloc[0]
    dsr = float(row["dsr"])
    sr0 = float(row["sr0"])
    n = int(row["n_trials"])
    sharpe = float(row["sharpe"])
    verdict = (
        f"**That does not clear the usual bar.** A deflated Sharpe is conventionally "
        f"read as clearing it at about {DSR_BAR:.2f}, and {dsr:.3f} is below that: "
        f"after {n} trials, the evidence that this book's true Sharpe is above the "
        f"selection threshold is weak."
        if dsr < DSR_BAR
        else f"**That clears the usual bar of about {DSR_BAR:.2f}.**"
    )
    return (
        f"The headline's annualised Sharpe is {sharpe:.3f}. Its **deflated Sharpe is "
        f"{dsr:.3f}**, and that number is **a probability, not a Sharpe ratio**: it is "
        f"the probability that the true Sharpe exceeds the multiple-testing threshold "
        f"SR0 = {sr0:.3f} on a monthly basis, which is the Sharpe that {n} trials would "
        f"be expected to produce by selection alone. N = {n} is the row count of "
        f"`reports/specifications.csv` at the moment this report was written, and every "
        f"run this project logged is in it.\n\n"
        f"{verdict}\n"
    )


def _date(value) -> str:
    """A config date as ``YYYY-MM-DD``; the TOML loader hands back a date object."""
    return pd.Timestamp(value).date().isoformat()


def results_block(cfg: dict, table: pd.DataFrame, years: pd.DataFrame, spec_path=None) -> str:
    """The block the README and the report share, character for character."""
    headline = backtest.HEADLINE
    row = table[(table["variant"] == headline) & (table["window"] == "full")].iloc[0]
    start = _date(cfg["sample"]["strategy_start"])
    end = _date(cfg["sample"]["strategy_end"])
    six = _date(cfg["sample"]["sample_full_start"])
    n_runs = int(row["n_trials"])
    return (
        f"### The headline\n\n"
        f"The headline result of this project is the **carry-only, hedged, book-wide "
        f"duration-neutral book, net of costs**, from {start} to {end}, on the universe "
        f"available each month: the `{headline}` variant, `full` window, `r_net`. It was "
        f"fixed before any result was seen. Everything else in the tables below is a "
        f"logged variant and is reported whether it helps or not.\n\n"
        f"It returned **{row['ann_return']:.2%} a year** at **{row['ann_vol']:.2%}** "
        f"annualised volatility, a Sharpe of **{row['sharpe']:.3f}**, a worst drawdown of "
        f"**{row['max_dd']:.2%}** ({row['dd_peak']} to {row['dd_trough']}) and "
        f"**{row['ret_2022']:.2%}** in 2022, over {int(row['n_months'])} months.\n\n"
        f"**The decomposition is the deliverable, not the Sharpe.** The per-year table "
        f"below splits every year into the carry it earned, the yield-change PnL it paid "
        f"for, and its costs; the four pieces sum to the reported return to 1e-10 in "
        f"every month.\n\n"
        f"### The headline book, year by year\n\n"
        f"{year_table_md(years)}\n"
        f"### Every logged variant, both windows\n\n"
        f"Windows: `full` from {start}, `six` from {six} (the first month all six "
        f"countries are present).\n\n"
        f"{report.metrics_table_md(table)}\n"
        f"### The deflated Sharpe\n\n"
        f"{dsr_sentences(table, headline)}\n"
        f"### Every logged run\n\n"
        f"{n_runs} runs, each logged in `reports/specifications.csv` **before** it "
        f"computed. A variant with no row did not happen.\n\n"
        f"{runs_table_md(spec_path)}"
    )


# ------------------------------------------------------------ the whole report


def read_block(text: str) -> str:
    """The text between the two markers, exclusive, stripped of the edge newlines."""
    before = text.index(BEGIN) + len(BEGIN)
    return text[before : text.index(END)].strip("\n")


def replace_block(text: str, block: str) -> str:
    before = text[: text.index(BEGIN) + len(BEGIN)]
    after = text[text.index(END) :]
    return f"{before}\n{block}\n{after}"


def report_text(cfg: dict, block: str, section: str, checks_dir: Path) -> str:
    """The whole of ``reports/results.md``: the shared block, then everything else."""
    c = Path(checks_dir)
    explained = (c / checks.PCA_EXPLAINED_TABLE.name).read_text(encoding="utf-8")
    stability = pd.read_csv(c / checks.PCA_STABILITY.name)
    shares = pd.read_csv(c / checks.DECOMPOSITION_SHARES.name)
    risk = pd.read_csv(c / checks.RISK_CONTROLS.name)
    a2022 = pd.read_csv(c / f"attribution_2022_{backtest.HEADLINE}.csv")
    figures = sorted(p.name for p in Path("reports/figures").glob("*.png"))
    return (
        f"# Results\n\n"
        f"Written at commit `{git_commit()}`, config hash "
        f"`{speclog.config_hash(cfg)}`.\n\n"
        f"Every number below is produced by `uv run curvecarry report`. The block "
        f"between the two markers is pasted into `README.md` verbatim and a test "
        f"asserts the two are equal.\n\n"
        f"{BEGIN}\n{block}\n{END}\n\n"
        f"## The decomposition\n\n"
        f"`data/checks/decomposition_shares.csv`, headline book. `cumulative` is the "
        f"sum of the monthly piece over the window; `share` is its fraction of the "
        f"summed `r_net`.\n\n"
        f"{_md(shares[shares['variant'] == backtest.HEADLINE])}\n"
        f"## 2022, month by month\n\n"
        f"`data/checks/attribution_2022_{backtest.HEADLINE}.csv`, the `ALL` rows; the "
        f"per-country and per-leg rows are in the file.\n\n"
        f"{_md(a2022[a2022['country'] == 'ALL'])}\n"
        f"## The three pre-registered risk controls\n\n"
        f"Each is its own logged run, applied to the base book named in "
        f"`config.risk.risk_control_base_variants`, and each is reported whether it "
        f"helps or not. None of them is the headline.\n\n"
        f"{_md(risk)}\n"
        f"## PCA: explained variance\n\n{explained}\n"
        f"## PCA: loading stability by decade\n\n{_md(stability)}\n"
        f"{section}\n"
        f"## Charts\n\n" + "".join(f"- `reports/figures/{name}`\n" for name in figures)
    )


FLOAT_PLACES = 6


def _cell(value) -> str:
    if isinstance(value, float):
        return f"{value:.{FLOAT_PLACES}f}"
    return str(value).replace("|", "\\|")


def _md(frame: pd.DataFrame) -> str:
    """A DataFrame as a markdown table, floats to six places.

    Written here rather than through ``DataFrame.to_markdown`` so the report
    does not add ``tabulate`` to the lockfile for one call.
    """
    lines = [
        "| " + " | ".join(str(c) for c in frame.columns) + " |",
        "|" + "|".join("---" for _ in frame.columns) + "|",
    ]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join(_cell(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def write(cfg: dict, processed: Path | None = None, checks_dir: Path | None = None) -> Path:
    """``reports/results.md`` and the README block, from one string. Step 6.4."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    c = Path(checks_dir) if checks_dir is not None else checks.CHECKS

    table = report.write_metrics_table(cfg, p)
    caveats.write_section(cfg, c, p)
    section = (c / checks.SECTION_6_3.name).read_text(encoding="utf-8")

    monthly = pd.read_parquet(p / f"backtest_{backtest.HEADLINE}.parquet")
    decomposition = pd.read_parquet(p / f"decomposition_{backtest.HEADLINE}.parquet")
    years = year_rows(monthly, decomposition, cfg)

    # rstrip so the block round-trips through ``read_block`` unchanged: the runs
    # table ends in a newline and the markers add their own
    block = results_block(cfg, table, years).rstrip("\n")
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(report_text(cfg, block, section, c), encoding="utf-8", newline="\n")
    README.write_text(
        replace_block(README.read_text(encoding="utf-8"), block), encoding="utf-8", newline="\n"
    )
    return RESULTS
