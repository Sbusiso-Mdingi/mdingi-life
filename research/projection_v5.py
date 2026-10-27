"""v4's projection on v5's book (research/PROTOCOL_v5.md, "v4" under "Funeral on the table" and "The rising-benefit
option"), or on v6's (research/PROTOCOL_v6.md) with --v6.

    python -m research.projection_v5 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv [--grids-cache PATH] [--v6]

v4's generator, paths, stresses, IFRS 17 and checks (research.projection_v4), with:
- funeral rates moving along calendar years: a cell's rates at year-end t are its rates on today's diagonal t years
  on, which is what ageing v5's cohort rows by a year gives;
- each rising benefit growing at each anniversary by the year's realised inflation (v4's one-year breakeven at the
  start of the year), floored at 0% and capped at 6%;
- each year-end valued by v5's balance sheet: the remaining increases by the inflation model centred on that
  year-end's 30-year breakeven, the volatility charge, and the hedge of the rising claims rematched with the
  annuities' matching (v4's key-rate method);
- with --v6, v6's scales (from research/results/mix_v6.json) and, if v6 says so, the whole book matched together.

R1 runs as in v4: with no inflation in the year, rising benefits do not grow, so it checks the roll-forward of
every cell as a level one. The rising claims' roll cannot agree exactly, since the inflation model restarts at x = 0
at each year-end rather than carrying the year's x on; that is a simplification of the protocol's "centred on that
year-end's breakeven", disclosed and not checked.

Writes research/results/projection_v5.json (or projection_v6.json). Refuses to run until the protocols are frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife import inflation_v5 as iv
from mdingilife.protocol import (PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V4, PROTOCOL_V5, PROTOCOL_V6, require_frozen)
from research import balance_v5 as b5
from research import book_v5 as bk
from research import mix_v6 as mx
from research import projection_v4 as pv
from research import curves as rc
from research.backtest import OUT
from research.balance_v3 import Curves, auctions, market

EXTRA = ("valuation", "fgrid", "growth", "rising_bounds", "scales", "matching")


def valuation(b, curves: dict, settle, assets=None, holdings=None, matched: bool = True) -> dict:
    """v5's balance sheet at a year-end; under v6's whole-book matching, the bonds matched to the whole book."""
    C = pv.CTX
    if matched and holdings is None and C.get("matching") == "book":
        m = mx.match_book(b, Curves(curves["nominal"], curves["real"]), C["bonds"], settle)
        k = C.get("scale", 1.0)
        holdings = {kind: {code: n * k for code, n in u.items()} for kind, u in m["units"].items()}
    return b5.run(C["grids"], C["fgrid"], b.basis, {b.basis.curve: curves}, C["bonds"], settle, C["growth"],
                  matched=matched, hedged=matched, method="key", book=b, assets=assets, holdings=holdings,
                  scale=C.get("scale", 1.0))


def setup(grids: dict, v6: bool = False) -> dict:
    """The CTX entries and book maker for v5 (v6: scaled, and the matching v6 chose)."""
    fgrid, growth = bk.grid(), b5.Growth.load()
    scales, matching = (1.0, 1.0), "v5"
    if v6:
        r = json.loads(mx.RESULT.read_text())
        scales, matching = (r["scales"]["annuities"], r["scales"]["funeral"]), r["matching"]
    ctx = {"valuation": valuation, "fgrid": fgrid, "growth": growth, "rising_bounds": (iv.FLOOR, iv.CAP),
           "scales": scales, "matching": matching, "extra": EXTRA}
    make = lambda basis: mx.scaled(b5.Book(grids, fgrid, basis, growth), *scales)
    return {"ctx": ctx, "make_book": make}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--grids-cache")
    ap.add_argument("--v6", action="store_true")
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v4": require_frozen(PROTOCOL_V4), "v5": require_frozen(PROTOCOL_V5)}
    if args.v6:
        frozen["v6"] = require_frozen(PROTOCOL_V6)
    needs = [(bk.FUNERAL, "research.book_v5 --write"), (b5.INFLATION, "research.inflation_v5")]
    if args.v6:
        needs.append((mx.RESULT, "research.mix_v6"))
    for f, how in needs:
        if not f.exists():
            raise SystemExit(f"run python -m {how} first")

    bonds = rc.book()
    a = auctions(bonds)
    curves, bonds, days, settle = market(a)
    grids = mx.grids(args.deaths, args.population, args.grids_cache)
    s = setup(grids, args.v6)
    pv.CTX.update(s["ctx"])
    out = pv.compute(a, curves, bonds, days, settle, grids, args.deaths, args.population, make_book=s["make_book"])
    out = {"protocol": frozen, "book": "v6" if args.v6 else "v5", "scales": s["ctx"]["scales"],
           "matching": s["ctx"]["matching"], **out}
    path = OUT / ("projection_v6.json" if args.v6 else "projection_v5.json")
    path.write_text(json.dumps(out, indent=1, default=float))
    sc = out["scenarios"]
    print("cover p5/p50/p95 by year", [np.round(sc["cover"][q], 3) for q in ("5", "50", "95")])
    print("below one", sc["below_one_share"], "A1", sc["A1"], "R1", out["checks"]["R1"]["worst"], "R2", out["checks"]["R2"])
    print("stresses", {k: np.round(v["cover"], 3).tolist() for k, v in out["stresses"].items()})


if __name__ == "__main__":
    main()
