"""Design and validation backtests from the protocol: choose a fitting window per model, then score once.

Writes research/results/backtest.json. Refuses to run until the protocol is frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife import data, scores
from mdingilife.models import MODELS
from mdingilife.protocol import require_frozen

AGES = range(50, 90)
COVID = (2020, 2021, 2022)
WINDOWS = {"full": 1997, "post-peak": 2006}
DESIGN = (2012, range(2013, 2017))
VALIDATION = (2016, range(2017, 2020))
PATHS, SEED = 5000, 20261025
OUT = data.ROOT / "research" / "results"


def score(cls, r: data.Rates, start: int, jump: int, scored: range, rng) -> dict:
    fit_years = [y for y in r.years if start <= y <= jump and y not in COVID]
    m = cls().fit(r.sub(AGES, fit_years))
    h = max(scored) - jump
    # Process uncertainty only, as the protocol's P3 reads it.
    sims = m.forecast(h, PATHS, rng)
    cols = [y - jump - 1 for y in scored]
    sims = sims[:, :, cols]
    obs = r.sub(AGES, scored)
    med = np.median(sims, axis=0)
    return {
        "deviance": scores.deviance(obs.D, obs.E * np.exp(med)),
        "annuity_error": scores.annuity_error(med, np.log(obs.m), obs.ages).tolist(),
        "coverage": scores.coverage(np.log(obs.m), sims),
    }


def run(panels: dict[str, data.Rates]) -> dict:
    rng = np.random.default_rng(SEED)
    out = {"design": {}, "validation": {}, "windows": {}}
    for period, (jump, scored) in (("design", DESIGN), ("validation", VALIDATION)):
        for name, cls in MODELS.items():
            for w, start in (WINDOWS.items() if name != "B0" else [("last three", 1997)]):
                if period == "validation" and name != "B0" and out["windows"][name] != w:
                    continue
                res = {s: score(cls, r, start, jump, scored, rng) for s, r in panels.items()}
                out[period][f"{name} {w}"] = res
        if period == "design":
            for name in MODELS:
                if name == "B0":
                    continue
                total = {w: sum(out["design"][f"{name} {w}"][s]["deviance"] for s in panels) for w in WINDOWS}
                out["windows"][name] = min(total, key=total.get)
    out["tests"] = tests(out, panels)
    return out


def tests(out: dict, panels) -> dict:
    v = out["validation"]
    chosen = {n: f"{n} {out['windows'][n]}" for n in MODELS if n != "B0"}
    dev = lambda key, s: v[key][s]["deviance"]
    best = {s: min(chosen.values(), key=lambda k: dev(k, s)) for s in panels}
    # P2 needs both Lee-Carter windows on the validation period, whichever was chosen.
    lc = {}
    rng = np.random.default_rng(SEED + 1)
    for w, start in WINDOWS.items():
        lc[w] = {s: score(MODELS["LC"], r, start, VALIDATION[0], VALIDATION[1], rng)["deviance"] for s, r in panels.items()}
    return {
        "chosen": best,
        "P1": {s: dev(best[s], s) < dev("B0 last three", s) for s in panels},
        "P2": {s: lc["post-peak"][s] < lc["full"][s] for s in panels},
        "P3": {s: v[best[s]][s]["coverage"] >= 0.90 for s in panels},
        "P4": {s: float(np.mean(np.abs(v[best[s]][s]["annuity_error"]))) < 0.02 for s in panels},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wpp", choices=["wpp", "statssa"])
    ap.add_argument("--deaths")
    ap.add_argument("--population")
    a = ap.parse_args()
    frozen = require_frozen()
    paths = {"deaths": a.deaths, "population": a.population} if a.source == "statssa" else {}
    out = run(data.load(a.source, **paths)) | {"source": a.source, "protocol": frozen}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"backtest_{a.source}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out["tests"], indent=1))


if __name__ == "__main__":
    main()
