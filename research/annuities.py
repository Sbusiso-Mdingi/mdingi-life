"""Annuity prices from the production fit: ages 55, 65 and 75 in 2026, by sex, with 95% intervals.

Uses the model and window chosen by backtest.py. Writes research/results/annuities.json. Refuses to run until the
protocol is frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife import annuity, bootstrap, data, kannisto
from mdingilife.models import MODELS
from mdingilife.protocol import require_frozen
from research.backtest import AGES, COVID, OUT, SEED, WINDOWS

YEAR, ENTRY_AGES = 2026, (55, 65, 75)
RATES, ADJ = (0.02, 0.04, 0.06), (0.6, 0.7, 0.8)
REFITS, PATHS = 500, 5000


def price(r: data.Rates, model: str, window: str, rng) -> dict:
    name = model.split()[0]
    years = [y for y in r.years if y >= WINDOWS[window] and y not in COVID]
    r = r.sub(AGES, years)
    jump = int(r.years[-1])
    start = YEAR - jump - 1
    h = start + kannisto.TOP - min(ENTRY_AGES) + 1
    sims = bootstrap.simulate(MODELS[name], r, h, REFITS, PATHS, rng)
    ages, full = kannisto.extend(sims, r.ages)
    out = {"jump_off": jump, "prices": []}
    for x in ENTRY_AGES:
        m = annuity.cohort(full, ages, x, start)
        for i in RATES:
            for adj in ADJ:
                a = annuity.factor(m, i, adj)
                lo, med, hi = np.quantile(a, [0.025, 0.5, 0.975])
                out["prices"].append({"age": x, "rate": i, "adj": adj, "median": med, "lo": lo, "hi": hi,
                                      "width_pct": 100 * (hi - lo) / med})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wpp", choices=["wpp", "statssa"])
    ap.add_argument("--deaths")
    ap.add_argument("--population")
    a = ap.parse_args()
    frozen = require_frozen()
    bt = json.loads((OUT / f"backtest_{a.source}.json").read_text())
    paths = {"deaths": a.deaths, "population": a.population} if a.source == "statssa" else {}
    panels = data.load(a.source, **paths)
    rng = np.random.default_rng(SEED + 2)
    out = {"source": a.source, "protocol": frozen}
    for s, r in panels.items():
        model = bt["tests"]["chosen"][s]
        out[s] = {"model": model} | price(r, model, model.split(maxsplit=1)[1], rng)
    (OUT / f"annuities_{a.source}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
