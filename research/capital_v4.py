"""v4's starting-capital levels (PROTOCOL_v4.md, "starting capital and the chance of staying covered"): v4's 1,000
scenarios and five named stresses at other levels of own funds, extra capital invested in the same mix as today's
assets.

    python -m research.capital_v4 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv --levels 600 800 1000 627

Adds each level (R million) to research/results/capital_v4.json, keeping levels already there.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from mdingilife.protocol import PROTOCOL_V4, require_frozen
from research import curves as rc
from research import projection_v4 as pv
from research import scenarios_v4 as sv
from research.backtest import OUT
from research.balance_v3 import Basis, Book, annuitant_grids, auctions, market
from research.book_v3 import TABLE

BASE_FUNDS = 400e6
OUTFILE = OUT / "capital_v4.json"
V4_COVER = 1.1486


def setup(deaths: str, population: str) -> dict:
    """The market, the generator and the R400 million valuation, shared by every level."""
    bonds = rc.book()
    a = auctions(bonds)
    curves, bonds, days, settle = market(a)
    grids = annuitant_grids(deaths, population)
    table = pd.read_csv(TABLE)
    fwd0 = curves["LI"]
    pv.CTX.update(grids=grids, table=table, bonds=bonds, settle=settle, fwd0=fwd0, scale=1.0)
    points = sv.month_points(a)
    jump = {k: rc.window(a[a["kind"] == kind], days[k][1], rc.WINDOW, inclusive=True) for k, kind in sv.KINDS.items()}
    cal = sv.calibrate(points, jump)
    sims, central = sv.paths(cal)
    book0 = pv.start(Book(grids, table, Basis()))
    r0 = pv.valuation(book0, fwd0, settle)
    print(f"R400m: t=0 cover {r0['cover']:.4f}, total assets {r0['assets']['total'] / 1e6:.1f}m", flush=True)
    if abs(r0["cover"] - V4_COVER) > 5e-5:
        raise SystemExit(f"k = 1 gives cover {r0['cover']:.4f}, not v4's {V4_COVER}")

    fw = lambda betas: [sv.forwards(cal, fwd0, beta) for beta in betas]
    central_curves = fw(central)
    fall = cal["beta0"].copy()
    fall[[0, cal["n"]]] -= pv.RATE_FALL
    fall_curves = fw(cal["ar"].central(fall, sv.MONTHS)[::12])
    ratio = pv.pandemic_ratio(deaths, population)
    long_book = pv.start(Book(grids, table, Basis(annuitant_adj=pv.LONGEVITY_ADJ)))
    wave_book = pv.lapse_wave(book0, pv.LAPSE_WAVE)
    stresses = {
        "S1 Rates fall": dict(curves=fall_curves, book=book0),
        "S2 Longevity": dict(curves=central_curves, book=long_book),
        "S3 Pandemic year": dict(curves=central_curves, book=book0, pandemic=ratio),
        "S4 Lapse wave": dict(curves=central_curves, book=wave_book),
        "S5 All at once": dict(curves=fall_curves, book=wave_book, pandemic=ratio),
    }
    return {"cal": cal, "sims": sims, "book0": book0, "r0": r0, "central": central_curves, "stresses": stresses}


def level(s: dict, funds: float, k: float | None = None) -> dict:
    """One level of own funds at t = 0: holdings and bill scaled by k (by default in proportion to the assets; v6
    passes k = 1, the change all in the bill), then the scenarios and the stresses."""
    r400 = s["r0"]
    total = r400["assets"]["total"] - BASE_FUNDS + funds
    k = total / r400["assets"]["total"] if k is None else k
    pv.CTX["scale"] = k
    r0 = pv.valuation(s["book0"], pv.CTX["fwd0"], pv.CTX["settle"], assets=total)
    pv.CTX.update(book0=s["book0"], r0=r0, cal={"main": s["cal"]})
    print(f"R{funds / 1e6:.0f}m: k {k:.4f}, own funds {r0['own_funds'] / 1e6:.1f}m, SCR {r0['scr'] / 1e6:.1f}m, "
          f"cover {r0['cover']:.4f}", flush=True)

    base = pv.path(s["central"], s["book0"], r0)
    stressed = {}
    for name, st in s["stresses"].items():
        assets0 = pv.revalue(r0, pv.CTX["settle"], st["curves"][0])
        p = pv.path(st["curves"], st["book"], assets0=assets0, holdings0=r0["assets"]["holdings"],
                    pandemic=st.get("pandemic"))
        short = [max(y["scr"] - y["own_funds"], 0.0) for y in p["years"]]
        stressed[name] = {"cover": p["cover"], "lowest": float(min(p["cover"])), "capital_to_restore": max(short)}
        print(f"  {name}: lowest {min(p['cover']):.3f}", flush=True)

    ctx = {key: pv.CTX[key] for key in ("grids", "table", "bonds", "settle", "fwd0", "book0", "r0", "cal", "scale")
           + pv.CTX.get("extra", ())}
    res = pv.scenarios(s["sims"], "main", True, ctx)
    sp = pv.spread(res)
    print(f"  covered throughout {sp['A1']['share_covered']:.3f}", flush=True)
    return {"own_funds": funds, "k": k, "total_assets": total, "scr": r0["scr"], "cover": r0["cover"],
            "market": r0["market"], "central_cover": base["cover"], "scenarios": sp, "stresses": stressed}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--levels", type=float, nargs="+", required=True, help="own funds at t = 0, R million")
    args = ap.parse_args()
    frozen = require_frozen(PROTOCOL_V4)
    s = setup(args.deaths, args.population)
    out = json.loads(OUTFILE.read_text()) if OUTFILE.exists() else {}
    out["protocol_v4"] = frozen
    out["rule"] = "extra capital is invested in the same mix as today's assets"
    levels = out.setdefault("levels", {})
    for m in args.levels:
        levels[f"{m:g}"] = level(s, m * 1e6)
        OUTFILE.write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
