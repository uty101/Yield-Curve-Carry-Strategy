"""Japan: MOF JGB benchmark yields by tenor (step 1.4).

Two csv files: ``historical/jgbcme_all.csv`` (1974-09 onward) and
``jgbcme.csv`` (the current month; the kickoff's URL without ``historical/``
is 404). Layout: line 1 ``Interest Rate,,…,(Unit : %)``, line 2
``Date,1Y,2Y,…,10Y,15Y,20Y,25Y,30Y,40Y``, dates ``YYYY/M/D``, ``-`` for a
tenor not yet issued, percent; the current file ends with a note line that
is not a date. ``curve_type = par`` (benchmark coupon bonds, semi-annual,
``config.coupon_frequency.JP = 2``). The 10-year starts 1986-07, 15-year
1991-08, 20-year 1986-12, 30-year 1999-09, 25-year 2004-03, 40-year 2007-11;
all recorded in ``data/checks/coverage.csv``, never filled.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base

SOURCE = "mof"
COUNTRY = "JP"
CURVE_TYPE = "par"
BASE_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
FILES: dict[str, str] = {
    "jgbcme_all": BASE_URL + "historical/jgbcme_all.csv",  # historical, wins on overlap
    "jgbcme": BASE_URL + "jgbcme.csv",  # current month
}


def fetch(cfg: dict) -> list[Path]:
    out = []
    for name, url in FILES.items():
        content = manifest.fetch_bytes(url)
        path = manifest.raw_path(SOURCE, name, "csv", base.today())
        manifest.write_raw(content, path, url, SOURCE)
        out.append(path)
    return out


def _tenor(col: str) -> float:
    if not col.endswith("Y"):
        raise ValueError(f"unexpected MOF column {col!r}")
    return float(col[:-1])


def parse_file(path: Path) -> pd.DataFrame:
    """One MOF csv -> daily long frame ``obs_date, tenor_years, yield`` (decimal)."""
    raw = Path(path).read_bytes().decode("utf-8-sig", errors="replace").splitlines()
    if not raw or not raw[0].startswith("Interest Rate"):
        raise ValueError(f"{path}: line 1 is not the 'Interest Rate' title")
    df = pd.read_csv(io.StringIO("\n".join(raw[1:])), na_values=["-"], dtype=str)
    if df.columns[0] != "Date":
        raise ValueError(f"{path}: first column {df.columns[0]!r} is not 'Date'")
    dates = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")
    df = df[dates.notna()].copy()  # drops the trailing note line of the current file
    df["obs_date"] = dates[dates.notna()]
    tenor_cols = [c for c in df.columns if c not in ("Date", "obs_date")]
    long = df.melt(id_vars=["obs_date"], value_vars=tenor_cols, var_name="col", value_name="pct")
    long["tenor_years"] = long["col"].map(_tenor)
    long["yield"] = pd.to_numeric(long["pct"], errors="coerce") / 100.0  # percent -> decimal, once
    return long.dropna(subset=["yield"])[["obs_date", "tenor_years", "yield"]]


def parse(paths: list[Path]) -> pd.DataFrame:
    """Both files; on an overlapping day the historical file wins."""
    ordered = sorted(paths, key=lambda p: 0 if "jgbcme_all" in Path(p).stem else 1)
    frames = [parse_file(p) for p in ordered]
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(["obs_date", "tenor_years"], keep="first").reset_index(drop=True)


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, n) for n in FILES]


def load(cfg: dict) -> pd.DataFrame:
    daily = parse(latest_paths())
    monthly = base.month_end_sample(daily)
    df = base.validate_curve(base.to_curveframe(monthly, COUNTRY, CURVE_TYPE, SOURCE))
    base.write_interim(df, COUNTRY)
    checks.write_coverage(df, "observed")
    checks.write_sample_day(daily, COUNTRY, cfg["tenors"])
    return df
