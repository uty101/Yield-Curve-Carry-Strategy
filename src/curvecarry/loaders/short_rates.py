"""Funding rates (step 1.7): BIS policy rates (default) and OECD 3-month interbank (robustness).

Policy rates: BIS ``WS_CBPOL`` monthly, areas ``US GB JP CA XM DE FR`` — the
BIS TITLE field reads "Central bank policy rates - <area> - Monthly - End of
period", so the monthly value is the end-of-month rate. ``DE`` and ``FR``
end 1998-12 (euro entry) and serve as the EUR legacy areas before
``config.hedge.eur_splice``; ``XM`` (euro area) from 1999-01. Percent.

3-month interbank: FRED ``IR3TIB01{US,GB,JP,CA,EZ}M156N`` (OECD MEI), monthly,
percent, dated the first of the month and stamped to that month's end; one
series type for all five currencies (issue #1 follow-up). JP starts 2002-04,
GB and EZ stop at 2026-01.

Policy-rate gap fill (Session 1 fix, 2026-09-22): the BIS JP series has no
value for 116 months (1999-03..2000-07, 2001-04..2006-02, 2013-05..2016-08 —
the zero-rate and QQE regimes with no stated target). For ``kind = policy``
any month inside the BIS series' span with no BIS value is filled from the
OECD immediate (overnight call money) rate, FRED
``IRSTCI01{US,GB,JP,CA,EZ}M156N``, and the row carries
``source = "fred_immediate"`` so the fill is visible in every row. A month
with a BIS value is never overwritten. The same rule runs for every
currency; today only JP has gaps. ``data/checks/funding_fill.csv`` lists
each filled run (``decisions/short_anchor.md``).

Two outputs: ``data/interim/short_rates.parquet`` (``date, area, rate, kind,
source``) — every series as fetched, the immediate rates as
``kind = immediate``; and ``data/interim/funding.parquet`` (``date, country,
currency, rate, kind, source``) — one row per country, month and kind
(``policy`` filled as above, ``interbank_3m``), with the EUR splice applied.
The funding rate is never placed on a curve (``decisions/short_anchor.md``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{area}?format=csv"
BIS_AREAS = ["US", "GB", "JP", "CA", "XM", "DE", "FR"]
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
INTERBANK: dict[str, str] = {  # currency -> OECD/FRED series (area code EZ for the euro area)
    "USD": "IR3TIB01USM156N",
    "GBP": "IR3TIB01GBM156N",
    "JPY": "IR3TIB01JPM156N",
    "CAD": "IR3TIB01CAM156N",
    "EUR": "IR3TIB01EZM156N",
}
IMMEDIATE: dict[str, str] = {  # currency -> OECD immediate (overnight) rate on FRED; fills BIS gaps
    "USD": "IRSTCI01USM156N",
    "GBP": "IRSTCI01GBM156N",
    "JPY": "IRSTCI01JPM156N",
    "CAD": "IRSTCI01CAM156N",
    "EUR": "IRSTCI01EZM156N",
}
CURRENCY_AREA: dict[str, str] = {"USD": "US", "GBP": "GB", "JPY": "JP", "CAD": "CA", "EUR": "XM"}
KIND_POLICY, KIND_INTERBANK, KIND_IMMEDIATE = "policy", "interbank_3m", "immediate"
SOURCE_FILL = "fred_immediate"
FUNDING_COLUMNS = ["date", "country", "currency", "rate", "kind", "source"]
FILL_COLUMNS = ["country", "first", "last", "months_filled"]


def _oecd_area(series: str) -> str:
    """``IR3TIB01EZM156N`` / ``IRSTCI01EZM156N`` -> ``EZ``."""
    return series[8:10]


def fetch(cfg: dict) -> list[Path]:
    out = []
    for area in BIS_AREAS:
        url = BIS_URL.format(area=area)
        path = manifest.raw_path("bis", f"CBPOL_{area}", "csv", base.today())
        manifest.write_raw(manifest.fetch_bytes(url), path, url, "bis")
        out.append(path)
    for series in list(INTERBANK.values()) + list(IMMEDIATE.values()):
        url = FRED_URL.format(series=series)
        path = manifest.raw_path("fred", series, "csv", base.today())
        manifest.write_raw(manifest.fetch_bytes(url), path, url, "fred")
        out.append(path)
    return out


def parse_bis(path: Path) -> pd.DataFrame:
    """One BIS SDMX csv -> ``date (month end), area, rate (decimal)``."""
    df = pd.read_csv(path)
    for col in ("REF_AREA", "TIME_PERIOD", "OBS_VALUE", "TITLE"):
        if col not in df.columns:
            raise ValueError(f"{path}: column {col!r} missing")
    if "End of period" not in str(df["TITLE"].iloc[0]):
        raise ValueError(f"{path}: TITLE does not say 'End of period': {df['TITLE'].iloc[0]!r}")
    out = pd.DataFrame(
        {
            "date": base.month_end(pd.to_datetime(df["TIME_PERIOD"], format="%Y-%m")),
            "area": df["REF_AREA"].astype(str),
            "rate": pd.to_numeric(df["OBS_VALUE"], errors="coerce") / 100.0,  # percent -> decimal
        }
    )
    return out.dropna(subset=["rate"]).sort_values("date").reset_index(drop=True)


def parse_fred_monthly(path: Path, area: str) -> pd.DataFrame:
    """One FRED monthly csv (first-of-month dates, percent) -> ``date (month end), area, rate``."""
    df = pd.read_csv(path, na_values=["."])
    series = [c for c in df.columns if c != "observation_date"]
    assert len(series) == 1, f"{path}: {series}"
    out = pd.DataFrame(
        {
            "date": base.month_end(pd.to_datetime(df["observation_date"])),
            "area": area,
            "rate": df[series[0]].astype("float64") / 100.0,  # percent -> decimal
        }
    )
    return out.dropna(subset=["rate"]).reset_index(drop=True)


def parse(paths: list[Path]) -> pd.DataFrame:
    """All raw files -> ``date, area, rate, kind, source``."""
    frames = []
    for p in paths:
        p = Path(p)
        name = manifest._split_stem(p)[0] if p.stem[-9:-8] == "_" else p.stem
        if name.startswith("CBPOL_"):
            d = parse_bis(p)
            d["kind"], d["source"] = KIND_POLICY, "bis"
        elif name.startswith("IR3TIB01"):
            d = parse_fred_monthly(p, _oecd_area(name))
            d["kind"], d["source"] = KIND_INTERBANK, "fred"
        elif name.startswith("IRSTCI01"):
            d = parse_fred_monthly(p, _oecd_area(name))
            d["kind"], d["source"] = KIND_IMMEDIATE, "fred"
        else:
            raise ValueError(f"{p}: not a policy-rate, interbank or immediate-rate file")
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    if out.duplicated(["date", "area", "kind"]).any():
        raise ValueError("duplicate (date, area, kind) in short rates")
    return out[["date", "area", "rate", "kind", "source"]]


def _validate_rates(df: pd.DataFrame) -> None:
    assert df["rate"].between(base.YIELD_LO, base.YIELD_HI).all(), "rate outside bounds: percent?"
    assert df["rate"].max() > base.YIELD_MIN_MAX, "rates too small: divided twice?"
    assert df["date"].equals(base.month_end(df["date"])), "dates must be month ends"


def fill_policy_gaps(policy: pd.DataFrame, immediate: pd.DataFrame) -> pd.DataFrame:
    """Months inside ``policy``'s span with no BIS value, taken from ``immediate``.

    Returns the filled rows only (``date, area, rate``, ``source = fred_immediate``);
    a month that has a BIS value is never touched, and nothing is added
    before the first or after the last BIS month.
    """
    if policy.empty or immediate.empty:
        return policy.iloc[0:0]
    span = pd.date_range(policy["date"].min(), policy["date"].max(), freq="ME")
    missing = span.difference(pd.DatetimeIndex(policy["date"]))
    fill = immediate[immediate["date"].isin(missing)].copy()
    fill["kind"], fill["source"] = KIND_POLICY, SOURCE_FILL
    return fill


def _fill_runs(dates: pd.Series) -> list[tuple[str, str, int]]:
    """Contiguous monthly runs of ``dates`` as (first, last, months)."""
    runs: list[list[pd.Period]] = []
    for per in sorted(pd.DatetimeIndex(dates).to_period("M")):
        if runs and per == runs[-1][-1] + 1:
            runs[-1].append(per)
        else:
            runs.append([per])
    return [
        (
            r[0].to_timestamp("M").date().isoformat(),
            r[-1].to_timestamp("M").date().isoformat(),
            len(r),
        )
        for r in runs
    ]


def funding_fill_rows(funding: pd.DataFrame) -> pd.DataFrame:
    """``data/checks/funding_fill.csv``: one row per filled run per country; a country
    with no fill gets one row with blank dates and 0 so its absence is visible."""
    rows = []
    for country, g in funding[funding["kind"] == KIND_POLICY].groupby("country"):
        filled = g[g["source"] == SOURCE_FILL]
        if filled.empty:
            rows.append((country, "", "", 0))
        for first, last, n in _fill_runs(filled["date"]):
            rows.append((country, first, last, n))
    return pd.DataFrame(rows, columns=FILL_COLUMNS)


def build_funding(short_rates: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per country, month and kind: the funding rate, with the EUR splice (amendment D)
    and the policy-rate gap fill from the OECD immediate rate (``fill_policy_gaps``)."""
    splice = pd.Timestamp(cfg["hedge"]["eur_splice"])
    legacy = cfg["hedge"]["eur_legacy"]
    countries = list(cfg["countries"])
    base_country = [c for c, cur in cfg["currency"].items() if cur == cfg["base_currency"]]
    for c in base_country:
        if c not in countries:
            countries.append(c)
    rows = []
    for country in countries:
        currency = cfg["currency"][country]
        # policy: legacy national area before the splice, the currency's area from it
        pol = short_rates[short_rates["kind"] == KIND_POLICY]
        area_now = CURRENCY_AREA[currency]
        if currency == "EUR" and country in legacy:
            before = pol[(pol["area"] == legacy[country]) & (pol["date"] < splice)]
            after = pol[(pol["area"] == area_now) & (pol["date"] >= splice)]
            p = pd.concat([before, after])
        else:
            p = pol[pol["area"] == area_now]
        oecd_area = _oecd_area(IMMEDIATE[currency])
        imm = short_rates[
            (short_rates["kind"] == KIND_IMMEDIATE) & (short_rates["area"] == oecd_area)
        ]
        p = pd.concat([p, fill_policy_gaps(p, imm)])  # BIS rows first; fills only where absent
        ib_area = _oecd_area(INTERBANK[currency])
        ib = short_rates[(short_rates["kind"] == KIND_INTERBANK) & (short_rates["area"] == ib_area)]
        for part in (p, ib):
            for _, r in part.iterrows():
                rows.append((r["date"], country, currency, r["rate"], r["kind"], r["source"]))
    out = pd.DataFrame(rows, columns=FUNDING_COLUMNS).sort_values(["country", "kind", "date"])
    assert not out.duplicated(["date", "country", "kind"]).any()
    return out.reset_index(drop=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw("bis", f"CBPOL_{a}") for a in BIS_AREAS] + [
        manifest.latest_raw("fred", s) for s in list(INTERBANK.values()) + list(IMMEDIATE.values())
    ]


def load(cfg: dict) -> pd.DataFrame:
    rates = parse(latest_paths())
    _validate_rates(rates)
    base.INTERIM.mkdir(parents=True, exist_ok=True)
    rates.to_parquet(base.INTERIM / "short_rates.parquet", index=False)
    funding = build_funding(rates, cfg)
    funding.to_parquet(base.INTERIM / "funding.parquet", index=False)
    checks.CHECKS.mkdir(parents=True, exist_ok=True)
    funding_fill_rows(funding).to_csv(checks.FUNDING_FILL, index=False, lineterminator="\n")
    cov = funding.rename(columns={"rate": "yield"})
    cov["tenor_years"] = 0.0
    cov["curve_type"] = "funding_" + cov["kind"]
    checks.write_coverage(
        cov[["date", "country", "tenor_years", "yield", "curve_type"]], "observed"
    )
    return funding
