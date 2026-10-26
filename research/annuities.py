"""Annuity prices from the production fit: ages 55, 65 and 75 in 2026, by sex, with 95% intervals.

Uses the model and window chosen by backtest.py. Writes research/results/annuities_{source}.json, or
annuities_{source}_{tag}.json with --tag (a sensitivity that keeps the run's chosen models). --model and
--last-year override the chosen model and the last year fitted, for exploratory runs outside the protocol; they need
a tag. Refuses to run until the protocol is frozen.
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


def simulate(r: data.Rates, model: str, window: str, rng):
    """The production forecast, extended to TOP: (log rates, ages, first forecast year of 2026, jump-off year)."""
    name = model.split()[0]
    years = [y for y in r.years if y >= WINDOWS[window] and y not in COVID]
    r = r.sub(AGES, years)
    jump = int(r.years[-1])
    start = YEAR - jump - 1
    h = start + kannisto.TOP - min(ENTRY_AGES) + 1
    sims = bootstrap.simulate(MODELS[name], r, h, REFITS, PATHS, rng)
    ages, full = kannisto.extend(sims, r.ages)
    return full, ages, start, jump


def price(r: data.Rates, model: str, window: str, rng) -> dict:
    full, ages, start, jump = simulate(r, model, window, rng)
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
    ap.add_argument("--tag")
    ap.add_argument("--model", help='e.g. "CBD full"; replaces the chosen model for both sexes')
    ap.add_argument("--last-year", type=int)
    a = ap.parse_args()
    if (a.model or a.last_year) and not a.tag:
        ap.error("--model and --last-year are outside the protocol and need --tag")
    frozen = require_frozen()
    bt = json.loads((OUT / f"backtest_{a.source}.json").read_text())
    paths = {"deaths": a.deaths, "population": a.population} if a.source == "statssa" else {}
    panels = data.load(a.source, **paths)
    rng = np.random.default_rng(SEED + 2)
    out = {"source": a.source, "tag": a.tag, "model": a.model, "last_year": a.last_year, "protocol": frozen}
    if a.last_year:
        panels = {s: r.sub(years=[y for y in r.years if y <= a.last_year]) for s, r in panels.items()}
    for s, r in panels.items():
        model = a.model or bt["tests"]["chosen"][s]
        out[s] = {"model": model} | price(r, model, model.split(maxsplit=1)[1], rng)
    name = f"annuities_{a.source}" + (f"_{a.tag}" if a.tag else "")
    (OUT / f"{name}.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
