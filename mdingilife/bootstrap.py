"""Parameter uncertainty: semiparametric Poisson bootstrap of deaths (Brouhns, Denuit and Van Keilegom, 2005).

Deaths are redrawn from Poisson(fitted deaths), the model is refitted, and each refit forecasts its share of the
paths, so the simulated fan carries both parameter and process uncertainty.
"""
from __future__ import annotations

import numpy as np

from mdingilife.data import Rates


def resample(model, rng: np.random.Generator) -> Rates:
    r = model.r
    return Rates(r.sex, r.ages, r.years, rng.poisson(r.E * np.exp(model.fitted())).astype(float), r.E)


def simulate(cls, r: Rates, h: int, refits: int, paths: int, rng: np.random.Generator) -> np.ndarray:
    """`paths` forecast paths, spread evenly over `refits` bootstrap refits of `cls`."""
    base = cls().fit(r)
    per = -(-paths // refits)
    out = [cls().fit(resample(base, rng)).forecast(h, per, rng) for _ in range(refits)]
    return np.concatenate(out)[:paths]


# v1.1 (research/PROTOCOL_v1.1.md): overdispersion, the anchored jump-off and parameter counts.

def n_params(model) -> int:
    """Free parameters of a fitted LC, CBD or RH model, after its identifiability constraints."""
    A, T = len(model.r.ages), len(model.r.years)
    if model.name == "CBD":
        return 2 * T
    if model.name == "RH":
        return 2 * A + T - 2 + int(model.ok.sum()) - 1
    return 2 * A + T - 2


def dispersion(model) -> float:
    """Pearson chi-square over residual degrees of freedom, floored at 1."""
    r = model.r
    Dh = r.E * np.exp(model.fitted())
    chi2 = float(((r.D - Dh) ** 2 / Dh).sum())
    return max(chi2 / (r.D.size - n_params(model)), 1.0)


def draw(mu: np.ndarray, phi: float, rng: np.random.Generator) -> np.ndarray:
    """Counts with mean mu and variance phi * mu: gamma-Poisson, or Poisson when phi is 1."""
    mu = np.asarray(mu, float)
    if phi <= 1:
        return rng.poisson(mu).astype(float)
    return rng.poisson(rng.gamma(mu / (phi - 1), phi - 1)).astype(float)


def observe(log_m: np.ndarray, E: np.ndarray, phi: float, rng: np.random.Generator) -> np.ndarray:
    """Simulated observed log rates: deaths drawn at exposure E around each simulated rate."""
    D = draw(E * np.exp(log_m), phi, rng)
    return np.log(np.maximum(D, 0.5) / E)


def offset(model, years: int = 3, span: int = 5) -> np.ndarray:
    """The anchor: mean of log observed minus log fitted over the last `years` fitted years, then a centred
    `span`-age moving average, shortened at the ends."""
    r = model.r
    obs = np.log(np.maximum(r.D[:, -years:], 0.5) / r.E[:, -years:])
    raw = (obs - model.fitted()[:, -years:]).mean(axis=1)
    h = span // 2
    return np.array([raw[max(i - h, 0): i + h + 1].mean() for i in range(len(raw))])


def paths(cls, r: Rates, h: int, refits: int, n: int, rng: np.random.Generator, phi: float | None = None):
    """v1.1's bootstrap: `n` paths over `refits` refits, deaths redrawn with dispersion `phi` (the base fit's
    when None). Returns (unanchored log rates, each path's anchor offset by age, phi)."""
    base = cls().fit(r)
    phi = dispersion(base) if phi is None else phi
    per = -(-n // refits)
    sims, offs = [], []
    for _ in range(refits):
        b = Rates(r.sex, r.ages, r.years, draw(r.E * np.exp(base.fitted()), phi, rng), r.E)
        m = cls().fit(b)
        sims.append(m.forecast(h, per, rng))
        offs.append(np.repeat(offset(m)[None, :], per, axis=0))
    return np.concatenate(sims)[:n], np.concatenate(offs)[:n], phi
