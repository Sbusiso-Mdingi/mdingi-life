"""v1.3's smoothed cohort term, on simulated data (research/PROTOCOL_v1.3.md, "Reporting")."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import scores
from mdingilife.data import Rates
from mdingilife.models import RenshawHaberman, SmoothRH, smooth
from tests.test_models import lc_truth

AGES, YEARS = np.arange(50, 90), np.arange(2006, 2020)
# WPP-sized exposures for South African men: about 300,000 at 50, falling to about 5,000 at 89
EXPOSURE = np.geomspace(3e5, 5e3, len(AGES))[:, None] * np.ones(len(YEARS))
COH = YEARS[None, :] - AGES[:, None]


def truth():
    """a, b and k of the model tests' shape on 2006 to 2019, and a known smooth cohort effect by birth year:
    a linear trend plus a bump 10 years wide, of size 0.15."""
    a, b, k = lc_truth()
    k = np.interp(np.linspace(0, len(k) - 1, len(YEARS)), np.arange(len(k)), k)
    k -= k.mean()
    c = np.arange(COH.min(), COH.max() + 1)
    g = 0.004 * (c - 1943) + np.where(np.abs(c - 1950) < 5, 0.15 * (1 + np.cos(np.pi * (c - 1950) / 5)) / 2, 0.0)
    return a, b, k, c, g


def simulated(heap: float = 1.0, seed: int = 3) -> Rates:
    a, b, k, c, g = truth()
    log_m = a[:, None] + np.outer(b, k) + g[COH - c[0]]
    lift = np.where(COH % 10 == 0, heap, 1.0)
    D = np.random.default_rng(seed).poisson(EXPOSURE * np.exp(log_m) * lift).astype(float)
    return Rates("Male", AGES, YEARS, D, EXPOSURE.copy())


def interior(m) -> np.ndarray:
    est = np.flatnonzero(m.ok)
    return est[2:-2]


def test_smoother_cuts_a_lone_spike_to_a_fifth():
    ok = np.ones(20, bool)
    g = np.zeros(20)
    g[10] = 1.0
    s = smooth(g, ok, 5)
    assert s[8:13] == pytest.approx(np.full(5, 0.2))
    assert s[:8] == pytest.approx(np.zeros(8)) and s[13:] == pytest.approx(np.zeros(7))


def test_smoother_ends_are_cut_not_padded():
    ok = np.array([False, False] + [True] * 10 + [False, False])
    g = np.where(ok, np.arange(14.0) ** 2, 99.0)
    s = smooth(g, ok, 5)
    est = np.flatnonzero(ok)
    rows = [(0, est[:3]), (1, est[:4]), (5, est[3:8]), (8, est[6:]), (9, est[7:])]
    for j, near in rows:
        assert s[est[j]] == pytest.approx(g[near].mean())
    assert (s[~ok] == 0).all()  # not estimated: stays 0 and never enters a mean


def test_v12_fit_is_unchanged_without_a_span():
    r = simulated()
    m = RenshawHaberman().fit(r)
    assert m.converged and RenshawHaberman.SPAN is None
    assert np.abs(m.g).max() > 0.01


def test_smoothed_fit_converges_and_sums_to_zero():
    m = SmoothRH().fit(simulated())
    assert m.converged and m.change < 1e-9
    assert m.g[m.ok].sum() == pytest.approx(0, abs=1e-10)
    assert (m.g[~m.ok] == 0).all()


def test_two_starts_agree_and_smoothing_does_not_fit_better():
    r = simulated(heap=1.15)
    raw = RenshawHaberman().fit(r)
    one, two = SmoothRH().fit(r), SmoothRH().fit(r, g0=raw.g)
    assert one.converged and two.converged
    assert np.abs(one.fitted() - two.fitted()).max() < 1e-6
    dev = lambda m: scores.deviance(r.D, r.E * np.exp(m.fitted()))
    assert dev(one) >= dev(raw)


def detrend(v: np.ndarray, est: np.ndarray) -> np.ndarray:
    """A linear trend in g over birth years is not identified separately from age and period in RH."""
    x = est.astype(float)
    return v[est] - np.polyval(np.polyfit(x, v[est], 1), x)


@pytest.mark.parametrize("first", [
    pytest.param(2006, marks=pytest.mark.xfail(strict=True, reason="pre-freeze result: fails on the 14-year post-peak window "
                                                                    "(error 0.045; the bump recovered at 0.062 of 0.104)")),
    1997,
])
def test_recovers_a_known_cohort_effect(first):
    years = np.arange(first, 2020)
    coh = years[None, :] - AGES[:, None]
    a, b, k = lc_truth()
    k = np.interp(np.linspace(0, len(k) - 1, len(years)), np.arange(len(k)), k)
    k -= k.mean()
    c = np.arange(coh.min(), coh.max() + 1)
    g = 0.004 * (c - 1943) + np.where(np.abs(c - 1950) < 5, 0.15 * (1 + np.cos(np.pi * (c - 1950) / 5)) / 2, 0.0)
    E = np.geomspace(3e5, 5e3, len(AGES))[:, None] * np.ones(len(years))
    D = np.random.default_rng(3).poisson(E * np.exp(a[:, None] + np.outer(b, k) + g[coh - c[0]])).astype(float)
    m = SmoothRH().fit(Rates("Male", AGES, years, D, E))
    assert m.converged
    est = np.flatnonzero(m.ok)
    err = detrend(m.g, est) - detrend(smooth(np.where(m.ok, g, 0.0), m.ok, 5), est)
    assert np.abs(err[2:-2]).max() < 0.03


def test_heaped_spikes_are_damped():
    r = simulated(heap=1.15)
    raw, sm = RenshawHaberman().fit(r), SmoothRH().fit(r)
    c0 = COH.min()
    rounds = [j for j in interior(sm) if (j + c0) % 10 == 0]
    assert rounds
    spike = lambda m: np.mean([m.g[j] - (m.g[j - 1] + m.g[j + 1]) / 2 for j in rounds])
    assert spike(raw) > 0.08  # the heaping shows up in the unsmoothed cohort term
    assert abs(spike(sm)) < spike(raw) / 3
