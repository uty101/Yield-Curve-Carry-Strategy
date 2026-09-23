"""Step 3.3: the explained-variance markdown table."""

from __future__ import annotations

import pandas as pd
import pytest

from curvecarry import report


def _explained() -> pd.DataFrame:
    rows = []
    shares = {
        "US": [0.9091, 0.0724, 0.0112, 0.0073],
        "DE": [0.8158, 0.1463, 0.0257, 0.0122],
        "pooled": [0.8911, 0.0860, 0.0160, 0.0069],
        "pooled_20y": [0.8507, 0.1169, 0.0221, 0.0103],
    }
    months = {"US": 775, "DE": 348, "pooled": 3023, "pooled_20y": 1566}
    for scope, vals in shares.items():
        for k, v in enumerate(vals, start=1):
            rows.append((scope, k, v * 100, v, months[scope]))
    return pd.DataFrame(
        rows, columns=["scope", "component", "eigenvalue", "explained_share", "n_months"]
    )


def _cfg() -> dict:
    return {"countries": ["US", "GB", "DE", "JP", "CA", "FR"]}


def test_explained_table_rows_sum() -> None:
    """One row per scope, and the PC1-3 column equals the sum of the three to 0.05 pp."""
    text = report.explained_table(_explained(), _cfg())
    body = [ln for ln in text.splitlines() if ln.startswith("| ") and "scope" not in ln]
    assert len(body) == 4
    for line in body:
        cells = [c.strip() for c in line.strip("|").split("|")]
        pc1, pc2, pc3, total = (float(c) for c in cells[2:6])
        assert abs(pc1 + pc2 + pc3 - total) <= 0.05


def test_explained_table_scope_order() -> None:
    """Countries in config order, then the primary pooled fit, then the secondary."""
    text = report.explained_table(_explained(), _cfg())
    scopes = [
        ln.strip("|").split("|")[0].strip()
        for ln in text.splitlines()
        if ln.startswith("| ") and "scope" not in ln
    ]
    assert scopes == ["US", "DE", "pooled", "pooled_20y"]


def test_explained_table_is_percent_to_one_dp() -> None:
    text = report.explained_table(_explained(), _cfg())
    us = next(ln for ln in text.splitlines() if ln.startswith("| US "))
    cells = [c.strip() for c in us.strip("|").split("|")]
    assert cells[1] == "775"
    assert cells[2] == "90.9" and cells[3] == "7.2" and cells[4] == "1.1"
    assert cells[5] == "99.2"  # the sum of the rounded parts, not the rounded sum


def test_write_explained_table(tmp_path) -> None:
    p = report.write_explained_table(_explained(), _cfg(), tmp_path / "t.md")
    got = p.read_text(encoding="utf-8")
    assert got.startswith("| scope |") and got.endswith("\n")
    assert got.count("\n") == 6  # header, rule, four scopes


def test_missing_component_is_an_error() -> None:
    e = _explained()
    with pytest.raises(KeyError):
        report.explained_table(e[e["component"] != 3], _cfg())
