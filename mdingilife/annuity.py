"""Life annuity factors: 1 a year paid monthly in advance, no guarantee period.

The force of mortality is constant within each year of age. Nobody survives past the last age given.
"""
from __future__ import annotations

import numpy as np


def factor(m: np.ndarray, rate: float | None = None, adj: float = 1.0, forwards: np.ndarray | None = None) -> np.ndarray:
    """Annuity factor for a life at the first age of `m` (last axis: successive years of age).

    Discounting is at a flat annual `rate`, or at `forwards`, the continuously compounded forward rate for each
    year ahead (from a zero curve), constant within the year like the force of mortality.
    adj multiplies every rate, standing in for the lighter mortality of people who buy annuities.
    """
    mu = adj * np.asarray(m, float)
    n = mu.shape[-1]
    delta = np.full(n, np.log1p(rate)) if forwards is None else np.asarray(forwards, float)[:n]
    if len(delta) < n:
        raise ValueError(f"need forward rates for {n} years")
    cum = lambda x: np.concatenate([np.zeros(x.shape[:-1] + (1,)), np.cumsum(x, axis=-1)[..., :-1]], axis=-1)
    alive = np.exp(-cum(mu))
    f = delta + mu
    months = (1 - np.exp(-f)) / (1 - np.exp(-f / 12))
    return (np.exp(-cum(delta)) * alive * months).sum(axis=-1) / 12


def cohort(log_m: np.ndarray, ages: np.ndarray, age: int, start: int) -> np.ndarray:
    """Rates along the diagonal of a forecast: `age` in forecast year `start` (0 = first year ahead), then a
    year older each year. Second-last axis is age, last is year ahead."""
    i0 = int(np.flatnonzero(ages == age)[0])
    n = len(ages) - i0
    if start + n > log_m.shape[-1]:
        raise ValueError(f"forecast needs at least {start + n} years ahead")
    i, j = i0 + np.arange(n), start + np.arange(n)
    return np.exp(log_m[..., i, j])


def period(log_m: np.ndarray, ages: np.ndarray, age: int) -> np.ndarray:
    """Rates of one calendar year from `age` upwards (age is the last axis of the input)."""
    return np.exp(log_m[..., ages >= age])
