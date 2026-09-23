"""Step 2.4: Chart 1 (fitted against observed, and RMSE by month) and Chart 3 (the betas).

Matplotlib on the ``Agg`` backend — no display, no interactivity, deterministic
files. Every function takes frames and an output directory, writes one or more
pngs, and returns the paths it wrote. Nothing here reads a file itself except
``build``, so each chart can be tested on a synthetic frame.

**Chart 3 is the amended one** (issue #14, option K; ``decisions/lambda_bound.md``).
Its top row is the ``ns_dl`` betas, at the fixed ``config.nelson_siegel.ns_lambda_fixed``:
with a free lambda the betas are coefficients on loadings whose shape changes
every month, so the same numeric value in two months is not the same quantity
and the series is not comparable across time or countries. Fixing lambda is
what makes it comparable, and is why Diebold-Li fix it. The bottom row is the
same three betas from ``ns_free`` with every ``lam_at_bound`` month **left as a
gap** — not clipped, not interpolated, not forward-filled. There is no
percentile clipping anywhere in this module.

Chart 1 and ``chart1_rmse`` are unchanged and keep NS-free: what they measure
is fit quality, which is where a free lambda earns its place.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from curvecarry import checks, harmonise, nelson_siegel  # noqa: E402

FIGURES = Path("reports/figures")
CHART1_DATES_COLUMNS = ["country", "decade", "date"]
CHART3_EXCLUDED_COLUMNS = ["country", "date", "model", "lam", "beta0", "beta1", "beta2"]
BETAS = ["beta0", "beta1", "beta2"]
BETA_LABELS = {"beta0": "beta0 (level)", "beta1": "beta1 (slope)", "beta2": "beta2 (curvature)"}
CHART3_START = pd.Timestamp("1995-01-01")
TENOR_GRID = (1.0, 30.0)  # chart 1 draws the fitted models across the standard tenor range
MODEL_STYLE = {"ns_free": ("NS-free", "tab:blue"), "sv": ("Svensson", "tab:red")}
RMSE_STYLE = {
    "ns_free": ("NS-free", "tab:blue"),
    "ns_dl": ("NS-DL", "tab:orange"),
    "sv": ("Svensson", "tab:red"),
}
DPI = 130


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def chart1_dates(fitted: pd.DataFrame, decades: list[int]) -> pd.DataFrame:
    """One date per country per decade: the last December month end with a fit.

    If a country has no fitted December in a decade, the **earliest fitted month**
    of that country is used instead (PLAN.md 2.4). A decade the country does not
    reach at all still gets that fallback row, so every country has one panel per
    decade and the figures are comparable.
    """
    rows = []
    for country, g in fitted.groupby("country", sort=True):
        dates = pd.DatetimeIndex(sorted(g["date"].unique()))
        first = dates.min()
        for decade in decades:
            dec = dates[(dates.year >= decade) & (dates.year < decade + 10) & (dates.month == 12)]
            rows.append((country, int(decade), dec.max() if len(dec) else first))
    out = pd.DataFrame(rows, columns=CHART1_DATES_COLUMNS)
    return out.sort_values(["country", "decade"]).reset_index(drop=True)


def fitted_curve(
    params: pd.DataFrame, country: str, date: pd.Timestamp, model: str, tau: np.ndarray
) -> np.ndarray | None:
    """The fitted model evaluated at arbitrary maturities, from its parameter row.

    Chart 1 draws the model as a **curve**, not as a polyline through the 8
    fitted tenors: what the chart is for is showing the shape the model puts
    between the observed points, and joining the nodes with straight segments
    would draw linear interpolation instead of Nelson-Siegel or Svensson.
    """
    g = params[
        (params["country"] == country)
        & (params["date"] == pd.Timestamp(date))
        & (params["model"] == model)
    ]
    if g.empty:
        return None
    return nelson_siegel.fitted_at(g.iloc[0], tau)


def chart1_fit(
    zero_panel: pd.DataFrame,
    params: pd.DataFrame,
    dates: pd.DataFrame,
    out_dir: Path = FIGURES,
) -> list[Path]:
    """One figure per country, 4 panels: observed standard tenors, NS-free, Svensson."""
    out_dir = Path(out_dir)
    obs = nelson_siegel.standard_points(zero_panel)
    grid = np.linspace(*TENOR_GRID, 300)
    paths = []
    for country, d in dates.groupby("country", sort=True):
        d = d.sort_values("decade")
        fig, axes = plt.subplots(1, len(d), figsize=(4.2 * len(d), 3.6), sharey=False)
        axes = np.atleast_1d(axes)
        for ax, (_, row) in zip(axes, d.iterrows(), strict=True):
            date = pd.Timestamp(row["date"])
            o = obs[(obs["country"] == country) & (obs["date"] == date)].sort_values("tenor_years")
            ax.plot(
                o["tenor_years"],
                o["yield"] * 100,
                "o",
                color="black",
                markersize=5,
                label="observed zero",
                zorder=3,
            )
            for model, (label, colour) in MODEL_STYLE.items():
                y = fitted_curve(params, country, date, model, grid)
                if y is not None:
                    ax.plot(grid, y * 100, "-", color=colour, linewidth=1.3, label=label)
            ax.set_title(f"{country} {date.date()}", fontsize=10)
            ax.set_xlabel("tenor (years)")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("zero yield (%)")
        axes[0].legend(fontsize=8, loc="best")
        fig.suptitle(
            f"Chart 1 — {country}: fitted against observed zero curve, "
            "one month per decade (last December with a fit)",
            fontsize=11,
        )
        paths.append(_save(fig, out_dir / f"chart1_fit_{country.lower()}.png"))
    return paths


def chart1_rmse(params: pd.DataFrame, out: Path = FIGURES / "chart1_rmse.png") -> Path:
    """6 panels, one per country: in-sample RMSE (bp) by month, the three models."""
    countries = sorted(params["country"].unique())
    fig, axes = plt.subplots(3, 2, figsize=(13, 10), sharex=False)
    for ax, country in zip(axes.ravel(), countries, strict=False):
        g = params[params["country"] == country]
        for model, (label, colour) in RMSE_STYLE.items():
            m = g[g["model"] == model].sort_values("date")
            if not m.empty:
                ax.plot(m["date"], m["rmse_bp"], "-", color=colour, linewidth=0.8, label=label)
        ax.set_title(country, fontsize=10)
        ax.set_ylabel("RMSE (bp)")
        ax.set_yscale("log")
        ax.grid(alpha=0.3)
    for ax in axes.ravel()[len(countries) :]:
        ax.set_visible(False)
    axes.ravel()[0].legend(fontsize=8, loc="best")
    fig.suptitle(
        "Chart 1b — in-sample fit RMSE by month, 8 standard tenors (log scale). "
        "NS-free keeps its free lambda here: this panel measures fit quality.",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return _save(fig, Path(out))


def chart3_excluded(ns_params: pd.DataFrame, start: pd.Timestamp = CHART3_START) -> pd.DataFrame:
    """The ``ns_free`` months Chart 3's lower row leaves as gaps (issue #14, option K)."""
    f = ns_params[
        (ns_params["model"] == "ns_free")
        & ns_params["lam_at_bound"].astype(bool)
        & (ns_params["date"] >= start)
    ]
    out = f[["country", "date", "model", "lam", *BETAS]].copy()
    return out.sort_values(["country", "date"]).reset_index(drop=True)


def chart3_series(
    ns_params: pd.DataFrame, country: str, model: str, beta: str
) -> tuple[pd.Series, np.ndarray]:
    """``(dates, values)`` for one Chart 3 line; NaN at every ``lam_at_bound`` month.

    NaN rather than a dropped row, so matplotlib breaks the line there instead
    of drawing a straight segment across the gap. Only ``ns_free`` is gapped:
    ``ns_dl`` has a fixed lambda and never hits a bound (issue #14, option K).
    """
    g = ns_params[(ns_params["country"] == country) & (ns_params["model"] == model)].sort_values(
        "date"
    )
    y = g[beta].to_numpy(dtype="float64").copy()
    if model == "ns_free":
        y[g["lam_at_bound"].astype(bool).to_numpy()] = np.nan  # a gap, not a clip
    return g["date"], y


def chart3_betas(
    ns_params: pd.DataFrame,
    out: Path = FIGURES / "chart3_betas.png",
    start: pd.Timestamp = CHART3_START,
) -> tuple[Path, pd.DataFrame]:
    """6 panels: NS-DL betas on top (the primary series), NS-free with gaps below.

    Returns ``(path, excluded)``. A ``lam_at_bound`` month is dropped from the
    NS-free series and the line is broken there — ``NaN`` rather than a missing
    row, so matplotlib leaves a gap instead of drawing across it.
    """
    p = ns_params[ns_params["date"] >= pd.Timestamp(start)]
    countries = sorted(p["country"].unique())
    colours = dict(zip(countries, plt.cm.tab10.colors, strict=False))
    excluded = chart3_excluded(ns_params, start)
    gaps = excluded.groupby("country").size().reindex(countries, fill_value=0)

    fig, axes = plt.subplots(2, 3, figsize=(16, 8), sharex=True)
    for j, beta in enumerate(BETAS):
        for i, model in enumerate(("ns_dl", "ns_free")):
            ax = axes[i, j]
            for country in countries:
                dates, y = chart3_series(p, country, model, beta)
                if len(dates) == 0:
                    continue
                ax.plot(dates, y * 100, "-", color=colours[country], linewidth=0.9, label=country)
            ax.grid(alpha=0.3)
            ax.set_ylabel(f"{BETA_LABELS[beta]} (%)" if j == 0 else "")
            head = (
                "NS-DL (fixed lambda)" if model == "ns_dl" else "NS-free (gaps at a lambda bound)"
            )
            ax.set_title(f"{head} — {beta}", fontsize=10)
    axes[0, 0].legend(fontsize=8, ncol=2, loc="best")
    caption = ", ".join(f"{c} {int(n)}" for c, n in gaps.items())
    fig.suptitle(
        "Chart 3 — Nelson-Siegel betas from 1995. Top row NS-DL at fixed lambda: the "
        "comparable series, because a free lambda changes the loadings each month.\n"
        "Bottom row NS-free, with lam_at_bound months left as gaps (not clipped, not "
        f"interpolated). Months gapped: {caption}. Listed in data/checks/chart3_excluded.csv.",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, Path(out)), excluded


def build(cfg: dict, processed: Path | None = None, out_dir: Path = FIGURES) -> list[Path]:
    """CLI ``report --charts 1,3``: the 8 pngs and the two check files."""
    p = Path(processed) if processed is not None else harmonise.PROCESSED
    zero = pd.read_parquet(p / "curves_zero.parquet")
    ns_params = pd.read_parquet(p / "ns_params.parquet")
    sv_params = pd.read_parquet(p / "sv_params.parquet")
    fitted = pd.read_parquet(p / "ns_fitted.parquet")
    params = pd.concat([ns_params, sv_params], ignore_index=True)

    dates = chart1_dates(fitted, list(cfg["report"]["chart1_decades"]))
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    dates.to_csv(checks.CHART1_DATES, index=False, lineterminator="\n")
    paths = chart1_fit(zero, params, dates, out_dir)
    paths.append(chart1_rmse(params, Path(out_dir) / "chart1_rmse.png"))
    path3, excluded = chart3_betas(ns_params, Path(out_dir) / "chart3_betas.png")
    excluded.to_csv(checks.CHART3_EXCLUDED, index=False, lineterminator="\n")
    paths.append(path3)
    return paths
