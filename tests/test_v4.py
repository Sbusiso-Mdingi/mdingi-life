"""v4 pieces on simulated data with known answers: the fixed-decay Nelson-Siegel fit, the AR(1)s, the curve shift
and the CSM roll-forward."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import esg, ifrs17
from mdingilife.curves import Bond, Point, ns, yield_from_price
from datetime import date


def _points(beta, tau, settle=date(2026, 1, 15)):
    out = []
    for code, (yr, cpn) in {"A": (2029, 8.0), "B": (2033, 8.5), "C": (2038, 9.0), "D": (2045, 10.0),
                            "E": (2053, 11.0)}.items():
        t, cf = Bond(code, cpn, ((date(yr, 3, 31), 1.0),)).cashflows(settle)
        price = float(np.sum(cf * np.exp(-ns(t, *beta, tau) * t)))
        out.append(Point(code, t, cf, yield_from_price(t, cf, price)))
    return out


def test_fixed_decay_fit_recovers_the_factors():
    beta = np.array([0.11, -0.03, 0.02])
    b, sse = esg.fit_fixed(_points(beta, 3.0), 3.0)
    assert b == pytest.approx(beta, abs=1e-7)
    assert sse < 1e-14


def test_ar1_recovers_its_parameters():
    rng = np.random.default_rng(1)
    true = esg.AR1(np.array([0.1, -0.02]), np.array([0.9, 0.6]), np.array([[1e-4, 3e-5], [3e-5, 4e-4]]), np.zeros(2, bool))
    path = true.simulate(true.mu, 20_000, 1, rng)[0]
    fit = esg.AR1.fit(path)
    assert fit.phi == pytest.approx(true.phi, abs=0.01)
    assert fit.mu == pytest.approx(true.mu, abs=0.002)
    assert fit.cov == pytest.approx(true.cov, abs=1e-5)


def test_ar1_skips_gaps_and_caps_a_unit_root():
    rng = np.random.default_rng(2)
    walk = np.cumsum(rng.normal(0, 0.01, 3000))[:, None]
    walk[100:105] = np.nan
    fit = esg.AR1.fit(walk)
    assert fit.capped[0] and fit.phi[0] == esg.PHI_CAP


def test_central_path_reverts_to_the_mean():
    ar = esg.AR1(np.array([0.1]), np.array([0.5]), np.eye(1), np.zeros(1, bool))
    assert ar.central(np.array([0.2]), 2)[:, 0] == pytest.approx([0.2, 0.15, 0.125])


def test_shift_with_unchanged_factors_keeps_the_curve():
    fwd = np.linspace(0.07, 0.11, 40)
    beta = np.array([0.1, -0.02, 0.01])
    assert esg.shift_forwards(fwd, beta, beta, 2.0) == pytest.approx(fwd)
    up = esg.shift_forwards(fwd, beta, beta + [0.01, 0, 0], 2.0)
    assert up - fwd == pytest.approx(np.full(40, 0.01))


def test_transition_csm_and_confidence():
    assert ifrs17.transition_csm(60.0, 0.06, 0.10) == pytest.approx(40.0)
    assert ifrs17.confidence(0.0, 1.0) == pytest.approx(0.5)
    assert ifrs17.confidence(1.0, 1.0) == pytest.approx(0.995)


def test_roll_accretes_releases_and_floors():
    r = ifrs17.roll(100.0, 0.08, 1.0, 4.0)
    assert r["accretion"] == pytest.approx(8.0) and r["release"] == pytest.approx(27.0) and r["close"] == pytest.approx(81.0)
    hit = ifrs17.roll(100.0, 0.08, 1.0, 4.0, start=-130.0)
    assert hit["loss"] == pytest.approx(30.0) and hit["close"] == 0.0
    last = ifrs17.roll(50.0, 0.0, 2.0, 2.0)
    assert last["close"] == pytest.approx(0.0)


def test_two_factor_fit_recovers_level_and_slope():
    beta = np.array([0.11, -0.03, 0.0])
    b, sse = esg.fit_fixed(_points(beta, 4.0), 4.0, n=2)
    assert b == pytest.approx(beta[:2], abs=1e-7)
    assert esg.shift_forwards(np.full(10, 0.1), b, b + [0.01, 0], 4.0) == pytest.approx(np.full(10, 0.11))
