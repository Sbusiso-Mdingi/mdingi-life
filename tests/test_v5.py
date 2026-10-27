"""v5's funeral table pieces (mdingilife/table_v5.py), on small constructed inputs only (research/PROTOCOL_v5.md)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mdingilife import table_v5 as t5


def test_hiv_codes():
    code = pd.Series(["B20", "B24", "B25", "C46", "J09", "J19", "J20", "D84", "E86", "A05", "A10", "K53", "", "R99"])
    assert t5.hiv_related(code).tolist() == [True, True, True, True, True, False, True, True, True, True, False,
                                             False, False, False]
    assert t5.kind(code).tolist()[-2:] == ["other", "ill"]
    assert t5.kind(pd.Series(["V01", "X99", "Y98", "W10"])).tolist() == ["ext"] * 4


def test_shares_spread_ill_defined_pro_rata():
    tally = pd.DataFrame({"year": 2024, "sex": "Male", "age": 30, "code": ["B20", "X95", "I21", "R99"],
                          "deaths": [30, 10, 60, 50]})
    s = t5.shares(tally).iloc[0]
    assert s["hiv"] == pytest.approx(0.3) and s["ext"] == pytest.approx(0.1)


def test_tail_meets_at_80_5():
    x = np.arange(t5.FIT_TOP + 1)
    lg = -9 + 0.09 * x
    m = t5.tail(lg, 0.09)
    assert len(m) == t5.TOP + 1 and np.array_equal(m[:81], lg)
    assert t5.tail_slope(lg) == pytest.approx(0.09)
    # Kannisto's log slope at 81 is close to the tied one and falls with age; m stays below 1
    assert np.all(np.diff(m[80:]) > 0) and np.all(np.diff(np.diff(m[81:])) < 0) and np.exp(m[-1]) < 1


def test_table_2024_is_the_base_and_slope_is_held():
    x = np.arange(t5.FIT_TOP + 1)
    base = np.exp(t5.tail(-9 + 0.09 * x, 0.09))
    lc = np.exp(-9 + 0.09 * np.arange(t5.LC_TOP + 1))[None, :] * np.linspace(1, 0.7, 5)[:, None]
    m = t5.table(base, lc)
    assert np.max(np.abs(m[0] / base - 1)) < 1e-12
    assert not np.allclose(m[-1][81:], 0.7 * base[81:], rtol=1e-6)                  # the tail is tied, not scaled
    assert np.allclose(m[-1][:81], 0.7 * base[:81], rtol=1e-12)


def test_extend_carries_the_last_pace():
    m = np.exp(np.array([[-5.0, -4.0], [-5.1, -3.9]]))
    yrs, e = t5.extend(m, [2049, 2050], 2053)
    assert yrs.tolist() == [2049, 2050, 2051, 2052, 2053]
    assert np.allclose(np.log(e[-1]), [-5.4, -3.6])


def test_poisson_lc_recovers_a_trend():
    rng = np.random.default_rng(5)
    ages, years = np.arange(40), np.arange(12)
    a, b = -7 + 0.08 * ages, np.full(40, 1 / 40)
    k = 4.0 * (years - years.mean())
    E = np.full((40, 12), 2e5)
    D = rng.poisson(E * np.exp(a[:, None] + np.outer(b, -k))).astype(float)
    ah, bh, kh, *_ = t5.poisson_lc(D, E)
    assert np.corrcoef(kh, -k)[0, 1] > 0.999 and np.allclose(bh.sum(), 1) and abs(kh.sum()) < 1e-8


def test_overdispersion_is_about_one_for_poisson():
    rng = np.random.default_rng(6)
    ages, years = np.arange(100), np.arange(2005, 2025)
    E = np.full((100, 20), 1e5)
    mu = E * np.exp(-8 + 0.07 * ages)[:, None] * np.exp(-0.01 * (years - 2005))[None, :]
    assert t5.overdispersion(ages, years, rng.poisson(mu).astype(float), E) == pytest.approx(1, abs=0.1)
