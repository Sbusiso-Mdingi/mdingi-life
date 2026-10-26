"""SAM pieces: shocked curves, the catastrophe addition, aggregation and the monthly projection."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife import sam

FLAT = np.full(120, np.log1p(0.08))


@pytest.mark.parametrize("kind,shock,term,s", [
    ("nominal", "up", 1, 0.9308), ("nominal", "up", 30, 0.5057), ("nominal", "up", 60, 0.5057),
    ("nominal", "down", 0.1, -0.4806), ("nominal", "down", 10, -0.2730), ("real", "up", 4, 0.6552),
    ("real", "down", 30, -0.6802)])
def test_shocks_follow_the_attachment_table(kind, shock, term, s):
    cv = sam.Curve(FLAT, kind, shock)
    assert cv.spot(term) == pytest.approx(0.08 * (1 + s), rel=1e-9)


def test_shock_interpolates_between_terms():
    cv = sam.Curve(FLAT, "nominal", "up")
    assert cv.spot(1.5) == pytest.approx(0.08 * (1 + (0.9308 + 0.8238) / 2), rel=1e-9)


def test_move_is_at_least_one_point_and_nominal_is_floored():
    low = np.full(120, np.log1p(0.005))
    assert sam.Curve(low, "nominal", "up").spot(10) == pytest.approx(0.015)
    assert sam.Curve(low, "nominal", "down").spot(10) == 0.0
    assert sam.Curve(low, "real", "down").spot(10) == pytest.approx(-0.005)


def test_unshocked_discounting_matches_annual_spot():
    cv = sam.Curve(FLAT)
    assert cv.df(7.25) == pytest.approx(1.08 ** -7.25, rel=1e-12)
    assert sam.Curve(FLAT, "nominal", "up").df(0) == 1.0
    with pytest.raises(ValueError):
        cv.df(121)


def test_breakeven():
    assert sam.breakeven(sam.Curve(FLAT), sam.Curve(np.full(120, np.log1p(0.03)), "real")) == pytest.approx(1.08 / 1.03 - 1)


def test_catastrophe_addition_bounds():
    assert sam.cat_addition(0.0) == pytest.approx(4 * 0.125 / 1000)
    assert sam.cat_addition(0.001) == pytest.approx(4 * 0.3 / 1000)
    assert sam.cat_addition(0.0001) == pytest.approx(4 * (0.2 * 0.1 + 0.105) / 1000)


def test_aggregation():
    assert sam.aggregate([3, 4, 0, 0, 0], np.eye(5)) == pytest.approx(5)
    assert sam.aggregate([1, 0, 0, 0, 0], sam.CORR_LIFE) == pytest.approx(1)
    assert sam.pair(3, 4, 0.25) == pytest.approx(np.sqrt(25 + 6))
    assert np.allclose(sam.CORR_LIFE, sam.CORR_LIFE.T)
    assert np.all(np.linalg.eigvalsh(sam.CORR_LIFE) > 0)


def test_projection_against_a_plain_loop():
    rng = np.random.default_rng(1)
    mu, lapse = rng.uniform(0.001, 0.3, (3, 5)), rng.uniform(0, 0.4, (3, 5))
    inforce, deaths = sam.project(mu, lapse, mass=0.4, cat=True)
    for i in range(3):
        alive = 0.6
        for k in range(60):
            q = 1 - np.exp(-mu[i, k // 12] / 12)
            if k < 3:
                q += float(sam.cat_addition(q))
            assert inforce[i, k] == pytest.approx(alive, rel=1e-12)
            assert deaths[i, k] == pytest.approx(alive * q, rel=1e-12)
            alive *= (1 - q) * (1 - lapse[i, k // 12]) ** (1 / 12)


def test_projection_without_lapses_conserves_policies():
    mu = np.full((1, 50), 0.05)
    inforce, deaths = sam.project(mu)
    assert inforce[0, 1:] == pytest.approx(inforce[0, :-1] - deaths[0, :-1])
    assert inforce[0, 12] == pytest.approx(np.exp(-0.05))
