"""Every model on simulated data with known parameters."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import bootstrap
from mdingilife.data import Rates
from mdingilife.models import B0, CBD, LeeCarter, RenshawHaberman

AGES, YEARS = np.arange(50, 90), np.arange(1990, 2020)
EXPOSURE = 2e6


def lc_truth():
    a = -9.5 + 0.09 * AGES
    b = np.linspace(1.5, 0.5, len(AGES))
    b /= b.sum()
    k = np.linspace(15, -15, len(YEARS)) + np.sin(np.arange(len(YEARS)))
    k -= k.mean()
    return a, b, k


def panel(log_m, rng, poisson=True):
    E = np.full(log_m.shape, EXPOSURE)
    D = rng.poisson(E * np.exp(log_m)).astype(float) if poisson else E * np.exp(log_m)
    return Rates("Male", AGES, YEARS, D, E)


def test_lee_carter_recovers_parameters():
    rng = np.random.default_rng(1)
    a, b, k = lc_truth()
    m = LeeCarter().fit(panel(a[:, None] + np.outer(b, k), rng))
    assert m.b.sum() == pytest.approx(1)
    assert m.k.sum() == pytest.approx(0, abs=1e-8)
    assert np.abs(m.a - a).max() < 0.01
    assert np.abs(m.b - b).max() < 0.002
    assert np.abs(m.k - k).max() < 0.3


def test_lee_carter_exact_on_noise_free_data():
    a, b, k = lc_truth()
    lm = a[:, None] + np.outer(b, k)
    m = LeeCarter().fit(panel(lm, None, poisson=False))
    assert np.abs(m.fitted() - lm).max() < 1e-6


def test_cbd_recovers_parameters():
    rng = np.random.default_rng(2)
    xc = AGES - AGES.mean()
    k1, k2 = np.linspace(-3.0, -3.6, len(YEARS)), np.linspace(0.10, 0.11, len(YEARS))
    q = 1 / (1 + np.exp(-(k1[None, :] + np.outer(xc, k2))))
    m = -np.log(1 - q)
    # Simulate deaths binomially on initial exposure, which is what CBD fits.
    Ec = np.full(q.shape, EXPOSURE)
    D = rng.binomial(Ec.astype(int), q).astype(float)
    fit = CBD().fit(Rates("Male", AGES, YEARS, D, Ec - D / 2))
    assert np.abs(fit.K[0] - k1).max() < 0.01
    assert np.abs(fit.K[1] - k2).max() < 0.001
    assert np.abs(fit.fitted() - np.log(m)).max() < 0.03


def test_renshaw_haberman_recovers_fit_and_cohorts():
    rng = np.random.default_rng(3)
    a, b, k = lc_truth()
    coh = YEARS[None, :] - AGES[:, None]
    gc = 0.08 * np.sin(np.arange(coh.min(), coh.max() + 1) / 4)
    lm = a[:, None] + np.outer(b, k) + gc[coh - coh.min()]
    m = RenshawHaberman().fit(panel(lm, rng))
    lc = LeeCarter().fit(m.r)
    assert np.abs(m.fitted() - lm)[:, 3:-3].max() < 0.05
    # The cohort term must explain what Lee-Carter cannot.
    assert np.abs(m.fitted() - lm).mean() < 0.5 * np.abs(lc.fitted() - lm).mean()
    # Cohort shape up to the linear trend the model cannot separate from age and period.
    c = np.flatnonzero(m.ok)
    est, true = m.g[c], gc[c]
    X = np.column_stack([np.ones(len(c)), c])
    detr = lambda v: v - X @ np.linalg.lstsq(X, v, rcond=None)[0]
    assert np.corrcoef(detr(est), detr(true))[0, 1] > 0.95


def test_b0_freezes_last_three_years():
    rng = np.random.default_rng(4)
    a, b, k = lc_truth()
    r = panel(a[:, None] + np.outer(b, k), rng)
    fc = B0().fit(r).forecast(5, 3, rng)
    assert fc.shape == (3, len(AGES), 5)
    assert np.allclose(fc[0, :, 0], np.log(r.m[:, -3:].mean(1)))
    assert np.allclose(fc[:, :, 0], fc[:, :, -1])


@pytest.mark.parametrize("cls", [LeeCarter, CBD, RenshawHaberman])
def test_forecast_shape_and_drift(cls):
    rng = np.random.default_rng(5)
    a, b, k = lc_truth()
    m = cls().fit(panel(a[:, None] + np.outer(b, k), rng))
    fc = m.forecast(40, 2000, rng)
    assert fc.shape == (2000, len(AGES), 40)
    assert np.isfinite(fc).all()
    # Mortality falls in the data, so the median path falls, and the fan widens with the horizon.
    med = np.median(fc, axis=0)
    assert (med[:, -1] < med[:, 0]).all()
    sd = fc.std(axis=0)
    assert (sd[:, -1] > sd[:, 0]).all()


def test_lee_carter_drift_matches_truth():
    rng = np.random.default_rng(6)
    a, b, k = lc_truth()
    m = LeeCarter().fit(panel(a[:, None] + np.outer(b, k), rng))
    assert m.mu == pytest.approx(np.diff(k).mean(), abs=0.02)


def test_bootstrap_widens_the_fan():
    rng = np.random.default_rng(7)
    a, b, k = lc_truth()
    r = panel(a[:, None] + np.outer(b, k), rng)
    sims = bootstrap.simulate(LeeCarter, r, 10, refits=20, paths=1000, rng=rng)
    assert sims.shape == (1000, len(AGES), 10)
    base = LeeCarter().fit(r).forecast(10, 1000, rng)
    assert sims.std(axis=0).mean() >= 0.95 * base.std(axis=0).mean()


def test_drift_with_a_gap_in_years():
    from mdingilife.models import rw_drift
    rng = np.random.default_rng(8)
    k = np.cumsum(-1 + 0.5 * rng.standard_normal(40))
    years = np.arange(1980, 2020)
    mu, sd = rw_drift(k, years)
    d = np.diff(k)
    assert mu == pytest.approx(d.mean()) and sd == pytest.approx(d.std(ddof=1))
    # Dropping three years leaves the drift an average over the same span.
    keep = ~np.isin(years, [2010, 2011, 2012])
    mu2, _ = rw_drift(k[keep], years[keep])
    assert mu2 == pytest.approx((k[-1] - k[0]) / 39)
    K = np.vstack([k, 2 * k])
    m2, cov = rw_drift(K, years)
    assert np.allclose(m2, [mu, 2 * mu]) and np.allclose(cov, np.cov(np.diff(K, axis=1)))
