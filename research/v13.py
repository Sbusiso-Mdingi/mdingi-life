"""v1.3 (research/PROTOCOL_v1.3.md): v1.2 with Renshaw-Haberman's cohort term smoothed over birth years (span 5)
inside the fit, scored at two backtest origins, with v1.2 rescored at origin B, the CBD fallback, convergence checks,
the plausibility gate and the pricing chain.

    python -m research.v13

Writes research/results/v13.json. Refuses to run until PROTOCOL_v1.3.md is frozen.
"""
from __future__ import annotations

import json
import time
import warnings

import numpy as np

from mdingilife import annuity, average, bootstrap, data, kannisto, scores
from mdingilife.models import CBD, LeeCarter, RenshawHaberman, SmoothRH
from mdingilife.protocol import PROTOCOL_V1_3, require_frozen
from research import v11
from research.annuities import ADJ, ENTRY_AGES, RATES, YEAR
from research.backtest import AGES, DESIGN, OUT, WINDOWS
from research.export import e65

SEED = 20261030
NAMES = v11.NAMES
ORIGINS = {"A": (2016, range(2017, 2020)), "B": (2013, range(2014, 2017))}
COVERED = (108, 117)  # Q2: 90% to 98% of 120 cells
RISE = 0.25  # the gate: e65 must rise by at least this from 2020 to 2030
CLASSES = {"v1.3": {"LC": LeeCarter, "CBD": CBD, "RH": SmoothRH},
           "v1.2": {"LC": LeeCarter, "CBD": CBD, "RH": RenshawHaberman}}
# v1's published production results (RESULTS.md), for the gate and the combined set
V1 = {"price65": {"Male": 13.53, "Female": 16.05}, "e65": {"Male": {"2020": 15.31, "2030": 16.11},
                                                          "Female": {"2020": 18.29, "2030": 19.69}}}
AGES_ARR = np.array(list(AGES))


def counting(fn, *args, **kw):
    """Call fn, counting Renshaw-Haberman fits that did not converge."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        out = fn(*args, **kw)
    return out, sum("did not converge" in str(x.message) for x in w)


def check(r: data.Rates) -> dict:
    """The protocol's checks on a main fit: convergence, two starts, and the deviance of smoothed against raw."""
    raw = RenshawHaberman().fit(r)
    one, two = SmoothRH().fit(r), SmoothRH().fit(r, g0=raw.g)
    dev = lambda m: scores.deviance(r.D, r.E * np.exp(m.fitted()))
    gap = float(np.abs(one.fitted() - two.fitted()).max())
    return {"converged": bool(one.converged), "iterations": one.iters, "last_change": one.change,
            "second_start_converged": bool(two.converged), "start_gap": gap, "deviance": dev(one), "deviance_raw": dev(raw),
            "passes": bool(one.converged and two.converged and gap < 1e-6 and dev(one) >= dev(raw))}


def design(panels: dict, windows: dict, rng, paths: int) -> dict:
    """Each sex's v1.2 windows, fitted to 2012 and scored on 2013 to 2016 with the smoothed RH: the weights."""
    jump, scored = DESIGN
    out = {}
    for s, r in panels.items():
        obs = r.sub(AGES, scored)
        cols = [y - jump - 1 for y in scored]
        sc = {}
        for n in NAMES:
            m = CLASSES["v1.3"][n]().fit(v11.years(r, WINDOWS[windows[s][n]], jump))
            med = np.median(m.forecast(max(scored) - jump, paths, rng)[:, :, cols], axis=0)
            sc[n] = {"deviance_anchored": scores.deviance(obs.D, obs.E * np.exp(med + bootstrap.offset(m)[:, None])),
                     "phi": bootstrap.dispersion(m)}
        dev = {n: sc[n]["deviance_anchored"] for n in NAMES}
        phi = float(np.mean([sc[n]["phi"] for n in NAMES]))
        out[s] = {"scores": sc, "weights": average.weights(dev, phi), "inverse_weights": average.inverse(dev),
                  "rh_check": check(v11.years(panels[s], WINDOWS[windows[s]["RH"]], jump))}
    return out


def score(obs: data.Rates, sims: np.ndarray, noisy: np.ndarray) -> dict:
    lo_obs = np.log(obs.m)
    med = np.median(sims, axis=0)
    lo, hi = np.quantile(noisy, [0.025, 0.975], axis=0)
    inside = (lo_obs >= lo) & (lo_obs <= hi)
    err = scores.annuity_error(med, lo_obs, obs.ages)
    return {"deviance": scores.deviance(obs.D, obs.E * np.exp(med)), "annuity_error": err.tolist(),
            "mean_abs_error": float(np.mean(np.abs(err))), "coverage": float(inside.mean()),
            "covered": int(inside.sum()), "cells": int(inside.size), "width": float(np.exp(hi - lo).mean())}


def tests(res: dict, b0: float) -> dict:
    a = res["anchored"]
    return {"Q1": a["deviance"] < b0, "Q2": COVERED[0] <= a["covered"] <= COVERED[1],
            "Q3": a["mean_abs_error"] < 0.02, "Q4": a["deviance"] < res["unanchored"]["deviance"]}


def origin(panels: dict, windows: dict, wts: dict, v12w: dict, o: str, rng, paths: int, refits: int) -> dict:
    jump, scored = ORIGINS[o]
    cols = [y - jump - 1 for y in scored]
    h = max(scored) - jump
    out = {}
    for s, r in panels.items():
        obs = r.sub(AGES, scored)
        sims = {}
        runs = [("LC", LeeCarter), ("CBD", CBD), ("RH", SmoothRH)] + ([("RH v1.2", RenshawHaberman)] if o == "B" else [])
        bad = 0
        for key, cls in runs:
            fit = v11.years(r, WINDOWS[windows[s][key.split()[0]]], jump)
            (raw, offs, phi), nc = counting(bootstrap.paths, cls, fit, h, refits, paths, rng)
            if cls is SmoothRH:
                bad += nc
            raw = raw[:, :, cols]
            anch = raw + offs[:, :, None]
            sims[key] = {"phi": phi, "raw": raw, "anch": anch, "noisy": bootstrap.observe(anch, obs.E, phi, rng),
                         "noisy_raw": bootstrap.observe(raw, obs.E, phi, rng)}
        b0 = v11.MODELS["B0"]().fit(v11.years(r, 1997, jump))
        b0_dev = scores.deviance(obs.D, obs.E * np.exp(b0.log_m)[:, None] * np.ones(len(scored)))
        models = {k: {"phi": v["phi"], "anchored": score(obs, v["anch"], v["noisy"]),
                      "unanchored": score(obs, v["raw"], v["noisy_raw"])} for k, v in sims.items()}
        for k in models:
            models[k]["tests"] = tests(models[k], b0_dev)

        def mix(w, keys):
            pick = lambda f: v11.mixture({n: sims[keys[n]][f] for n in NAMES}, w)
            res = {"anchored": score(obs, pick("anch"), pick("noisy")), "unanchored": score(obs, pick("raw"), pick("noisy_raw"))}
            return res | {"tests": tests(res, b0_dev)}

        same = {n: n for n in NAMES}
        res = {"B0": b0_dev, "models": models, "v1.3": mix(wts[s]["weights"], same),
               "inverse": mix(wts[s]["inverse_weights"], same), "rh_refits": refits, "rh_not_converged": bad,
               "rh_check": check(v11.years(r, WINDOWS[windows[s]["RH"]], jump))}
        if o == "B":
            res["v1.2"] = mix(v12w[s], same | {"RH": "RH v1.2"})
        out[s] = res
    return out


def forecast(r, windows: dict, w: dict, rng, paths: int, refits: int, classes=CLASSES["v1.3"], phi=True):
    sims, bad, total = [], 0, 0
    for n, (k, nref) in average.split(w, paths, refits).items():
        fit = v11.years(r, WINDOWS[windows[n]])
        jump = int(fit.years[-1])
        h = YEAR - jump - 1 + kannisto.TOP - min(ENTRY_AGES) + 1
        (s, off, _), nc = counting(bootstrap.paths, classes[n], fit, h, nref, k, rng)
        if classes[n] is SmoothRH:
            bad, total = bad + nc, total + nref
        sims.append(s + off[:, :, None])
    sims = np.concatenate(sims)
    ages, full = kannisto.extend(sims, fit.ages)
    return full, ages, YEAR - jump - 1, jump, sims, bad, total


def price(r, windows, w, rng, paths, refits) -> dict:
    full, ages, start, jump, sims, bad, total = forecast(r, windows, w, rng, paths, refits)
    out = {"jump_off": jump, "prices": [], "e65": {}, "rh_refits": total, "rh_not_converged": bad}
    for x in ENTRY_AGES:
        m = annuity.cohort(full, ages, x, start)
        for i in RATES:
            for adj in ADJ:
                f = annuity.factor(m, i, adj)
                lo, med, hi = np.quantile(f[np.isfinite(f)], [0.025, 0.5, 0.975])
                out["prices"].append({"age": x, "rate": i, "adj": adj, "median": med, "lo": lo, "hi": hi,
                                      "width_pct": 100 * (hi - lo) / med, "left_out": int((~np.isfinite(f)).sum())})
    e = e65(sims, AGES_ARR)
    for y in v11.E65_YEARS:
        ey = e[:, y - jump - 1]
        lo, med, hi = np.quantile(ey[np.isfinite(ey)], [0.025, 0.5, 0.975])
        out["e65"][str(y)] = {"median": med, "lo": lo, "hi": hi, "left_out": int((~np.isfinite(ey)).sum())}
    return out


def price65(p: dict) -> float:
    return next(x["median"] for x in p["prices"] if x["age"] == 65 and x["rate"] == 0.04 and x["adj"] == 0.7)


def gate(p65: dict, e: dict) -> dict:
    rise = {s: e[s]["2030"] - e[s]["2020"] for s in e}
    women = p65["Female"] > p65["Male"]
    rising = all(v >= RISE for v in rise.values())
    return {"price65": p65, "women_above_men": bool(women), "e65_rise_2020_2030": rise, "e65_rising": bool(rising),
            "passes": bool(women and rising)}


def jump_split(m) -> dict:
    """e65 from the fitted 2019 rates to 2020 with the period index held at 2019, and each age's share."""
    g = np.append(m.g, 0.0)
    now = m.fitted()[:, -1]
    held = m.a + m.b * m.k[-1] + g[m.idx[:, -1] + 1]
    base = float(e65(now[:, None], AGES_ARR)[0])
    total = float(e65(held[:, None], AGES_ARR)[0]) - base
    by_age = {}
    for j, x in enumerate(AGES_ARR):
        one = now.copy()
        one[j] = held[j]
        by_age[int(x)] = float(e65(one[:, None], AGES_ARR)[0]) - base
    return {"e65_2019_fitted": base, "move": total, "by_age": by_age}


def cohort(m) -> dict:
    c = m.c0 + np.flatnonzero(m.ok)
    return {"birth_years": c.tolist(), "g": m.g[m.ok].tolist(), "ar": float(m.phi)}


def run(panels: dict, windows: dict, v12w: dict, rng, paths: int = average.PATHS, refits: int = average.REFITS,
        registered: dict | None = None, log=print) -> dict:
    t = time.time()
    out = {"windows": windows}
    out["design"] = d = design(panels, windows, rng, paths)
    log("design", {s: d[s]["weights"] for s in d}, f"{time.time() - t:.0f}s")
    out["origins"] = {}
    for o in ORIGINS:
        out["origins"][o] = origin(panels, windows, d, v12w, o, rng, paths, refits)
        log("origin", o, f"{time.time() - t:.0f}s")
    out["production"] = {}
    for s, r in panels.items():
        prod = v11.years(r, WINDOWS[windows[s]["RH"]])
        sm, raw = SmoothRH().fit(prod), RenshawHaberman().fit(prod)
        out["production"][s] = {"rh_check": check(prod), "cohort_v1.3": cohort(sm), "cohort_v1.2": cohort(raw),
                                "jump_v1.3": jump_split(sm), "jump_v1.2": jump_split(raw)}
    runs = {"v1.3": (panels, "weights"), "inverse": (panels, "inverse_weights"), "cbd": (panels, None)}
    if registered:
        runs["registered"] = (registered, "weights")
    out["prices"] = {}
    for name, (pn, key) in runs.items():
        out["prices"][name] = {s: price(r, windows[s], d[s][key] if key else {"CBD": 1.0}, rng, paths, refits)
                               for s, r in pn.items()}
        log(name, f"{time.time() - t:.0f}s")
    out["decision"] = decide(out)
    return out


def decide(out: dict, v12: dict | None = None) -> dict:
    sexes = list(out["design"])
    p = out["prices"]
    g13 = gate({s: price65(p["v1.3"][s]) for s in sexes}, {s: {y: p["v1.3"][s]["e65"][y]["median"] for y in ("2020", "2030")} for s in sexes})
    gcbd = gate({s: price65(p["cbd"][s]) for s in sexes}, {s: {y: p["cbd"][s]["e65"][y]["median"] for y in ("2020", "2030")} for s in sexes})
    g1 = gate(V1["price65"], V1["e65"])
    g12 = gate(*v12) if v12 else None
    o = out["origins"]
    fit_ok = lambda s: (all(o[k][s]["rh_check"]["passes"] for k in o) and out["production"][s]["rh_check"]["passes"]
                        and out["design"][s]["rh_check"]["passes"])
    refit_ok = lambda s: (sum(o[k][s]["rh_not_converged"] for k in o) + p["v1.3"][s]["rh_not_converged"]
                          <= 0.05 * (sum(o[k][s]["rh_refits"] for k in o) + p["v1.3"][s]["rh_refits"]))
    q = lambda key, s, ks=("A", "B"): all(all(v for t, v in (o[k][s][key]["tests"] if key in o[k][s] else o[k][s]["models"][key]["tests"]).items() if t != "Q4") for k in ks)
    out_ = {"gate": {"v1.3": g13, "cbd": gcbd, "v1": g1, "v1.2": g12}, "by_sex": {}}
    for s in sexes:
        v13 = {"tests_both_origins": q("v1.3", s), "fits": fit_ok(s), "refits": refit_ok(s), "gate": g13["passes"]}
        v13["passes"] = all(v13.values())
        if s == "Male":
            v12b = all(v for t, v in o["B"][s]["v1.2"]["tests"].items() if t != "Q4")
            alt = {"name": "v1.2", "origin_B": v12b, "gate": g12["passes"] if g12 else None}
            alt["passes"] = bool(v12b and alt["gate"])
        else:
            alt = {"name": "CBD", "tests_both_origins": q("CBD", s), "gate": gcbd["passes"]}
            alt["passes"] = bool(alt["tests_both_origins"] and alt["gate"])
        chosen = "v1.3" if v13["passes"] else (alt["name"] if alt["passes"] else "v1")
        out_["by_sex"][s] = {"v1.3": v13, "fallback": alt, "prices_on": chosen, "lower_bounds": chosen == "v1"}
    return out_


def combined(out: dict, v12: tuple) -> dict:
    """The final set, each sex on its own version, against the gate."""
    on = {s: x["prices_on"] for s, x in out["decision"]["by_sex"].items()}
    p65, e = {}, {}
    for s, v in on.items():
        if v == "v1":
            p65[s], e[s] = V1["price65"][s], V1["e65"][s]
        elif v == "v1.2":
            p65[s], e[s] = v12[0][s], v12[1][s]
        else:
            p = out["prices"]["v1.3" if v == "v1.3" else "cbd"][s]
            p65[s], e[s] = price65(p), {y: p["e65"][y]["median"] for y in ("2020", "2030")}
    return {"prices_on": on} | gate(p65, e)


def main() -> None:
    frozen = require_frozen(PROTOCOL_V1_3)
    v12 = json.loads((OUT / "v12.json").read_text())
    windows = {s: x["windows"] for s, x in v12["design"]["by_sex"].items()}
    v12w = {s: x["weights"][s] for s, x in v12["design"]["by_sex"].items()}
    p12 = v12["prices"]["v1.1"]
    v12g = ({s: price65(p12[s]) for s in p12}, {s: {y: p12[s]["e65"][y]["median"] for y in ("2020", "2030")} for s in p12})
    load = lambda deaths: data.load("statssa", deaths=deaths, population=v11.POPULATION)
    scaled, registered = load(v11.SCALED), load(v11.DEATHS)
    rng = np.random.default_rng(SEED)
    out = {"protocol_v1_3": frozen, "seed": SEED}
    out |= run(scaled, windows, v12w, rng, registered=registered, log=lambda *a: print(*a, flush=True))
    out["decision"] = decide(out, v12g)
    out["combined"] = combined(out, v12g)
    print(json.dumps({"decision": out["decision"], "combined": out["combined"]}, indent=1, default=float))
    (OUT / "v13.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
