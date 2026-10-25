"""Forecast scores from the protocol: Poisson deviance, annuity factor error at 65, interval coverage."""
from __future__ import annotations

import numpy as np

from mdingilife import annuity, kannisto

RATE, AGE, LEVEL = 0.04, 65, 0.95


def deviance(D: np.ndarray, Dh: np.ndarray) -> float:
    """Poisson deviance of observed deaths D against forecast deaths Dh (forecast rate times observed exposure)."""
    D, Dh = np.asarray(D, float), np.asarray(Dh, float)
    t = np.where(D > 0, D * np.log(np.where(D > 0, D, 1) / Dh), 0.0)
    return float(2 * (t - (D - Dh)).sum())


def annuity_error(log_m_fc: np.ndarray, log_m_obs: np.ndarray, ages: np.ndarray, rate: float = RATE) -> np.ndarray:
    """Period annuity factor at 65 from forecast rates over the one from observed rates, minus 1, per year.

    Inputs are (ages, years) on ages up to 89; both are extended to 120 the same way.
    """
    out = []
    for lm in (log_m_fc, log_m_obs):
        full_ages, full = kannisto.extend(lm, ages)
        out.append(annuity.factor(annuity.period(full.T, full_ages, AGE), rate))
    return out[0] / out[1] - 1


def coverage(log_m_obs: np.ndarray, sims: np.ndarray, level: float = LEVEL) -> float:
    """Share of observed log rates inside the central `level` interval of the simulated paths (axis 0)."""
    lo, hi = np.quantile(sims, [(1 - level) / 2, (1 + level) / 2], axis=0)
    return float(((log_m_obs >= lo) & (log_m_obs <= hi)).mean())
