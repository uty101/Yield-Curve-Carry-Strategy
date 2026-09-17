"""Step 1.3: Germany loader on tests/fixtures/bundesbank/*.csv (header + 50 rows each)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from curvecarry.loaders import base, de
from curvecarry.svensson import svensson_yield

FIX = Path("tests/fixtures/bundesbank")
PARAM_PATHS = [FIX / f"{p}.csv" for p in de.PARAMS]


@pytest.fixture(scope="module")
def params() -> pd.DataFrame:
    return de.parse_params(PARAM_PATHS)


@pytest.fixture(scope="module")
def frame(params: pd.DataFrame) -> pd.DataFrame:
    monthly = base.month_end_sample(de.reconstruct(params))
    return base.validate_curve(base.to_curveframe(monthly, "DE", "zero", "bundesbank"))


def test_units_de(frame: pd.DataFrame, params: pd.DataFrame) -> None:
    assert frame["yield"].between(-0.05, 0.5).all()
    assert frame["yield"].max() > 0.001
    assert params["beta0"].abs().max() < 1.0  # betas were percent, now decimal
    assert params["tau1"].min() > 0 and params["tau2"].min() > 0  # decay times in years, untouched


def test_tenors_de(frame: pd.DataFrame) -> None:
    assert set(frame["tenor_years"]) == {0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30}
    assert frame["curve_type"].eq("zero").all()


def test_dates_de(frame: pd.DataFrame) -> None:
    assert frame["date"].equals(base.month_end(frame["date"]))
    for _, g in frame.groupby("tenor_years"):
        assert g["date"].is_monotonic_increasing and g["date"].is_unique


def test_no_duplicates_de(frame: pd.DataFrame) -> None:
    assert not frame.duplicated(["date", "country", "tenor_years"]).any()


def test_reconstruct_published_10y_within_1bp(params: pd.DataFrame) -> None:
    published = de.read_series(FIX / "Y10.csv") / 100.0  # percent -> decimal, check series
    recon = de.reconstruct(params, [10.0]).set_index("obs_date")["yield"]
    both = pd.concat([recon.rename("recon"), published.rename("pub")], axis=1).dropna()
    assert len(both) >= 20
    rng = np.random.default_rng(0)
    pick = rng.choice(len(both), 20, replace=False)
    diff = (both["recon"].iloc[pick] - both["pub"].iloc[pick]).abs()
    assert (diff <= 1e-4).all(), diff.max()


def test_svensson_yield_limits() -> None:
    b = dict(beta0=0.04, beta1=-0.02, beta2=0.01, beta3=0.005, tau1=1.5, tau2=8.0)
    assert svensson_yield(1e8, **b) == pytest.approx(0.04, abs=1e-8)
    assert svensson_yield(1e-9, **b) == pytest.approx(0.04 - 0.02, abs=1e-8)


def test_no_value_rows_are_dropped_not_zero() -> None:
    s = de.read_series(FIX / "B0.csv")
    assert s.index.min() == pd.Timestamp("1997-08-07")  # 1997-08-01..06 are "No value available"
    assert (s != 0).all()
