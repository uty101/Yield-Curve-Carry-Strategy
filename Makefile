.PHONY: setup test lint fetch build run report

setup:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

# The four targets below are placeholders until the step that builds each
# one lands (fetch: Phase 1, build: 1.8/1.9, run: 5.3, report: 6.4).
fetch:
	@echo "fetch: not built yet (Phase 1)"

build:
	@echo "build: not built yet (steps 1.8-1.9)"

run:
	@echo "run: not built yet (step 5.3)"

report:
	@echo "report: not built yet (step 6.4)"
