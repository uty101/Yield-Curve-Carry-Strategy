"""Command-line entry point. Sub-commands are added by the step that builds them."""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="curvecarry")
    parser.add_argument("command", nargs="?", help="fetch | build | run | report (added per step)")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    print(f"'{args.command}' is not built yet; see PLAN.md for the step that adds it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
