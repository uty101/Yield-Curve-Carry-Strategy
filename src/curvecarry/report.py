"""Report tables. Step 3.3 builds the first one; the full report is step 6.4.

``explained_table`` renders ``data/checks/pca_explained.csv`` as the markdown
table ``scope | PC1 | PC2 | PC3 | PC1-3``, in percent to one decimal place,
one row per scope. The rows are the six countries in ``config.countries``
order, then the primary pooled fit, then the secondary ``pooled_20y`` fit —
which is reported here and read by no step after 3.3 (issue #15 answer 5).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from curvecarry import checks

TABLE_COMPONENTS = [1, 2, 3]
HEADER = "| scope | n months | PC1 | PC2 | PC3 | PC1-3 |"
RULE = "|---|---:|---:|---:|---:|---:|"


def _scope_order(scopes: list[str], cfg: dict) -> list[str]:
    from curvecarry.pca import PRIMARY_POOLED, SECONDARY_POOLED

    order = [c for c in cfg["countries"] if c in scopes]
    return order + [s for s in (PRIMARY_POOLED, SECONDARY_POOLED) if s in scopes]


def explained_table(explained: pd.DataFrame, cfg: dict) -> str:
    """The markdown explained-variance table, percentages to 1 dp."""
    lines = [HEADER, RULE]
    for scope in _scope_order(list(explained["scope"].unique()), cfg):
        g = explained[explained["scope"] == scope].set_index("component")
        shares = [round(float(g.loc[k, "explained_share"]) * 100, 1) for k in TABLE_COMPONENTS]
        n = int(g["n_months"].iloc[0])
        cells = " | ".join(f"{v:.1f}" for v in shares)
        # the total is the sum of the **rounded** components, not the rounded sum,
        # so the printed row adds up: PLAN.md 3.3 asks for the PC1-3 column to equal
        # the sum of the three to 0.05 pp, and rounding the exact total instead can
        # put it 0.1 pp away from what the reader adds (US: 90.9 + 7.2 + 1.1 = 99.2,
        # while the exact 99.27 would print 99.3).
        lines.append(f"| {scope} | {n} | {cells} | {sum(shares):.1f} |")
    return "\n".join(lines) + "\n"


def write_explained_table(
    explained: pd.DataFrame, cfg: dict, path: Path = checks.PCA_EXPLAINED_TABLE
) -> Path:
    text = explained_table(explained, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path
