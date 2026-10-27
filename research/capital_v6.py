"""v6's capital level (research/PROTOCOL_v6.md, "Reruns" 3): the own funds at which cover starts at 1.0 on v6's
book, solved by Brent's method, then v4's scenarios and five named stresses at that level (research.capital_v4's
level, with the change in own funds all in the 182-day bill and the whole-book match left on the BEL).

    python -m research.capital_v6 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv [--grids-cache PATH]

R400 million, cover 1.8, is v6's main projection (research.projection_v5 --v6). Needs research.mix_v6 first. Writes
research/results/capital_v6.json. Refuses to run until the v2 to v6 protocols are frozen.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd
from scipy.optimize import brentq

from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V4, PROTOCOL_V5, PROTOCOL_V6, require_frozen
from research import capital_v4 as c4
from research import curves as rc
from research import mix_v6 as mx
from research import projection_v4 as pv
from research import projection_v5 as p5
from research import scenarios_v4 as sv
from research.backtest import OUT
from research.balance_v3 import Basis, auctions, market
from research.book_v3 import TABLE

OUTFILE = OUT / "capital_v6.json"
TARGET, TOL = 1.0, 1e-6


def setup(deaths: str, population: str, cache: str | None) -> dict:
    """capital_v4's setup on v6's book: the market, the generator, the R400 million valuation and the stresses."""
    bonds = rc.book()
    a = auctions(bonds)
    curves, bonds, days, settle = market(a)
    grids = mx.grids(deaths, population, cache)
    s = p5.setup(grids, v6=True)
    make = s["make_book"]
    fwd0 = curves["LI"]
    pv.CTX.update(s["ctx"])
    pv.CTX.update(grids=grids, table=pd.read_csv(TABLE), bonds=bonds, settle=settle, fwd0=fwd0, scale=1.0)
    points = sv.month_points(a)
    jump = {k: rc.window(a[a["kind"] == kind], days[k][1], rc.WINDOW, inclusive=True) for k, kind in sv.KINDS.items()}
    cal = sv.calibrate(points, jump)
    sims, central = sv.paths(cal)
    book0 = pv.start(make(Basis()))
    r0 = pv.valuation(book0, fwd0, settle)
    want = json.loads(mx.RESULT.read_text())["main"]["cover"]
    print(f"R400m: t=0 cover {r0['cover']:.6f} (mix_v6 {want:.6f})", flush=True)
    if abs(r0["cover"] - want) > TOL:
        raise SystemExit(f"t = 0 cover {r0['cover']:.6f} is not mix_v6's {want:.6f}")

    fw = lambda betas: [sv.forwards(cal, fwd0, beta) for beta in betas]
    central_curves = fw(central)
    fall = cal["beta0"].copy()
    fall[[0, cal["n"]]] -= pv.RATE_FALL
    fall_curves = fw(cal["ar"].central(fall, sv.MONTHS)[::12])
    ratio = pv.pandemic_ratio(deaths, population)
    long_book = pv.start(make(Basis(annuitant_adj=pv.LONGEVITY_ADJ)))
    wave_book = pv.lapse_wave(book0, pv.LAPSE_WAVE)
    stresses = {
        "S1 Rates fall": dict(curves=fall_curves, book=book0),
        "S2 Longevity": dict(curves=central_curves, book=long_book),
        "S3 Pandemic year": dict(curves=central_curves, book=book0, pandemic=ratio),
        "S4 Lapse wave": dict(curves=central_curves, book=wave_book),
        "S5 All at once": dict(curves=fall_curves, book=wave_book, pandemic=ratio),
    }
    return {"cal": cal, "sims": sims, "book0": book0, "r0": r0, "central": central_curves, "stresses": stresses}


def cover_at(s: dict, funds: float) -> float:
    """t = 0 cover with own funds `funds`, the change in the bill."""
    total = s["r0"]["assets"]["total"] - c4.BASE_FUNDS + funds
    pv.CTX["scale"] = 1.0
    return pv.valuation(s["book0"], pv.CTX["fwd0"], pv.CTX["settle"], assets=total)["cover"]


def solve(s: dict) -> float:
    """The own funds at which cover is TARGET, bracketed around the R400 million SCR."""
    scr = s["r0"]["scr"]
    lo, hi = 0.5 * scr, 1.5 * scr
    while cover_at(s, lo) > TARGET:
        lo /= 2
    while cover_at(s, hi) < TARGET:
        hi *= 2
    return brentq(lambda f: cover_at(s, f) - TARGET, lo, hi, xtol=1.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--grids-cache")
    args = ap.parse_args()
    frozen = {"v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3), "v4": require_frozen(PROTOCOL_V4),
              "v5": require_frozen(PROTOCOL_V5), "v6": require_frozen(PROTOCOL_V6)}
    if not mx.RESULT.exists():
        raise SystemExit("run python -m research.mix_v6 first")
    s = setup(args.deaths, args.population, args.grids_cache)
    funds = solve(s)
    lv = c4.level(s, funds, k=1.0)
    check = {"cover": lv["cover"], "pass": bool(abs(lv["cover"] - TARGET) < TOL)}
    out = {"protocol": frozen, "rule": "the change in own funds is in the 182-day bill; the match stays on the BEL", "target_cover": TARGET,
           "levels": {"cover 1.0": lv}, "checks": {"cover": check}}
    OUTFILE.write_text(json.dumps(out, indent=1, default=float))
    print(f"cover 1.0 at own funds {funds / 1e6:,.1f}m (k {lv['k']:.4f}); covered throughout "
          f"{lv['scenarios']['A1']['share_covered']:.3f}; check {check['pass']}")


if __name__ == "__main__":
    main()
