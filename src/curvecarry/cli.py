"""Command-line entry point. Sub-commands are added by the step that builds them.

uv run curvecarry fetch --source us        # Phase 1: download to data/raw/, record in the manifest
uv run curvecarry build --step us          # raw -> data/interim/curves_us.parquet + coverage rows
uv run curvecarry fetch --all / build --all
"""

from __future__ import annotations

import argparse
import importlib
import sys

from curvecarry import config

# loader modules by their CLI name; a name is added by the step that builds it
LOADERS: list[str] = ["us", "gb", "de", "jp"]
NOT_BUILT = {"run": "step 5.3", "report": "step 6.4"}


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
    names = LOADERS if args.all else [args.step]
    for name in names:
        df = _loader(name).load(cfg)
        print(
            f"built {name}: {len(df)} rows, {df['date'].min().date()} .. {df['date'].max().date()}"
        )
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
    g.add_argument("--step", choices=LOADERS)
    g.add_argument("--all", action="store_true")
    b.set_defaults(fn=cmd_build)

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
