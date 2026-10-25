"""Bundle backtest and annuity results, plus observed and fitted rates, into data/research.json for the service.

Refuses to run until the protocol is frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from mdingilife import data
from mdingilife.models import MODELS
from mdingilife.protocol import require_frozen
from research.backtest import AGES, COVID, OUT, WINDOWS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wpp", choices=["wpp", "statssa"])
    ap.add_argument("--deaths")
    ap.add_argument("--population")
    a = ap.parse_args()
    frozen = require_frozen()
    bt = json.loads((OUT / f"backtest_{a.source}.json").read_text())
    an = json.loads((OUT / f"annuities_{a.source}.json").read_text())
    paths = {"deaths": a.deaths, "population": a.population} if a.source == "statssa" else {}
    panels = data.load(a.source, **paths)
    rates = {}
    for s, r in panels.items():
        name, window = bt["tests"]["chosen"][s].split(maxsplit=1)
        obs = r.sub(AGES, [y for y in r.years if y >= 1997])
        fit_years = [y for y in obs.years if y >= WINDOWS[window] and y not in COVID]
        m = MODELS[name]().fit(obs.sub(years=fit_years))
        rates[s] = {"ages": obs.ages.tolist(), "years": obs.years.tolist(),
                    "observed": np.round(np.log(obs.m), 5).tolist(),
                    "fitted_years": [int(y) for y in fit_years],
                    "fitted": np.round(m.fitted(), 5).tolist()}
    out = {"source": a.source, "protocol": frozen, "backtest": bt, "annuities": an, "rates": rates}
    (data.ROOT / "data" / "research.json").write_text(json.dumps(out, default=float))
    print("wrote data/research.json")


if __name__ == "__main__":
    main()
