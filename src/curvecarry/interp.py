"""The one interpolation function (global rule 13).

Linear in yield against tenor, between the two adjacent observed tenors
only; exact at an observed tenor; NaN for any target outside
``[tenors.min(), tenors.max()]`` — never extrapolated. NaN inputs are
dropped first. The flat short end below the shortest observed tenor
(``config.short_end``) is not here: it lives in ``Curve.at`` and nowhere
else, so that this function can never be the source of a value off the
observed range.
"""

from __future__ import annotations

import numpy as np


def interpolate_yield(
    tenors: np.ndarray, yields: np.ndarray, target: float | np.ndarray
) -> float | np.ndarray:
    """Linear interpolation in tenor; NaN outside the observed range; needs 2 finite points."""
    t = np.asarray(tenors, dtype="float64")
    y = np.asarray(yields, dtype="float64")
    if t.shape != y.shape:
        raise ValueError(f"tenors {t.shape} and yields {y.shape} differ in shape")
    keep = np.isfinite(t) & np.isfinite(y)
    t, y = t[keep], y[keep]
    if t.size < 2:
        raise ValueError(f"interpolation needs at least 2 finite points, got {t.size}")
    order = np.argsort(t)
    t, y = t[order], y[order]
    if np.any(np.diff(t) == 0):
        raise ValueError("duplicate tenors")
    x = np.asarray(target, dtype="float64")
    out = np.interp(x, t, y)
    out = np.where((x < t[0]) | (x > t[-1]), np.nan, out)
    return float(out) if np.ndim(target) == 0 else out
