"""v2 annuity prices on the government bond curves, with duration, key rates and a matching portfolio
(PROTOCOL_v2.md, Annuity prices and Matching, as amended).

    python -m research.annuities_v2 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Mortality is v1's production fit on the Stats SA run, simulated with v1's seed, so the flat 4% price reproduces
annuities_statssa.json. Curves: the zero curve behind LI (the design choice for both kinds), with NS as a
sensitivity, fitted on the 91 days up to the valuation date. Writes research/results/annuities_v2.json. Refuses to
run until both protocols are frozen and the curves' validation has been run.
"""
from __future__ import annotations

import argparse
import json
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from mdingilife import annuity, curves as c, data
from mdingilife.protocol import PROTOCOL_V2, require_frozen
from research import curves as rc
from research.annuities import ADJ, ENTRY_AGES, RATES, simulate
from research.backtest import OUT, SEED
from research.treasury import ILB

KEYS = (5, 10, 20, 30)
BP = 1e-4
YEARS = 80  # forward rates needed: age 55 to the top age of the extended table


def valuation_curves(a: pd.DataFrame) -> dict:
    """On the latest inflation-linked auction day and the fixed-rate auction day closest before it: the window's
    points, the curves and their forwards."""
    ilb_day = a.loc[a["kind"] == "ilb", "auction_date"].max()
    days = {"ilb": ilb_day, "fixed": a.loc[(a["kind"] == "fixed") & (a["auction_date"] <= ilb_day), "auction_date"].max()}
    out = {}
    for kind, d in days.items():
        pts = rc.window(a[a["kind"] == kind], d, rc.WINDOW, inclusive=True)
        last = max(q.maturity for q in pts)
        boot, ns = c.Bootstrap.fit(pts), rc.fit("NS", pts)
        out[kind] = {"date": d, "points": pts, "last": last, "curve": boot,
                     "forwards": {"LI": c.forwards(boot, last, YEARS), "NS": c.forwards(ns, last, YEARS)}}
    return out


def bump(fwd: np.ndarray, shift) -> np.ndarray:
    """Forwards after adding shift(t) to the zero rate at each whole year t (zero rate times t is the running
    sum of forwards)."""
    t = np.arange(len(fwd) + 1, dtype=float)
    zt = np.concatenate([[0.0], np.cumsum(fwd)]) + shift(t) * t
    return np.diff(zt)


def tent(k: int):
    """1 basis point at key rate k, falling linearly to zero at its neighbouring keys (flat beyond the end keys)."""
    i = KEYS.index(k)
    xs = [0.0] + list(KEYS) + [200.0]
    ys = [1.0 if j == i + 1 else 0.0 for j in range(len(xs))]
    if i == 0:
        ys[0] = 1.0
    if i == len(KEYS) - 1:
        ys[-1] = 1.0
    return lambda t: BP * np.interp(t, xs, ys)


def bond_value(t, cf, fwd: np.ndarray) -> float:
    """Price from yearly forwards, the zero rate integrated linearly within the year."""
    zt = np.interp(t, np.arange(len(fwd) + 1), np.concatenate([[0.0], np.cumsum(fwd)]))
    return float(np.sum(cf * np.exp(-zt)))


def risk(value, fwd: np.ndarray) -> dict:
    """Value, effective duration (parallel 1bp in the zero curve) and the key-rate DV01s (value lost per 1bp)."""
    v = value(fwd)
    up, dn = value(bump(fwd, lambda t: BP + 0 * t)), value(bump(fwd, lambda t: -BP + 0 * t))
    return {"value": v, "duration": (dn - up) / (2 * v * BP),
            "dv01": {k: value(fwd) - value(bump(fwd, tent(k))) for k in KEYS}}


def implied_rate(m, adj, target) -> float:
    return brentq(lambda i: float(np.median(annuity.factor(m, i, adj))) - target, -0.05, 0.25)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2)}
    if not (OUT / "curves_validation.json").exists():
        raise SystemExit("run python -m research.curves --period validation first")
    chosen = json.loads((OUT / "curves_design.json").read_text())["chosen"]
    if chosen != {"fixed": "LI", "ilb": "LI"}:
        raise SystemExit(f"this script prices on the zero curve behind LI; the design chose {chosen}")

    bonds = rc.book()
    a, _ = rc.load(bonds)
    a = a[~rc.screen(a)]
    cv = valuation_curves(a)
    out = {"protocol": frozen, "curves": {}}
    for kind, v in cv.items():
        out["curves"][kind] = {
            "date": str(v["date"].date()), "longest": v["last"],
            "bonds": [{"bond": q.code, "maturity": q.maturity, "yield": q.y} for q in sorted(v["points"], key=lambda q: q.maturity)],
            "forwards": {m: list(f[:45]) for m, f in v["forwards"].items()},
        }

    bt = json.loads((OUT / "backtest_statssa.json").read_text())
    panels = data.load("statssa", deaths=args.deaths, population=args.population)
    rng = np.random.default_rng(SEED + 2)  # as v1, sexes in the same order
    products = {"inflation-linked": "ilb", "level": "fixed"}
    for s, r in panels.items():
        model = bt["tests"]["chosen"][s]
        full, ages, start, jump = simulate(r, model, model.split(maxsplit=1)[1], rng)
        res = {"model": model, "jump_off": jump, "prices": []}
        for x in ENTRY_AGES:
            m = annuity.cohort(full, ages, x, start)
            for adj in ADJ:
                row = {"age": x, "adj": adj, "flat": {}}
                for i in RATES:
                    row["flat"][i] = float(np.median(annuity.factor(m, i, adj)))
                for prod, kind in products.items():
                    for curve, fwd in cv[kind]["forwards"].items():
                        f = annuity.factor(m, adj=adj, forwards=fwd)
                        lo, med, hi = np.quantile(f, [0.025, 0.5, 0.975])
                        row[f"{prod} {curve}"] = {"median": med, "lo": lo, "hi": hi,
                                                  "implied_flat_rate": implied_rate(m, adj, med)}
                res["prices"].append(row)
            if x == 65:
                mm = m
        res["matching"] = matching(mm, 0.7, cv["ilb"], bonds)
        out[s] = res
        print(s, model, json.dumps(res["matching"]["annuity"], default=float))
    (OUT / "annuities_v2.json").write_text(json.dumps(out, indent=1, default=float))


def matching(m: np.ndarray, adj: float, cv: dict, bonds: dict) -> dict:
    """Duration and key rates of the inflation-linked annuity at 65, and the two inflation-linked bonds in issue
    whose durations bracket it, held to match its value and duration."""
    fwd = cv["forwards"]["LI"]
    ann = risk(lambda f: float(np.mean(annuity.factor(m, adj=adj, forwards=f))), fwd)
    settle = (cv["date"] + timedelta(days=3)).date()
    book = {}
    for code, b in bonds.items():
        if (code[0] == "I" or code in ILB) and max(d for d, _ in b.redemptions) > settle:
            t, cf = b.cashflows(settle)
            if t[-1] >= c.FLOOR:
                book[code] = risk(lambda f, t=t, cf=cf: bond_value(t, cf, f), fwd)
    below = max((k for k in book if book[k]["duration"] <= ann["duration"]), key=lambda k: book[k]["duration"])
    above = min((k for k in book if book[k]["duration"] > ann["duration"]), key=lambda k: book[k]["duration"])
    (p1, d1), (p2, d2) = [(book[k]["value"], book[k]["duration"]) for k in (below, above)]
    # n1 p1 + n2 p2 = V and n1 p1 d1 + n2 p2 d2 = V D, in nominal per 100 per unit of annuity
    w2 = (ann["duration"] - d1) / (d2 - d1)
    n = {below: ann["value"] * (1 - w2) / p1, above: ann["value"] * w2 / p2}
    port = {k: sum(n[b] * book[b]["dv01"][k] for b in n) for k in KEYS}
    return {"annuity": ann, "bonds": book, "portfolio": {"holdings_per_100_nominal": n, "dv01": port,
            "mismatch": {k: port[k] - ann["dv01"][k] for k in KEYS}}}


if __name__ == "__main__":
    main()
