"""Bundle backtest and annuity results, plus observed and fitted rates, into data/research.json for the service.

Also adds what the dashboard draws: life expectancy at birth and at 65 by year from the WPP life tables (1950 on), and a fan
of period life expectancy at 65 from the production fit (same model, window, bootstrap and seed offset style as
annuities.py), with the observed series, Covid years included, to set against it.

With --source statssa it also bundles the comparison with the WPP run: annuity prices from each run in COMPARE that
exists, the completeness of registration and the WPP/Stats SA population check.

If annuities_v2.json exists it bundles v2 as well, from the saved results only (nothing is refitted): the curves' design
and validation scores, the validation error by year, the valuation-date curves, the annuity prices on them and the
matching portfolio.

If balance_v3.json exists it bundles v3 the same way: the balance sheet, the SCR by risk, matched and unmatched, the
sensitivities, the checks, the funeral table, a summary of the invented book with its funeral premium rates, the key-rate
DV01 of the annuities and of each portfolio and, if keyrate_v3.json exists, the key-rate matched result.

If projection_v4.json exists it bundles v4: the scenario generator's parameters and 10-year rate fans, cover across the
scenarios, the central path's balance sheets and IFRS 17 results, the named stresses, the sensitivities and the checks.
If capital_v4.json exists too, it adds the starting-capital levels, with v4's own R400 million run as the first.

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
# Steps from the WPP run to the Stats SA run; each changes one thing. Exploratory ones are outside the protocol.
COMPARE = [
    ("wpp", "UN WPP deaths, CBD full, jump-off 2023", False),
    ("wpp_cbd_2019", "Same, jump-off 2019", True),
    ("wpp_rh_2019", "Same, RH post-peak", True),
    ("statssa_scaled", "Registered deaths, scaled to WPP's level", False),
    ("statssa", "Registered deaths, as registered", False),
]


def compare() -> dict:
    runs = []
    for key, label, exploratory in COMPARE:
        f = OUT / f"annuities_{key}.json"
        if f.exists():
            a = json.loads(f.read_text())
            runs.append({"key": key, "label": label, "exploratory": exploratory,
                         **{s: {"model": a[s]["model"], "jump_off": a[s]["jump_off"], "prices": a[s]["prices"]}
                            for s in data.SEXES}})
    table = lambda name: (lambda t: {"years": t.index.tolist(), **{s: t[s].tolist() for s in data.SEXES}})(
        pd.read_csv(OUT / name, index_col=0))
    return {"runs": runs, "completeness": table("completeness.csv"), "exposure": table("exposure_check.csv")}


def v2() -> dict | None:
    f = OUT / "annuities_v2.json"
    if not f.exists():
        return None
    an = json.loads(f.read_text())
    design, val = (json.loads((OUT / f"curves_{p}.json").read_text()) for p in ("design", "validation"))
    keep = lambda d: {k: d[k] for k in ("curves", "all")}
    pr = pd.read_csv(OUT / "curves_validation_predictions.csv", parse_dates=["date"])
    by_year = {}
    for kind, g in pr.groupby("kind"):
        cols = ["LI", "NS", "B0"] + (["NSS"] if kind == "fixed" else [])
        g = g.dropna(subset=cols)
        rmse = lambda e: float(np.sqrt(np.mean(e ** 2)) * 1e4)
        yrs = sorted(g["date"].dt.year.unique())
        by_year[kind] = {"years": [int(y) for y in yrs], "n": [int((g["date"].dt.year == y).sum()) for y in yrs],
                         **{c: [round(rmse(g.loc[g["date"].dt.year == y, c] - g.loc[g["date"].dt.year == y, "y"]), 2)
                                for y in yrs] for c in cols}}
    curves = {}
    for kind, c in an["curves"].items():
        t = np.arange(1, 41)
        z = {m: np.cumsum(f)[:40] / t for m, f in c["forwards"].items()}
        curves[kind] = {"date": c["date"], "longest": c["longest"], "bonds": c["bonds"], "years": t.tolist(),
                        # zero rates at semi-annual compounding, to sit beside the bonds' yields
                        "zero": {m: np.round(2 * np.expm1(v / 2), 6).tolist() for m, v in z.items()},
                        "forwards": {m: np.round(f[:40], 6).tolist() for m, f in c["forwards"].items()}}
    sexes = {}
    for s in data.SEXES:
        a = an[s]
        m = a["matching"]
        held = m["portfolio"]["holdings_per_100_nominal"]
        sexes[s] = {"model": a["model"], "jump_off": a["jump_off"], "prices": a["prices"],
                    "matching": {"annuity": m["annuity"], "portfolio": m["portfolio"],
                                 "bonds": {k: m["bonds"][k] for k in held}}}
    return {"protocol": an["protocol"]["v2"], "design": keep(design) | {"chosen": design["chosen"]},
            "validation": keep(val) | {"without_covid": val["without_covid"], "tests": val["tests"]},
            "data": {k: val["data"][k] for k in ("usable", "screened")}, "by_year": by_year, "curves": curves, **sexes}


BOOK = data.ROOT / "data" / "book"


def ages(a: pd.Series) -> dict:
    """Counts in five-year age bands."""
    c = (a // 5 * 5).value_counts().sort_index()
    return {"from": [int(x) for x in c.index], "n": [int(x) for x in c]}


def book() -> dict:
    """The invented book in summary, a few policies from it, and the monthly funeral premium by sex, entry age and sum
    assured (premiums are linear in the sum assured, so two sums give every one)."""
    ann, fun = pd.read_csv(BOOK / "annuities.csv"), pd.read_csv(BOOK / "funeral.csv")
    rates = {}
    for s, g in fun.groupby("sex"):
        out = []
        for e, h in g.groupby("entry_age"):
            p = h.groupby("sum_assured")["premium"].first()
            per = (p.iloc[-1] - p.iloc[0]) / (p.index[-1] - p.index[0])
            out.append({"age": int(e), "per_rand": float(per), "fixed": float(p.iloc[0] - per * p.index[0])})
        rates[s] = out
    pick = lambda df, by: df.groupby(by).head(1).head(4).to_dict("records")  # the first policy of each kind
    return {"annuities": {"n": len(ann), "income": float(ann["income"].sum()), "median_income": float(ann["income"].median()),
                          "types": ann["type"].value_counts().to_dict(), "sexes": ann["sex"].value_counts().to_dict(),
                          "ages": ages(ann["age"]), "median_age": float(ann["age"].median()),
                          "sample": pick(ann, ["sex", "type"])},
            "funeral": {"n": len(fun), "cover": float(fun["sum_assured"].sum()), "premiums": float(fun["premium"].sum() * 12),
                        "sums": {int(k): int(v) for k, v in fun["sum_assured"].value_counts().sort_index().items()},
                        "sexes": fun["sex"].value_counts().to_dict(), "ages": ages(fun["age"]),
                        "median_age": float(fun["age"].median()), "median_premium": float(fun["premium"].median()),
                        "sample": pick(fun[fun["sum_assured"].isin([10_000, 30_000])], ["sex", "sum_assured"])},
            "premium_rates": rates, "sums": sorted(int(x) for x in fun["sum_assured"].unique())}


def dv01(matching: dict) -> dict:
    """Key-rate DV01 by curve: the annuities' and the matching portfolio's (units times each bond's)."""
    return {kind: {"liability": v["liability"]["dv01"],
                   "portfolio": {t: sum(n * v["bonds"][c]["dv01"][t] for c, n in v["units"].items())
                                 for t in v["liability"]["dv01"]}} for kind, v in matching.items()}


def v3() -> dict | None:
    f = OUT / "balance_v3.json"
    if not f.exists():
        return None
    b = json.loads(f.read_text())
    sheet = lambda r: {k: r[k] for k in ("bel", "risk_margin", "scr_life", "market", "bscr", "scr", "cover", "own_funds",
                                         "life", "interest", "inflation")} | {"op": r["op"]["charge"]}
    m = b["main"]
    tab = pd.read_csv(OUT / "funeral_table.csv")
    k1 = b["checks"]["K1"]
    kf = OUT / "keyrate_v3.json"
    key = None
    if kf.exists():
        kr = json.loads(kf.read_text())
        k = kr["key_rate"]
        key = sheet(k) | {"rate_losses": k["rate_losses"], "checks": kr["checks"],
                          "dv01": dv01(k["assets"]["matching"]),
                          "holdings": {kind: {c: n * v["bonds"][c]["value"] for c, n in v["units"].items()}
                                       for kind, v in k["assets"]["matching"].items()}}
    return {"protocol": b["protocol"]["v3"], "valuation_date": b["valuation_date"], "curve_dates": b["curve_dates"],
            "main": sheet(m) | {"bel_parts": m["bel_parts"], "lapse": m["lapse"], "rate_losses": m["rate_losses"],
                                "op_detail": m["op"], "policies": m["policies"], "capital_for": m["capital_for"],
                                "assets": {k: m["assets"][k] for k in ("total", "bill", "matched")},
                                "matching": {k: {"liability": v["liability"], "bonds": {
                                    c: {"duration": bd["duration"], "value": v["units"][c] * bd["value"]}
                                    for c, bd in v["bonds"].items()}} for k, v in m["assets"]["matching"].items()},
                                "scr_ru": m["scr_ru"], "dv01": dv01(m["assets"]["matching"])},
            "unmatched": sheet(b["unmatched"]),
            "sensitivities": {k: sheet(r) for k, r in b["sensitivities"].items()},
            "checks": {"K1": {"worst_relative": k1["worst_relative"], "pass": k1["pass"], "cells": k1["cells"],
                              "scenarios": len(k1["scenarios"])},
                       **{k: b["checks"][k] for k in ("K3", "K4", "K5")}},
            "funeral_table": {"ages": sorted(tab["age"].unique().tolist()),
                              **{s: tab[tab["sex"] == s].sort_values("age")["mu"].round(6).tolist() for s in data.SEXES}},
            "book": book() if (BOOK / "funeral.csv").exists() else None,
            "key_rate": key}


def v4() -> dict | None:
    f = OUT / "projection_v4.json"
    if not f.exists():
        return None
    p = json.loads(f.read_text())
    year = lambda y: {"cover": y["cover"], "own_funds": y["own_funds"], "scr": y["scr"], "assets": y["assets"]["total"],
                      "bel": y["bel"], "risk_margin": y["risk_margin"], "policies": y["policies"],
                      "inflation": y.get("inflation_realised")}
    esg = p["esg"]
    # One history point a year, at the September month-end, beside the year-end fans.
    hist = {}
    for k, h in esg["history"].items():
        pts = [(int(d[:4]), v) for d, v in zip(h["dates"], h["rate"]) if d[5:7] == "09" and v == v]
        hist[k] = {"years": [y for y, _ in pts], "rate": [v for _, v in pts]}
    keep = ("factors", "tau", "months", "names", "mu", "phi", "capped", "sd", "corr", "beta0", "hist_sd_12m")
    frozen3 = esg["frozen_three_factor"]
    ifrs = {c: {k: v[k] for k in ("csm_transition", "csm", "equity", "profit", "service_result", "finance_result",
                                  "roll")} for c, v in p["ifrs17"].items()}
    stress_ifrs = {n: {k: v[k] for k in ("csm", "profit", "service_result", "csm_used", "losses", "loss_t0",
                                         "fs_change_t0", "fs_change_t1", "experience_t1")} for n, v in p["stresses_ifrs17"].items()}
    return {
        "protocol": p["protocol"]["v4"], "valuation_date": p["valuation_date"],
        "esg": {**{k: esg[k] for k in keep}, "ten_year": esg["ten_year"], "history": hist, "checks": esg["checks"],
                "frozen_three_factor": {**{k: frozen3[k] for k in keep}, "checks": frozen3["checks"],
                                        "cover": frozen3["cover"]},
                "covid_excluded": {k: esg["covid_excluded"][k] for k in ("tau", "phi", "checks")}},
        "central": [year(y) for y in p["central"]["years"]],
        "scenarios": p["scenarios"],
        "stresses": {n: {"cover": v["cover"], "own_funds": v["own_funds"], "scr": v["scr"],
                         "capital_to_restore": v["capital_to_restore"], "worst_year": v["worst_year"], "A2": v["A2"]}
                     | stress_ifrs[n] for n, v in p["stresses"].items()},
        "pandemic_ratio": p["pandemic_ratio"],
        "ifrs17": ifrs, "transition": p["transition"],
        "sensitivities": p["sensitivities"],
        "checks": p["checks"],
        "capital": capital(p),
    }


def capital(p: dict) -> dict | None:
    """The starting-capital levels: v4's R400 million run, then each level in capital_v4.json, by own funds."""
    f = OUT / "capital_v4.json"
    if not f.exists():
        return None
    c = json.loads(f.read_text())
    row = lambda funds, scr, cover, share, stresses: {"own_funds": funds, "scr": scr, "cover": cover,
                                                      "share_covered": share, "stresses": stresses}
    rows = [row(p["t0"]["own_funds"], p["t0"]["scr"], p["t0"]["cover"], p["scenarios"]["A1"]["share_covered"],
                {n: min(v["cover"]) for n, v in p["stresses"].items()})]
    rows += [row(v["own_funds"], v["scr"], v["cover"], v["scenarios"]["A1"]["share_covered"],
                 {n: s["lowest"] for n, s in v["stresses"].items()}) for v in c["levels"].values()]
    return {"rule": c["rule"], "levels": sorted(rows, key=lambda x: x["own_funds"])}


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
    out["history"] = history()
    if a.source == "statssa":
        out["compare"] = compare()
    if (b := v2()) is not None:
        out["v2"] = b
    if (b := v3()) is not None:
        out["v3"] = b
    if (b := v4()) is not None:
        out["v4"] = b
    (data.ROOT / "data" / "research.json").write_text(json.dumps(out, default=float))
    print("wrote data/research.json")


if __name__ == "__main__":
    main()
