"""IFRS 17 pieces for v4 (research/PROTOCOL_v4.md): the CSM at transition by the fair value approach, its yearly
roll-forward, and the risk adjustment's approximate confidence level."""
from __future__ import annotations

from scipy.stats import norm

COC_FAIR_VALUE = 0.10  # a buyer's cost of capital, the protocol's assumption


def transition_csm(ra: float, coc_ra: float, coc_fv: float = COC_FAIR_VALUE) -> float:
    """Fair value (BEL + cost of capital at `coc_fv`) less fulfilment cash flows (BEL + RA at `coc_ra`)."""
    return (coc_fv / coc_ra - 1) * ra


def confidence(ra: float, scr_ru: float) -> float:
    """Φ(2.576 RA / SCR): the RA as a quantile, if the 1-in-200 SCR were a normal 99.5% quantile."""
    return float(norm.cdf(norm.ppf(0.995) * ra / scr_ru))


def roll(open_: float, rate: float, units_now: float, units_left: float, start: float = 0.0, end: float = 0.0) -> dict:
    """One year: future-service changes at the start (`start`) and at the end before release (`end`), accretion at
    the locked-in `rate`, release over coverage units (`units_left` includes this year's). Changes that push the CSM
    below nil are a loss, and the CSM stays at nil."""
    x = open_ + start
    loss = max(-x, 0.0)
    x = max(x, 0.0)
    accretion = x * rate
    y = x + accretion + end
    loss += max(-y, 0.0)
    y = max(y, 0.0)
    release = y * units_now / units_left if units_left > 0 else y
    return {"open": open_, "adjustment": start + end, "accretion": accretion, "loss": loss, "release": release,
            "close": y - release}
