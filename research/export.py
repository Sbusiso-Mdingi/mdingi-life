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

If mix_v6.json exists it bundles v6: the mix and size, the balance sheet with the whole book matched (holdings priced on
the valuation date's curves, checked against the matched value), the variants and checks, v5's result on the old counts,
the book at v6's scales with the v5 premium rates by benefit, and v4's projection on v6's book (projection_v6.json) with
the cover 1.0 level (capital_v6.json). With --only-v6, v6 is added to the existing data/research.json and nothing is
refitted.

If balance_v7.json exists it bundles v7 the same way: the balance sheet with default risk and the sovereign reverse
stress, the review and lapse variants, the book with the level rates and the age-rated schedule, v4's projection on
v7's book with the cover 1.0 level, v6 and v7 side by side on the central path, and the empty-match replays if their
results exist. --only-v7 adds v7 alone.

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


def v4(name: str = "projection_v4.json", levels: str = "capital_v4.json", protocol: str = "v4") -> dict | None:
    f = OUT / name
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
        "protocol": p["protocol"][protocol], "valuation_date": p["valuation_date"],
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
        "capital": capital(p, levels),
    }


def capital(p: dict, name: str = "capital_v4.json") -> dict | None:
    """The starting-capital levels: the projection's own R400 million run, then each level in `name`, by own funds."""
    f = OUT / name
    if not f.exists():
        return None
    c = json.loads(f.read_text())
    row = lambda funds, scr, cover, sc, stresses: {"own_funds": funds, "scr": scr, "cover": cover,
                                                   "share_covered": sc["A1"]["share_covered"],
                                                   "below_one_by_year": sc["below_one_by_year"], "stresses": stresses}
    rows = [row(p["t0"]["own_funds"], p["t0"]["scr"], p["t0"]["cover"], p["scenarios"],
                {n: min(v["cover"]) for n, v in p["stresses"].items()})]
    rows += [row(v["own_funds"], v["scr"], v["cover"], v["scenarios"],
                 {n: s["lowest"] for n, s in v["stresses"].items()}) for v in c["levels"].values()]
    return {"rule": c["rule"], "levels": sorted(rows, key=lambda x: x["own_funds"])}


def book_v6(scales: dict) -> dict:
    """v6's book in summary: v5's policies, each line's counts, incomes, sums assured and premiums times its scale (so
    every drawn policy stands for that many), a few policies from it, and the monthly funeral premium by sex, entry
    age and benefit on the v5 table."""
    from research import book_v5 as bk
    A, F = scales["annuities"], scales["funeral"]
    ann, fun = pd.read_csv(BOOK / "annuities.csv"), pd.read_csv(bk.FUNERAL)
    times = lambda d, k: {str(x): float(n * k) for x, n in d.items()}
    band = lambda a, k: (lambda b: {"from": b["from"], "n": [n * k for n in b["n"]]})(ages(a))
    rates = {}
    for s, g in bk.rates(bk.grid()).groupby("sex"):
        rates[s] = [{"age": int(e), **{bt: {"per_rand": float(r["per_rand"]), "fixed": float(r["fixed"])}
                                       for bt, r in h.set_index("benefit").iterrows()}} for e, h in g.groupby("entry_age")]
    pick = lambda df, by: df.groupby(by).head(1).head(4).to_dict("records")
    return {"weights": {"annuities": A, "funeral": F}, "drawn": {"annuities": len(ann), "funeral": len(fun)},
            "annuities": {"n": len(ann) * A, "income": float(ann["income"].sum() * A),
                          "median_income": float(ann["income"].median()), "types": times(ann["type"].value_counts(), A),
                          "sexes": times(ann["sex"].value_counts(), A), "ages": band(ann["age"], A),
                          "median_age": float(ann["age"].median()), "sample": pick(ann, ["sex", "type"])},
            "funeral": {"n": len(fun) * F, "cover": float(fun["sum_assured"].sum() * F),
                        "premiums": float(fun["premium"].sum() * 12 * F),
                        "sums": {str(int(k)): float(v * F) for k, v in fun["sum_assured"].value_counts().sort_index().items()},
                        "benefits": times(fun["benefit"].value_counts(), F), "sexes": times(fun["sex"].value_counts(), F),
                        "ages": band(fun["age"], F), "median_age": float(fun["age"].median()),
                        "median_premium": {bt: float(g["premium"].median()) for bt, g in fun.groupby("benefit")},
                        "sample": pick(fun[fun["sum_assured"].isin([10_000, 30_000])], ["sex", "benefit"])},
            "premium_rates": rates, "sums": sorted(int(x) for x in fun["sum_assured"].unique()),
            "margin": bk.b3.PRICING["margin"], "pricing_growth": bk.PRICING_GROWTH,
            "expense": bk.b3.EXPENSE["funeral"]}


def holdings_v6(units: dict) -> dict:
    """The whole-book match's holdings by value, each bond priced on the valuation date's curves as the match was."""
    from research import balance_v3 as b3
    from research import balance_v5 as b5
    curves, bonds, _, settle = b3.market()
    cv = b3.Curves(curves[b3.Basis().curve]["nominal"], curves[b3.Basis().curve]["real"])
    out = {}
    for kind, u in units.items():
        book = b5.bond_book(bonds, settle, kind)
        out[kind] = {c: n * b5.bond_value(*book[c], cv.fwd[kind]) for c, n in u.items()}
    return out


def v6() -> dict | None:
    """v6 (research/PROTOCOL_v6.md): the mix and size, the balance sheet with the whole book matched, the variants,
    the checks, v5's result on the old counts beside it, the book, and v4's projection on v6's book with the two
    capital levels."""
    f = OUT / "mix_v6.json"
    if not f.exists():
        return None
    x = json.loads(f.read_text())
    sheet = lambda r: {k: r[k] for k in ("bel", "risk_margin", "scr_life", "market", "bscr", "scr", "cover", "own_funds",
                                         "life", "interest", "inflation", "diversification")} | {"op": r["op"]["charge"]}
    m = x["main"]
    match = m["assets"]["matching"]["book"]
    held = holdings_v6(match["units"])
    worth = sum(v for h in held.values() for v in h.values())
    if abs(worth / m["assets"]["matched"] - 1) > 1e-8:
        raise SystemExit(f"holdings priced at {worth:,.0f}, not the matched {m['assets']['matched']:,.0f}")
    v5 = json.loads((OUT / "balance_v5.json").read_text())["main"]
    c = x["checks"]
    return {"protocol": x["protocol"]["v6"], "protocol_v5": x["protocol"]["v5"], "valuation_date": x["valuation_date"],
            "matching": x["matching"],
            **{k: x[k] for k in ("exposures", "mix", "scales", "policies", "trend", "large")},
            "main": sheet(m) | {"bel_parts": m["bel_parts"], "rising_claims": m["rising_claims"], "lapse": m["lapse"],
                                "rate_losses": m["rate_losses"], "vol_loss": m["vol_loss"],
                                "risk_margin_parts": m["risk_margin_parts"], "breakeven": m["f"],
                                "capital_for": m["capital_for"],
                                "assets": {k: m["assets"][k] for k in ("total", "bill", "matched")},
                                "holdings": held, "dv01": {"liability": match["liability"]["dv01"],
                                                           "portfolio": match["portfolio_dv01"]}},
            "v5_matching": sheet(x["other_matching"]), "unmatched": sheet(x["unmatched"]),
            "sensitivities": {k: sheet(r) for k, r in x["sensitivities"].items()},
            "checks": {"D1": c["D1"], "D2": c["D2"], "D3": {"pass": c["D3"]["pass"], "worst": max(c["D3"]["relative"].values())},
                       "D5": c["D5"], **{k: {"pass": c[k]["pass"]} for k in ("C4", "C5", "C6")}},
            "v5": {k: v5[k] for k in ("bel", "scr", "risk_margin", "cover", "own_funds")} | {"policies": {"annuities": 5000, "funeral": 50000}},
            "book": book_v6(x["scales"]),
            "projection": v4("projection_v6.json", "capital_v6.json", "v6")}


def book_v7(scales: dict) -> dict:
    """v7's book in summary, as book_v6 with the premium type in place of the benefit: the level rates by entry age
    (v5's level benefit) and the age-rated schedule, by sex and entry age, a monthly rate per rand and a fixed part for
    each policy year."""
    from research import book_v5 as bk
    from research import book_v7 as bk7
    out = book_v6(scales)
    A, F = scales["annuities"], scales["funeral"]
    fun = pd.read_csv(bk7.FUNERAL)
    times = lambda d: {str(x): float(n * F) for x, n in d.items()}
    pick = fun[fun["sum_assured"].isin([10_000, 30_000])].groupby(["sex", "premium_type"]).head(1).head(4)
    f = out["funeral"]
    f.pop("benefits")
    f.update(premiums=float(fun["premium"].sum() * 12 * F), types=times(fun["premium_type"].value_counts()),
             median_premium={t: float(g["premium"].median()) for t, g in fun.groupby("premium_type")},
             sample=pick.to_dict("records"))
    level = bk.rates(bk.grid())
    level = level[level["benefit"] == "level"]
    sched = pd.read_csv(bk7.SCHEDULE)
    out["premium_rates"] = {s: [{"age": int(e), "level": {"per_rand": float(r["per_rand"].iloc[0]), "fixed": float(r["fixed"].iloc[0])}}
                                for e, r in g.groupby("entry_age")] for s, g in level.groupby("sex")}
    out["schedule"] = {s: {str(int(e)): {"per_rand": h.sort_values("policy_year")["per_rand"].round(10).tolist(),
                                         "fixed": h.sort_values("policy_year")["fixed"].round(6).tolist()}
                           for e, h in g.groupby("entry_age")} for s, g in sched.groupby("sex")}
    out.pop("pricing_growth")
    out["review"] = {"every": 5, "lapse_spike": 0.10}
    return out


def central_compare() -> dict | None:
    """v6 and v7 on the central path at R400 million, year by year: own funds and their change, the capital requirement
    and its interest charges, the funeral line's net cash flow, and IFRS 17 profit."""
    rows = {}
    for v in ("v6", "v7"):
        f = OUT / f"projection_{v}.json"
        if not f.exists():
            return None
        p = json.loads(f.read_text())
        Y = p["central"]["years"]
        net = lambda y: -(y.get("cash_flows") or {}).get("funeral", 0.0)
        rows[v] = {"own_funds": [y["own_funds"] for y in Y], "scr": [y["scr"] for y in Y], "cover": [y["cover"] for y in Y],
                   "nominal": [y["interest"]["nominal"] for y in Y], "real": [y["interest"]["real"] for y in Y],
                   "market": [y["market"] for y in Y], "scr_life": [y["scr_life"] for y in Y],
                   "bel_funeral": [y["bel"]["funeral"] for y in Y], "funeral_net": [net(y) for y in Y[1:]],
                   "profit": p["ifrs17"]["0.1"]["profit"]}
    return rows


def empty_match_v7() -> dict:
    """The read-only replays of v7's projection (research/diag_v7.py, diag_v7_split.py) counting the year-ends where the
    whole-book match held no bonds, and the count in the projection's own log."""
    out = {"logged": 491, "logged_capital": 0}
    for key, name in (("main", "empty_match_v7_main.json"), ("split", "empty_match_v7_split.json")):
        f = OUT / name
        if f.exists():
            out[key] = json.loads(f.read_text())
    return out


def v7() -> dict | None:
    """v7 (research/PROTOCOL_v7.md): v6's sizing on the funeral book with a premium choice, the balance sheet with
    default risk and the sovereign reverse stress, the review and lapse variants, the checks, v6 beside it, the book, v4's
    projection on v7's book with the cover 1.0 level, the central path against v6's, and the empty-match record."""
    f = OUT / "balance_v7.json"
    if not f.exists():
        return None
    x = json.loads(f.read_text())
    sheet = lambda r: {k: r[k] for k in ("bel", "risk_margin", "scr_life", "market", "scr", "cover", "own_funds", "life",
                                         "interest")} | {"op": r["op"]["charge"] if isinstance(r["op"], dict) else r["op"]}
    m = x["main"]
    match = m["assets"]["matching"]["book"]
    held = holdings_v6(match["units"])
    worth = sum(v for h in held.values() for v in h.values())
    if abs(worth / m["assets"]["matched"] - 1) > 1e-8:
        raise SystemExit(f"holdings priced at {worth:,.0f}, not the matched {m['assets']['matched']:,.0f}")
    c = m["credit"]
    cover = lambda r: {k: r[k] for k in ("cover", "scr", "bel") if k in r}
    return {"protocol": x["protocol"]["v7"], "protocol_v6": x["protocol"]["v6"], "valuation_date": x["valuation_date"],
            **{k: x[k] for k in ("exposures", "mix", "scales", "policies", "trend")},
            "main": sheet(m) | {"bscr": m["bscr"], "diversification": m["diversification"], "bel_parts": m["bel_parts"],
                                "bel_by_type": m["bel_funeral_by_type"], "lapse": m["lapse"], "rate_losses": m["rate_losses"],
                                "risk_margin_parts": m["risk_margin_parts"],
                                "assets": {k: m["assets"][k] for k in ("total", "bill", "matched", "credit")},
                                "holdings": held, "dv01": {"liability": match["liability"]["dv01"], "portfolio": match["portfolio_dv01"]},
                                "credit": {k: c[k] for k in ("receivable", "cash", "outgo", "step", "factor", "type2", "type3", "default", "A")}
                                | {"by_step": {s: v["cover"] for s, v in c["by_step"].items()}},
                                "sovereign": m["sovereign"]},
            "review": {k: x["review"][k] for k in ("cover", "scr", "life")},
            "lapse_spike": {k: cover(v) for k, v in x["lapse_spike"].items()},
            "without_default": cover(x["without_default"]),
            "checks": {k: {"pass": v["pass"]} for k, v in x["checks"].items()},
            "v6": {"scales": x["v6"]["scales"], "policies": x["v6"]["policies"], "mix": x["v6"]["mix"],
                   **{k: x["v6"]["main"][k] for k in ("bel", "scr", "cover") if k in x["v6"]["main"]}},
            "book": book_v7(x["scales"]),
            "projection": v4("projection_v7.json", "capital_v7.json", "v7"),
            "central_compare": central_compare(), "empty_match": empty_match_v7()}


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
    ap.add_argument("--only-v6", action="store_true", help="add v6 to the existing data/research.json, refitting nothing")
    ap.add_argument("--only-v7", action="store_true", help="add v7 to the existing data/research.json, refitting nothing")
    a = ap.parse_args()
    frozen = require_frozen()
    if a.only_v6 or a.only_v7:
        path = data.ROOT / "data" / "research.json"
        out = json.loads(path.read_text())
        key, make = ("v6", v6) if a.only_v6 else ("v7", v7)
        out[key] = make()
        path.write_text(json.dumps(out, default=float))
        print(f"added {key} to data/research.json")
        return
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
    if (b := v6()) is not None:
        out["v6"] = b
    if (b := v7()) is not None:
        out["v7"] = b
    (data.ROOT / "data" / "research.json").write_text(json.dumps(out, default=float))
    print("wrote data/research.json")


if __name__ == "__main__":
    main()
