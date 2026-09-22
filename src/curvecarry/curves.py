"""The Curve object (PLAN.md, Conventions), built in step 1.8 with the interpolator it uses.

A frozen dataclass: ``tenors``, ``yields`` (decimal, annual compounding),
``curve_type`` (``zero`` | ``par``), ``country``, ``date``; sorted by tenor,
NaNs dropped. ``Curve.at(t)`` is the one place the flat short end lives:
``interpolate_yield`` inside ``[tenors.min(), tenors.max()]``, ``yields[0]``
below ``tenors.min()`` (``config.short_end = "flat"``, amendment B), NaN
above ``tenors.max()`` (rule 13). ``Curve.from_panel`` takes every observed
tenor of a country-month, standard or not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from curvecarry.interp import interpolate_yield

CURVE_TYPES = ("zero", "par")


@dataclass(frozen=True)
class Curve:
    tenors: np.ndarray
    yields: np.ndarray
    curve_type: str
    country: str
    date: pd.Timestamp

    def __post_init__(self) -> None:
        object.__setattr__(self, "date", pd.Timestamp(self.date))
        if self.curve_type not in CURVE_TYPES:
            raise ValueError(f"curve_type must be zero or par, got {self.curve_type!r}")
        t = np.asarray(self.tenors, dtype="float64")
        y = np.asarray(self.yields, dtype="float64")
        if t.shape != y.shape:
            raise ValueError("tenors and yields differ in shape")
        keep = np.isfinite(t) & np.isfinite(y)
        order = np.argsort(t[keep])
        t, y = t[keep][order], y[keep][order]
        if t.size == 0:
            raise ValueError(f"{self.country} {self.date.date()}: no finite points")
        if np.any(np.diff(t) == 0):
            raise ValueError(f"{self.country} {self.date.date()}: duplicate tenors")
        t.setflags(write=False)
        y.setflags(write=False)
        object.__setattr__(self, "tenors", t)
        object.__setattr__(self, "yields", y)

    @classmethod
    def from_panel(cls, panel: pd.DataFrame, country: str, date: pd.Timestamp) -> Curve:
        """All observed tenors of that country-month (``interpolated == False`` rows if the
        column exists, else every row)."""
        g = panel[(panel["country"] == country) & (panel["date"] == pd.Timestamp(date))]
        if "interpolated" in g.columns:
            g = g[~g["interpolated"].astype(bool)]
        if g.empty:
            raise ValueError(f"no rows for {country} {pd.Timestamp(date).date()}")
        types = set(g["curve_type"].unique())
        if len(types) != 1:
            raise ValueError(f"{country} {pd.Timestamp(date).date()}: mixed curve types {types}")
        return cls(
            tenors=g["tenor_years"].to_numpy(),
            yields=g["yield"].to_numpy(),
            curve_type=types.pop(),
            country=country,
            date=pd.Timestamp(date),
        )

    def at(self, tenor: float | np.ndarray) -> float | np.ndarray:
        """Yield at ``tenor``: interpolated inside the observed range, flat below the
        shortest observed tenor, NaN above the longest."""
        x = np.asarray(tenor, dtype="float64")
        if self.tenors.size == 1:
            inside = np.full(x.shape, np.nan)
        else:
            inside = np.asarray(interpolate_yield(self.tenors, self.yields, x), dtype="float64")
        out = np.where(x < self.tenors[0], self.yields[0], inside)
        out = np.where(x > self.tenors[-1], np.nan, out)
        return float(out) if np.ndim(tenor) == 0 else out
