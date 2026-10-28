"""Diagnostic (no results changed): replay v7's main scenario set at R400m and record each year-end where the
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
sims, _ = sv.paths(cal, sv.N)
book0 = pv.start(s["make_book"](Basis()))
r0 = pv.valuation(book0, fwd0, settle)
pv.CTX.update(book0=book0, r0=r0, cal={"main": cal})
print("t0 cover", r0["cover"], "t0 empty", list(EV), flush=True)

def job(i):
    EV.clear()
    p = pv.path([sv.forwards(cal, fwd0, beta) for beta in sims[i]], book0, r0)
    return i, p["cover"], list(EV)

with ProcessPoolExecutor(8) as ex:
    res = list(ex.map(job, range(len(sims)), chunksize=8))
cover = np.array([c for _, c, _ in res])
hit = [(i, e) for i, _, e in res if e]
mask = np.array([bool(e) for _, _, e in res])
out = {"paths": len(res), "paths_with_empty_match": int(mask.sum()), "year_ends_empty": sum(len(e) for _, e in hit),
       "bel_at_empty": [v for _, e in hit for _, v in e],
       "A1_all": float(np.mean((cover >= 1).all(1))), "A1_affected": float(np.mean((cover[mask] >= 1).all(1))) if mask.any() else None,
       "A1_unaffected": float(np.mean((cover[~mask] >= 1).all(1))), "examples": hit[:10]}
json.dump(out, open("/home/sbusisomdingi/diag_v7.json", "w"), indent=1)
b = np.array(out["bel_at_empty"])
print({k: v for k, v in out.items() if k not in ("bel_at_empty", "examples")})
if len(b): print("BEL at empty (m): min %.1f median %.1f max %.1f, share <= 0: %.3f" % (b.min()/1e6, np.median(b)/1e6, b.max()/1e6, np.mean(b <= 0)))
print("DIAG DONE", flush=True)
