"""Step 6.4, global rule 8: no number in ``README.md`` is typed by hand."""

from __future__ import annotations

import re
from pathlib import Path

from curvecarry import results

README = Path("README.md")
RESULTS = Path("reports/results.md")


def _normalise(text: str) -> str:
    """Line-end whitespace only; nothing else may differ."""
    return "\n".join(line.rstrip() for line in text.splitlines())


def test_readme_results_equal_results_md():
    """The README block is the ``results.md`` block, character for character."""
    readme = results.read_block(README.read_text(encoding="utf-8"))
    report = results.read_block(RESULTS.read_text(encoding="utf-8"))
    assert _normalise(readme) == _normalise(report)


def test_readme_has_no_number_outside_the_block():
    """Outside the generated block the README carries prose and paths, not results.

    A *result* is a percentage, a decimal or a date. Those may only come from
    the generated block. "G7" in the title is a name, not a result, so the
    pattern looks for the shapes a result takes and not for any digit at all.
    """
    text = README.read_text(encoding="utf-8")
    outside = text[: text.index(results.BEGIN)] + text[text.index(results.END) :]
    outside = re.sub(r"`[^`]*`", "", outside)  # code spans: paths, commands, keys
    outside = re.sub(r"\[[^\]]*\]\([^)]*\)", "", outside)  # links
    result_shaped = r"-?\d+\.\d+|-?\d+%|\d{4}-\d{2}-\d{2}"
    assert re.findall(result_shaped, outside) == []


def test_readme_block_carries_the_headline_and_the_dsr_verdict():
    """The block names the headline variant and says in its own sentence whether it clears."""
    block = results.read_block(README.read_text(encoding="utf-8"))
    assert "carry_hedged" in block
    assert "deflated Sharpe" in block
    assert "a probability, not a Sharpe ratio" in block
    assert "clear the usual bar" in block


def test_readme_block_has_the_three_tables_amendment_5_asks_for():
    """The per-year table, the full variant table, and every logged run with its label."""
    block = results.read_block(README.read_text(encoding="utf-8"))
    assert results.YEAR_HEADER in block
    assert results.RUNS_HEADER in block
    assert "| variant | window | ann return |" in block
