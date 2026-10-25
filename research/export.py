"""Bundle backtest and annuity results, plus observed and fitted rates, into data/research.json for the service.

Also adds what the dashboard draws: life expectancy at birth and at 65 by year from the WPP life tables (1950 on), and a fan
of period life expectancy at 65 from the production fit (same model, window, bootstrap and seed offset style as
annuities.py), with the observed series, Covid years included, to set against it.

Refuses to run until the protocol is frozen.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from mdingilife import bootstrap, data, kannisto
from mdingilife.models import MODELS
from mdingilife.protocol import require_frozen
from research.backtest import AGES, COVID, OUT, SEED, WINDOWS

FAN_TO, REFITS, PATHS = 2050, 500, 5000


def e65(log_m: np.ndarray, ages: np.ndarray) -> np.ndarray:
    """Period life expectancy at 65, constant force within each year of age, Kannisto above 89."""
    ages, full = kannisto.extend(log_m, ages)
    mu = np.exp(np.compress(ages >= 65, full, axis=-2))
    alive = np.exp(-np.cumsum(mu, axis=-2))
    start = np.concatenate([np.ones_like(alive[..., :1, :]), alive[..., :-1, :]], axis=-2)
    return (start * -np.expm1(-mu) / mu).sum(axis=-2)


def history() -> dict:
    lt = pd.read_csv(data.WPP / "wpp2024_zaf_life_tables_1950-2023.csv", usecols=["Time", "Sex", "AgeGrp", "ex"])
    out = {"years": sorted(lt["Time"].unique().tolist())}
    for age, key in (("0", "e0"), ("65-65", "e65")):
        at = lt[lt["AgeGrp"] == age]
        out[key] = {s: at[at["Sex"] == s].sort_values("Time")["ex"].round(3).tolist() for s in data.SEXES}
    return out


def fan(r: data.Rates, model: str, window: str, rng) -> dict:
    obs = r.sub(AGES, [y for y in r.years if y >= 1997])
    fit = obs.sub(years=[y for y in obs.years if y >= WINDOWS[window] and y not in COVID])
    jump = int(fit.years[-1])
    sims = bootstrap.simulate(MODELS[model], fit, FAN_TO - jump, REFITS, PATHS, rng)
    lo, med, hi = np.quantile(e65(sims, fit.ages), [0.025, 0.5, 0.975], axis=0)
    return {"jump_off": jump, "years": list(range(jump + 1, FAN_TO + 1)),
            "median": med.round(3).tolist(), "lo": lo.round(3).tolist(), "hi": hi.round(3).tolist(),
            "observed_years": obs.years.tolist(), "observed": e65(np.log(obs.m), obs.ages).round(3).tolist(),
            "covid": list(COVID)}


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
    rates, fans = {}, {}
    rng = np.random.default_rng(SEED + 3)
    for s, r in panels.items():
        name, window = bt["tests"]["chosen"][s].split(maxsplit=1)
        obs = r.sub(AGES, [y for y in r.years if y >= 1997])
        fit_years = [y for y in obs.years if y >= WINDOWS[window] and y not in COVID]
        m = MODELS[name]().fit(obs.sub(years=fit_years))
        rates[s] = {"ages": obs.ages.tolist(), "years": obs.years.tolist(),
                    "observed": np.round(np.log(obs.m), 5).tolist(),
                    "fitted_years": [int(y) for y in fit_years],
                    "fitted": np.round(m.fitted(), 5).tolist()}
        fans[s] = {"model": bt["tests"]["chosen"][s]} | fan(r, name, window, rng)
    out = {"source": a.source, "protocol": frozen, "backtest": bt, "annuities": an, "rates": rates,
           "fan": fans}
    if a.source == "wpp":
        out["history"] = history()
    (data.ROOT / "data" / "research.json").write_text(json.dumps(out, default=float))
    print("wrote data/research.json")


if __name__ == "__main__":
    main()
