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
