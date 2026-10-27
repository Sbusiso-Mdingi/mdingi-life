"""v5's inflation model for the rising funeral benefit (research/PROTOCOL_v5.md, "The rising-benefit option").

One-year inflation i(t) = f + x(t): f the 30-year breakeven held flat, x(t + 1/12) = phi x(t) + eps with x(0) = 0.
The increase on the k-th anniversary is the year's inflation, i(k - 1), the one-year breakeven at the start of the
year (as v4 applies inflation to the inflation-linked annuities), floored and capped.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SEED, PATHS = 20261029, 10_000
CAP, FLOOR = 0.06, 0.0
VOL_RISE = 0.10                        # FSI 4.1 §5.17 to 5.18: 0.1 / sqrt(t) on the volatility, step (b) in full
PRICING_GROWTH = 0.05


@dataclass(frozen=True)
class Model:
    phi: float
    sigma: float                       # of eps, a month

    @classmethod
    def fit(cls, i: np.ndarray) -> "Model":
        """Least squares of i(t + 1/12) on 1 and i(t), over consecutive months present (NaN for a missing month)."""
        i = np.asarray(i, float)
        ok = ~np.isnan(i[1:]) & ~np.isnan(i[:-1])
        y, x = i[1:][ok], i[:-1][ok]
        X = np.column_stack([np.ones_like(x), x])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ coef
        return cls(float(coef[1]), float(np.sqrt(res @ res / (len(y) - 2))))

    def sd(self, years: np.ndarray) -> np.ndarray:
        """The standard deviation of x at each term in years (whole months)."""
        n = np.rint(12 * np.asarray(years, float))
        return self.sigma * np.sqrt((1 - self.phi ** (2 * n)) / (1 - self.phi ** 2))


def paths(model: Model, years: int, n: int = PATHS, seed: int = SEED) -> np.ndarray:
    """x at the anniversaries 0, 1, ..., years - 1 (the start of each year): (n, years). x(0) = 0."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, years))
    x = np.zeros(n)
    for m in range(1, 12 * (years - 1) + 1):
        x = model.phi * x + model.sigma * rng.standard_normal(n)
        if m % 12 == 0:
            out[:, m // 12] = x
    return out


def shock_scale(model: Model, f: float, years: int) -> np.ndarray:
    """The factor on x at each anniversary that raises its standard deviation by VOL_RISE f / sqrt(t) (none at 0)."""
    t = np.arange(years, dtype=float)
    s = model.sd(t)
    out = np.ones(years)
    out[1:] = 1 + VOL_RISE * f / (np.sqrt(t[1:]) * s[1:])
    return out


def growth(f: float, x: np.ndarray, cap: float | None = CAP, floor: float | None = FLOOR,
           scale: np.ndarray | None = None, se: bool = False):
    """G(n), n = 0, 1, ..., years: the mean over paths of the product of 1 + clip(f + x, floor, cap) over the
    anniversaries 1 to n (the increase on anniversary k from x at k - 1). `cap` or `floor` None leaves it out.
    With `se`, also the simulation's standard error of each G(n)."""
    xs = x if scale is None else x * scale[None, :]
    i = f + xs
    i = np.clip(i, -np.inf if floor is None else floor, np.inf if cap is None else cap)
    prod = np.cumprod(1 + i, axis=1)
    g = np.r_[1.0, prod.mean(axis=0)]
    if not se:
        return g
    return g, np.r_[0.0, prod.std(axis=0, ddof=1) / np.sqrt(len(prod))]


def monthly(g: np.ndarray, months: int) -> np.ndarray:
    """G for each month 0, 1, ...: the benefit is level within a year, so month m has G(m // 12)."""
    k = np.arange(months) // 12
    return g[np.minimum(k, len(g) - 1)]
