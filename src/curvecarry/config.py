"""Read ``config.toml`` and hash it.

Every number that affects a result lives in ``config.toml`` and nowhere else
(global rule 4). ``load`` returns the file as a nested dict, unchanged except
that ``sample.strategy_end`` becomes a ``pd.Timestamp``; blank strings (the
two dates step 1.9 fills in) stay ``""``. ``REQUIRED_KEYS`` lists every
dotted key PLAN.md names, so a missing key fails at load time, not in the
step that needs it (rule 14: no later step adds a knob).
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pandas as pd

REQUIRED_KEYS: tuple[str, ...] = (
    "base_currency",
    "countries",
    "tenors",
    "short_end",
    "bootstrap_max_node_gap_years",
    "bootstrap_zero_par_tolerance_bp",
    "coupon_frequency.US",
    "coupon_frequency.GB",
    "coupon_frequency.JP",
    "coupon_frequency.CA",
    "coupon_frequency.DE",
    "coupon_frequency.FR",
    "currency.US",
    "currency.GB",
    "currency.DE",
    "currency.JP",
    "currency.CA",
    "currency.FR",
    "sample.strategy_start",
    "sample.sample_full_start",
    "sample.strategy_end",
    "sample.sample_min_countries",
    "sample.sample_max_tenor",
    "nelson_siegel.ns_lambda_grid",
    "nelson_siegel.ns_lambda_fixed",
    "nelson_siegel.min_tenors",
    "pca.pca_min_months",
    "pca.pca_z_window",
    "pca.stability_min_months",
    "pca.tenor_presence_min",
    "pca.us_borderline_gap_bp",
    "signal.yield_floor",
    "weights.long_duration_budget",
    "weights.duration_neutral_scope",
    "weights.min_eligible_buckets",
    "overlay.z_entry",
    "overlay.z_exit",
    "overlay.overlay_duration_budget",
    "overlay.overlay_tenors",
    "hedge.funding_rate",
    "hedge.funding_rate_robustness",
    "hedge.eur_splice",
    "hedge.eur_legacy.DE",
    "hedge.eur_legacy.FR",
    "costs.cost_bp_per_duration_year",
    "risk.target_vol",
    "risk.vol_window_months",
    "risk.max_leverage",
    "risk.dd_stop",
    "risk.dd_reentry_months",
    "risk.rates_vol_pct",
    "risk.risk_control_base_variants",
    "report.chart1_decades",
)


def _get(cfg: dict, dotted: str):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def load(path: str | Path = "config.toml") -> dict:
    """Load ``config.toml``. Raises ``KeyError`` naming the first missing key."""
    with open(path, "rb") as fh:
        cfg = tomllib.load(fh)
    for key in REQUIRED_KEYS:
        _get(cfg, key)
    end = cfg["sample"]["strategy_end"]
    if end != "":
        cfg["sample"]["strategy_end"] = pd.Timestamp(end)
    return cfg


def config_hash(cfg: dict) -> str:
    """First 12 hex chars of sha256 of the sorted JSON dump of ``cfg``."""
    payload = json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
