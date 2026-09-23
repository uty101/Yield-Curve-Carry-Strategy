"""Command-line entry point. Sub-commands are added by the step that builds them.

uv run curvecarry fetch --source us        # Phase 1: download to data/raw/, record in the manifest
uv run curvecarry build --step us          # raw -> data/interim/curves_us.parquet + coverage rows
uv run curvecarry build --step harmonise    # 1.8: interim curves -> data/processed/curves.parquet
uv run curvecarry build --step zero         # 1.9: par -> zero, curves_zero.parquet, sample window
uv run curvecarry build --step ns           # 2.2: ns_params.parquet, ns_fitted.parquet, fit checks
uv run curvecarry build --step svensson     # 2.3: sv_params.parquet, svensson_vs_bundesbank.csv
uv run curvecarry build --step pca          # 3.1: pca_loadings.parquet, pca_scores.parquet, sets
uv run curvecarry report --charts 1,2,3     # 2.4, 3.3: reports/figures/*.png (full report 6.4)
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
}
NOT_BUILT = {"run": "step 5.3"}
CHARTS_BUILT = {"1", "3"}  # step 2.4; the rest arrive with the full report in 6.4


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
    names = LOADERS + list(STEPS) if args.all else [args.step]
    for name in names:
        if name in STEPS:
            module, fn = STEPS[name]
            df = getattr(importlib.import_module(module), fn)(cfg)
        else:
            df = _loader(name).load(cfg)
        print(
            f"built {name}: {len(df)} rows, {df['date'].min().date()} .. {df['date'].max().date()}"
        )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = config.load()
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
        "--charts",
        default="1,3",
        help='comma-separated chart numbers; only "1,3" is built (step 2.4). The full '
        "report is step 6.4.",
    )
    r.set_defaults(fn=cmd_report)

    for name, step in NOT_BUILT.items():
        s = sub.add_parser(name, help=f"not built yet ({step})")
        s.set_defaults(fn=lambda a, step=step: print(f"not built yet; see PLAN.md {step}") or 1)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
