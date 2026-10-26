"""SAM standard formula pieces (PA Financial Soundness Standards for Insurers, version 1, 1 July 2018): shocked
curves, a monthly projection of policies in force, and the correlation aggregation.

Parameters are quoted from the standards with their section; research/PROTOCOL_v3.md says where each is used.
"""
from __future__ import annotations

import numpy as np

# FSI 4.1 Attachment 3: relative shocks to annual spot rates by term, held at the 30-year value beyond (A.4, B.4).
TERMS = np.array([0.25, 0.5] + list(range(1, 31)), float)
NOMINAL_UP = np.array([78.55, 78.55, 93.08, 82.38, 64.68, 51.24, 42.12, 36.49, 33.19, 31.19, 29.88, 29.08, 28.80,
                       28.99, 29.55, 30.36, 31.35, 32.51, 33.80, 35.20, 36.66, 38.16, 39.67, 41.15, 42.57, 43.91,
                       45.18, 46.59, 48.03, 49.31, 50.22, 50.57]) / 100
NOMINAL_DOWN = -np.array([48.06, 48.06, 52.87, 50.73, 44.65, 38.86, 34.37, 31.37, 29.55, 28.45, 27.74, 27.30, 27.14,
                          27.26, 27.62, 28.12, 28.74, 29.46, 30.24, 31.09, 31.95, 32.82, 33.68, 34.52, 35.32, 36.07,
                          36.78, 37.57, 38.38, 39.09, 39.60, 39.79]) / 100
REAL = np.array([75.89, 75.89, 75.89, 75.89, 67.36, 65.52, 63.95, 61.17, 58.22, 56.74, 54.07, 54.81, 54.50, 53.56,
                 53.89, 54.89, 55.33, 54.40, 53.02, 52.27, 52.23, 52.72, 53.60, 54.81, 56.32, 58.10, 60.11, 62.29,
                 64.42, 66.25, 67.54, 68.02]) / 100
SHOCKS = {("nominal", "up"): NOMINAL_UP, ("nominal", "down"): NOMINAL_DOWN,
          ("real", "up"): REAL, ("real", "down"): -REAL}
MIN_SHIFT = 0.01  # §5.11

# FSI 4.2 §4.9, in the order mortality, longevity, lapse, expense, catastrophe (disability and retrenchment are nil).
LIFE = ("mortality", "longevity", "lapse", "expense", "catastrophe")
CORR_LIFE = np.array([[1.00, -0.25, 0.00, 0.25, 0.25],
                      [-0.25, 1.00, 0.25, 0.25, 0.00],
                      [0.00, 0.25, 1.00, 0.00, 0.25],
                      [0.25, 0.25, 0.00, 1.00, 0.25],
                      [0.25, 0.00, 0.25, 0.25, 1.00]])
CORR_NOMINAL_REAL = 0.25  # FSI 4.1 §5.6
CORR_MARKET_LIFE = 0.25   # FSI 4 §6.3
MORTALITY_UP = 0.15       # FSI 4.2 §5.3
LONGEVITY_LEVEL, LONGEVITY_TREND = 0.10, 0.01  # §6.3
LAPSE_LEVEL, MASS_LAPSE = 0.50, 0.40           # §8.6, §8.5 (individual business)
EXPENSE_LEVEL, INFLATION_ADD, INFLATION_REL = 0.10, 0.02, 0.20  # §9.4
COC = 0.06                # FSI 2.2 §14.14
OP_CAP, OP_PREMIUMS, OP_PROVISIONS = 0.30, 0.04, 0.0045  # FSI 4.4 §4.5, §5.2, §5.5


def aggregate(x, corr) -> float:
    x = np.asarray(x, float)
    return float(np.sqrt(x @ corr @ x))


def pair(a: float, b: float, rho: float) -> float:
    return float(np.sqrt(a * a + b * b + 2 * rho * a * b))


class Curve:
    """Discount factors from yearly continuously compounded forwards (zero rate times term linear within each
    year, as in v2), optionally shocked as FSI 4.1 §5.11 to §5.12 set out."""

    def __init__(self, forwards, kind: str = "nominal", shock: str | None = None):
        self.fwd = np.asarray(forwards, float)
        self.kind, self.shock = kind, shock
        self._cum = np.concatenate([[0.0], np.cumsum(self.fwd)])

    def zt(self, t):
        t = np.asarray(t, float)
        if np.any(t > len(self.fwd)):
            raise ValueError(f"curve has forwards for {len(self.fwd)} years only")
        return np.interp(t, np.arange(len(self._cum)), self._cum)

    def spot(self, t):
        """Annual spot rate at term t (after the shock, if any)."""
        t = np.maximum(np.asarray(t, float), 1e-9)
        i = np.expm1(self.zt(t) / t)
        if self.shock is None:
            return i
        s = np.interp(t, TERMS, SHOCKS[self.kind, self.shock])  # flat below 0.25 and beyond 30 years
        move = i * s
        move = np.where(self.shock == "up", np.maximum(move, MIN_SHIFT), np.minimum(move, -MIN_SHIFT))
        out = i + move
        return np.maximum(out, 0.0) if self.kind == "nominal" else out

    def df(self, t):
        t = np.asarray(t, float)
        if self.shock is None:
            return np.exp(-self.zt(t))
        return np.where(t > 0, (1 + self.spot(t)) ** -t, 1.0)


def breakeven(nominal: Curve, real: Curve, term: float = 30.0) -> float:
    """Annual inflation from the nominal and real zero rates at `term`."""
    return float((1 + nominal.spot(term)) / (1 + real.spot(term)) - 1)


def cat_addition(q_month):
    """FSI 4.2 §10.5: addition to a monthly mortality rate, both as probabilities."""
    per_mille = 1000 * np.asarray(q_month, float)
    return 4 * np.minimum(np.maximum(0.2 * per_mille + 0.105, 0.125), 0.3) / 1000


def project(mu, lapse=None, mass: float = 0.0, cat: bool = False):
    """Policies in force at the start of each month and deaths in each month, per policy in force today.

    mu and lapse: (cells, years), the force of mortality and the annual lapse rate in each year ahead. Deaths happen
    at mid-month with probability 1 - exp(-mu/12); lapses at the end of the month among the survivors. `mass` lapses
    that share at once, before the first month; `cat` adds the §10.5 addition in the first three months.
    """
    mu = np.asarray(mu, float)
    cells, years = mu.shape
    qd = -np.expm1(-mu / 12)
    ql = np.zeros_like(qd) if lapse is None else 1 - (1 - np.minimum(lapse, 1.0)) ** (1 / 12)
    l = np.full(cells, 1.0 - mass)
    inforce, deaths = np.empty((cells, 12 * years)), np.empty((cells, 12 * years))
    for k in range(12 * years):
        y = k // 12
        q = qd[:, y]
        if cat and k < 3:
            q = np.minimum(q + cat_addition(q), 1.0)
        inforce[:, k] = l
        deaths[:, k] = l * q
        l = (l - deaths[:, k]) * (1 - ql[:, y])
    return inforce, deaths
