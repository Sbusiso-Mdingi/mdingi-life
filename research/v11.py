"""v1.1 (research/PROTOCOL_v1.1.md): overdispersion, completeness-scaled deaths, an anchored jump-off and an average
of LC, CBD and RH. Design, validation, production prices and the step-by-step comparison with v1.

    python -m research.v11

Writes research/results/v11.json. Refuses to run until PROTOCOL_v1.1.md is frozen.
"""
from __future__ import annotations

import json
import time

import numpy as np

from mdingilife import annuity, average, bootstrap, data, kannisto, scores
from mdingilife.models import MODELS
from mdingilife.protocol import PROTOCOL_V1_1, require_frozen
from research.annuities import ADJ, ENTRY_AGES, RATES, YEAR
from research.backtest import AGES, COVID, DESIGN, OUT, VALIDATION, WINDOWS
from research.completeness import SCALED
from research.exposure import OUT as POPULATION
from research.export import e65
from research.mcd import OUT as DEATHS

SEED = 20261028
NAMES = ("LC", "CBD", "RH")
V1_CHOSEN = "RH post-peak"
E65_YEARS = (2020, 2030, 2050)
PATHS, REFITS = average.PATHS, average.REFITS


def years(r: data.Rates, start: int, jump: int | None = None) -> data.Rates:
    keep = [y for y in r.years if y >= start and (jump is None or y <= jump) and y not in COVID]
    return r.sub(AGES, keep)


def design(panels: dict, rng) -> dict:
    """Every model and window fitted to 2012 and scored on 2013 to 2016, unanchored and anchored."""
    jump, scored = DESIGN
    out = {s: {} for s in panels}
    for s, r in panels.items():
        obs = r.sub(AGES, scored)
        cols = [y - jump - 1 for y in scored]
        for name in NAMES:
            for w, start in WINDOWS.items():
                m = MODELS[name]().fit(years(r, start, jump))
                med = np.median(m.forecast(max(scored) - jump, PATHS, rng)[:, :, cols], axis=0)
                off = bootstrap.offset(m)[:, None]
                out[s][f"{name} {w}"] = {
                    "deviance": scores.deviance(obs.D, obs.E * np.exp(med)),
                    "deviance_anchored": scores.deviance(obs.D, obs.E * np.exp(med + off)),
                    "phi": bootstrap.dispersion(m)}
        b0 = MODELS["B0"]().fit(years(r, 1997, jump))
        out[s]["B0"] = {"deviance": scores.deviance(obs.D, obs.E * np.exp(b0.log_m)[:, None] * np.ones(len(scored)))}
    windows = {n: min(WINDOWS, key=lambda w: sum(out[s][f"{n} {w}"]["deviance"] for s in panels)) for n in NAMES}
    wts, inv = {}, {}
    for s in panels:
        dev = {n: out[s][f"{n} {windows[n]}"]["deviance_anchored"] for n in NAMES}
        phi = float(np.mean([out[s][f"{n} {windows[n]}"]["phi"] for n in NAMES]))
        wts[s], inv[s] = average.weights(dev, phi), average.inverse(dev)
    return {"scores": out, "windows": windows, "weights": wts, "inverse_weights": inv}


def mixture(parts: dict, w: dict) -> np.ndarray:
    """First n paths of each model, n from the weights (the paths of the first refits, as in average.split)."""
    return np.concatenate([parts[m][:n] for m, (n, _) in average.split(w).items()])


def validation(panels: dict, d: dict, rng) -> dict:
    jump, scored = VALIDATION
    cols = [y - jump - 1 for y in scored]
    h = max(scored) - jump
    out = {}
    for s, r in panels.items():
        obs = r.sub(AGES, scored)
        lo = np.log(obs.m)
        score = lambda sims, noisy: {
            "deviance": scores.deviance(obs.D, obs.E * np.exp(np.median(sims, axis=0))),
            "annuity_error": scores.annuity_error(np.median(sims, axis=0), lo, obs.ages).tolist(),
            "coverage": scores.coverage(lo, noisy)}
        anch, raw, noisy, noisy_raw, res = {}, {}, {}, {}, {}
        for n in NAMES:
            fit = years(r, WINDOWS[d["windows"][n]], jump)
            sims, offs, phi = bootstrap.paths(MODELS[n], fit, h, REFITS, PATHS, rng)
            raw[n] = sims[:, :, cols]
            anch[n] = raw[n] + offs[:, :, None]
            noisy[n] = bootstrap.observe(anch[n], obs.E, phi, rng)
            noisy_raw[n] = bootstrap.observe(raw[n], obs.E, phi, rng)
            base = MODELS[n]().fit(fit)
            proc = base.forecast(h, PATHS, rng)[:, :, cols]
            res[n] = {"phi": phi, "anchored": score(anch[n], noisy[n]), "unanchored": score(raw[n], noisy_raw[n]),
                      "v1_setup": score(proc, proc)}
        b0 = MODELS["B0"]().fit(years(r, 1997, jump))
        b0_dev = scores.deviance(obs.D, obs.E * np.exp(b0.log_m)[:, None] * np.ones(len(scored)))
        avg = {}
        for key, w in (("average", d["weights"][s]), ("inverse", d["inverse_weights"][s])):
            avg[key] = {"anchored": score(mixture(anch, w), mixture(noisy, w)),
                        "unanchored": score(mixture(raw, w), mixture(noisy_raw, w))}
        out[s] = {"models": res, "B0": b0_dev} | avg
    a = {s: out[s]["average"] for s in panels}
    out["tests"] = {
        "Q1": {s: a[s]["anchored"]["deviance"] < out[s]["B0"] for s in panels},
        "Q2": {s: a[s]["anchored"]["coverage"] >= 0.90 for s in panels},
        "Q3": {s: float(np.mean(np.abs(a[s]["anchored"]["annuity_error"]))) < 0.02 for s in panels},
        "Q4": {s: a[s]["anchored"]["deviance"] < a[s]["unanchored"]["deviance"] for s in panels},
    }
    return out


def forecast(r: data.Rates, spec: dict, d: dict, sex: str, rng):
    """Production paths, extended to 120: (log rates, ages, first forecast year of 2026, jump-off)."""
    if spec["models"] == "v1":
        name, w = V1_CHOSEN.split()
        parts = {name: (PATHS, REFITS)}
        windows = {name: w}
    else:
        windows = d["windows"]
        parts = average.split(d[spec["models"]][sex])
    sims, jump = [], None
    for n, (k, refits) in parts.items():
        fit = years(r, WINDOWS[windows[n]])
        jump = int(fit.years[-1])
        h = YEAR - jump - 1 + kannisto.TOP - min(ENTRY_AGES) + 1
        s, off, _ = bootstrap.paths(MODELS[n], fit, h, refits, k, rng, phi=None if spec["phi"] else 1.0)
        sims.append(s + off[:, :, None] if spec["anchor"] else s)
    ages, full = kannisto.extend(np.concatenate(sims), fit.ages)
    return full, ages, YEAR - jump - 1, jump, np.concatenate(sims)


def price(r, spec, d, sex, rng) -> dict:
    full, ages, start, jump, sims = forecast(r, spec, d, sex, rng)
    out = {"jump_off": jump, "prices": [], "e65": {}}
    for x in ENTRY_AGES:
        m = annuity.cohort(full, ages, x, start)
        for i in RATES:
            for adj in ADJ:
                f = annuity.factor(m, i, adj)
                lo, med, hi = np.quantile(f[np.isfinite(f)], [0.025, 0.5, 0.975])
                out["prices"].append({"age": x, "rate": i, "adj": adj, "median": med, "lo": lo, "hi": hi,
                                      "width_pct": 100 * (hi - lo) / med, "left_out": int((~np.isfinite(f)).sum())})
    e = e65(sims, AGES_ARR)
    for y in E65_YEARS:
        ey = e[:, y - jump - 1]
        lo, med, hi = np.quantile(ey[np.isfinite(ey)], [0.025, 0.5, 0.975])
        out["e65"][str(y)] = {"median": med, "lo": lo, "hi": hi, "left_out": int((~np.isfinite(ey)).sum())}
    return out


AGES_ARR = np.array(list(AGES))
RUNS = {  # the protocol's steps, each keeping the ones before it, then the two sensitivities
    "anchor": dict(data="scaled", models="v1", anchor=True, phi=False),
    "average": dict(data="scaled", models="weights", anchor=True, phi=False),
    "v1.1": dict(data="scaled", models="weights", anchor=True, phi=True),
    "registered": dict(data="registered", models="weights", anchor=True, phi=True),
    "inverse": dict(data="scaled", models="inverse_weights", anchor=True, phi=True),
}


def main() -> None:
    frozen = require_frozen(PROTOCOL_V1_1)
    load = lambda deaths: data.load("statssa", deaths=deaths, population=POPULATION)
    panels = {"scaled": load(SCALED), "registered": load(DEATHS)}
    rng = np.random.default_rng(SEED)
    out = {"protocol_v1_1": frozen, "seed": SEED}
    t = time.time()
    out["design"] = d = design(panels["scaled"], rng)
    print("windows", d["windows"], "weights", json.dumps(d["weights"], default=float), flush=True)
    out["validation"] = validation(panels["scaled"], d, rng)
    print("tests", out["validation"]["tests"], f"{time.time() - t:.0f}s", flush=True)
    obs = {}
    for s, r in panels["scaled"].items():
        o = r.sub(AGES, [y for y in r.years if y >= 2017])
        obs[s] = dict(zip(o.years.tolist(), e65(np.log(o.m), o.ages).tolist()))
    out["observed_e65_scaled"] = obs
    out["prices"] = {}
    for name, spec in RUNS.items():
        out["prices"][name] = {s: price(r, spec, d, s, rng) for s, r in panels[spec["data"]].items()}
        print(name, f"{time.time() - t:.0f}s", flush=True)
        (OUT / "v11.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
