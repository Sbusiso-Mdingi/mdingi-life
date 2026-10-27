"""v5's rising funeral benefit (mdingilife/inflation_v5.py, research/book_v5.py, research/balance_v5.py), on small
constructed inputs only (research/PROTOCOL_v5.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mdingilife import inflation_v5 as iv, sam
from research import balance_v5 as b5, book_v5 as bk
from research.balance_v3 import BASE, LIFE_STRESSES, RATE_STRESSES, YEARS, Curves


def test_fit_recovers_an_ar1():
    rng = np.random.default_rng(1)
    i = np.empty(20_000)
    i[0] = 0.06
    for t in range(1, len(i)):
        i[t] = 0.06 * (1 - 0.7) + 0.7 * i[t - 1] + 0.01 * rng.standard_normal()
    i[500] = np.nan                                                               # a missing month is skipped
    m = iv.Model.fit(i)
    assert m.phi == pytest.approx(0.7, abs=0.01) and m.sigma == pytest.approx(0.01, rel=0.02)


def test_paths_start_at_zero_and_have_the_model_sd():
    m = iv.Model(0.7, 0.01)
    x = iv.paths(m, 4, 40_000)
    assert x.shape == (40_000, 4) and np.all(x[:, 0] == 0)
    assert np.std(x[:, 3]) == pytest.approx(m.sd(3), rel=0.02)


def test_growth_without_noise_is_compound_and_clipped():
    x = np.zeros((3, 10))
    for f, rate in ((0.05, 0.05), (0.08, 0.06), (-0.01, 0.0)):
        assert np.allclose(iv.growth(f, x), (1 + rate) ** np.arange(11), rtol=1e-14)
    assert np.allclose(iv.growth(0.08, x, None, None), 1.08 ** np.arange(11), rtol=1e-14)
    assert np.array_equal(iv.growth(0.08, np.ones((3, 10)), cap=0.0), np.ones(11))


def test_growth_uses_the_start_of_year_rate():
    x = np.array([[0.0, 0.01, -0.02]])
    assert np.allclose(iv.growth(0.03, x, None, None), [1, 1.03, 1.03 * 1.04, 1.03 * 1.04 * 1.01])


def test_shock_raises_the_sd_by_the_rule():
    m = iv.Model(0.7, 0.02)
    s = iv.shock_scale(m, 0.07, 30)
    t = np.arange(1, 30)
    assert s[0] == 1 and np.allclose(m.sd(t) * s[1:], m.sd(t) + iv.VOL_RISE * 0.07 / np.sqrt(t))


def test_monthly_is_level_within_the_year():
    assert iv.monthly(np.array([1.0, 1.1, 1.2]), 40).tolist() == [1.0] * 12 + [1.1] * 12 + [1.2] * 16


def test_mu_rows_follow_the_cohort():
    g = {s: np.arange(5 * 121, dtype=float).reshape(5, 121) for s in ("Female", "Male")}
    mu = bk.mu_rows(g, np.array(["Male"]), np.array([118]), 5, adj=2.0)
    assert mu[0].tolist() == [2 * 118, 2 * (121 + 119), 2 * (242 + 120), 1e3, 1e3]


def test_growth_rows():
    r = bk.growth_rows([False, True], 25, 0.05)
    assert np.all(r[0] == 1) and r[1, 11] == 1 and r[1, 12] == pytest.approx(1.05) and r[1, 24] == pytest.approx(1.05 ** 2)


def toy(cap=iv.CAP):
    """A balance-sheet book of one annuity cell and two funeral cells, the second rising, on flat curves."""
    years = YEARS
    b = b5.Book.__new__(b5.Book)
    b.ann = pd.DataFrame({"income": [12_000.0], "count": [1], "new": [True]})
    b.mu_ann = {lv: np.full((1, years), 0.03 * (0.9 if lv else 1)) for lv in (False, True)}
    b.ilb = np.array([False])
    b.fun = pd.DataFrame({"sex": ["Male"] * 2, "age": [40] * 2, "years_in_force": [0, 3], "benefit": ["level", "rising"],
                          "sum_assured": [20_000.0, 30_000.0], "premium": [90.0, 160.0], "count": [2, 3]})
    b.mu_fun = np.tile(np.exp(-8 + 0.09 * (40 + np.arange(years))), (2, 1)).clip(max=5)
    b.lapse = np.full((2, years), 0.05)
    b.rising = np.array([False, True])
    model = iv.Model(0.7, 0.01)
    b.growth = b5.Growth(model, iv.paths(model, years, 2_000), cap=cap)
    b.t = np.arange(12 * years) / 12
    cv = Curves(np.full(110, 0.10), np.full(110, 0.035))
    return b, cv


def test_loop_agrees_with_the_main_code():
    b, cv = toy()
    f = b.fun.iloc[1]
    for sc in {"base": BASE, **LIFE_STRESSES, **RATE_STRESSES, "volatility": b5.VOL}.values():
        L = b5.liabilities(b, cv, sc)
        nom, real = cv.get(sc)
        lf = b5.loop_rising(b.mu_fun[1], b.lapse[1], f["sum_assured"], f["premium"], f["count"], nom, real, sc, b.growth)
        ef = L["claims"][1] + L["fun_expenses"][1] - L["premiums"][1]
        assert abs(lf / ef - 1) < 1e-8


def test_no_growth_is_level_and_the_level_cell_is_untouched():
    from research import balance_v3 as b3
    b, cv = toy(cap=0.0)
    assert np.array_equal(b5.liabilities(b, cv, BASE)["claims"], b3.liabilities(b, cv, BASE)["claims"])
    b, cv = toy()
    L, L3 = b5.liabilities(b, cv, BASE), b3.liabilities(b, cv, BASE)
    assert L["claims"][0] == L3["claims"][0] and L["claims"][1] > L3["claims"][1]


def test_the_expense_stress_leaves_growth_alone():
    b, cv = toy()
    assert np.array_equal(b5.liabilities(b, cv, BASE)["rising_claims"],
                          b5.liabilities(b, cv, LIFE_STRESSES["expense"])["rising_claims"])
