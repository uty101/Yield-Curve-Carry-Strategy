"""Command-line entry point. Sub-commands are added by the step that builds them.

uv run curvecarry fetch --source us        # Phase 1: download to data/raw/, record in the manifest
uv run curvecarry build --step us          # raw -> data/interim/curves_us.parquet + coverage rows
uv run curvecarry build --step harmonise    # 1.8: interim curves -> data/processed/curves.parquet
uv run curvecarry build --step zero         # 1.9: par -> zero, curves_zero.parquet, sample window
uv run curvecarry build --step ns           # 2.2: ns_params.parquet, ns_fitted.parquet, fit checks
uv run curvecarry build --step svensson     # 2.3: sv_params.parquet, svensson_vs_bundesbank.csv
uv run curvecarry build --step pca          # 3.1: pca_loadings.parquet, pca_scores.parquet, sets
uv run curvecarry build --step carry        # 4.1: carry.parquet, carry_missing.csv
uv run curvecarry build --step returns      # 4.2: returns.parquet, approx gap, universe, identity
uv run curvecarry build --step fx_hedge     # 4.3: hedged/unhedged columns, return_coverage.csv
uv run curvecarry build --step signal       # 5.1: signal.parquet, universe join, exclusion checks
uv run curvecarry build --step weights      # 5.2: weights.parquet, weights_empty_months.csv
uv run curvecarry build --step overlay      # 5.4: pc2_expanding, overlay_positions, overlay_states
uv run curvecarry build --step overlay_trades  # after the overlay run: the per-trade anatomy
uv run curvecarry build --step decomposition   # 6.1: decomposition_<variant>.parquet, the shares
uv run curvecarry run --risk-controls       # 6.2: the six risk-control runs, each logged first
uv run curvecarry build --step risk_controls  # 6.2: attribution_2022_*.csv, risk_controls.csv
uv run curvecarry build --step caveats      # 6.3: ns_lambda_bound.csv, section_6_3.md
uv run curvecarry run --variant carry_hedged  # 5.3: one logged run; --all runs every variant built
uv run curvecarry report --charts 1,2,3,4   # 2.4, 3.3, 4.4: reports/figures/*.png (full report 6.4)
uv run curvecarry report --table            # 5.5: metrics_table.csv/.md, unhedged_fx_exposure.csv
uv run curvecarry report                    # 6.4: every chart, reports/results.md, the README block
uv run curvecarry fetch --all / build --all  # build --all runs every loader, then the build steps
"""

from __future__ import annotations

import argparse
import importlib
import sys

from curvecarry import config

# loader modules by their CLI name; a name is added by the step that builds it
LOADERS: list[str] = ["us", "gb", "de", "jp", "ca", "fr", "short_rates", "fx", "gsw"]
# build-only steps after the loaders: CLI name -> (module, function); run in this order by --all
STEPS: dict[str, tuple[str, str]] = {
    "harmonise": ("curvecarry.harmonise", "build"),
    "zero": ("curvecarry.bootstrap", "build"),
    "ns": ("curvecarry.nelson_siegel", "build"),
    "svensson": ("curvecarry.svensson", "build"),
    "pca": ("curvecarry.pca", "build"),
    "pca_stability": ("curvecarry.pca", "build_stability"),
    "carry": ("curvecarry.carry", "build"),
    "returns": ("curvecarry.returns", "build"),
    "fx_hedge": ("curvecarry.returns", "build_fx"),
    "signal": ("curvecarry.signal", "build"),
    "weights": ("curvecarry.weights", "build"),
    "overlay": ("curvecarry.overlay", "build"),
    "overlay_trades": ("curvecarry.overlay", "build_trades"),
    "decomposition": ("curvecarry.decomposition", "build"),
    "risk_controls": ("curvecarry.risk_controls", "build"),
    "caveats": ("curvecarry.caveats", "build"),
}
# Steps that read a completed backtest and so cannot run before `run`; they are
# excluded from `build --all` and are named explicitly (see the Makefile).
POST_RUN_STEPS = ("decomposition", "risk_controls", "caveats")
NOT_BUILT: dict[str, str] = {}
CHARTS_BUILT = {"1", "2", "3", "4", "5"}  # 2.4, 3.3, 4.4 and 6.1


def _loader(name: str):
    if name not in LOADERS:
        sys.exit(f"unknown source {name!r}; built so far: {LOADERS}")
    return importlib.import_module(f"curvecarry.loaders.{name}")


def cmd_fetch(args: argparse.Namespace) -> int:
    cfg = config.load()
    names = LOADERS if args.all else [args.source]
    for name in names:
        for p in _loader(name).fetch(cfg):
            print(f"fetched {p}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    cfg = config.load()
    names = LOADERS + [s for s in STEPS if s not in POST_RUN_STEPS] if args.all else [args.step]
    for name in names:
        if name in STEPS:
            module, fn = STEPS[name]
            df = getattr(importlib.import_module(module), fn)(cfg)
        else:
            df = _loader(name).load(cfg)
        span = f", {df['date'].min().date()} .. {df['date'].max().date()}" if "date" in df else ""
        print(f"built {name}: {len(df)} rows{span}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Step 5.3. Every run is a row in reports/specifications.csv before it computes."""
    cfg = config.load()
    backtest = importlib.import_module("curvecarry.backtest")
    if args.risk_controls:
        risk = importlib.import_module("curvecarry.risk_controls")
        names = [
            risk.variant_name(base, control)
            for base in cfg["risk"]["risk_control_base_variants"]
            for control in risk.CONTROLS
        ]
    else:
        names = list(backtest.VARIANTS) if args.all else [args.variant]
    for name in names:
        res = backtest.run(cfg, name, note=args.note)
        net = res.metrics
        row = net[(net["window"] == "full") & (net["metric"] == "sharpe")]["value"]
        sharpe = float(row.iloc[0])
        print(f"ran {name} ({res.run_id}): {len(res.monthly)} months, full net Sharpe {sharpe:.3f}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = config.load()
    if args.table:
        module = importlib.import_module("curvecarry.report")
        table = module.write_metrics_table(cfg)
        n = int(table["n_trials"].iloc[0])
        print(f"wrote metrics_table.csv: {table['variant'].nunique()} variants, N = {n}")
        _rows, summary = module.unhedged_fx_exposure(cfg)
        worst = summary["r_squared"].max()
        print(f"wrote unhedged_fx_exposure.csv: {len(summary)} unhedged runs, max R2 {worst:.3f}")
        return 0
    if args.full or not (args.table or args.charts_given):
        charts = importlib.import_module("curvecarry.charts")
        for path in charts.build(cfg):
            print(f"wrote {path}")
        module = importlib.import_module("curvecarry.results")
        path = module.write(cfg)
        print(f"wrote {path} and the README block")
        return 0
    want = {c.strip() for c in args.charts.split(",") if c.strip()}
    if want - CHARTS_BUILT:
        sys.exit(f"charts {sorted(want - CHARTS_BUILT)} are not built yet; see PLAN.md step 6.4")
    charts = importlib.import_module("curvecarry.charts")
    for path in charts.build(cfg):
        print(f"wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="curvecarry")
    sub = parser.add_subparsers(dest="command")

    f = sub.add_parser("fetch", help="download raw data (Phase 1)")
    g = f.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", choices=LOADERS)
    g.add_argument("--all", action="store_true")
    f.set_defaults(fn=cmd_fetch)

    b = sub.add_parser("build", help="raw -> interim/processed + data/checks")
    g = b.add_mutually_exclusive_group(required=True)
    g.add_argument("--step", choices=LOADERS + list(STEPS))
    g.add_argument("--all", action="store_true")
    b.set_defaults(fn=cmd_build)

    r = sub.add_parser("report", help="charts and tables (2.4 builds charts 1 and 3)")
    r.add_argument(
        "--table",
        action="store_true",
        help="write data/checks/metrics_table.csv and .md (step 5.5)",
    )
    r.add_argument(
        "--full",
        action="store_true",
        help="step 6.4: regenerate every chart, reports/results.md and the README block",
    )
    r.add_argument(
        "--charts",
        default="1,2,3,4,5",
        help='comma-separated chart numbers; "1,2,3,4" are built (2.4, 3.3, 4.4). The full '
        "report is step 6.4.",
    )
    r.set_defaults(fn=cmd_report)

    rn = sub.add_parser("run", help="one logged strategy run (5.3)")
    g = rn.add_mutually_exclusive_group(required=True)
    g.add_argument("--variant")
    g.add_argument("--all", action="store_true")
    g.add_argument(
        "--risk-controls",
        action="store_true",
        help="step 6.2: the three pre-registered controls on each base book, six logged runs",
    )
    rn.add_argument("--note", default="")
    rn.set_defaults(fn=cmd_run)

    for name, step in NOT_BUILT.items():
        s = sub.add_parser(name, help=f"not built yet ({step})")
        s.set_defaults(fn=lambda a, step=step: print(f"not built yet; see PLAN.md {step}") or 1)

    args = parser.parse_args(argv)
    # "report" with no flag at all is the full report of step 6.4
    args.charts_given = any(a.startswith("--charts") for a in (argv or sys.argv[1:]))
    if args.command is None:
        parser.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
