"""Old-age extension: m(x) = c exp(d x) / (1 + c exp(d x)) (Kannisto), fitted on ages 80 to 89.

Fitted by least squares on logit m, separately for every year (and every simulated path), so the tail moves with
the forecast. Works on any array whose second-last axis is age.
"""
from __future__ import annotations

import numpy as np

FIT_AGES, TOP = range(80, 90), 120


def fit(log_m: np.ndarray, ages: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sel = np.isin(ages, list(FIT_AGES))
    if sel.sum() != len(FIT_AGES):
        raise ValueError("Kannisto needs every age from 80 to 89")
    x = ages[sel].astype(float)
    m = np.exp(np.take(log_m, np.flatnonzero(sel), axis=-2))
    y = np.log(m / (1 - m))
    xm = x - x.mean()
    d = (np.moveaxis(y, -2, -1) @ xm) / (xm ** 2).sum()
    logc = y.mean(axis=-2) - d * x.mean()
    return logc, d


def extend(log_m: np.ndarray, ages: np.ndarray, top: int = TOP) -> tuple[np.ndarray, np.ndarray]:
    """Rates up to age 89 as given; Kannisto from 90 to `top`."""
    logc, d = fit(log_m, ages)
    keep = ages < 90
    old = np.arange(90, top + 1, dtype=float)
    eta = logc[..., None, :] + d[..., None, :] * old[:, None]
    tail = eta - np.log1p(np.exp(eta))
    out = np.concatenate([np.compress(keep, log_m, axis=-2), tail], axis=-2)
    return np.concatenate([ages[keep], old.astype(int)]), out
