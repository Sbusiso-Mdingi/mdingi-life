"""A dynamic Nelson-Siegel scenario generator (Diebold and Li, 2006): Nelson-Siegel zero curves with a fixed decay,
fitted to bonds month by month, the three factors of each curve as AR(1)s with correlated normal innovations.

research/PROTOCOL_v4.md says how each piece is used.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from mdingilife.curves import Point, _l1, _l2, dv, ns

PHI_CAP = 0.995


def loadings(t, tau: float, n: int = 3) -> np.ndarray:
    t = np.asarray(t, float)
    return np.column_stack([np.ones_like(t), _l1(t / tau), _l2(t / tau)][:n])


def full(beta) -> np.ndarray:
    """(b0, b1, b2) from the first `len(beta)` factors, the rest nil (two factors: level and slope only)."""
    return np.concatenate([beta, np.zeros(3 - len(beta))])


def fit_fixed(pts: list[Point], tau: float, n: int = 3) -> tuple[np.ndarray, float]:
    """The first `n` factors of a Nelson-Siegel zero curve with decay `tau` (b0, b1 and, with n = 3, b2), by least
    squares on price errors over each bond's price change per unit of yield (v2's fit), and the sum of squared yield
    errors."""
    p = np.array([q.price for q in pts])
    w = np.array([dv(q.t, q.cf, q.y) for q in pts])
    y = np.array([q.y for q in pts])
    k = max(len(q.t) for q in pts)
    T = np.ones((len(pts), k))
    CF = np.zeros((len(pts), k))
    for i, q in enumerate(pts):
        T[i, :len(q.t)], CF[i, :len(q.t)] = q.t, q.cf

    def res(b):
        return ((CF * np.exp(-ns(T, *full(b), tau) * T)).sum(axis=1) - p) / w

    z = 2 * np.log1p(y / 2)
    x0 = np.linalg.lstsq(loadings([q.maturity for q in pts], tau, n), z, rcond=None)[0]
    with np.errstate(over="ignore", invalid="ignore"):
        if not np.all(np.isfinite(res(x0))) or np.abs(x0).max() > 1:  # few bonds and a short decay: a flat start
            x0 = np.r_[z.mean(), np.zeros(n - 1)]
        r = least_squares(res, x0, x_scale="jac")
    return r.x, float(np.sum(r.fun ** 2))


@dataclass
class AR1:
    """Independent AR(1)s at a monthly step with jointly normal innovations."""
    mu: np.ndarray
    phi: np.ndarray
    cov: np.ndarray
    capped: np.ndarray

    @classmethod
    def fit(cls, F: np.ndarray) -> "AR1":
        """F: (months, factors), consecutive months, NaN where a month has no curve. Each factor is fitted on its own
        consecutive pairs; the covariance on the months where every factor has a residual."""
        F = np.asarray(F, float)
        n = F.shape[1]
        mu, phi, capped = np.empty(n), np.empty(n), np.zeros(n, bool)
        resid = np.full((len(F) - 1, n), np.nan)
        for j in range(n):
            x, y = F[:-1, j], F[1:, j]
            ok = ~np.isnan(x) & ~np.isnan(y)
            slope, icpt = np.polyfit(x[ok], y[ok], 1)
            if slope > PHI_CAP:
                slope, capped[j] = PHI_CAP, True
                m = np.mean(y[ok] - slope * x[ok]) / (1 - slope)
            else:
                m = icpt / (1 - slope)
            mu[j], phi[j] = m, slope
            resid[ok, j] = y[ok] - m - slope * (x[ok] - m)
        full = ~np.isnan(resid).any(axis=1)
        return cls(mu, phi, np.cov(resid[full], rowvar=False), capped)

    def central(self, start: np.ndarray, months: int) -> np.ndarray:
        """The expected path, (months + 1, factors), starting at `start`."""
        k = np.arange(months + 1)[:, None]
        return self.mu + self.phi ** k * (np.asarray(start) - self.mu)

    def simulate(self, start: np.ndarray, months: int, n: int, rng: np.random.Generator) -> np.ndarray:
        """(n, months + 1, factors) paths starting at `start`."""
        L = np.linalg.cholesky(self.cov)
        out = np.empty((n, months + 1, len(self.mu)))
        out[:, 0] = start
        for m in range(months):
            eps = rng.standard_normal((n, len(self.mu))) @ L.T
            out[:, m + 1] = self.mu + self.phi * (out[:, m] - self.mu) + eps
        return out


def shift_forwards(fwd0: np.ndarray, beta0: np.ndarray, beta: np.ndarray, tau: float) -> np.ndarray:
    """Yearly forwards of the curve z0(T) + NS(beta)(T) - NS(beta0)(T), with z0 the curve behind `fwd0`."""
    T = np.arange(len(fwd0) + 1, dtype=float)
    dz = T * (ns(T, *full(beta), tau) - ns(T, *full(beta0), tau))
    return np.asarray(fwd0) + np.diff(dz)
