.PHONY: setup test lint fetch build run report all

setup:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

# Step 6.4: the four targets call the CLI. `run` logs a row in
# reports/specifications.csv for every variant before it computes, and that
# file is append-only, so `make run` is not idempotent: N in the deflated
# Sharpe is its row count. Run it when you mean to add runs, not to rebuild.
fetch:
	uv run curvecarry fetch --all

build:
	uv run curvecarry build --all

run:
	uv run curvecarry run --all

report:
	uv run curvecarry report

# `build --all` stops before the three steps that read a completed backtest.
# The whole sequence, from raw files to the report, is:
#     make build                                  # loaders, curves, carry, returns, signal, weights, overlay
#     uv run curvecarry run --all                 # every logged run, the risk controls included
#     uv run curvecarry build --step decomposition
#     uv run curvecarry build --step risk_controls
#     uv run curvecarry build --step caveats
#     make report
#
# `run --all` covers the risk-control variants too, so it is NOT followed by
# `run --risk-controls`: that would log the eight controls a second time and
# move N. `--risk-controls [--only <v>]` is for adding a control to a spec log
# that already has its base, which is how session 6 added them.
# Everything except the two `run` lines, which append to the spec log.
all: build report
