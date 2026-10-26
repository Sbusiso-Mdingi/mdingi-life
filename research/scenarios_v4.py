"""v4's economic scenario generator (PROTOCOL_v4.md): fixed-decay Nelson-Siegel curves at month-ends, AR(1) factor
dynamics, and 1,000 five-year paths of the nominal and real curves.

Two factors a kind, level and slope, under the amendment of 26 October 2026; the frozen three are reported beside.
Used by research.projection_v4, which writes the results; nothing here is run on its own.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mdingilife import esg
from mdingilife.curves import ns
from research import curves as rc

START, END = "2011-01-31", "2026-09-30"
KINDS = {"nominal": "fixed", "real": "ilb"}
MIN_BONDS = 4
TAUS = np.arange(0.5, 10.01, 0.5)
SEED = 20261027
N, MONTHS = 1_000, 60
COVID = ("2020-03", "2020-05")
FACTORS = 2   # amendment of 26 October 2026; the protocol as frozen had 3
NAMES = ("b0", "b1", "b2")


def month_points(a: pd.DataFrame) -> dict:
    """Each kind's window points at each month-end, where the window holds at least MIN_BONDS bonds."""
    ends = pd.date_range(START, END, freq="ME")
    out = {}
    for k, kind in KINDS.items():
        g = a[a["kind"] == kind]
        pts = {d: rc.window(g, d, rc.WINDOW, inclusive=True) for d in ends}
        out[k] = {d: p for d, p in pts.items() if len(p) >= MIN_BONDS}
    return out


def calibrate(points: dict, jump: dict, exclude: tuple | None = None, n: int = FACTORS) -> dict:
    """τ for each kind from the grid, the month-end factors (`n` a kind), the AR(1)s and the jump-off factors.
    `exclude`: a (first, last) month range left out of everything."""
    ends = pd.date_range(START, END, freq="ME")
    if exclude:
        drop = (ends >= pd.Period(exclude[0]).start_time) & (ends <= pd.Period(exclude[1]).end_time)
        ends = ends[~drop]
    tau, factors = {}, {}
    for k, pts in points.items():
        months = [d for d in ends if d in pts]
        sse = {t: sum(esg.fit_fixed(pts[d], t, n)[1] for d in months) for t in TAUS}
        tau[k] = float(min(sse, key=sse.get))
        factors[k] = pd.DataFrame({d: esg.fit_fixed(pts[d], tau[k], n)[0] for d in months}, index=NAMES[:n]).T
    full = pd.date_range(START, END, freq="ME")
    F = pd.concat([factors[k].reindex(full).add_prefix(k[0]) for k in KINDS], axis=1)
    ar = esg.AR1.fit(F.to_numpy())
    beta0 = np.concatenate([esg.fit_fixed(jump[k], tau[k], n)[0] for k in KINDS])
    z10 = {k: pd.Series(ten(factors[k].reindex(full).to_numpy(), tau[k]), index=full) for k in KINDS}
    hist = {k: float((z10[k] - z10[k].shift(12)).dropna().std()) for k in KINDS}
    return {"n": n, "tau": tau, "factors": F, "ar": ar, "beta0": beta0, "z10": z10, "hist_sd_12m": hist,
            "months": {k: int(len(factors[k])) for k in KINDS}}


def ten(beta: np.ndarray, tau: float) -> np.ndarray:
    """The continuously compounded 10-year zero rate of factors (..., n)."""
    beta = np.asarray(beta, float)
    b = [beta[..., j] if j < beta.shape[-1] else 0.0 for j in range(3)]
    return ns(10.0, *b, tau)


def kind(cal: dict, beta: np.ndarray, i: int) -> np.ndarray:
    """Kind i's factors out of all of them (last axis)."""
    n = cal["n"]
    return np.asarray(beta)[..., n * i:n * (i + 1)]


def paths(cal: dict, n: int = N, seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """Factors at the year-ends (months 0, 12, ..., 60): (n, 6, factors) for the scenarios and (6, factors) for the
    central path."""
    sims = cal["ar"].simulate(cal["beta0"], MONTHS, n, np.random.default_rng(seed))[:, ::12]
    central = cal["ar"].central(cal["beta0"], MONTHS)[::12]
    return sims, central


def forwards(cal: dict, fwd0: dict, beta: np.ndarray) -> dict:
    """{kind: forwards} of the curve at factors `beta` (6,), the valuation curve moved by the Nelson-Siegel change."""
    out = {}
    for i, k in enumerate(KINDS):
        out[k] = esg.shift_forwards(fwd0[k], kind(cal, cal["beta0"], i), kind(cal, beta, i), cal["tau"][k])
    return out


def summary(cal: dict) -> dict:
    ar = cal["ar"]
    names = [f"{k} {b}" for k in KINDS for b in NAMES[:cal["n"]]]
    sd = np.sqrt(np.diag(ar.cov))
    return {"factors": cal["n"], "tau": cal["tau"], "months": cal["months"], "names": names, "mu": list(ar.mu), "phi": list(ar.phi),
            "capped": [bool(x) for x in ar.capped], "sd": list(sd), "corr": (ar.cov / np.outer(sd, sd)).tolist(),
            "beta0": list(cal["beta0"]), "hist_sd_12m": cal["hist_sd_12m"]}
