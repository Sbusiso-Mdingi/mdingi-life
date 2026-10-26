"""Rolling-origin backtest, repricing and blended price, from the protocol amendment of 26 October 2026.

A robustness check on the single design/validation split: every jump-off from 2009 to 2016 is scored on the three
years after it, for ten candidates (LC, CBD and RH on three windows, plus B0). Nothing here changes the chosen
models. Writes research/results/rolling_{source}.json and, from the production fit, the blended price
research/results/annuities_{source}_blend.json. Refuses to run until the protocol is frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife import annuity, data, kannisto
from mdingilife.models import MODELS
from mdingilife.protocol import require_frozen
from research import annuities
from research.backtest import AGES, COVID, OUT, PATHS, SEED, score

ORIGINS = range(2009, 2017)
HORIZON = 3
ROLLING = 10
BLEND = ("LC", "CBD", "RH")
PRICE_AGE, PRICE_RATE, PRICE_ADJ = 65, 0.04, 0.7


def start(window: str, jump: int) -> int:
    return {"full": 1997, "post-peak": 2006, "rolling": jump - ROLLING + 1, "last three": 1997}[window]


def candidates() -> list[tuple[str, str]]:
    return [("B0", "last three")] + [(n, w) for n in BLEND for w in ("full", "post-peak", "rolling")]


def quote(cls, r: data.Rates, first: int, jump: int, rng) -> dict:
    """Median process-only price for a life aged PRICE_AGE in the year after jump-off.

    Short windows can fit a negative age loading at the oldest ages, so rates there rise as the rest improve and
    pass 1 before the life reaches 89, where the Kannisto tail cannot be fitted. The quote is then left out
    (price None) and the share of failed paths reported, rather than taking the median of the survivors.
    """
    m = cls().fit(r.sub(AGES, [y for y in r.years if first <= y <= jump and y not in COVID]))
    sims = m.forecast(kannisto.TOP - PRICE_AGE + 1, PATHS, rng)
    failed = float((sims[:, np.isin(m.r.ages, list(kannisto.FIT_AGES)), :] >= 0).any(axis=(1, 2)).mean())
    if failed:
        return {"price": None, "failed": failed}
    ages, full = kannisto.extend(sims, m.r.ages)
    a = annuity.factor(annuity.cohort(full, ages, PRICE_AGE, 0), PRICE_RATE, PRICE_ADJ)
    return {"price": float(np.median(a)), "failed": 0.0}


def backtest(panels: dict[str, data.Rates], rng) -> dict:
    out = {}
    for name, w in candidates():
        key = f"{name} {w}"
        out[key] = {s: [score(MODELS[name], r, start(w, T), T, range(T + 1, T + HORIZON + 1), rng) | {"origin": T}
                        for T in ORIGINS] for s, r in panels.items()}
        print(key, {s: round(sum(o["deviance"] for o in v)) for s, v in out[key].items()}, flush=True)
    return out


def summarise(scores: dict, panels, chosen: dict, windows: dict) -> dict:
    out = {}
    for s in panels:
        dev = {k: [o["deviance"] for o in v[s]] for k, v in scores.items()}
        best = [min(dev, key=lambda k: dev[k][i]) for i in range(len(ORIGINS))]
        out[s] = {k: {"deviance": sum(dev[k]), "wins": best.count(k),
                      "abs_annuity_error": float(np.mean([np.abs(o["annuity_error"]).mean() for o in scores[k][s]])),
                      "coverage": float(np.mean([o["coverage"] for o in scores[k][s]]))} for k in scores}
        out[s]["_winner_by_origin"] = best
    total = lambda s, k: out[s][k]["deviance"]
    readings = {
        "R1": {s: min((k for k in scores), key=lambda k: total(s, k)) == chosen[s] for s in panels},
        "R2": {s: out[s][chosen[s]]["coverage"] >= 0.90 for s in panels},
        "lowest": {s: min((k for k in scores), key=lambda k: total(s, k)) for s in panels},
    }
    weights = {s: (lambda inv: {n: v / sum(inv.values()) for n, v in inv.items()})(
        {n: 1 / total(s, f"{n} {windows[n]}") for n in BLEND}) for s in panels}
    return {"by_sex": out, "readings": readings, "weights": weights}


def reprice(panels, windows: dict, rng) -> dict:
    out = {}
    for s, r in panels.items():
        prod = int(max(y for y in r.years if y not in COVID))
        jumps = list(ORIGINS) + [2019] + ([prod] if prod > 2019 else [])
        out[s] = {"jump_offs": jumps}
        for name, w in [("B0", "last three")] + [(n, windows[n]) for n in BLEND]:
            out[s][f"{name} {w}"] = [quote(MODELS[name], r, start(w, T), T, rng) for T in jumps]
    return out


def blend(panels, chosen: dict, windows: dict, weights: dict, rng) -> dict:
    out = {"model": "blend", "weights": weights}
    for s, r in panels.items():
        parts, jump = {}, None
        for n in BLEND:
            jump, parts[n] = annuities.factors(r, f"{n} {windows[n]}", windows[n], rng)
        take = {n: int(round(weights[s][n] * annuities.PATHS)) for n in BLEND}
        pick = {n: rng.choice(annuities.PATHS, take[n], replace=False) for n in BLEND}
        mix = {key: np.concatenate([parts[n][key][pick[n]] for n in BLEND]) for key in parts[BLEND[0]]}
        out[s] = {"model": "blend of " + ", ".join(f"{n} {windows[n]} {weights[s][n]:.0%}" for n in BLEND),
                  "chosen": chosen[s], "jump_off": jump, "prices": annuities.summary(mix)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wpp", choices=["wpp", "statssa"])
    ap.add_argument("--deaths")
    ap.add_argument("--population")
    a = ap.parse_args()
    frozen = require_frozen()
    bt = json.loads((OUT / f"backtest_{a.source}.json").read_text())
    chosen, windows = bt["tests"]["chosen"], bt["windows"]
    paths = {"deaths": a.deaths, "population": a.population} if a.source == "statssa" else {}
    panels = data.load(a.source, **paths)
    rng = np.random.default_rng(SEED + 4)
    scores = backtest(panels, rng)
    summ = summarise(scores, panels, chosen, windows)
    out = {"source": a.source, "protocol": frozen, "origins": list(ORIGINS), "horizon": HORIZON,
           "chosen": chosen, "windows": windows, **summ, "reprice": reprice(panels, windows, rng), "scores": scores}
    (OUT / f"rolling_{a.source}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(summ["readings"], indent=1), json.dumps(summ["weights"], indent=1))
    b = {"source": a.source, "tag": "blend", "protocol": frozen} | blend(panels, chosen, windows, summ["weights"], rng)
    (OUT / f"annuities_{a.source}_blend.json").write_text(json.dumps(b, indent=1, default=float))
    print("wrote", f"rolling_{a.source}.json and annuities_{a.source}_blend.json")


if __name__ == "__main__":
    main()
