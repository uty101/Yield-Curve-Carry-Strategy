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
same three betas from ``ns_free`` with every ``ns_degenerate`` month **left as a
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

from curvecarry import checks, harmonise, nelson_siegel, report  # noqa: E402

FIGURES = Path("reports/figures")
CHART1_DATES_COLUMNS = ["country", "decade", "date"]
CHART3_EXCLUDED_COLUMNS = [
    "country",
    "date",
    "model",
    "lam",
    "beta0",
    "beta1",
    "beta2",
    "reason",
]
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
NO_FIT_TEXT = "no fitted months\nin this decade"  # chart 1, a decade the country never reaches


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return path


def chart1_dates(fitted: pd.DataFrame, decades: list[int]) -> pd.DataFrame:
    """One date per country per decade: the last December month end with a fit.

    Where a decade has no fitted December but the country does have fitted months
    in it, that decade's **last fitted month** is used. Where the country has no
    fitted month in the decade at all, **no row is emitted**: the file holds only
    real dates, and ``chart1_fit`` draws an empty panel for the missing decade
    (session 2 fix round; the earlier fallback to the country's earliest month
    put a date in one decade's panel that belonged to another).
    """
    rows = []
    for country, g in fitted.groupby("country", sort=True):
        dates = pd.DatetimeIndex(sorted(g["date"].unique()))
        for decade in decades:
            inside = dates[(dates.year >= decade) & (dates.year < decade + 10)]
            if not len(inside):
                continue
            december = inside[inside.month == 12]
            rows.append((country, int(decade), (december if len(december) else inside).max()))
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
    decades: list[int],
    out_dir: Path = FIGURES,
) -> list[Path]:
    """One figure per country, one panel per decade: observed tenors, NS-free, Svensson.

    A decade with no row in ``dates`` — the country has no fitted month in it —
    gets an empty panel saying so, rather than a repeat of another decade's
    curve. A country with no row for **any** configured decade has no month to
    draw and gets no figure at all.
    """
    out_dir = Path(out_dir)
    obs = nelson_siegel.standard_points(zero_panel)
    grid = np.linspace(*TENOR_GRID, 300)
    paths = []
    for country, d in dates.groupby("country", sort=True):
        by_decade = dict(zip(d["decade"], d["date"], strict=True))
        fig, axes = plt.subplots(1, len(decades), figsize=(4.2 * len(decades), 3.6), sharey=False)
        axes = np.atleast_1d(axes)
        for ax, decade in zip(axes, decades, strict=True):
            if int(decade) not in by_decade:
                ax.set_title(f"{country} {decade}s", fontsize=10)
                ax.text(
                    0.5,
                    0.5,
                    NO_FIT_TEXT,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="grey",
                    transform=ax.transAxes,
                )
                ax.set_xticks([])
                ax.set_yticks([])
                continue
            date = pd.Timestamp(by_decade[int(decade)])
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
        drawn = [ax for ax, dec in zip(axes, decades, strict=True) if int(dec) in by_decade]
        drawn[0].set_ylabel("zero yield (%)")
        drawn[0].legend(fontsize=8, loc="best")  # the first panel that has something in it
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
    """The ``ns_free`` months Chart 3's lower row leaves as gaps, and why.

    ``reason`` is ``bound`` (lambda on a grid bound, betas below the threshold),
    ``beta`` (lambda interior, some |beta| above 50 percentage points) or
    ``both``.
    """
    f = ns_params[
        (ns_params["model"] == "ns_free")
        & ns_params["ns_degenerate"].astype(bool)
        & (ns_params["date"] >= start)
    ]
    out = f[["country", "date", "model", "lam", *BETAS]].copy()
    bound = f["lam_at_bound"].astype(bool).to_numpy()
    beta = np.asarray(nelson_siegel.beta_degenerate(f["beta0"], f["beta1"], f["beta2"]), dtype=bool)
    out["reason"] = np.where(bound & beta, "both", np.where(bound, "bound", "beta"))
    return out[CHART3_EXCLUDED_COLUMNS].sort_values(["country", "date"]).reset_index(drop=True)


def chart3_series(
    ns_params: pd.DataFrame, country: str, model: str, beta: str
) -> tuple[pd.Series, np.ndarray]:
    """``(dates, values)`` for one Chart 3 line; NaN at every ``ns_degenerate`` month.

    NaN rather than a dropped row, so matplotlib breaks the line there instead
    of drawing a straight segment across the gap. The criterion is
    ``ns_degenerate`` — ``lam_at_bound`` **or** a beta above 50 percentage
    points — not ``lam_at_bound`` alone: a lambda just inside the bound leaves
    the loadings nearly collinear and the betas still run away. Only the
    ``ns_free`` panel is gapped; ``ns_dl`` has a fixed lambda and trips the beta
    criterion in no month of any country (largest max |beta| 0.3365, GB).
    """
    g = ns_params[(ns_params["country"] == country) & (ns_params["model"] == model)].sort_values(
        "date"
    )
    y = g[beta].to_numpy(dtype="float64").copy()
    if model == "ns_free":
        y[g["ns_degenerate"].astype(bool).to_numpy()] = np.nan  # a gap, not a clip
    return g["date"], y


def chart3_betas(
    ns_params: pd.DataFrame,
    out: Path = FIGURES / "chart3_betas.png",
    start: pd.Timestamp = CHART3_START,
) -> tuple[Path, pd.DataFrame]:
    """6 panels: NS-DL betas on top (the primary series), NS-free with gaps below.

    Returns ``(path, excluded)``. An ``ns_degenerate`` month is dropped from the
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
            head = "NS-DL (fixed lambda)" if model == "ns_dl" else "NS-free (gaps where degenerate)"
            ax.set_title(f"{head} — {beta}", fontsize=10)
    axes[0, 0].legend(fontsize=8, ncol=2, loc="best")
    caption = ", ".join(f"{c} {int(n)}" for c, n in gaps.items())
    fig.suptitle(
        "Chart 3 — Nelson-Siegel betas from 1995. Top row NS-DL at fixed lambda: the "
        "comparable series, because a free lambda changes the loadings each month.\n"
        "Bottom row NS-free, with ns_degenerate months left as gaps (lambda on a bound, "
        "or a beta above 50 points; not clipped, not "
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

    decades = [int(x) for x in cfg["report"]["chart1_decades"]]
    dates = chart1_dates(fitted, decades)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    dates.to_csv(checks.CHART1_DATES, index=False, lineterminator="\n")
    paths = chart1_fit(zero, params, dates, decades, out_dir)
    paths.append(chart1_rmse(params, Path(out_dir) / "chart1_rmse.png"))
    path3, excluded = chart3_betas(ns_params, Path(out_dir) / "chart3_betas.png")
    excluded.to_csv(checks.CHART3_EXCLUDED, index=False, lineterminator="\n")
    paths.append(path3)

    # step 3.3
    loadings = pd.read_parquet(p / "pca_loadings.parquet")
    paths.append(chart2_loadings(loadings, Path(out_dir) / "chart2_loadings.png"))
    explained = pd.read_csv(checks.PCA_EXPLAINED)
    paths.append(report.write_explained_table(explained, cfg))
    return paths


# ------------------------------------------------- step 3.3: Chart 2, PCA


PC_PANELS = [1, 2, 3]
PC_TITLES = {1: "PC1 (level)", 2: "PC2 (slope)", 3: "PC3 (curvature)"}
POOLED_STYLE = {"color": "black", "linestyle": "--", "linewidth": 2.0, "zorder": 5}


def chart2_country_scopes(loadings: pd.DataFrame) -> list[str]:
    """The scopes chart 2 draws as country lines: everything but the two pooled fits."""
    from curvecarry.pca import PRIMARY_POOLED, SECONDARY_POOLED

    return [s for s in loadings["scope"].unique() if s not in (PRIMARY_POOLED, SECONDARY_POOLED)]


def chart2_loadings(loadings: pd.DataFrame, out: Path = FIGURES / "chart2_loadings.png") -> Path:
    """Three panels, PC1 to PC3: loading against tenor, one line per country.

    The primary pooled fit is the dashed black line. Each country is drawn on
    its own tenor set, which is why the lines end at different tenors: the US
    and GB sets stop at 10 years, DE runs to 30 (step 3.1, issue #15). The
    secondary ``pooled_20y`` fit is not drawn — it is a reported robustness
    column, and putting it on the same axes would invite reading it as a
    seventh country.
    """
    scopes = chart2_country_scopes(loadings)
    from curvecarry.pca import PRIMARY_POOLED

    fig, axes = plt.subplots(1, len(PC_PANELS), figsize=(14, 4.2), sharex=True)
    for ax, k in zip(np.atleast_1d(axes), PC_PANELS, strict=True):
        for scope in sorted(scopes):
            g = loadings[(loadings["scope"] == scope) & (loadings["component"] == k)]
            g = g.sort_values("tenor_years")
            ax.plot(g["tenor_years"], g["loading"], marker="o", markersize=3, label=scope)
        g = loadings[(loadings["scope"] == PRIMARY_POOLED) & (loadings["component"] == k)]
        g = g.sort_values("tenor_years")
        ax.plot(g["tenor_years"], g["loading"], label="pooled", **POOLED_STYLE)
        ax.axhline(0.0, color="0.7", linewidth=0.8, zorder=0)
        ax.set_title(PC_TITLES[k])
        ax.set_xlabel("tenor (years)")
    np.atleast_1d(axes)[0].set_ylabel("loading")
    np.atleast_1d(axes)[0].legend(fontsize=8, ncol=2)
    fig.suptitle(
        "Chart 2 — PCA loadings on monthly zero-yield changes, per country and pooled",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return _save(fig, Path(out))
