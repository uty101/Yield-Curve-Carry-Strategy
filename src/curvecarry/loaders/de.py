"""Germany: Bundesbank Svensson parameters for listed Federal securities (step 1.3).

Six daily parameter series from the Bundesbank API (``BBSIS`` dataflow):
``B0 B1 B2 B3`` (percent) and ``T1 T2`` (decay times, years), from 1997-08,
plus the Bundesbank's own published 10-year spot rate (``ZI … R10XX``,
percent) as the check series for the 1 bp reconstruction test. The curve at
0.25, 0.5 and the 8 standard tenors is reconstructed daily from the
parameters with ``curvecarry.svensson.svensson_yield``.

Compounding: the Bundesbank's Svensson spot rates are annually compounded
(Discussion Paper 4/97, eq. 6 and 23: ``DF = (1+z)^-m``), so no conversion
is applied (``decisions/compounding.md``). ``curve_type = zero``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from curvecarry import checks, manifest
from curvecarry.loaders import base
from curvecarry.svensson import svensson_yield

SOURCE = "bundesbank"
COUNTRY = "DE"
CURVE_TYPE = "zero"
URL = (
    "https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
    "D.I.ZST.{p}.EUR.S1311.B.A604.{r}.R.A.A._Z._Z.A?format=csv&lang=en"
)
PARAMS = ["B0", "B1", "B2", "B3", "T1", "T2"]
CHECK = "Y10"  # the published 10-year spot rate
CODES: dict[str, tuple[str, str]] = {**{p: (p, "_Z") for p in PARAMS}, CHECK: ("ZI", "R10XX")}
COLUMNS = {"B0": "beta0", "B1": "beta1", "B2": "beta2", "B3": "beta3", "T1": "tau1", "T2": "tau2"}
RECON_TENORS = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2},")


def fetch(cfg: dict) -> list[Path]:
    out = []
    for name, (p, r) in CODES.items():
        url = URL.format(p=p, r=r)
        content = manifest.fetch_bytes(url)
        path = manifest.raw_path(SOURCE, name, "csv", base.today())
        manifest.write_raw(content, path, url, SOURCE)
        out.append(path)
    return out


def read_series(path: Path) -> pd.Series:
    """One Bundesbank csv -> Series indexed by obs_date (raw units); header lines skipped."""
    rows = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            if _DATA.match(line):
                d, v, *_ = line.rstrip("\n").split(",")
                rows.append((d, float(v) if v not in (".", "") else float("nan")))
    if not rows:
        raise ValueError(f"{path}: no data lines matching YYYY-MM-DD,")
    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]), name=path.stem)
    return s.dropna()


def parse_params(paths: list[Path]) -> pd.DataFrame:
    """The six parameter files -> daily ``obs_date, beta0..beta3 (decimal), tau1, tau2 (years)``."""
    by_name = {}
    for p in paths:
        name = (
            manifest._split_stem(Path(p))[0]
            if re.search(r"_\d{8}$", Path(p).stem)
            else Path(p).stem
        )
        if name in PARAMS:
            by_name[name] = read_series(p)
    missing = [p for p in PARAMS if p not in by_name]
    if missing:
        raise ValueError(f"missing parameter files: {missing}")
    df = pd.concat({COLUMNS[k]: by_name[k] for k in PARAMS}, axis=1).dropna()
    for c in ("beta0", "beta1", "beta2", "beta3"):
        df[c] = df[c] / 100.0  # percent -> decimal, once
    return df.rename_axis("obs_date").reset_index()


def reconstruct(params: pd.DataFrame, tenors: list[float] = RECON_TENORS) -> pd.DataFrame:
    """Daily parameters -> long frame ``obs_date, tenor_years, yield`` at ``tenors``."""
    frames = []
    for t in tenors:
        y = svensson_yield(
            t,
            params["beta0"].to_numpy(),
            params["beta1"].to_numpy(),
            params["beta2"].to_numpy(),
            params["beta3"].to_numpy(),
            params["tau1"].to_numpy(),
            params["tau2"].to_numpy(),
        )
        frames.append(pd.DataFrame({"obs_date": params["obs_date"], "tenor_years": t, "yield": y}))
    return pd.concat(frames, ignore_index=True)


def parse(paths: list[Path]) -> pd.DataFrame:
    return reconstruct(parse_params(paths))


def latest_paths() -> list[Path]:
    return [manifest.latest_raw(SOURCE, n) for n in CODES]


def load(cfg: dict) -> pd.DataFrame:
    paths = latest_paths()
    params = parse_params(paths)
    monthly = base.month_end_sample(reconstruct(params))
    df = base.validate_curve(base.to_curveframe(monthly, COUNTRY, CURVE_TYPE, SOURCE))
    base.write_interim(df, COUNTRY)
    checks.write_coverage(df, "observed")
    # month-end sampled parameters: the Phase 2 Svensson benchmark
    p = params.copy()
    p["date"] = base.month_end(p["obs_date"])
    p = p.sort_values("obs_date").groupby("date", as_index=False).last()
    base.INTERIM.mkdir(parents=True, exist_ok=True)
    p[["date", "obs_date", "beta0", "beta1", "beta2", "beta3", "tau1", "tau2"]].to_parquet(
        base.INTERIM / "svensson_params_de.parquet", index=False
    )
    return df
