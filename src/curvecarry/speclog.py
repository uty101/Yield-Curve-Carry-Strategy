"""The specification log: ``reports/specifications.csv``.

Every strategy run is a row here *before* it computes anything (global rule
6). A variant that has no row did not happen. The file is opened in append
mode only; nothing in the package rewrites it. Its data-row count is N for
the deflated Sharpe in step 5.5 and is never an argument.
"""

from __future__ import annotations

import csv
import datetime as dt
import subprocess
from pathlib import Path

from curvecarry.config import config_hash

HEADER = ["run_id", "timestamp_utc", "git_commit", "config_hash", "label", "note"]
DEFAULT_PATH = Path("reports/specifications.csv")


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip() or "nogit"
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def log_run(cfg: dict, label: str, note: str = "", path: str | Path = DEFAULT_PATH) -> str:
    """Append one row and return its ``run_id``. Creates the file with a header if absent."""
    path = Path(path)
    stamp = dt.datetime.now(dt.UTC).replace(microsecond=0)
    h = config_hash(cfg)
    base = f"{stamp:%Y%m%dT%H%M%S}-{h}"
    # Two runs of one config inside the same second (``run --all``) would share
    # the plan's id; a suffix keeps every row's run_id unique.
    existing = {r["run_id"] for r in _rows(path)}
    run_id, n = base, 1
    while run_id in existing:
        n += 1
        run_id = f"{base}-{n}"
    new_file = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(HEADER)
        writer.writerow([run_id, stamp.isoformat(), _git_commit(), h, label, note])
    return run_id


def _rows(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def count_runs(path: str | Path = DEFAULT_PATH) -> int:
    """Number of **distinct labels**: N for the deflated Sharpe.

    **A trial is a specification, not an execution** (owner's ruling,
    2026-09-24). Re-running a variant that has already been logged is the same
    trial done twice: it tests nothing new, so it cannot deflate the Sharpe
    further, and a rebuild of this project must leave every reported number
    where it was. ``N`` is therefore the count of distinct ``label`` values.

    The row count is still the audit trail and is still append-only - see
    ``count_rows`` - and every report prints both, because "19 trials across 19
    logged runs" and "``specifications.csv`` holds 19 rows" answer different
    questions and only one of them is ``N``.
    """
    return len({r["label"] for r in _rows(path)})


def count_rows(path: str | Path = DEFAULT_PATH) -> int:
    """Number of data rows: the append-only audit trail, never ``N``."""
    return len(_rows(path))


def require_logged(run_id: str, path: str | Path = DEFAULT_PATH) -> None:
    """Raise ``RuntimeError`` unless a row with ``run_id`` exists."""
    if not any(r["run_id"] == run_id for r in _rows(path)):
        raise RuntimeError(f"run {run_id!r} has no row in {path}: log it before computing")
