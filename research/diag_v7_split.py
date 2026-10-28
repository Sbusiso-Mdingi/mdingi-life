"""Diagnostic (no results changed): replay v7's secondary scenario sets (COVID-excluded, no-rematch, frozen three-factor) at R400m and record each year-end where the
whole-book match comes back empty, with the whole book's BEL there."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from research import projection_v4 as pv, projection_v7 as p7, scenarios_v4 as sv, curves as rc, mix_v6 as mx, balance_v5 as b5
from research.balance_v3 import auctions, market, Basis
from research.book_v3 import TABLE

EV = []
_orig = b5.key_rate_units
def _wrapped(liab, cv, bonds, settle, weight=1e3):
    out = _orig(liab, cv, bonds, settle, weight)
    if not out["units"]:
        EV.append((str(settle), float(liab["value"])))
    return out
b5.key_rate_units = _wrapped

deaths, pop, cache = sys.argv[1:4]
bonds = rc.book(); a = auctions(bonds)
curves, bonds, days, settle = market(a)
grids = mx.grids(deaths, pop, cache)
s = p7.setup(grids)
fwd0 = curves["LI"]
pv.CTX.update(s["ctx"]); pv.CTX.update(grids=grids, table=pd.read_csv(TABLE), bonds=bonds, settle=settle, fwd0=fwd0)
points = sv.month_points(a)
jump = {k: rc.window(a[a["kind"] == kind], days[k][1], rc.WINDOW, inclusive=True) for k, kind in sv.KINDS.items()}
cal = sv.calibrate(points, jump)
cal_covid = sv.calibrate(points, jump, exclude=sv.COVID)
cal_frozen = sv.calibrate(points, jump, n=3)
sims, _ = sv.paths(cal, sv.N)
sims_covid, _ = sv.paths(cal_covid, sv.N)
sims_frozen, _ = sv.paths(cal_frozen, sv.N)
book0 = pv.start(s["make_book"](Basis()))
r0 = pv.valuation(book0, fwd0, settle)
pv.CTX.update(book0=book0, r0=r0, cal={"main": cal, "covid": cal_covid, "frozen": cal_frozen})
print("t0 cover", r0["cover"], "t0 empty", list(EV), flush=True)
SETS = {"frozen": (sims_frozen, "frozen", True), "covid": (sims_covid, "covid", True), "no_rematch": (sims, "main", False)}

def job(a):
    name, i = a
    sm, key, rematch = SETS[name]
    EV.clear()
    p = pv.path([sv.forwards(pv.CTX["cal"][key], fwd0, beta) for beta in sm[i]], book0, r0, rematch=rematch)
    return i, p["cover"], list(EV)

out = {}
for name in SETS:
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(job, [(name, i) for i in range(sv.N)], chunksize=8))
    cover = np.array([c for _, c, _ in res])
    mask = np.array([bool(e) for _, _, e in res])
    bel = np.array([v for _, _, e in res for _, v in e])
    years = [int(round((pd.Timestamp(d) - pd.Timestamp(settle)).days / 365)) for _, _, e in res for d, _ in e]
    o = {"paths": len(res), "paths_with_empty_match": int(mask.sum()), "year_ends_empty": int(len(bel)),
         "by_year": {str(t): years.count(t) for t in sorted(set(years))},
         "bel_m": {"min": float(bel.min() / 1e6), "median": float(np.median(bel) / 1e6), "max": float(bel.max() / 1e6),
                   "share_le_0": float(np.mean(bel <= 0))} if len(bel) else None,
         "A1_all": float(np.mean((cover >= 1).all(1))),
         "A1_affected": float(np.mean((cover[mask] >= 1).all(1))) if mask.any() else None,
         "A1_unaffected": float(np.mean((cover[~mask] >= 1).all(1))) if (~mask).any() else None}
    out[name] = o
    print(name, o, flush=True)
    json.dump(out, open("/home/sbusisomdingi/diag_v7_split.json", "w"), indent=1)
print("total empty year-ends", sum(o["year_ends_empty"] for o in out.values()), "(log: 491)")
print("DIAG DONE", flush=True)
