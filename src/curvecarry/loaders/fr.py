"""France: Banque de France Webstat TEC constant-maturity OAT yields (step 1.6).

Ten daily series ``FM.D.FR.EUR.FR2.BB.FRMOYTEC<N>.HSTA`` for N in
{1,2,3,5,7,10,15,20,25,30} ("Taux de l'Echéance Constante", the CNO
constant-maturity yields of hypothetical par OATs), percent, from
2004-11-03. ``curve_type = par`` (annual coupon, ``config.coupon_frequency.FR = 1``).

Endpoint (found in step 1.6; the per-tenor catalog datasets named in the
plan are empty shells with ``has_records: false``): the Webstat Explore API
dataset ``observations`` filtered by ``series_key``,
``GET https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/observations/exports/csv?where=series_key="<key>"``.

The API key is read from the environment variable ``BDF_API_KEY`` only and
sent as the ``Authorization: Apikey`` header, so it is never part of a URL
and never reaches the manifest, a log, a review or an issue. Without a valid
key the API answers 200 with zero rows, so ``fetch`` refuses to write an
export that has no data rows.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

SOURCE = "bdf"
COUNTRY = "FR"
CURVE_TYPE = "par"
TENORS = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30]
ENV_KEY = "BDF_API_KEY"
URL = "https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets/observations/exports/csv"
SERIES = "FM.D.FR.EUR.FR2.BB.FRMOYTEC{n}.HSTA"
MIN_DATA_ROWS = 100  # an export with fewer rows than this is a failed (unauthenticated) export


def _key() -> str:
    key = os.environ.get(ENV_KEY, "")
    if not key:
        raise RuntimeError(f"{ENV_KEY} not set; the Banque de France export needs it (env only)")
    return key


def _data_rows(content: bytes) -> int:
    return max(content.decode("utf-8-sig", errors="replace").count("\n") - 1, 0)


def fetch(cfg: dict) -> list[Path]:
    key = _key()  # before any request
    out = []
    for n in TENORS:
        params = {"where": f'series_key="{SERIES.format(n=n)}"'}
        content = manifest.fetch_bytes(
            URL, params=params, headers={"Authorization": f"Apikey {key}"}, timeout=300
        )
        if _data_rows(content) < MIN_DATA_ROWS:
            raise RuntimeError(
                f"empty export for TEC{n}: {_data_rows(content)} data rows (bad key?)"
            )
        # the manifest URL carries the query, never the key
        url_logged = f'{URL}?where=series_key="{SERIES.format(n=n)}"'
        path = manifest.raw_path(SOURCE, f"tec{n}", "csv", base.today())
        manifest.write_raw(content, path, url_logged, SOURCE)
        out.append(path)
    return out


def parse_file(path: Path) -> pd.DataFrame:
    """One export (semicolon csv) -> daily long frame ``obs_date, tenor_years, yield``."""
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    for col in ("series_key", "time_period", "obs_value"):
        if col not in df.columns:
            raise ValueError(f"{path}: column {col!r} missing; columns {list(df.columns)}")
    keys = df["series_key"].unique()
    if len(keys) != 1 or "FRMOYTEC" not in keys[0]:
        raise ValueError(f"{path}: expected one TEC series, got {keys}")
    n = keys[0].split("FRMOYTEC")[1].split(".")[0]
    out = pd.DataFrame(
        {
            "obs_date": pd.to_datetime(df["time_period"]),
            "tenor_years": float(n),
            "yield": pd.to_numeric(df["obs_value"], errors="coerce") / 100.0,  # percent -> decimal
        }
    )
    return out.dropna(subset=["yield"])


def parse(paths: list[Path]) -> pd.DataFrame:
    return pd.concat([parse_file(p) for p in paths], ignore_index=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, f"tec{n}") for n in TENORS]


def load(cfg: dict) -> pd.DataFrame:
    daily = parse(latest_paths())
    monthly = base.month_end_sample(daily)
    df = base.validate_curve(base.to_curveframe(monthly, COUNTRY, CURVE_TYPE, SOURCE))
    base.write_interim(df, COUNTRY)
    checks.write_coverage(df, "observed")
    checks.write_sample_day(daily, COUNTRY, cfg["tenors"])
    return df
