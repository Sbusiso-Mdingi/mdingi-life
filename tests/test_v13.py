"""v1.3's smoothed cohort term, on simulated data (research/PROTOCOL_v1.3.md, "Reporting")."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import scores
from mdingilife.data import Rates
from mdingilife.models import RenshawHaberman, SmoothRH, smooth
from tests.test_models import lc_truth

AGES = np.arange(50, 90)
WINDOWS = {"men, 14 years": 2006, "women, 23 years": 1997}  # v1.2's RH windows, each ending in 2019
# WPP-sized exposures for South African men: about 300,000 at 50, falling to about 5,000 at 89
SIZE = np.geomspace(3e5, 5e3, len(AGES))[:, None]


def known_g(c: np.ndarray) -> np.ndarray:
    """A known smooth cohort effect by birth year: a linear trend plus a bump 10 years wide, of size 0.15."""
    return 0.004 * (c - 1943) + np.where(np.abs(c - 1950) < 5, 0.15 * (1 + np.cos(np.pi * (c - 1950) / 5)) / 2, 0.0)


def truth(years: np.ndarray):
    """a, b and k of the model tests' shape on `years`, and the known g."""
    a, b, k = lc_truth()
    k = np.interp(np.linspace(0, len(k) - 1, len(years)), np.arange(len(k)), k)
    k -= k.mean()
    coh = years[None, :] - AGES[:, None]
    c = np.arange(coh.min(), coh.max() + 1)
    return a, b, k, c, known_g(c)


def draw(a, b, k, c, g, years, E, heap: float = 1.0, seed: int = 3) -> Rates:
    coh = years[None, :] - AGES[:, None]
    log_m = a[:, None] + np.outer(b, k) + g[coh - c[0]]
    lift = np.where(coh % 10 == 0, heap, 1.0)
    D = np.random.default_rng(seed).poisson(E * np.exp(log_m) * lift).astype(float)
    return Rates("Male", AGES, years, D, E.copy())


def simulated(first: int = 2006, heap: float = 1.0, seed: int = 3) -> Rates:
    years = np.arange(first, 2020)
    return draw(*truth(years), years, SIZE * np.ones(len(years)), heap, seed)


both = pytest.mark.parametrize("first", list(WINDOWS.values()), ids=list(WINDOWS))


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


@both
def test_v12_fit_is_unchanged_without_a_span(first):
    r = simulated(first)
    m = RenshawHaberman().fit(r)
    assert m.converged and RenshawHaberman.SPAN is None
    assert np.abs(m.g).max() > 0.01


@both
def test_smoothed_fit_converges_and_sums_to_zero(first):
    m = SmoothRH().fit(simulated(first))
    assert m.converged and m.change < 1e-9
    assert m.g[m.ok].sum() == pytest.approx(0, abs=1e-10)
    assert (m.g[~m.ok] == 0).all()


@both
def test_two_starts_agree_and_smoothing_does_not_fit_better(first):
    r = simulated(first, heap=1.15)
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


def recovery_error(r: Rates, c: np.ndarray, g: np.ndarray) -> tuple[float, float, float]:
    """Largest miss at the interior cohorts, after a straight line is removed from both, and the bump's height
    in the fit and in the target (the five-year mean of the true g)."""
    m = SmoothRH().fit(r)
    assert m.converged
    est = np.flatnonzero(m.ok)
    target = smooth(np.where(m.ok, g, 0.0), m.ok, 5)
    fit, want = detrend(m.g, est), detrend(target, est)
    return float(np.abs(fit - want)[2:-2].max()), float(fit.max()), float(want.max())


@pytest.mark.parametrize("first", [
    pytest.param(2006, id="men, 14 years", marks=pytest.mark.xfail(
        strict=True, reason="seen before the freeze: misses by 0.045 on the 14-year window (the bump recovered at 0.062 of 0.104)")),
    pytest.param(1997, id="women, 23 years"),
])
def test_recovers_a_known_cohort_effect(first):
    years = np.arange(first, 2020)
    a, b, k, c, g = truth(years)
    assert recovery_error(draw(a, b, k, c, g, years, SIZE * np.ones(len(years))), c, g)[0] < 0.03


@both
def test_heaped_spikes_are_damped(first):
    r = simulated(first, heap=1.15)
    raw, sm = RenshawHaberman().fit(r), SmoothRH().fit(r)
    c0 = int(r.years[0] - r.ages[-1])
    rounds = [j for j in interior(sm) if (j + c0) % 10 == 0]
    assert rounds
    spike = lambda m: np.mean([m.g[j] - (m.g[j - 1] + m.g[j + 1]) / 2 for j in rounds])
    assert spike(raw) > 0.08  # the heaping shows up in the unsmoothed cohort term
    assert abs(spike(sm)) < spike(raw) / 3
