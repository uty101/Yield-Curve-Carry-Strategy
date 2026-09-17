"""FX spot versus the base currency (step 1.7).

FRED daily ``DEXUSUK`` (USD per GBP), ``DEXJPUS`` (JPY per USD), ``DEXCAUS``
(CAD per USD), ``DEXUSEU`` (USD per EUR, from 1999-01-04); ``"."`` on
holidays. Each is turned into USD per unit of foreign currency (inverting the
two quoted the other way), then into **units of base currency per unit of
foreign currency**, ``spot = usd_per_foreign / usd_per_base``, so that a
foreign appreciation is a gain for a base-currency investor. Sampled at the
last observation of each calendar month like the curves. The base currency
has a row at ``spot = 1.0``. There is no EUR spot before 1999-01, so DE and
FR unhedged returns are missing before then (recorded, never filled).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
USD_PER_FOREIGN, FOREIGN_PER_USD = "usd_per_foreign", "foreign_per_usd"
QUOTES: dict[str, tuple[str, str]] = {
    "GBP": ("DEXUSUK", USD_PER_FOREIGN),
    "JPY": ("DEXJPUS", FOREIGN_PER_USD),
    "CAD": ("DEXCAUS", FOREIGN_PER_USD),
    "EUR": ("DEXUSEU", USD_PER_FOREIGN),
}


def fetch(cfg: dict) -> list[Path]:
    out = []
    for series, _ in QUOTES.values():
        url = FRED_URL.format(series=series)
        path = manifest.raw_path("fred", series, "csv", base.today())
        manifest.write_raw(manifest.fetch_bytes(url), path, url, "fred")
        out.append(path)
    return out


def parse_usd(paths: list[Path]) -> pd.DataFrame:
    """Raw csvs -> daily ``obs_date, currency, usd_per_foreign`` for the four quoted currencies."""
    by_series = {s: cur for cur, (s, _) in QUOTES.items()}
    frames = []
    for p in paths:
        df = pd.read_csv(p, na_values=["."])
        series = [c for c in df.columns if c != "observation_date"]
        assert len(series) == 1, f"{p}: {series}"
        s = series[0]
        if s not in by_series:
            raise ValueError(f"{p}: unknown FX series {s!r}")
        cur = by_series[s]
        value = df[s].astype("float64")
        usd_per_foreign = value if QUOTES[cur][1] == USD_PER_FOREIGN else 1.0 / value
        frames.append(
            pd.DataFrame(
                {
                    "obs_date": pd.to_datetime(df["observation_date"]),
                    "currency": cur,
                    "usd_per_foreign": usd_per_foreign,
                }
            ).dropna(subset=["usd_per_foreign"])
        )
    return pd.concat(frames, ignore_index=True)


def to_base(daily_usd: pd.DataFrame, base_currency: str) -> pd.DataFrame:
    """USD-per-foreign daily -> base-per-foreign daily, plus the base's own row at 1.0."""
    d = daily_usd.copy()
    if base_currency == "USD":
        d["spot"] = d["usd_per_foreign"]
        usd_row = d[["obs_date"]].drop_duplicates().assign(currency="USD", spot=1.0)
        out = pd.concat([d[["obs_date", "currency", "spot"]], usd_row], ignore_index=True)
    else:
        if base_currency not in QUOTES:
            raise ValueError(f"no FX series for base currency {base_currency!r}")
        usd_per_base = d[d["currency"] == base_currency].set_index("obs_date")["usd_per_foreign"]
        d = d.join(usd_per_base.rename("usd_per_base"), on="obs_date", how="inner")
        d["spot"] = d["usd_per_foreign"] / d["usd_per_base"]
        usd_row = usd_per_base.rename("spot").rdiv(1.0).reset_index().assign(currency="USD")
        out = pd.concat(
            [d[d["currency"] != base_currency][["obs_date", "currency", "spot"]], usd_row],
            ignore_index=True,
        )
        base_row = d[["obs_date"]].drop_duplicates().assign(currency=base_currency, spot=1.0)
        out = pd.concat([out, base_row], ignore_index=True)
    return out.sort_values(["currency", "obs_date"]).reset_index(drop=True)


def monthly(daily_base: pd.DataFrame) -> pd.DataFrame:
    """Last observation of each calendar month, per currency."""
    frames = []
    for cur, g in daily_base.groupby("currency"):
        m = base.month_end_sample(
            g.rename(columns={"spot": "yield"}).assign(tenor_years=0.0)[
                ["obs_date", "tenor_years", "yield"]
            ]
        )
        frames.append(pd.DataFrame({"date": m["date"], "currency": cur, "spot": m["yield"]}))
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["currency", "date"])
        .reset_index(drop=True)
    )


def latest_paths() -> list[Path]:
    return [manifest.latest_raw("fred", s) for s, _ in QUOTES.values()]


def load(cfg: dict) -> pd.DataFrame:
    out = monthly(to_base(parse_usd(latest_paths()), cfg["base_currency"]))
    out["source"] = "fred"
    assert (out["spot"] > 0).all()
    base.INTERIM.mkdir(parents=True, exist_ok=True)
    out.to_parquet(base.INTERIM / "fx.parquet", index=False)
    cov = out.rename(columns={"currency": "country", "spot": "yield"}).assign(
        tenor_years=0.0, curve_type="fx"
    )
    checks.write_coverage(
        cov[["date", "country", "tenor_years", "yield", "curve_type"]], "observed"
    )
    return out
