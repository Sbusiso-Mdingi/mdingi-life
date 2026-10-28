"""v7's pieces (research/PROTOCOL_v7.md), on small constructed inputs only."""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from research import balance_v3 as b3
from research import balance_v7 as b7
from research import book_v5 as bk5
from research import book_v7 as bk
from research import projection_v4 as pv


def test_review_years_are_6_11_16():
    py = np.arange(1, 22)
    assert py[b7.review_year(py)].tolist() == [6, 11, 16, 21]


def test_lapse_spike_only_for_age_rated_in_review_years():
    n = np.array([0, 4, 4])
    rated = np.array([True, True, False])
    r = b7.lapse_rows(n, rated, 0.10, years=12)
    base = b7.lapse_rows(n, rated, 0.0, years=12)
    assert np.array_equal(base, b7.lapse_rows(n, np.zeros(3, bool), 0.10, years=12))       # F3's identity
    assert np.allclose(r - base, [[0] * 5 + [0.1] + [0] * 4 + [0.1, 0],
                                  [0, 0.1] + [0] * 4 + [0.1] + [0] * 4 + [0.1],
                                  [0] * 12])
    assert np.all(b7.lapse_rows(np.array([0]), np.array([True]), 0.99, years=6) <= 1.0)


def _sched():
    rows = []
    for s in ("Male", "Female"):
        for e in bk5.ENTRY:
            n = bk.TOP - e + 1
            rows.append(pd.DataFrame({"sex": s, "entry_age": e, "policy_year": np.arange(n),
                                      "per_rand": 1e-3 * (1 + np.arange(n)), "fixed": 30.0}))
    return pd.concat(rows, ignore_index=True)


def test_rows_follow_the_schedule_from_years_in_force():
    fun = pd.DataFrame({"sex": ["Male", "Female"], "entry_age": [30, 64], "years_in_force": [2, 0],
                        "sum_assured": [10_000, 20_000], "premium_type": ["age-rated", "level"], "premium": [0.0, 55.5]})
    r = bk.rows(_sched(), fun, 5)
    assert r[0].tolist() == [60.0, 70.0, 80.0, 90.0, 100.0]          # 1e-3 (1 + 2 + k) 10,000 + 30
    assert r[1].tolist() == [55.5] * 5
    late = fun.assign(entry_age=[64, 64], years_in_force=[bk.TOP - 64 - 1, 0])
    assert bk.rows(_sched(), late, 4)[0].tolist() == [10 * (bk.TOP - 64) + 30.0] + [10 * (bk.TOP - 64 + 1) + 30.0] * 3
    start = bk.rows(_sched(), fun, 5, start=np.array([3, 0]))
    assert np.isnan(start[0, :3]).all() and start[0, 3:].tolist() == [90.0, 100.0]


def test_premium_rows_hook_matches_scalar_premiums():
    b = b3.Book.__new__(b3.Book)
    b.fun = pd.DataFrame({"sum_assured": [1e4, 2e4], "premium": [50.0, 80.0], "count": [1, 2]})
    b.mu_fun = np.full((2, 4), 0.01)
    b.lapse = np.full((2, 4), 0.1)
    b.mu_ann = {lv: np.full((1, 4), 0.02) for lv in (False, True)}
    b.ann = pd.DataFrame({"income": [12_000.0], "count": [1]})
    b.ilb = np.array([False])
    b.t = np.arange(48) / 12
    cv = b3.Curves(np.full(110, 0.08), np.full(110, 0.03))
    flat = b3.liabilities(b, cv, b3.BASE)
    b.prem = np.repeat(b.fun["premium"].to_numpy()[:, None], 4, axis=1)
    assert np.allclose(b3.liabilities(b, cv, b3.BASE)["premiums"], flat["premiums"], rtol=1e-14)
    b.prem = b.prem * np.array([1.0, 2.0, 1.0, 1.0])
    assert np.all(b3.liabilities(b, cv, b3.BASE)["premiums"] > flat["premiums"])


def test_ageing_moves_premium_rows_with_survivors():
    b = b3.Book.__new__(b3.Book)
    b.ann = pd.DataFrame({"age": [70], "income": [1.0], "count": [1.0], "policies": [1.0], "new": [False]})
    b.fun = pd.DataFrame({"age": [40], "years_in_force": [0], "sum_assured": [1e4], "premium": [10.0],
                          "count": [1.0], "policies": [1.0]})
    b.ilb = np.array([False])
    b.mu_ann = {False: np.full((1, 3), 0.02), True: np.full((1, 3), 0.01)}
    b.mu_fun, b.lapse = np.full((1, 3), 0.01), np.full((1, 3), 0.1)
    b.prem = np.array([[10.0, 20.0, 30.0]])
    b.index, b.years, b.basis = 1.0, 0, b3.Basis()
    pv.CTX["longevity"] = {(b.basis.annuitant_adj, 1): np.zeros((1, 3))}
    dec = pv.decrements(b)
    n = pv.age(b, dec, 0.0, 0.0)
    w = dec[1][0, 12]
    assert np.allclose(n.prem, [[20 * w, 30 * w, 30 * w]]) and n.fun["premium"].iloc[0] == pytest.approx(20 * w)
    wave = pv.lapse_wave(b, 0.3)
    assert np.allclose(wave.prem, 0.7 * b.prem)
    pv.CTX.pop("longevity")


def test_default_risk_and_market_aggregation():
    assert b7.FACTORS[12] == 0.0435 and len(b7.FACTORS) == 18 and all(np.diff(list(b7.FACTORS.values())) > 0)
    assert b7.market(3.0, 4.0, 0.0) == pytest.approx(5.0)
    assert b7.market(3.0, 4.0, 0.5) == pytest.approx(np.sqrt(9 + 12 + 16))
    assert b7.market(3.0, 0.0, 0.5) == 3.0


def test_sovereign_reverse_stress():
    s = b7.sovereign(400.0, 222.0, 800.0)
    assert (400 - s["cover_one"] * 800) / 222 == pytest.approx(1.0)
    assert 400 - s["own_funds_zero"] * 800 == pytest.approx(0.0)


def test_scaled_scales_premium_rows():
    b = b7.Book.__new__(b7.Book)
    b.ann = pd.DataFrame({"income": [1.0], "count": [1.0]})
    b.fun = pd.DataFrame({"sum_assured": [1.0], "premium": [2.0], "count": [1.0]})
    b.prem, b.fun_scale, b.n_ann, b.n_fun = np.array([[2.0, 3.0]]), 1.0, 1, 1
    s = b7.scaled(b, 2.0, 5.0)
    assert s.prem.tolist() == [[10.0, 15.0]] and s.fun_scale == 5.0 and b.prem.tolist() == [[2.0, 3.0]]
    assert copy.copy(s).prem is s.prem
