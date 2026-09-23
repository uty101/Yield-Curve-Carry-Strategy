"""Step 5.3: the performance metrics, and (5.5) the deflated Sharpe.

Everything here is arithmetic on a monthly excess-return series. The series
is already an excess return over each bucket's own funding rate (4.2, 4.3),
so **no risk-free rate is subtracted anywhere**: the Sharpe is
``annualised_return / annualised_vol`` and nothing else.

- ``annualised_return = mean(r) * 12`` - arithmetic, not geometric, and
  stated as such on every row that reports it.
- ``annualised_vol = std(r, ddof=1) * sqrt(12)``.
- ``max_drawdown`` is computed on the wealth index ``prod(1 + r)``, and comes
  back with the peak date and the trough date, because a drawdown number
  without its dates cannot be checked against anything.
- ``year_2022`` is the same four numbers on the twelve months of 2022 alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS = 12
ANNUALISATION = "arithmetic: mean x 12"


@dataclass(frozen=True)
class Drawdown:
    depth: float
    peak_date: pd.Timestamp | None
    trough_date: pd.Timestamp | None


def annualised_return(r: pd.Series) -> float:
    return float(r.mean() * MONTHS) if len(r) else float("nan")


def annualised_vol(r: pd.Series) -> float:
    return float(r.std(ddof=1) * math.sqrt(MONTHS)) if len(r) > 1 else float("nan")


def sharpe(r: pd.Series) -> float:
    """No risk-free subtraction: ``r`` is already an excess return."""
    vol = annualised_vol(r)
    if not np.isfinite(vol) or vol == 0.0:
        return float("nan")
    return annualised_return(r) / vol


def max_drawdown(r: pd.Series) -> Drawdown:
    """Deepest peak-to-trough fall of ``prod(1 + r)``, with both dates.

    The running peak starts at **1.0, the level at inception**, so a series
    that falls in its first month is in drawdown from that first month. A
    peak of inception has no date in the series, and ``peak_date`` is then
    ``None`` (the metrics table writes it as an empty cell).
    """
    if len(r) == 0:
        return Drawdown(float("nan"), None, None)
    wealth = (1.0 + r).cumprod()
    running = np.maximum(wealth.cummax(), 1.0)
    dd = wealth / running - 1.0
    trough = dd.idxmin()
    depth = float(dd.loc[trough])
    if depth == 0.0:
        return Drawdown(0.0, None, None)
    before = wealth.loc[:trough]
    peak = before.idxmax() if float(before.max()) >= float(running.loc[trough]) else None
    return Drawdown(depth, peak, trough)


def turnover_mean(turnover: pd.Series) -> float:
    return float(turnover.mean()) if len(turnover) else float("nan")


def summary(r: pd.Series, turnover: pd.Series | None = None) -> dict[str, float | str]:
    """The metric block of one return series."""
    dd = max_drawdown(r)
    out: dict[str, float | str] = {
        "ann_return": annualised_return(r),
        "ann_vol": annualised_vol(r),
        "sharpe": sharpe(r),
        "max_dd": dd.depth,
        "dd_peak": dd.peak_date.date().isoformat() if dd.peak_date is not None else "",
        "dd_trough": dd.trough_date.date().isoformat() if dd.trough_date is not None else "",
        "n_months": float(len(r)),
    }
    if turnover is not None:
        out["turnover"] = turnover_mean(turnover)
    year = r[r.index.year == 2022] if isinstance(r.index, pd.DatetimeIndex) else r.iloc[:0]
    out["ret_2022"] = annualised_return(year)
    out["vol_2022"] = annualised_vol(year)
    out["sharpe_2022"] = sharpe(year)
    out["dd_2022"] = max_drawdown(year).depth
    out["n_months_2022"] = float(len(year))
    return out


# ------------------------------------------------------- the deflated Sharpe

EULER_GAMMA = 0.5772156649015329
NORMAL_KURTOSIS = 3.0  # ``kurt`` is raw, not excess


def deflated_sharpe(
    sr_monthly: float,
    sr_var_trials: float,
    n_trials: int,
    t_months: int,
    skew: float,
    kurt: float,
) -> tuple[float, float]:
    """``(SR0, DSR)`` - Bailey & Lopez de Prado (2014), per period (monthly).

    ``SR0 = sqrt(V[SR]) * [(1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N e))]``
    with ``g`` the Euler-Mascheroni constant, and

    ``DSR = Phi((SR - SR0) sqrt(T - 1) / sqrt(1 - g3 SR + (g4 - 1)/4 SR^2))``

    where ``g3`` is the skew and ``g4`` the **raw** kurtosis (3 for a normal).
    ``SR0 = 0`` when ``N <= 1`` or ``V[SR] = 0``: with one trial there is no
    selection to deflate.

    ``N`` is never an argument of the caller's choosing - ``report.metrics_table``
    takes it from ``speclog.count_runs()``, the row count of
    ``reports/specifications.csv`` (global rule 6).
    """
    from scipy.stats import norm

    if n_trials <= 1 or sr_var_trials <= 0.0:
        sr0 = 0.0
    else:
        n = float(n_trials)
        sr0 = math.sqrt(sr_var_trials) * (
            (1.0 - EULER_GAMMA) * float(norm.ppf(1.0 - 1.0 / n))
            + EULER_GAMMA * float(norm.ppf(1.0 - 1.0 / (n * math.e)))
        )
    denominator = 1.0 - skew * sr_monthly + (kurt - 1.0) / 4.0 * sr_monthly**2
    if t_months <= 1 or denominator <= 0.0:
        return sr0, float("nan")
    z = (sr_monthly - sr0) * math.sqrt(t_months - 1) / math.sqrt(denominator)
    return sr0, float(norm.cdf(z))


def monthly_sharpe(r: pd.Series) -> float:
    """The per-period Sharpe the deflated Sharpe takes: ``mean(r) / sd(r)``, ddof 1."""
    if len(r) < 2:
        return float("nan")
    sd = float(r.std(ddof=1))
    if sd == 0.0:
        return float("nan")
    return float(r.mean()) / sd
