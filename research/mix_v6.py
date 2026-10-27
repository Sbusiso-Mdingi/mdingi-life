"""v6's book size and mix (research/PROTOCOL_v6.md): v5's two lines, each scaled as a whole, the funeral line so a
uniform change in mortality leaves the total BEL unchanged, and the whole book so cover is 1.8 at R400 million.

    python -m research.mix_v6 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv [--grids-cache PATH]

Needs research.book_v5 --write and research.inflation_v5. Writes research/results/mix_v6.json. Refuses to run until
the v1 to v3, v5 and v6 protocols are frozen. With --grids-cache, v1's annuitant grids are read from PATH if it
exists and written to it if not (they are the slow part); keep PATH outside the repository.
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V5, PROTOCOL_V6, require_frozen
from research import balance_v3 as b3
from research import balance_v5 as b5
from research import book_v5 as bk
from research.backtest import OUT
from research.annuities_v2 import KEYS, bump, tent
from research.balance_v3 import BASE, INDUSTRY_COVER, OWN_FUNDS, YEARS, Basis, Curves

RESULT = OUT / "mix_v6.json"
STEP = 0.01                             # the uniform change, either way, for the exposures
FASTER = 0.01                           # improvement 1 point a year faster, reported only
LARGE = 0.15                            # the uniform change for the curvature residual, reported only
ANNUITANTS, FUNERAL = 5_000, 50_000     # v5's counts, for the book in policies
TOL = 1e-12
MATCHING = "book"                       # Q1: "book", the whole book's net cash flows matched together, or "v5"


def scaled(b: b5.Book, ann: float = 1.0, fun: float = 1.0) -> b5.Book:
    """v5's book with every annuity cell's count and income times `ann`, and every funeral cell's count, sum assured
    and premium times `fun`."""
    out = b5.Book.__new__(b5.Book)
    out.__dict__.update(b.__dict__)
    out.ann = b.ann.assign(income=b.ann["income"] * ann, count=b.ann["count"] * ann)
    out.fun = b.fun.assign(sum_assured=b.fun["sum_assured"] * fun, premium=b.fun["premium"] * fun,
                           count=b.fun["count"] * fun)
    out.n_ann, out.n_fun = b.n_ann * ann, b.n_fun * fun
    return out


def moved(b: b5.Book, factor) -> b5.Book:
    """The book with every force of mortality, both lines, times `factor` (a number, or one per projection year)."""
    out = b5.Book.__new__(b5.Book)
    out.__dict__.update(b.__dict__)
    f = np.broadcast_to(np.asarray(factor, float), (YEARS,))
    out.mu_ann = {lv: m * f for lv, m in b.mu_ann.items()}
    out.mu_fun = b.mu_fun * f
    return out


def bel(b: b5.Book, cv: Curves) -> dict:
    return b5._totals(b5.liabilities(b, cv, BASE))


def exposures(b: b5.Book, cv: Curves, h: float = STEP) -> dict:
    """dBEL / ds for each line, every force times (1 + s), by central difference at s = ±h."""
    up, dn = bel(moved(b, 1 + h), cv), bel(moved(b, 1 - h), cv)
    return {k: (up[k] - dn[k]) / (2 * h) for k in ("annuities", "funeral", "total")}


def trend(b: b5.Book, cv: Curves, faster: float = FASTER) -> dict:
    """The BEL change for improvement `faster` a year faster: the force in projection year k times (1 - faster)^k."""
    base, fast = bel(b, cv), bel(moved(b, (1 - faster) ** np.arange(YEARS)), cv)
    return {k: fast[k] - base[k] for k in ("annuities", "funeral", "total")}


def mix(e: dict) -> float:
    """F / A with A E_ann + F E_fun = 0."""
    if not (e["annuities"] < 0 < e["funeral"]):
        raise ValueError(f"exposures of the wrong sign: {e}")
    return -e["annuities"] / e["funeral"]


def book_risk(b: b5.Book, cv: Curves) -> dict:
    """The whole book's BEL on unshocked curves, and its DV01s at each key rate of each curve with the other held.
    Expense inflation and G are re-centred on each moved breakeven, as v5's stresses do."""
    value = lambda fn, fr: bel(b, Curves(fn, fr))["total"]
    fn, fr = cv.fwd["nominal"], cv.fwd["real"]
    v = value(fn, fr)
    dv = {("nominal", k): v - value(bump(fn, tent(k)), fr) for k in KEYS}
    dv |= {("real", k): v - value(fn, bump(fr, tent(k))) for k in KEYS}
    return {"value": v, "dv01": dv}


def match_book(b: b5.Book, cv: Curves, bonds: dict, settle) -> dict:
    """Q1 (b): non-negative holdings in every bond that match the whole book's BEL and come nearest its eight key-rate
    DV01s (v3's key-rate method, both curves at once)."""
    return b5.key_rate_units(book_risk(b, cv), cv, bonds, settle)


def size(cover, target: float = INDUSTRY_COVER, guess: float = 1.0) -> float:
    """The annuity scale A at which cover(A) = target. Cover falls as the book grows, close to in proportion, so the
    root is bracketed from a first guess at guess × cover(guess) / target and widened until it holds."""
    c0 = cover(guess)
    a = guess * c0 / target
    lo, hi = a / 1.5, a * 1.5
    while cover(lo) < target:
        lo /= 2
    while cover(hi) > target:
        hi *= 2
    return brentq(lambda x: cover(x) - target, lo, hi, xtol=TOL * a, rtol=4 * np.finfo(float).eps)


def check_d1(b: b5.Book, cv: Curves, A: float, F: float) -> dict:
    s = scaled(b, A, F)
    e = exposures(s, cv)
    rel = abs(e["total"]) / (A * abs(exposures(b, cv)["annuities"]))
    return {"total_exposure": e["total"], "relative": rel, "pass": bool(rel < 1e-9)}


def check_d3(r: dict, v5: dict) -> dict:
    pairs = {"bel": (r["bel"]["total"], v5["bel"]["total"]), "scr": (r["scr"], v5["scr"]),
             "risk margin": (r["risk_margin"], v5["risk_margin"])}
    rel = {k: abs(a / b - 1) for k, (a, b) in pairs.items()}
    return {"relative": rel, "pass": bool(max(rel.values()) < 1e-10)}


def check_d4(b: b5.Book, cv: Curves, fgrid: dict, r: dict, A: float) -> dict:
    v3 = json.loads((OUT / "balance_v3.json").read_text())["main"]
    pairs = {"bel annuities": (r["bel"]["annuities"], A * v3["bel"]["annuities"]),
             "longevity": (r["life"]["longevity"], A * v3["life"]["longevity"]),
             "life alone, annuities": (r["life_alone"]["annuities"], A * v3["life_alone"]["annuities"])}
    rel = {k: abs(a / b - 1) for k, (a, b) in pairs.items()}
    c6 = {"relative": rel, "pass": bool(max(rel.values()) < 1e-8)}
    return {"C4": b5.check_c4(b, cv), "C5": b5.check_c5(b, cv, fgrid), "C6": c6}


def check_d5(r: dict) -> dict:
    """The whole-book match: holdings worth the BEL, none short."""
    rel = abs(r["assets"]["matched"] / r["bel"]["total"] - 1)
    low = min(n for u in r["assets"]["holdings"].values() for n in u.values())
    return {"relative": rel, "lowest_units": low, "pass": bool(rel < 1e-8 and low >= 0)}


def grids(deaths: str, population: str, cache: str | None) -> dict:
    if cache and Path(cache).exists():
        return pickle.loads(Path(cache).read_bytes())
    g = b3.annuitant_grids(deaths, population)
    if cache:
        Path(cache).write_bytes(pickle.dumps(g))
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--grids-cache")
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v5": require_frozen(PROTOCOL_V5), "v6": require_frozen(PROTOCOL_V6)}
    curves, bonds, days, settle = b3.market()
    g = grids(args.deaths, args.population, args.grids_cache)
    fgrid = bk.grid()
    growth = b5.Growth.load()
    basis = Basis()
    b = b5.Book(g, fgrid, basis, growth)
    cv = Curves(curves[basis.curve]["nominal"], curves[basis.curve]["real"])
    plain = lambda book, **kw: b5.run(g, fgrid, kw.pop("basis", basis), curves, bonds, settle,
                                      kw.pop("growth", growth), book=book, **kw)

    def whole(book, **kw):
        """Q1 (b): the whole book matched together; the result carries the match."""
        bs = kw.get("basis", basis)
        m = match_book(book, Curves(curves[bs.curve]["nominal"], curves[bs.curve]["real"]), bonds, settle)
        r = plain(book, holdings=m["units"], **kw)
        r["assets"]["matching"] = {"book": m}
        return r

    go = whole if MATCHING == "book" else plain
    other = plain if MATCHING == "book" else whole

    e = exposures(b, cv)
    ratio = mix(e)
    A = size(lambda a: go(scaled(b, a, ratio * a))["cover"])
    F = ratio * A
    book = scaled(b, A, F)
    out = {"protocol": frozen, "valuation_date": str(days["real"][1].date()), "matching": MATCHING,
           "exposures": e, "mix": ratio, "scales": {"annuities": A, "funeral": F},
           "policies": {"annuitants": round(ANNUITANTS * A), "funeral": round(FUNERAL * F)},
           "trend": trend(book, cv),
           "large": {f"{s:+.2f}": bel(moved(book, 1 + s), cv)["total"] - bel(book, cv)["total"] for s in (LARGE, -LARGE)}}
    out["main"] = main_ = go(book)
    out["other_matching"] = other(book)
    if MATCHING == "v5":
        out["unhedged"] = plain(book, hedged=False)
    out["unmatched"] = plain(book, matched=False, hedged=False)
    if main_["interest"]["volatility"] > 0:
        out["no_floor"] = go(book, growth=growth.variant(floor=None))
    out["sensitivities"] = {}
    for adj in (0.8, 1.2):
        s = b5.Book(g, fgrid, Basis(funeral_adj=adj), growth)
        out["sensitivities"][f"funeral {adj}"] = go(scaled(s, A, F), basis=Basis(funeral_adj=adj))
    v5 = json.loads(b5.RESULT.read_text())["main"]
    out["checks"] = {"D1": check_d1(b, cv, A, F),
                     "D2": {"cover": main_["cover"], "pass": bool(abs(main_["cover"] - INDUSTRY_COVER) < 1e-6)},
                     "D3": check_d3(plain(b), v5), **check_d4(book, cv, fgrid, main_, A)}
    if MATCHING == "book":
        out["checks"]["D5"] = check_d5(main_)
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    m = main_
    print(f"exposures {({k: round(v / 1e6, 2) for k, v in e.items()})}; F / A {ratio:.4f}; A {A:.4f}, F {F:.4f}; "
          f"policies {out['policies']}")
    print(f"BEL {({k: round(v / 1e6, 1) for k, v in m['bel'].items()})}  RM {m['risk_margin'] / 1e6:,.1f}  "
          f"SCR {m['scr'] / 1e6:,.1f}  cover {m['cover']:.4f} (own funds {OWN_FUNDS / 1e6:.0f}m)")
    print("life", {k: round(v / 1e6, 1) for k, v in m["life"].items()},
          "interest", {k: round(v / 1e6, 1) for k, v in m["interest"].items()})
    print("trend", {k: round(v / 1e6, 1) for k, v in out["trend"].items()}, "large", {k: round(v / 1e6, 1) for k, v in out["large"].items()})
    print(f"other matching: SCR {out['other_matching']['scr'] / 1e6:,.1f}, cover {out['other_matching']['cover']:.4f}")
    print("checks", {k: v["pass"] for k, v in out["checks"].items()})


if __name__ == "__main__":
    main()
