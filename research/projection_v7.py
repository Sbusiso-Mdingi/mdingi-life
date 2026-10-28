"""v4's projection on v7's book (research/PROTOCOL_v7.md, "Reruns and reporting" 3), at R400 million, or with
--capital at the own funds at which cover starts at 1.0 (research.capital_v6's rule and solver).

    python -m research.projection_v7 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv [--grids-cache PATH] [--capital]

v4's generator, paths, stresses, IFRS 17 and checks (research.projection_v4) as v6 runs them, with:
- each funeral cell's premiums by projection year moved a year along at each year-end with its survivors, so an
  age-rated cell pays its schedule's next year (research.projection_v4.age);
- each year-end valued by v7's balance sheet (research.balance_v7.run): the whole book matched again, and the
  receivable (one month of that year-end's premiums in force) and bank cash (three months of the next year's expected
  outgo) recomputed from that year-end's book and taken from the bill; both are carried through the year at par.

Needs research.balance_v7 first (its scales). Writes research/results/projection_v7.json, or capital_v7.json with
--capital. Refuses to run until the v1 to v7 protocols are frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife.protocol import (PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V4, PROTOCOL_V5, PROTOCOL_V6, PROTOCOL_V7,
                                 require_frozen)
from research import balance_v7 as b7
from research import book_v5 as bk5
from research import capital_v4 as c4
from research import capital_v6 as c6
from research import curves as rc
from research import mix_v6 as mx
from research import projection_v4 as pv
from research.backtest import OUT
from research.balance_v3 import auctions, market

EXTRA = ("valuation", "fgrid", "scales")


def valuation(b, curves: dict, settle, assets=None, holdings=None, matched: bool = True) -> dict:
    C = pv.CTX
    return b7.run(C["grids"], C["fgrid"], b.basis, {b.basis.curve: curves}, C["bonds"], settle, book=b,
                  matched=matched, assets=assets, holdings=holdings, scale=C.get("scale", 1.0))


def setup(grids: dict) -> dict:
    """The CTX entries and book maker for v7, at balance_v7's scales."""
    fgrid = bk5.grid()
    r = json.loads(b7.RESULT.read_text())
    scales = (r["scales"]["annuities"], r["scales"]["funeral"])
    ctx = {"valuation": valuation, "fgrid": fgrid, "scales": scales, "extra": EXTRA}
    make = lambda basis: b7.scaled(b7.Book(grids, fgrid, basis), *scales)
    return {"ctx": ctx, "make_book": make}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--grids-cache")
    ap.add_argument("--capital", action="store_true")
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v4": require_frozen(PROTOCOL_V4), "v5": require_frozen(PROTOCOL_V5), "v6": require_frozen(PROTOCOL_V6),
              "v7": require_frozen(PROTOCOL_V7)}
    if not b7.RESULT.exists():
        raise SystemExit("run python -m research.balance_v7 first")

    if args.capital:
        want = (json.loads(b7.RESULT.read_text())["main"]["cover"], "balance_v7")
        s = c6.setup(args.deaths, args.population, args.grids_cache, book=setup, want=want)
        funds = c6.solve(s)
        lv = c4.level(s, funds, k=1.0)
        check = {"cover": lv["cover"], "pass": bool(c6.TARGET <= lv["cover"] < c6.TARGET + c6.TOL)}
        out = {"protocol": frozen, "rule": "the change in own funds is in the 182-day bill; the match stays on the BEL",
               "target_cover": c6.TARGET, "levels": {"cover 1.0": lv}, "checks": {"cover": check}}
        (OUT / "capital_v7.json").write_text(json.dumps(out, indent=1, default=float))
        print(f"cover 1.0 at own funds {funds / 1e6:,.1f}m; covered throughout "
              f"{lv['scenarios']['A1']['share_covered']:.3f}; check {check['pass']}")
        return

    bonds = rc.book()
    a = auctions(bonds)
    curves, bonds, days, settle = market(a)
    grids = mx.grids(args.deaths, args.population, args.grids_cache)
    s = setup(grids)
    pv.CTX.update(s["ctx"])
    out = pv.compute(a, curves, bonds, days, settle, grids, args.deaths, args.population, make_book=s["make_book"])
    out = {"protocol": frozen, "book": "v7", "scales": s["ctx"]["scales"], "matching": "book", **out}
    (OUT / "projection_v7.json").write_text(json.dumps(out, indent=1, default=float))
    sc = out["scenarios"]
    print("cover p5/p50/p95 by year", [np.round(sc["cover"][q], 3) for q in ("5", "50", "95")])
    print("below one", sc["below_one_share"], "A1", sc["A1"], "R1", out["checks"]["R1"]["worst"], "R2", out["checks"]["R2"])
    print("stresses", {k: np.round(v["cover"], 3).tolist() for k, v in out["stresses"].items()})


if __name__ == "__main__":
    main()
