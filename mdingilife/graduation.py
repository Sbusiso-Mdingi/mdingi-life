"""Whittaker-Henderson graduation on a Poisson likelihood (research/PROTOCOL_v1.4.md, "Graduation").

log m minimises the Poisson deviance plus lam * sum (second difference over age of log m)^2. lam is chosen by
BIC = deviance + log(n) * ED, with ED the trace of the hat matrix, over 10^0, 10^0.25, ..., 10^8.
"""
from __future__ import annotations

import numpy as np

GRID = 10.0 ** np.arange(0, 8.001, 0.25)
MAX_ITER, TOL = 200, 1e-10


def _penalty(n: int) -> np.ndarray:
    P = np.diff(np.eye(n), 2, axis=0)
    return P.T @ P


def deviance(D: np.ndarray, mu: np.ndarray) -> float:
    t = np.where(D > 0, D * np.log(np.where(D > 0, D, 1) / mu), 0.0)
    return float(2 * (t - (D - mu)).sum())


def whittaker(D: np.ndarray, E: np.ndarray, lam: float) -> tuple[np.ndarray, float, float]:
    """Graduated log m, its effective dimension and its deviance, for one lam. Newton's method with halving."""
    D, E = np.asarray(D, float), np.asarray(E, float)
    Q = 2 * lam * _penalty(len(D))
    eta = np.log(np.maximum(D, 0.5) / E)

    def objective(e):
        return float((E * np.exp(e) - D * e).sum() + 0.5 * e @ Q @ e)

    f = objective(eta)
    for _ in range(MAX_ITER):
        mu = E * np.exp(eta)
        H = np.diag(mu) + Q
        step = np.linalg.solve(H, D - mu - Q @ eta)
        t = 1.0
        while objective(eta + t * step) > f + 1e-12 * abs(f) and t > 1e-8:
            t /= 2
        eta = eta + t * step
        f_new = objective(eta)
        if np.abs(t * step).max() < TOL:
            break
        f = f_new
    mu = E * np.exp(eta)
    ed = float(np.trace(np.linalg.solve(np.diag(mu) + Q, np.diag(mu))))
    return eta, ed, deviance(D, mu)


def graduate(D: np.ndarray, E: np.ndarray, lam: float | None = None) -> dict:
    """Graduate pooled deaths and exposures. With lam None, lam is chosen by BIC on GRID."""
    n = len(D)
    if lam is None:
        best = None
        for g in GRID:
            eta, ed, dev = whittaker(D, E, g)
            bic = dev + np.log(n) * ed
            if best is None or bic < best["bic"]:
                best = {"lam": float(g), "log_m": eta, "ed": ed, "deviance": dev, "bic": bic}
        return best
    eta, ed, dev = whittaker(D, E, lam)
    return {"lam": float(lam), "log_m": eta, "ed": ed, "deviance": dev, "bic": dev + np.log(n) * ed}


def checks(D: np.ndarray, E: np.ndarray, log_m: np.ndarray, ages: np.ndarray) -> dict:
    """The standard graduation tests, reported as checks (not pass marks)."""
    mu = E * np.exp(log_m)
    z = (D - mu) / np.sqrt(mu)
    s = np.sign(z[z != 0])
    lo, hi = (ages >= 50) & (ages <= 69), (ages >= 70) & (ages <= 89)
    return {
        "chi2": float((z ** 2).sum()),
        "cells": int(len(z)),
        "positive": int((z > 0).sum()),
        "runs": int(1 + (np.diff(s) != 0).sum()) if len(s) else 0,
        "max_abs_z": float(np.abs(z).max()),
        "cum_dev_50_69": float((D[lo] - mu[lo]).sum() / np.sqrt(mu[lo].sum())),
        "cum_dev_70_89": float((D[hi] - mu[hi]).sum() / np.sqrt(mu[hi].sum())),
    }
