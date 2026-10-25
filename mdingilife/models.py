"""Stochastic mortality models: B0, Lee-Carter, Cairns-Blake-Dowd and Renshaw-Haberman.

Every model is fitted to one `Rates` panel (one sex, ages in rows, years in columns) and forecasts log central
death rates as an array of shape (paths, ages, years ahead). Parameter uncertainty comes from `bootstrap.py`;
`forecast` alone gives process uncertainty only.
"""
from __future__ import annotations

import warnings

import numpy as np

from mdingilife.data import Rates

MAX_ITER, TOL = 20000, 1e-9
MIN_COHORT_CELLS = 3


def rw_drift(k: np.ndarray, years: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drift and innovation covariance of a random walk in k (time on the last axis).

    Fitted years may have a gap (the Covid years are left out): a step over g years has mean g * drift and
    variance g * sigma^2. With consecutive years this is the usual mean and variance of the differences.
    """
    dt = np.diff(years).astype(float)
    dk = np.diff(k, axis=-1)
    mu = dk.sum(axis=-1) / dt.sum()
    e = (dk - mu[..., None] * dt) / np.sqrt(dt) if dk.ndim > 1 else (dk - mu * dt) / np.sqrt(dt)
    cov = np.atleast_2d(e) @ np.atleast_2d(e).T / (len(dt) - 1)
    return mu, (np.sqrt(cov[0, 0]) if dk.ndim == 1 else cov)


def simulate_rw(last: float, mu: float, sd: float, h: int, n: int, rng: np.random.Generator) -> np.ndarray:
    return last + np.cumsum(mu + sd * rng.standard_normal((n, h)), axis=1)


class B0:
    """No improvement: rates frozen at the average of the last three fitted years."""

    name = "B0"

    def fit(self, r: Rates) -> "B0":
        self.r = r
        self.log_m = np.log(r.m[:, -3:].mean(axis=1))
        return self

    def fitted(self) -> np.ndarray:
        return np.repeat(self.log_m[:, None], len(self.r.years), axis=1)

    def forecast(self, h: int, n: int, rng: np.random.Generator) -> np.ndarray:
        return np.broadcast_to(self.log_m[None, :, None], (n, len(self.log_m), h)).copy()


class LeeCarter:
    """log m(x,t) = a(x) + b(x) k(t), Poisson maximum likelihood (Brouhns, Denuit and Vermunt, 2002).

    Constraints: sum b = 1, sum k = 0. k(t) is a random walk with drift.
    """

    name = "LC"

    def fit(self, r: Rates) -> "LeeCarter":
        self.r = r
        D, E = r.D, r.E
        a = np.log(D.sum(1) / E.sum(1))
        u, s, vt = np.linalg.svd(np.log(np.maximum(D, 0.5) / E) - a[:, None], full_matrices=False)
        b, k = u[:, 0] / u[:, 0].sum(), s[0] * vt[0] * u[:, 0].sum()
        prev = a[:, None] + np.outer(b, k)
        for _ in range(MAX_ITER):
            Dh = E * np.exp(a[:, None] + np.outer(b, k))
            a += (D - Dh).sum(1) / Dh.sum(1)
            Dh = E * np.exp(a[:, None] + np.outer(b, k))
            k += ((D - Dh) * b[:, None]).sum(0) / (Dh * b[:, None] ** 2).sum(0)
            a, k = a + b * k.mean(), k - k.mean()
            Dh = E * np.exp(a[:, None] + np.outer(b, k))
            b += ((D - Dh) * k).sum(1) / (Dh * k ** 2).sum(1)
            eta = a[:, None] + np.outer(b, k)
            if np.abs(eta - prev).max() < TOL:
                break
            prev = eta
        else:
            warnings.warn(f"Lee-Carter did not converge ({r.sex})")
        s = b.sum()
        self.b, k = b / s, k * s
        self.a, self.k = a + self.b * k.mean(), k - k.mean()
        self.mu, self.sd = rw_drift(self.k, r.years)
        return self

    def fitted(self) -> np.ndarray:
        return self.a[:, None] + np.outer(self.b, self.k)

    def forecast(self, h: int, n: int, rng: np.random.Generator) -> np.ndarray:
        k = simulate_rw(self.k[-1], self.mu, self.sd, h, n, rng)
        return self.a[None, :, None] + self.b[None, :, None] * k[:, None, :]


class CBD:
    """logit q(x,t) = k1(t) + (x - mean age) k2(t), binomial on initial exposure E + D/2 (Cairns, Blake and Dowd, 2006).

    (k1, k2) is a bivariate random walk with drift. Rates are returned as m = -log(1 - q).
    """

    name = "CBD"

    def fit(self, r: Rates) -> "CBD":
        self.r = r
        self.xc = r.ages - r.ages.mean()
        X = np.column_stack([np.ones_like(self.xc), self.xc])
        Ec = r.E + r.D / 2
        K = np.zeros((2, len(r.years)))
        for t in range(len(r.years)):
            d, n = r.D[:, t], Ec[:, t]
            beta = np.linalg.lstsq(X, np.log(d / (n - d)), rcond=None)[0]
            for _ in range(100):
                p = 1 / (1 + np.exp(-X @ beta))
                step = np.linalg.solve(X.T @ (X * (n * p * (1 - p))[:, None]), X.T @ (d - n * p))
                beta += step
                if np.abs(step).max() < 1e-12:
                    break
            K[:, t] = beta
        self.K = K
        self.mu, self.cov = rw_drift(K, r.years)
        return self

    def _log_m(self, K: np.ndarray) -> np.ndarray:
        eta = K[..., 0, None, :] + self.xc[:, None] * K[..., 1, None, :]
        return np.log(np.log1p(np.exp(eta)))  # -log(1 - q) with q = logistic(eta)

    def fitted(self) -> np.ndarray:
        return self._log_m(self.K)

    def forecast(self, h: int, n: int, rng: np.random.Generator) -> np.ndarray:
        z = rng.standard_normal((n, h, 2)) @ np.linalg.cholesky(self.cov).T
        K = self.K[:, -1] + np.cumsum(self.mu + z, axis=1)
        return self._log_m(np.swapaxes(K, 1, 2))


class RenshawHaberman:
    """log m(x,t) = a(x) + b(x) k(t) + g(t - x), the age-period-cohort form with a unit cohort loading
    (Haberman and Renshaw, 2011), because the full model with an age-varying cohort loading often fails to converge.

    Constraints: sum b = 1, sum k = 0, sum g = 0 over the cohorts estimated. Cohorts seen in fewer than three cells
    are not estimated (g = 0). k(t) is a random walk with drift; g an ARIMA(1,1,0) over birth years.
    """

    name = "RH"

    def fit(self, r: Rates) -> "RenshawHaberman":
        self.r = r
        D, E = r.D, r.E
        coh = r.years[None, :] - r.ages[:, None]
        self.c0 = coh.min()
        idx = coh - self.c0
        cells = np.bincount(idx.ravel(), minlength=idx.max() + 1)
        ok = cells >= MIN_COHORT_CELLS
        lc = LeeCarter().fit(r)
        a, b, k, g = lc.a.copy(), lc.b.copy(), lc.k.copy(), np.zeros(len(cells))
        prev = a[:, None] + np.outer(b, k)
        for _ in range(MAX_ITER):
            eta = lambda: a[:, None] + np.outer(b, k) + g[idx]
            Dh = E * np.exp(eta())
            a += (D - Dh).sum(1) / Dh.sum(1)
            Dh = E * np.exp(eta())
            k += ((D - Dh) * b[:, None]).sum(0) / (Dh * b[:, None] ** 2).sum(0)
            a, k = a + b * k.mean(), k - k.mean()
            Dh = E * np.exp(eta())
            b += ((D - Dh) * k).sum(1) / (Dh * k ** 2).sum(1)
            Dh = E * np.exp(eta())
            num = np.bincount(idx.ravel(), (D - Dh).ravel(), len(cells))
            den = np.bincount(idx.ravel(), Dh.ravel(), len(cells))
            g = np.where(ok, g + num / den, 0.0)
            a, g = a + g[ok].mean(), np.where(ok, g - g[ok].mean(), 0.0)
            if np.abs(eta() - prev).max() < TOL:
                break
            prev = eta()
        else:
            warnings.warn(f"Renshaw-Haberman did not converge ({r.sex})")
        s = b.sum()
        self.a, self.b, self.k, self.g, self.ok, self.idx = a, b / s, k * s, g, ok, idx
        self.mu, self.sd = rw_drift(self.k, r.years)
        self.last = np.flatnonzero(ok)[-1]
        dg = np.diff(g[ok])
        X = np.column_stack([np.ones(len(dg) - 1), dg[:-1]])
        (c, self.phi), *_ = np.linalg.lstsq(X, dg[1:], rcond=None)
        self.g_mu = c / (1 - self.phi)
        self.g_sd = (dg[1:] - X @ np.array([c, self.phi])).std(ddof=2)
        self.dg_last = dg[-1]
        return self

    def fitted(self) -> np.ndarray:
        return self.a[:, None] + np.outer(self.b, self.k) + self.g[self.idx]

    def forecast(self, h: int, n: int, rng: np.random.Generator) -> np.ndarray:
        r = self.r
        k = simulate_rw(self.k[-1], self.mu, self.sd, h, n, rng)
        years = r.years[-1] + 1 + np.arange(h)
        idx = years[None, :] - r.ages[:, None] - self.c0
        ahead = max(int(idx.max()) - self.last, 0)
        g = np.tile(np.where(self.ok, self.g, 0.0), (n, 1))[:, : self.last + 1]
        if ahead:
            dg, prev = np.empty((n, ahead)), np.full(n, self.dg_last)
            for j in range(ahead):
                prev = self.g_mu + self.phi * (prev - self.g_mu) + self.g_sd * rng.standard_normal(n)
                dg[:, j] = prev
            g = np.concatenate([g, g[:, -1:] + np.cumsum(dg, axis=1)], axis=1)
        return self.a[None, :, None] + self.b[None, :, None] * k[:, None, :] + g[:, idx]


MODELS = {m.name: m for m in (B0, LeeCarter, CBD, RenshawHaberman)}
