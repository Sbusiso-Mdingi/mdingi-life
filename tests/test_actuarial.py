"""Annuity factors, the Kannisto tail, scores and data handling against closed forms."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mdingilife import annuity, kannisto, scores
from mdingilife.data import panel, spread_unknown


def monthly_sum(mu: float, rate: float, years: int) -> float:
    """Direct sum of 12 * years monthly payments at a constant force."""
    k = np.arange(12 * years)
    return float(np.exp(-(np.log1p(rate) + mu) * k / 12).sum() / 12)


@pytest.mark.parametrize("mu,rate", [(0.02, 0.04), (0.1, 0.0), (0.05, 0.06)])
def test_annuity_matches_closed_form_at_constant_force(mu, rate):
    n = 56  # ages 65 to 120
    assert annuity.factor(np.full(n, mu), rate) == pytest.approx(monthly_sum(mu, rate, n), rel=1e-12)
    # And the perpetuity limit for a long life.
    f = np.log1p(rate) + mu
    assert annuity.factor(np.full(2000, mu), rate) == pytest.approx(1 / 12 / (1 - np.exp(-f / 12)), rel=1e-9)


def test_annuitant_adjustment_scales_the_force():
    m = np.linspace(0.01, 0.5, 56)
    assert annuity.factor(m, 0.04, adj=0.6) == pytest.approx(annuity.factor(0.6 * m, 0.04))
    assert annuity.factor(m, 0.04, adj=0.6) > annuity.factor(m, 0.04)


def test_cohort_diagonal():
    ages = np.arange(50, 121)
    lm = np.log(np.add.outer(ages * 1e-4, np.arange(80) * 1e-6))  # m(x, j) = x/1e4 + j/1e6
    c = annuity.cohort(lm, ages, 65, 6)
    j = np.arange(len(c))
    assert np.allclose(c, (65 + j) * 1e-4 + (6 + j) * 1e-6)
    with pytest.raises(ValueError):
        annuity.cohort(lm[:, :40], ages, 65, 6)


def test_kannisto_recovers_known_curve():
    ages = np.arange(50, 90)
    logc, d = np.log(2e-5), 0.11
    eta = logc + d * np.arange(50, 121)
    true = eta - np.log1p(np.exp(eta))
    lm = np.stack([true[:40], true[:40] + 0.0], axis=1)  # two identical years
    out_ages, out = kannisto.extend(lm, ages)
    assert out_ages[-1] == 120 and len(out_ages) == 71
    assert np.allclose(out[:, 0], true, atol=1e-10)
    # Rates stay below 1 at any age.
    assert (np.exp(out) < 1).all()


def test_kannisto_vectorises_over_paths():
    ages = np.arange(50, 90)
    rng = np.random.default_rng(0)
    lm = -9 + 0.09 * ages[None, :, None] + 0.01 * rng.standard_normal((5, 40, 3))
    out_ages, out = kannisto.extend(lm, ages)
    assert out.shape == (5, 71, 3)
    one = kannisto.extend(lm[2], ages)[1]
    assert np.allclose(out[2], one)


def test_deviance_zero_at_perfect_fit_and_positive_otherwise():
    D = np.array([[0.0, 3, 10], [5, 7, 200]])
    assert scores.deviance(D, D + (D == 0) * 1e-300) == pytest.approx(0, abs=1e-9)
    assert scores.deviance(D, D * 1.1 + 0.1) > 0


def test_coverage():
    rng = np.random.default_rng(1)
    sims = rng.standard_normal((20000, 10, 5))
    assert scores.coverage(np.zeros((10, 5)), sims) == 1.0
    assert scores.coverage(np.full((10, 5), 5.0), sims) == 0.0
    big = rng.standard_normal((200, 50))
    assert abs(scores.coverage(big, rng.standard_normal((20000, 200, 50))) - 0.95) < 0.01


def test_annuity_error_zero_when_forecast_is_right():
    ages = np.arange(50, 90)
    lm = (-9 + 0.09 * ages)[:, None] + np.zeros((1, 3))
    assert np.allclose(scores.annuity_error(lm, lm, ages), 0)
    assert (scores.annuity_error(lm - 0.1, lm, ages) > 0).all()  # lighter mortality, dearer annuity


def test_spread_unknown_ages_pro_rata():
    df = pd.DataFrame({"year": 2000, "sex": "Male", "age": [50, 51, None], "deaths": [30.0, 10.0, 8.0]})
    out = spread_unknown(df, ["year", "sex"])
    assert out["deaths"].tolist() == [36.0, 12.0]


def test_panel_rejects_holes():
    df = pd.DataFrame({"year": [2000, 2000, 2001], "sex": "Male", "age": [50, 51, 50],
                       "deaths": 1.0, "exposure": 100.0})
    with pytest.raises(ValueError):
        panel(df, "Male")


def test_flat_forwards_match_a_flat_rate():
    m = np.linspace(0.01, 0.4, 56)
    flat = annuity.factor(m, 0.04, 0.7)
    assert annuity.factor(m, adj=0.7, forwards=np.full(60, np.log1p(0.04))) == pytest.approx(flat, rel=1e-12)
    rising = np.linspace(0.02, 0.06, 60)
    assert annuity.factor(m, 0.02, 0.7) > annuity.factor(m, adj=0.7, forwards=rising) > annuity.factor(m, 0.07, 0.7)
