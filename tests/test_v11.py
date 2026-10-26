"""v1.1's overdispersion, anchor and average, on simulated data."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import average, bootstrap
from mdingilife.data import Rates
from mdingilife.models import CBD, LeeCarter, RenshawHaberman
from tests.test_models import AGES, EXPOSURE, YEARS, lc_truth


def overdispersed(phi, seed=1):
    rng = np.random.default_rng(seed)
    a, b, k = lc_truth()
    E = np.full((len(AGES), len(YEARS)), EXPOSURE)
    D = bootstrap.draw(E * np.exp(a[:, None] + np.outer(b, k)), phi, rng)
    return Rates("Male", AGES, YEARS, D, E)


def test_draw_has_the_asked_variance():
    rng = np.random.default_rng(0)
    for phi in (1.0, 5.0, 14.0):
        x = bootstrap.draw(np.full(200_000, 400.0), phi, rng)
        assert x.mean() == pytest.approx(400, rel=0.01)
        assert x.var() / 400 == pytest.approx(phi, rel=0.03)


@pytest.mark.parametrize("phi", [1.0, 6.0, 14.0])
def test_dispersion_recovers_phi(phi):
    m = LeeCarter().fit(overdispersed(phi))
    assert bootstrap.dispersion(m) == pytest.approx(phi, rel=0.15, abs=0.15)


def test_parameter_counts():
    r = overdispersed(1.0)
    A, T = len(AGES), len(YEARS)
    assert bootstrap.n_params(LeeCarter().fit(r)) == 2 * A + T - 2
    assert bootstrap.n_params(CBD().fit(r)) == 2 * T
    rh = RenshawHaberman().fit(r)
    assert bootstrap.n_params(rh) == 2 * A + T - 2 + rh.ok.sum() - 1


def test_offset_is_the_smoothed_recent_error():
    r = overdispersed(1.0)
    m = LeeCarter().fit(r)
    shift = 0.05 * np.sin(AGES / 5.0)
    bumped = Rates(r.sex, r.ages, r.years, r.D * np.exp(shift[:, None] * (r.years >= 2017)), r.E)
    base = bootstrap.offset(m)
    m.r = bumped  # same fit, data moved in the last three years
    off = bootstrap.offset(m)
    # The anchor picks up the shift, smoothed over five ages.
    i = 20
    assert off[i] - base[i] == pytest.approx(shift[i - 2: i + 3].mean(), abs=1e-6)
    assert len(off) == len(AGES)


def test_offset_end_ages_use_shorter_windows():
    r = overdispersed(1.0)
    m = LeeCarter().fit(r)
    obs = np.log(r.D[:, -3:] / r.E[:, -3:])
    raw = (obs - m.fitted()[:, -3:]).mean(axis=1)
    off = bootstrap.offset(m)
    assert off[0] == pytest.approx(raw[:3].mean())
    assert off[1] == pytest.approx(raw[:4].mean())
    assert off[-1] == pytest.approx(raw[-3:].mean())


def test_wider_bootstrap_with_overdispersion():
    r = overdispersed(10.0)
    rng = np.random.default_rng(3)
    s1, _, _ = bootstrap.paths(LeeCarter, r, 10, 100, 2000, rng, phi=1.0)
    s10, _, phi = bootstrap.paths(LeeCarter, r, 10, 100, 2000, rng)
    assert phi > 5
    w = lambda s: np.subtract(*np.quantile(s[:, :, -1], [0.975, 0.025], axis=0)).mean()
    assert w(s10) > w(s1)


def test_observation_noise_covers_overdispersed_data():
    """Intervals with observation noise cover held-out overdispersed data about as often as they should."""
    phi = 10.0
    r = overdispersed(phi, seed=5)
    fit, held = r.sub(years=YEARS[:-3]), r.sub(years=YEARS[-3:])
    rng = np.random.default_rng(4)
    sims, off, phi_hat = bootstrap.paths(LeeCarter, fit, 3, 100, 2000, rng)
    noisy = bootstrap.observe(sims + off[:, :, None], held.E, phi_hat, rng)
    lo, hi = np.quantile(noisy, [0.025, 0.975], axis=0)
    obs = np.log(held.m)
    cover = ((obs >= lo) & (obs <= hi)).mean()
    assert cover > 0.88


def test_weights():
    w = average.weights({"LC": 1000.0, "CBD": 1010.0, "RH": 1200.0}, phi=10.0)
    assert sum(w.values()) == pytest.approx(1)
    assert w["LC"] / w["CBD"] == pytest.approx(np.exp(0.5))
    assert w["RH"] < 1e-4
    assert average.inverse({"LC": 1.0, "CBD": 3.0})["LC"] == pytest.approx(0.75)


def test_split_adds_up():
    s = average.split({"LC": 0.333, "CBD": 0.333, "RH": 0.334})
    assert sum(n for n, _ in s.values()) == average.PATHS
    assert all(k >= 1 for _, k in s.values())
    s = average.split({"LC": 0.99995, "CBD": 0.00005, "RH": 0.0})
    assert s == {"LC": (5000, 500)}
