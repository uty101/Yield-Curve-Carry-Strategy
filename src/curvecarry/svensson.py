"""The Svensson (1994) spot-rate function, in the Bundesbank's decay-time form.

    z(m) = b0 + b1 (1 - e^{-m/t1})/(m/t1)
              + b2 [(1 - e^{-m/t1})/(m/t1) - e^{-m/t1}]
              + b3 [(1 - e^{-m/t2})/(m/t2) - e^{-m/t2}]

with ``m`` the maturity in years and ``t1, t2`` decay *times* in years
(``lambda = 1 / t`` in the lambda form of step 2.3). Deutsche Bundesbank,
Monthly Report October 1997 and Discussion Paper 4/97 (Schich); the
Bundesbank's z is an annually compounded spot rate (``decisions/compounding.md``).
Step 2.3 adds the lambda-form loadings and the fitter to this module.
"""

from __future__ import annotations

import numpy as np


def _term(m: np.ndarray, t: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = m / t
    slope = np.where(x == 0, 1.0, (1.0 - np.exp(-x)) / np.where(x == 0, 1.0, x))
    return slope, slope - np.exp(-x)


def svensson_yield(
    m: float | np.ndarray,
    beta0: float | np.ndarray,
    beta1: float | np.ndarray,
    beta2: float | np.ndarray,
    beta3: float | np.ndarray,
    tau1: float | np.ndarray,
    tau2: float | np.ndarray,
) -> np.ndarray:
    """Spot rate at maturity ``m`` (years); units follow the betas (decimal in, decimal out)."""
    m = np.asarray(m, dtype=float)
    s1, c1 = _term(m, np.asarray(tau1, dtype=float))
    _, c2 = _term(m, np.asarray(tau2, dtype=float))
    return beta0 + beta1 * s1 + beta2 * c1 + beta3 * c2
