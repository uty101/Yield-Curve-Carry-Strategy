"""Step 1.8: the one interpolation function and the Curve object (synthetic)."""

import dataclasses
import math

import numpy as np
import pandas as pd
import pytest

from curvecarry.curves import Curve
from curvecarry.interp import interpolate_yield

T = np.array([1.0, 2.0, 4.0, 10.0])
Y = np.array([0.01, 0.02, 0.04, 0.05])


def test_interp_exact_at_observed() -> None:
    for t, y in zip(T, Y, strict=True):
        assert interpolate_yield(T, Y, t) == y
    assert interpolate_yield(T, Y, T).tolist() == Y.tolist()


def test_interp_midpoint() -> None:
    assert abs(interpolate_yield(np.array([2.0, 4.0]), np.array([0.02, 0.04]), 3.0) - 0.03) < 1e-15
    assert abs(interpolate_yield(T, Y, 7.0) - 0.045) < 1e-15  # halfway between 4y and 10y


def test_interp_never_extrapolates() -> None:
    assert math.isnan(interpolate_yield(np.array([1.0, 30.0]), np.array([0.01, 0.05]), 31.0))
    assert math.isnan(interpolate_yield(np.array([0.25, 30.0]), np.array([0.01, 0.05]), 0.1))
    out = interpolate_yield(T, Y, np.array([0.5, 1.0, 10.0, 10.5]))
    assert math.isnan(out[0]) and out[1] == 0.01 and out[2] == 0.05 and math.isnan(out[3])


def test_interp_needs_two_points() -> None:
    with pytest.raises(ValueError):
        interpolate_yield(np.array([5.0]), np.array([0.03]), 5.0)
    with pytest.raises(ValueError):  # NaNs are dropped first, then counted
        interpolate_yield(np.array([1.0, 2.0, 3.0]), np.array([0.01, np.nan, np.nan]), 1.5)
    got = interpolate_yield(np.array([1.0, 2.0, 3.0]), np.array([0.01, np.nan, 0.03]), 2.0)
    assert got == pytest.approx(0.02, abs=1e-15)


def test_curve_at_flat_short_end_and_nan_long_end() -> None:
    c = Curve(T, Y, "par", "XX", pd.Timestamp("2020-01-31"))
    assert c.at(0.5) == 0.01 and c.at(0.9167) == 0.01  # flat below the shortest observed tenor
    assert c.at(1.0) == 0.01 and abs(c.at(3.0) - 0.03) < 1e-15
    assert math.isnan(c.at(10.01)) and math.isnan(c.at(30.0))
    out = c.at(np.array([0.1, 7.0, 40.0]))
    assert out[0] == 0.01 and abs(out[1] - 0.045) < 1e-15 and math.isnan(out[2])


def test_curve_sorted_nans_dropped_frozen() -> None:
    c = Curve(
        np.array([10.0, np.nan, 1.0, 4.0]),
        np.array([0.05, 0.03, 0.01, np.nan]),
        "zero",
        "XX",
        "2020-01-31",
    )
    assert c.tenors.tolist() == [1.0, 10.0] and c.yields.tolist() == [0.01, 0.05]
    assert c.date == pd.Timestamp("2020-01-31")
    with pytest.raises(ValueError):
        Curve(T, Y, "spot", "XX", "2020-01-31")
    with pytest.raises(ValueError):
        Curve(np.array([1.0, 1.0]), np.array([0.01, 0.02]), "par", "XX", "2020-01-31")
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.country = "YY"  # type: ignore[misc]


def test_curve_from_panel_takes_observed_rows_only() -> None:
    rows = [
        ("2020-01-31", "XX", 1.0, 0.01, "par", "s", False, True),
        ("2020-01-31", "XX", 2.0, 0.02, "par", "s", True, True),  # interpolated: excluded
        ("2020-01-31", "XX", 3.0, 0.03, "par", "s", False, True),
        ("2020-01-31", "XX", 15.0, 0.04, "par", "s", False, False),  # non-standard: included
        ("2020-02-29", "XX", 1.0, 0.09, "par", "s", False, True),
        ("2020-01-31", "YY", 1.0, 0.09, "zero", "s", False, True),
    ]
    panel = pd.DataFrame(
        rows,
        columns=[
            "date",
            "country",
            "tenor_years",
            "yield",
            "curve_type",
            "source",
            "interpolated",
            "standard",
        ],
    )
    panel["date"] = pd.to_datetime(panel["date"])
    c = Curve.from_panel(panel, "XX", pd.Timestamp("2020-01-31"))
    assert c.tenors.tolist() == [1.0, 3.0, 15.0] and c.curve_type == "par"
    with pytest.raises(ValueError):
        Curve.from_panel(panel, "ZZ", pd.Timestamp("2020-01-31"))
