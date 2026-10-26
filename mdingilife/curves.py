"""Government bond cash flows, prices from yields and from zero curves, and three curves fitted to a handful of bonds.

Rates are decimals. A yield y is compounded semi-annually; a zero rate z(t) is continuously compounded, t in years
(actual/365) from settlement. Every bond in a fit carries its own settlement date: a window pools auctions from
different days, and the curve is read as a function of time to payment only.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy.optimize import brentq, least_squares

FLOOR = 1.0  # bonds with less than a year to their final redemption are not used


def _back(d: date, months: int) -> date:
    """`d` moved back by `months`, staying on the month end if `d` is one."""
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    m += 1
    last = calendar.monthrange(y, m)[1]
    end = d.day == calendar.monthrange(d.year, d.month)[1]
    return date(y, m, last if end else min(d.day, last))


@dataclass(frozen=True)
class Bond:
    code: str
    coupon: float  # per cent a year
    redemptions: tuple[tuple[date, float], ...]  # (date, share of principal)

    def coupon_dates(self) -> list[date]:
        """Every coupon date back to 50 years before the final redemption: the last is on the redemption date."""
        final = max(d for d, _ in self.redemptions)
        return [_back(final, 6 * k) for k in range(100, -1, -1)]

    def cashflows(self, settle: date) -> tuple[np.ndarray, np.ndarray]:
        """Times (years from settlement) and amounts per 100 nominal of everything paid after `settle`."""
        reds = sorted(self.redemptions)
        out = {}
        for d in self.coupon_dates():
            if d > settle:
                left = 1 - sum(s for r, s in reds if r < d)
                out[d] = out.get(d, 0.0) + 100 * left * self.coupon / 200
        for r, s in reds:
            if r > settle:
                out[r] = out.get(r, 0.0) + 100 * s
        ds = sorted(out)
        return np.array([(d - settle).days / 365 for d in ds]), np.array([out[d] for d in ds])


def price_from_yield(t: np.ndarray, cf: np.ndarray, y: float) -> float:
    return float(np.sum(cf * (1 + y / 2) ** (-2 * t)))


def dv(t: np.ndarray, cf: np.ndarray, y: float) -> float:
    """Price change per unit of yield (positive)."""
    return float(np.sum(cf * t * (1 + y / 2) ** (-2 * t - 1)))


def yield_from_price(t: np.ndarray, cf: np.ndarray, p: float) -> float:
    return brentq(lambda y: price_from_yield(t, cf, y) - p, -0.5, 2.0)


# Zero curves -----------------------------------------------------------------------------------------------------

def _l1(x):
    return np.where(x < 1e-8, 1 - x / 2, (1 - np.exp(-x)) / np.maximum(x, 1e-12))


def _l2(x):
    return _l1(x) - np.exp(-x)


def ns(t, b0, b1, b2, tau):
    t = np.asarray(t, float)
    return b0 + b1 * _l1(t / tau) + b2 * _l2(t / tau)


def nss(t, b0, b1, b2, b3, tau1, tau2):
    return ns(t, b0, b1, b2, tau1) + b3 * _l2(np.asarray(t, float) / tau2)


@dataclass
class Point:
    """One bond's clearing yield in a window, with its cash flows from its own settlement date."""
    code: str
    t: np.ndarray
    cf: np.ndarray
    y: float

    @property
    def maturity(self) -> float:
        return float(self.t[-1])

    @property
    def price(self) -> float:
        return price_from_yield(self.t, self.cf, self.y)


class Curve:
    name = ""
    n_params = 0

    def zero(self, t):
        raise NotImplementedError

    def bond_yield(self, t: np.ndarray, cf: np.ndarray) -> float:
        return yield_from_price(t, cf, float(np.sum(cf * np.exp(-self.zero(t) * t))))


class Parametric(Curve):
    def __init__(self, params):
        self.params = np.asarray(params, float)

    @classmethod
    def unpack(cls, x):
        raise NotImplementedError

    @classmethod
    def starts(cls):
        raise NotImplementedError

    @classmethod
    def fit(cls, pts: list[Point]) -> "Parametric":
        """Least squares on price errors divided by each bond's price change per unit of yield, i.e. on yield errors."""
        p = np.array([q.price for q in pts])
        w = np.array([dv(q.t, q.cf, q.y) for q in pts])
        y = np.array([q.y for q in pts])
        level = 2 * np.log1p(y / 2)
        k = max(len(q.t) for q in pts)  # cash flows padded into one matrix; padding pays nothing
        T = np.ones((len(pts), k))
        CF = np.zeros((len(pts), k))
        for i, q in enumerate(pts):
            T[i, :len(q.t)], CF[i, :len(q.t)] = q.t, q.cf

        def res(x):
            return ((CF * np.exp(-cls.zero_of(cls.unpack(x), T) * T)).sum(axis=1) - p) / w

        best = None
        for start in cls.starts():
            x0 = cls.initial(level, np.array([q.maturity for q in pts]), start)
            lo, hi = cls.bounds()
            try:
                r = least_squares(res, np.clip(x0, lo + 1e-9, hi - 1e-9), bounds=(lo, hi), x_scale="jac")
            except ValueError:
                continue
            if best is None or r.cost < best.cost:
                best = r
        return cls(cls.unpack(best.x))

    def zero(self, t):
        return self.zero_of(self.params, t)


class NS(Parametric):
    """Nelson-Siegel. Fitted as (b0, b0 + b1, b2, tau) so that b0 > 0 and b0 + b1 > 0 are box bounds."""
    name, n_params = "NS", 4

    @staticmethod
    def zero_of(p, t):
        return ns(t, *p)

    @staticmethod
    def unpack(x):
        return np.array([x[0], x[1] - x[0], x[2], x[3]])

    @staticmethod
    def bounds():
        return np.array([0, 0, -1, 0.1]), np.array([1, 1, 1, 30])

    @staticmethod
    def starts():
        return [(tau,) for tau in (0.5, 1, 2, 3, 5, 8, 12)]

    @staticmethod
    def initial(level, mat, start):
        (tau,) = start
        X = np.column_stack([np.ones_like(mat), _l1(mat / tau), _l2(mat / tau)])
        b = np.linalg.lstsq(X, level, rcond=None)[0]
        return np.array([max(b[0], 1e-4), max(b[0] + b[1], 1e-4), b[2], tau])


class NSS(Parametric):
    """Svensson. Fitted as (b0, b0 + b1, b2, b3, tau1, tau2 - tau1) so that tau1 < tau2 is a box bound."""
    name, n_params = "NSS", 6

    @staticmethod
    def zero_of(p, t):
        return nss(t, *p)

    @staticmethod
    def unpack(x):
        return np.array([x[0], x[1] - x[0], x[2], x[3], x[4], x[4] + x[5]])

    @staticmethod
    def bounds():
        return np.array([0, 0, -1, -1, 0.1, 0.1]), np.array([1, 1, 1, 1, 30, 30])

    @staticmethod
    def starts():
        return [(a, b) for a in (0.5, 1, 2, 4) for b in (5, 10, 20) if b > a]

    @staticmethod
    def initial(level, mat, start):
        t1, t2 = start
        X = np.column_stack([np.ones_like(mat), _l1(mat / t1), _l2(mat / t1), _l2(mat / t2)])
        b = np.linalg.lstsq(X, level, rcond=None)[0]
        return np.array([max(b[0], 1e-4), max(b[0] + b[1], 1e-4), b[2], b[3], t1, t2 - t1])


class LI(Curve):
    """Yield to maturity linear in maturity between the window's bonds, flat beyond them. Not a zero curve:
    a bond's yield is read off directly."""
    name, n_params = "LI", 2

    def __init__(self, mat, y):
        order = np.argsort(mat)
        self.mat, self.y = np.asarray(mat)[order], np.asarray(y)[order]

    @classmethod
    def fit(cls, pts: list[Point]) -> "LI":
        return cls([q.maturity for q in pts], [q.y for q in pts])

    def bond_yield(self, t, cf) -> float:
        return float(np.interp(t[-1], self.mat, self.y))


class Bootstrap(Curve):
    """The zero curve behind LI: forwards constant between successive final redemptions, each set so that the
    bond maturing at the segment's end prices exactly at its clearing yield. Flat before the first and beyond the
    last node."""
    name = "LI zero"

    def __init__(self, nodes, fwd):
        self.nodes, self.fwd = np.asarray(nodes, float), np.asarray(fwd, float)  # fwd[i] applies up to nodes[i]

    def zero(self, t):
        t = np.asarray(t, float)
        edges = np.concatenate([[0.0], self.nodes])
        cum = np.concatenate([[0.0], np.cumsum(self.fwd * np.diff(edges))])
        i = np.clip(np.searchsorted(self.nodes, t), 0, len(self.fwd) - 1)
        integral = cum[i] + self.fwd[i] * (t - edges[i])
        return np.where(t > 0, integral / np.maximum(t, 1e-12), self.fwd[0])

    @classmethod
    def fit(cls, pts: list[Point]) -> "Bootstrap":
        pts = sorted(pts, key=lambda q: q.maturity)
        nodes, fwd = [], []
        for q in pts:
            nodes.append(q.maturity)
            def err(f):
                c = cls(nodes, fwd + [f])
                return float(np.sum(q.cf * np.exp(-c.zero(q.t) * q.t))) - q.price
            fwd.append(brentq(err, -0.5, 2.0))
        return cls(nodes, fwd)


MODELS = {"LI": LI, "NS": NS, "NSS": NSS}


def forwards(curve: Parametric, last: float, years: int) -> np.ndarray:
    """Continuously compounded forward rate for each year 0..years-1 from the curve, with the forward held at its
    value at `last` (the longest maturity fitted) beyond it."""
    def zt(t):
        t = np.asarray(t, float)
        tc = np.minimum(t, last)
        h = 1e-4
        f_last = (curve.zero(last + h) * (last + h) - curve.zero(last - h) * (last - h)) / (2 * h)
        return curve.zero(np.maximum(tc, 1e-9)) * tc + f_last * (t - tc)
    edges = np.arange(years + 1, dtype=float)
    return np.diff(zt(edges))
