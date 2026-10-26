"""Bond pricing and curve fits on simulated bonds with known answers."""
from datetime import date

import numpy as np
import pytest

from mdingilife import curves as c

SETTLE = date(2024, 5, 3)
TRUE_NS = (0.11, -0.03, 0.02, 2.5)
TRUE_NSS = (0.11, -0.03, -0.08, 0.10, 0.8, 12.0)


def bond(code, coupon, y, m, d, shares=None):
    if shares is None:
        return c.Bond(code, coupon, ((date(y, m, d), 1.0),))
    return c.Bond(code, coupon, tuple((date(y + k, m, d), s) for k, s in enumerate(shares)))


BOOK = [bond("A", 8.0, 2026, 1, 31), bond("B", 8.25, 2028, 3, 31), bond("C", 7.0, 2031, 2, 28),
        bond("D", 8.875, 2035, 2, 28), bond("E", 8.5, 2037, 1, 31), bond("F", 9.0, 2040, 1, 31),
        bond("G", 8.75, 2043, 1, 31, (1 / 3, 1 / 3, 1 / 3)), bond("H", 8.75, 2048, 2, 28),
        bond("I", 11.625, 2053, 3, 31)]


def points(zero, noise=0.0, rng=None):
    out = []
    for b in BOOK:
        t, cf = b.cashflows(SETTLE)
        y = c.yield_from_price(t, cf, float(np.sum(cf * np.exp(-zero(t) * t))))
        if noise:
            y += rng.normal(0, noise)
        out.append(c.Point(b.code, t, cf, y))
    return out


def test_coupon_dates_follow_the_redemption_date():
    b = bond("R2030", 8.0, 2030, 1, 31)
    ds = b.coupon_dates()
    assert ds[-1] == date(2030, 1, 31) and ds[-2] == date(2029, 7, 31) and ds[-3] == date(2029, 1, 31)
    feb = bond("R213", 7.0, 2031, 2, 28).coupon_dates()
    assert date(2030, 8, 31) in feb and date(2028, 2, 29) in feb  # month ends, including a leap year


def test_par_bond_prices_at_100_on_a_coupon_date():
    b = bond("X", 9.0, 2034, 6, 30)
    t, cf = b.cashflows(date(2024, 6, 30))
    assert cf.sum() == pytest.approx(100 + 20 * 4.5)
    assert c.price_from_yield(t, cf, 0.09) == pytest.approx(100, abs=0.05)  # actual/365 against half-years


def test_instalments_reduce_later_coupons():
    b = bond("G", 8.0, 2043, 1, 31, (1 / 3, 1 / 3, 1 / 3))
    t, cf = b.cashflows(date(2042, 12, 1))
    assert cf[0] == pytest.approx(4 + 100 / 3)  # coupon on the full amount, plus a third repaid
    assert cf[1] == pytest.approx(4 * 2 / 3)  # next coupon on two thirds
    assert cf[-1] == pytest.approx(4 / 3 + 100 / 3)


def test_yield_and_price_invert():
    t, cf = BOOK[4].cashflows(SETTLE)
    p = c.price_from_yield(t, cf, 0.1123)
    assert c.yield_from_price(t, cf, p) == pytest.approx(0.1123, abs=1e-10)
    h = 1e-6
    assert c.dv(t, cf, 0.1123) == pytest.approx(-(c.price_from_yield(t, cf, 0.1123 + h)
                                                  - c.price_from_yield(t, cf, 0.1123 - h)) / (2 * h), rel=1e-5)


def test_ns_recovers_its_own_curve():
    fit = c.NS.fit(points(lambda t: c.ns(t, *TRUE_NS)))
    grid = np.linspace(1, 30, 30)
    assert np.abs(fit.zero(grid) - c.ns(grid, *TRUE_NS)).max() < 1e-5


def test_nss_recovers_its_own_curve_and_ns_cannot():
    pts = points(lambda t: c.nss(t, *TRUE_NSS))
    worst = lambda f: max(abs(f.bond_yield(q.t, q.cf) - q.y) for q in pts)
    assert worst(c.NSS.fit(pts)) < 2e-5
    assert worst(c.NS.fit(pts)) > 1e-4  # one basis point


def test_noisy_fit_errors_are_yield_errors():
    rng = np.random.default_rng(1)
    pts = points(lambda t: c.ns(t, *TRUE_NS), noise=0.0010, rng=rng)
    fit = c.NS.fit(pts)
    err = np.array([fit.bond_yield(q.t, q.cf) - q.y for q in pts])
    assert 0.0002 < np.sqrt(np.mean(err ** 2)) < 0.0015


def test_li_reads_off_between_bonds_and_flat_beyond():
    pts = points(lambda t: c.ns(t, *TRUE_NS))
    li = c.LI.fit(pts)
    t, cf = BOOK[3].cashflows(SETTLE)
    assert li.bond_yield(t, cf) == pytest.approx(pts[3].y)
    long = bond("Z", 9.0, 2060, 3, 31).cashflows(SETTLE)
    assert li.bond_yield(*long) == pytest.approx(pts[-1].y)


def test_forwards_flat_beyond_the_last_maturity():
    fit = c.NS(TRUE_NS)
    f = c.forwards(fit, 20.0, 60)
    z = lambda t: c.ns(t, *TRUE_NS) * t
    assert f[5] == pytest.approx(z(6) - z(5), abs=1e-10)
    assert np.allclose(f[21:], f[25])
    assert f[25] == pytest.approx((z(20 + 1e-4) - z(20 - 1e-4)) / 2e-4, abs=1e-6)
