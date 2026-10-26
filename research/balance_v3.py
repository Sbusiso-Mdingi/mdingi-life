"""v3 balance sheet on the SAM standard formula (PROTOCOL_v3.md): BEL, matching assets, the SCR by risk, the risk
margin and the cover ratio, with the protocol's sensitivities and checks.

    python -m research.balance_v3 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Needs research.book_v3 to have been run. Writes research/results/balance_v3.json. Refuses to run until the v1, v2
and v3 protocols are frozen.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from mdingilife import annuity, curves as c, data, sam
from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, require_frozen
from research import curves as rc
from research.annuities import simulate
from research.annuities_v2 import bond_value, risk
from research.backtest import OUT, SEED
from research.book_v3 import BOOK, EXPENSE, TABLE, lapse_rate, mu_rows
from research.treasury import ILB

YEARS = 103            # age 18 to 120
CURVE_YEARS = 110
OWN_FUNDS = 400e6
BILL = 0.5             # the 182-day bill, in years
ANNUITANT_ADJ = 0.7
INDUSTRY_COVER = 1.8   # SARB FSR 2026, Table B.2, median for life insurers in 2025


@dataclass(frozen=True)
class Scenario:
    nominal: str | None = None   # "up" or "down"
    real: str | None = None
    longevity: bool = False
    mortality: float = 1.0
    lapse: float = 1.0
    mass: float = 0.0
    expense: float = 1.0
    inflation: bool = False
    cat: bool = False


BASE = Scenario()
LIFE_STRESSES = {
    "mortality": Scenario(mortality=1 + sam.MORTALITY_UP),
    "longevity": Scenario(longevity=True),
    "lapse up": Scenario(lapse=1 + sam.LAPSE_LEVEL),
    "lapse down": Scenario(lapse=1 - sam.LAPSE_LEVEL),
    "mass lapse": Scenario(mass=sam.MASS_LAPSE),
    "expense": Scenario(expense=1 + sam.EXPENSE_LEVEL, inflation=True),
    "catastrophe": Scenario(cat=True),
}
RATE_STRESSES = {f"{k} {d}": Scenario(**{k: d}) for k in ("nominal", "real") for d in ("up", "down")}


@dataclass(frozen=True)
class Basis:
    curve: str = "LI"
    annuitant_adj: float = ANNUITANT_ADJ
    funeral_adj: float = 1.0


# --- mortality -----------------------------------------------------------------------------------------------------

def annuitant_grids(deaths: str, population: str) -> dict:
    """v1's production fit on the Stats SA run, simulated with v1's seed: median log rates by age and calendar year,
    with the first forecast year that is 2026."""
    bt = json.loads((OUT / "backtest_statssa.json").read_text())
    panels = data.load("statssa", deaths=deaths, population=population)
    rng = np.random.default_rng(SEED + 2)
    out = {}
    for s, r in panels.items():
        model = bt["tests"]["chosen"][s]
        full, ages, start, jump = simulate(r, model, model.split(maxsplit=1)[1], rng)
        out[s] = {"log_m": np.median(full, axis=0), "ages": ages, "start": start, "model": model, "jump_off": jump}
        del full
    return out


def longevity_grid(log_m: np.ndarray, start: int) -> np.ndarray:
    """FSI 4.2 §6.3: rates times 0.9, and each future year's improvement rate up by 1 point, from the year after
    `start`."""
    m = np.exp(log_m)
    ratio = m[:, 1:] / m[:, :-1]                      # 1 - improvement
    step = (ratio - sam.LONGEVITY_TREND) / ratio
    cum = np.ones_like(m)
    cum[:, start + 1:] = np.cumprod(step[:, start:], axis=1)
    return np.log((1 - sam.LONGEVITY_LEVEL) * m * cum)


def annuitant_rows(grids: dict, sex, age, adj: float, longevity: bool) -> np.ndarray:
    out = np.full((len(age), YEARS), 1e3)
    for s, g in grids.items():
        lm = longevity_grid(g["log_m"], g["start"]) if longevity else g["log_m"]
        for i in np.flatnonzero(np.asarray(sex) == s):
            m = annuity.cohort(lm, g["ages"], int(age[i]), g["start"])
            out[i, :len(m)] = adj * m
    return out


# --- the book on a basis -------------------------------------------------------------------------------------------

class Book:
    def __init__(self, grids: dict, table: pd.DataFrame, basis: Basis):
        ann = pd.read_csv(BOOK / "annuities.csv")
        fun = pd.read_csv(BOOK / "funeral.csv")
        ann["new"] = ann["years_since_purchase"] == 0
        self.ann = ann.groupby(["sex", "age", "type", "new"], as_index=False).agg(
            income=("income", "sum"), count=("id", "size"))
        self.fun = fun.groupby(["sex", "age", "years_in_force"], as_index=False).agg(
            sum_assured=("sum_assured", "sum"), premium=("premium", "sum"), count=("id", "size"))
        self.n_ann, self.n_fun = len(ann), len(fun)
        self.basis = basis
        a, f = self.ann, self.fun
        self.mu_ann = {lv: annuitant_rows(grids, a["sex"], a["age"].to_numpy(), basis.annuitant_adj, lv)
                       for lv in (False, True)}
        self.mu_fun = mu_rows(table, f["sex"].to_numpy(), f["age"].to_numpy(), YEARS, basis.funeral_adj)
        policy_year = f["years_in_force"].to_numpy()[:, None] + 1 + np.arange(YEARS)
        self.lapse = lapse_rate(policy_year)
        self.ilb = (a["type"] == "inflation-linked").to_numpy()
        self.t = np.arange(12 * YEARS) / 12


class Curves:
    def __init__(self, fwd_nominal, fwd_real):
        self.fwd = {"nominal": np.asarray(fwd_nominal), "real": np.asarray(fwd_real)}

    def get(self, sc: Scenario):
        return sam.Curve(self.fwd["nominal"], "nominal", sc.nominal), sam.Curve(self.fwd["real"], "real", sc.real)


def liabilities(b: Book, cv: Curves, sc: Scenario, e: float | None = None) -> dict:
    """BEL per cell, by part, under a scenario. `e` overrides the expense inflation before any stress to it."""
    nom, real = cv.get(sc)
    e = sam.breakeven(nom, real) if e is None else e
    if sc.inflation:
        e += max(sam.INFLATION_ADD, sam.INFLATION_REL * e)
    t = b.t
    v_nom, v_real, v_mid = nom.df(t), real.df(t), nom.df(t + 1 / 24)
    exp_index = sc.expense * (1 + e) ** t / 12

    inf_a, _ = sam.project(b.mu_ann[sc.longevity])
    income = b.ann["income"].to_numpy() / 12 * np.where(b.ilb, inf_a @ v_real, inf_a @ v_nom)
    exp_a = b.ann["count"].to_numpy() * EXPENSE["annuity"] * (inf_a @ (exp_index * v_nom))

    lapse = np.minimum(b.lapse * sc.lapse, 1.0)
    inf_f, deaths = sam.project(b.mu_fun * sc.mortality, lapse, mass=sc.mass, cat=sc.cat)
    f = b.fun
    claims = f["sum_assured"].to_numpy() * (deaths @ v_mid)
    premiums = f["premium"].to_numpy() * (inf_f @ v_nom)
    exp_f = f["count"].to_numpy() * EXPENSE["funeral"] * (inf_f @ (exp_index * v_nom))
    if sc.mass:
        first = t < 1  # §8.5: the lapsed policies' expenses are still paid for a year
        exp_f += f["count"].to_numpy() * EXPENSE["funeral"] * sc.mass * np.sum((exp_index * v_nom)[first])
    return {"income": income, "ann_expenses": exp_a, "claims": claims, "premiums": premiums,
            "fun_expenses": exp_f, "inflation": e}


def totals(L: dict) -> dict:
    ann = L["income"].sum() + L["ann_expenses"].sum()
    fun = L["claims"].sum() + L["fun_expenses"].sum() - L["premiums"].sum()
    return {"annuities": ann, "funeral": fun, "total": ann + fun}


# --- assets ---------------------------------------------------------------------------------------------------------

def bond_book(bonds: dict, settle, kind: str) -> dict:
    out = {}
    for code, bd in bonds.items():
        is_ilb = code[0] == "I" or code in ILB
        if is_ilb == (kind == "real") and max(d for d, _ in bd.redemptions) > settle:
            t, cf = bd.cashflows(settle)
            if t[-1] >= c.FLOOR:
                out[code] = (t, cf)
    return out


def match(b: Book, cv: Curves, bonds: dict, settle, method: str = "duration") -> dict:
    """For each annuity type, bonds of its kind held to match the income's value on the unshocked curve, and either
    its duration with the two bonds whose effective durations bracket it (v2's method), or its key-rate DV01s as
    nearly as non-negative holdings in every bond of the kind allow (amendment of 26 October 2026)."""
    out = {}
    for kind, sel in (("real", b.ilb), ("nominal", ~b.ilb)):
        inf, _ = sam.project(b.mu_ann[False][sel])
        w = b.ann["income"].to_numpy()[sel] / 12 @ inf
        fwd = cv.fwd[kind]
        liab = risk(lambda f: float(w @ sam.Curve(f).df(b.t)), fwd)
        book = {k: risk(lambda f, t=t, cf=cf: bond_value(t, cf, f), fwd) for k, (t, cf) in bond_book(bonds, settle, kind).items()}
        if method == "key":
            units = key_rate_units(liab, book)
        else:
            below = max((k for k in book if book[k]["duration"] <= liab["duration"]), key=lambda k: book[k]["duration"])
            above = min((k for k in book if book[k]["duration"] > liab["duration"]), key=lambda k: book[k]["duration"])
            (p1, d1), (p2, d2) = [(book[k]["value"], book[k]["duration"]) for k in (below, above)]
            w2 = (liab["duration"] - d1) / (d2 - d1)
            units = {below: liab["value"] * (1 - w2) / p1, above: liab["value"] * w2 / p2}
        out[kind] = {"liability": liab, "bonds": {k: book[k] for k in units}, "units": units}
    return out


def key_rate_units(liab: dict, book: dict, weight: float = 1e3) -> dict:
    """Non-negative holdings that match the value (a row weighted by `weight`) and come nearest the key-rate DV01s,
    each row scaled to the liability's; then scaled to the value exactly. Bonds held at zero are dropped."""
    codes = sorted(book)
    keys = list(liab["dv01"])
    total = sum(liab["dv01"].values())
    A = np.array([[book[c]["dv01"][k] / total for c in codes] for k in keys]
                 + [[weight * book[c]["value"] / liab["value"] for c in codes]])
    y = np.array([liab["dv01"][k] / total for k in keys] + [weight])
    n, _ = nnls(A, y)
    n *= liab["value"] / sum(n[i] * book[c]["value"] for i, c in enumerate(codes))
    return {c: float(n[i]) for i, c in enumerate(codes) if n[i] > 0}


def asset_value(holdings: dict, cashflows: dict, bill: float, cv: Curves, sc: Scenario) -> float:
    nom, real = cv.get(sc)
    v = bill * float(nom.df(BILL))
    for kind, curve in (("nominal", nom), ("real", real)):
        for code, n in holdings.get(kind, {}).items():
            t, cf = cashflows[code]
            v += n * float(np.sum(cf * curve.df(t)))
    return v


# --- the SCR --------------------------------------------------------------------------------------------------------

def run(grids: dict, table: pd.DataFrame, basis: Basis, curves: dict, bonds: dict, settle, matched: bool = True,
        method: str = "duration", book: Book | None = None, assets: float | None = None,
        holdings: dict | None = None, scale: float = 1.0) -> dict:
    """v3's balance sheet and SCR. v4 passes an aged `book`, the `assets` carried forward (own funds are what is
    left after BEL and risk margin; by default they are R400 million) and, to hold a portfolio without rematching,
    the bond `holdings` by kind. `scale` multiplies the matched holdings (v4's starting-capital levels)."""
    b = book or Book(grids, table, basis)
    cv = Curves(curves[basis.curve]["nominal"], curves[basis.curve]["real"])
    L0 = liabilities(b, cv, BASE)
    bel = totals(L0)
    if holdings is None:
        m = match(b, cv, bonds, settle, method) if matched else {}
        holdings = {k: {code: n * scale for code, n in v["units"].items()} for k, v in m.items()}
        cashflows = {**bond_book(bonds, settle, "real"), **bond_book(bonds, settle, "nominal")}
    else:
        m = {}
        cashflows = {code: bonds[code].cashflows(settle) for units in holdings.values() for code in units}
    matched_value = asset_value(holdings, cashflows, 0.0, cv, BASE)

    life = {}
    losses = {}
    for name, sc in LIFE_STRESSES.items():
        T = totals(liabilities(b, cv, sc))
        losses[name] = {k: T[k] - bel[k] for k in T}
    up, down = losses["lapse up"]["funeral"], losses["lapse down"]["funeral"]
    level = max(up, 0) if max(up, 0) >= max(down, 0) else max(down, 0)
    mass = max(losses["mass lapse"]["funeral"], 0) if bel["funeral"] < 0 else 0.0
    combined = np.hypot(mass, level * (1 - 0.5 * sam.MASS_LAPSE)) if mass > 0 else level
    lapse = max(mass, level, combined)
    life["mortality"] = max(losses["mortality"]["funeral"], 0)
    life["longevity"] = max(losses["longevity"]["annuities"], 0)
    life["lapse"] = lapse
    life["expense"] = max(losses["expense"]["total"], 0)
    life["catastrophe"] = max(losses["catastrophe"]["funeral"], 0)
    vec = [life[k] for k in sam.LIFE]
    scr_life = sam.aggregate(vec, sam.CORR_LIFE)
    alone = {"annuities": sam.aggregate([0, life["longevity"], 0, max(losses["expense"]["annuities"], 0), 0], sam.CORR_LIFE),
             "funeral": sam.aggregate([life["mortality"], 0, lapse, max(losses["expense"]["funeral"], 0),
                                       life["catastrophe"]], sam.CORR_LIFE)}

    earned = 12 * b.fun["premium"].sum() + (L0["income"] + L0["ann_expenses"])[b.ann["new"].to_numpy()].sum()
    op_base = max(sam.OP_PREMIUMS * earned, sam.OP_PROVISIONS * max(bel["total"], 0))

    # Risk margin (FSI 2.2 §14): the reference insurer's life and operational SCR, run off with the book.
    scr_ru0 = scr_life + min(sam.OP_CAP * scr_life, op_base)
    w = alone["annuities"] / (alone["annuities"] + alone["funeral"])
    nom, real = cv.get(BASE)
    run_off = runoff(b, nom, real)
    years = np.arange(YEARS)
    scr_ru = scr_ru0 * (w * run_off["annuities"] / run_off["annuities"][0] + (1 - w) * run_off["sum_assured"] / run_off["sum_assured"][0])
    rm = sam.COC * float(np.sum(scr_ru * nom.df(years + 1)))
    rm_annuities = sam.COC * scr_ru0 * w * float(np.sum(run_off["annuities"] / run_off["annuities"][0] * nom.df(years + 1)))

    # Assets: the matched bonds, and the bill for the rest (BEL + risk margin + own funds).
    total_assets = bel["total"] + rm + OWN_FUNDS if assets is None else assets
    own_funds = total_assets - bel["total"] - rm
    bill = (total_assets - matched_value) / float(nom.df(BILL))
    bof0 = asset_value(holdings, cashflows, bill, cv, BASE) - bel["total"]
    rate = {}
    for name, sc in RATE_STRESSES.items():
        bof = asset_value(holdings, cashflows, bill, cv, sc) - totals(liabilities(b, cv, sc))["total"]
        rate[name] = bof0 - bof
    nominal = max(rate["nominal up"], rate["nominal down"], 0)
    real_ = max(rate["real up"], rate["real down"], 0)
    market = sam.pair(nominal, real_, sam.CORR_NOMINAL_REAL)
    bscr = sam.pair(market, scr_life, sam.CORR_MARKET_LIFE)
    op = min(sam.OP_CAP * bscr, op_base)
    scr = bscr + op
    return {
        "basis": basis.__dict__, "matched": matched, "method": method if matched else None, "policies": {"annuities": b.n_ann, "funeral": b.n_fun},
        "inflation": L0["inflation"],
        "bel": bel, "bel_parts": {k: float(np.sum(v)) for k, v in L0.items() if k != "inflation"},
        "life_losses": losses, "life": life, "life_alone": alone, "scr_life": scr_life,
        "lapse": {"up": up, "down": down, "level": level, "mass": mass, "combined": combined},
        "rate_losses": rate, "interest": {"nominal": nominal, "real": real_, "combined": market},
        "market": market, "bscr": bscr, "diversification": nominal + real_ + sum(vec) - bscr,
        "op": {"earned_premiums": earned, "premiums": sam.OP_PREMIUMS * earned,
               "provisions": sam.OP_PROVISIONS * max(bel["total"], 0), "charge": op},
        "scr": scr, "risk_margin": rm, "risk_margin_parts": {"annuities": rm_annuities, "funeral": rm - rm_annuities}, "scr_ru": {"t0": scr_ru0, "annuity_weight": w, "by_year": list(scr_ru[:60])},
        "assets": {"total": total_assets, "bill": bill * float(nom.df(BILL)), "matched": matched_value,
                   "matching": {k: {"liability": v["liability"], "units": v["units"],
                                    "bonds": {code: bd for code, bd in v["bonds"].items()}} for k, v in m.items()},
                   "holdings": holdings},
        "own_funds": own_funds, "cover": own_funds / scr,
        "capital_for": {"1.0": scr, str(INDUSTRY_COVER): INDUSTRY_COVER * scr},
    }


def runoff(b: Book, nom: sam.Curve, real: sam.Curve) -> dict:
    """Each whole year ahead: the annuities' BEL then, and the funeral sum assured expected in force."""
    inf_a, _ = sam.project(b.mu_ann[False])
    e = sam.breakeven(nom, real)
    t = b.t
    v_nom, v_real = nom.df(t), real.df(t)
    inc = b.ann["income"].to_numpy()[:, None] / 12 * inf_a
    cf_real = inc[b.ilb].sum(0)
    cf_nom = inc[~b.ilb].sum(0) + (b.ann["count"].to_numpy()[:, None] * EXPENSE["annuity"] / 12 * (1 + e) ** t * inf_a).sum(0)
    pv_real, pv_nom = np.cumsum((cf_real * v_real)[::-1])[::-1], np.cumsum((cf_nom * v_nom)[::-1])[::-1]
    k = 12 * np.arange(YEARS)
    ann = pv_real[k] / v_real[k] + pv_nom[k] / v_nom[k]
    inf_f, _ = sam.project(b.mu_fun, b.lapse)
    sa = b.fun["sum_assured"].to_numpy() @ inf_f[:, k]
    return {"annuities": ann, "sum_assured": sa}


# --- K1: a plain loop over months for one policy of each line -------------------------------------------------------

def loop_annuity(mu, income, count, ilb, nom, real, sc) -> float:
    e = sam.breakeven(nom, real)
    if sc.inflation:
        e += max(sam.INFLATION_ADD, sam.INFLATION_REL * e)
    alive, v = 1.0, 0.0
    for k in range(12 * len(mu)):
        t = k / 12
        pay = income / 12 * float((real if ilb else nom).df(t))
        cost = count * EXPENSE["annuity"] * sc.expense / 12 * (1 + e) ** t * float(nom.df(t))
        v += alive * (pay + cost)
        alive *= np.exp(-mu[k // 12] / 12)
    return v


def loop_funeral(mu, lapse, sum_assured, premium, count, nom, real, sc) -> float:
    e = sam.breakeven(nom, real)
    if sc.inflation:
        e += max(sam.INFLATION_ADD, sam.INFLATION_REL * e)
    alive, v = 1.0 - sc.mass, 0.0
    for k in range(12 * len(mu)):
        t = k / 12
        q = 1 - np.exp(-mu[k // 12] * sc.mortality / 12)
        if sc.cat and k < 3:
            q = min(q + float(sam.cat_addition(q)), 1.0)
        cost = count * EXPENSE["funeral"] * sc.expense / 12 * (1 + e) ** t * float(nom.df(t))
        v += alive * (cost - premium * float(nom.df(t))) + alive * q * sum_assured * float(nom.df(t + 1 / 24))
        if sc.mass and k < 12:
            v += sc.mass * cost
        alive *= (1 - q) * (1 - min(lapse[k // 12] * sc.lapse, 1.0)) ** (1 / 12)
    return v


def check_k1(grids, table, curves) -> dict:
    b = Book(grids, table, Basis())
    cv = Curves(curves["LI"]["nominal"], curves["LI"]["real"])
    ia = int(np.argmax(b.ann["count"].to_numpy()))
    jf = int(np.argmax(b.fun["count"].to_numpy()))
    worst = 0.0
    rows = {}
    for name, sc in {"base": BASE, **LIFE_STRESSES, **RATE_STRESSES}.items():
        L = liabilities(b, cv, sc)
        nom, real = cv.get(sc)
        a = b.ann.iloc[ia]
        f = b.fun.iloc[jf]
        la = loop_annuity(b.mu_ann[sc.longevity][ia], a["income"], a["count"], bool(b.ilb[ia]), nom, real, sc)
        lf = loop_funeral(b.mu_fun[jf], b.lapse[jf], f["sum_assured"], f["premium"], f["count"], nom, real, sc)
        ea = L["income"][ia] + L["ann_expenses"][ia]
        ef = L["claims"][jf] + L["fun_expenses"][jf] - L["premiums"][jf]
        rel = max(abs(la - ea) / abs(ea), abs(lf - ef) / abs(ef))
        rows[name] = {"annuity": [la, ea], "funeral": [lf, ef], "relative": rel}
        worst = max(worst, rel)
    return {"cells": {"annuity": b.ann.iloc[ia][["sex", "age", "type"]].to_dict(),
                      "funeral": b.fun.iloc[jf][["sex", "age", "years_in_force"]].to_dict()},
            "scenarios": rows, "worst_relative": worst, "pass": bool(worst < 1e-8)}


def auctions(bonds: dict) -> pd.DataFrame:
    """v2's auctions after its screen."""
    a, _ = rc.load(bonds)
    return a[~rc.screen(a)]


def market(a: pd.DataFrame | None = None) -> tuple[dict, dict, dict, object]:
    """v2's curves on the valuation date (LI and NS, both kinds), the bonds, the auction days and the settlement date."""
    bonds = rc.book()
    a = auctions(bonds) if a is None else a
    ilb_day = a.loc[a["kind"] == "ilb", "auction_date"].max()
    days = {"real": ("ilb", ilb_day),
            "nominal": ("fixed", a.loc[(a["kind"] == "fixed") & (a["auction_date"] <= ilb_day), "auction_date"].max())}
    curves = {"LI": {}, "NS": {}}
    for k, (kind, d) in days.items():
        pts = rc.window(a[a["kind"] == kind], d, rc.WINDOW, inclusive=True)
        last = max(q.maturity for q in pts)
        curves["LI"][k] = c.forwards(c.Bootstrap.fit(pts), last, CURVE_YEARS)
        curves["NS"][k] = c.forwards(rc.fit("NS", pts), last, CURVE_YEARS)
    return curves, bonds, days, (ilb_day + timedelta(days=3)).date()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3)}
    if not (BOOK / "funeral.csv").exists():
        raise SystemExit("run python -m research.book_v3 first")
    curves, bond_codes, days, settle = market()
    ilb_day = days["real"][1]

    grids = annuitant_grids(args.deaths, args.population)
    table = pd.read_csv(TABLE)
    out = {"protocol": frozen, "valuation_date": str(ilb_day.date()),
           "curve_dates": {k: str(d.date()) for k, (_, d) in days.items()},
           "mortality": {s: {"model": g["model"], "jump_off": g["jump_off"]} for s, g in grids.items()}}
    out["main"] = run(grids, table, Basis(), curves, bond_codes, settle)
    out["unmatched"] = run(grids, table, Basis(), curves, bond_codes, settle, matched=False)
    out["sensitivities"] = {
        "funeral 0.8": run(grids, table, Basis(funeral_adj=0.8), curves, bond_codes, settle),
        "funeral 1.2": run(grids, table, Basis(funeral_adj=1.2), curves, bond_codes, settle),
        "annuitant 0.6": run(grids, table, Basis(annuitant_adj=0.6), curves, bond_codes, settle),
        "annuitant 0.8": run(grids, table, Basis(annuitant_adj=0.8), curves, bond_codes, settle),
        "NS curves": run(grids, table, Basis(curve="NS"), curves, bond_codes, settle),
    }
    main_ = out["main"]
    k1 = check_k1(grids, table, curves)
    k3 = main_["interest"]["combined"] / out["unmatched"]["interest"]["combined"]
    out["checks"] = {
        "K1": k1,
        "K3": {"matched": main_["interest"]["combined"], "unmatched": out["unmatched"]["interest"]["combined"],
               "ratio": k3, "pass": bool(k3 < 0.25)},
        "K4": {"largest": max(main_["life"], key=main_["life"].get),
               "pass": max(main_["life"], key=main_["life"].get) == "longevity"},
        "K5": {"cover": main_["cover"], "industry_median": INDUSTRY_COVER},
    }
    out["curves"] = {k: {kk: list(vv[:45]) for kk, vv in v.items()} for k, v in curves.items()}
    (OUT / "balance_v3.json").write_text(json.dumps(out, indent=1, default=float))
    m = main_
    print(f"BEL {m['bel']}  RM {m['risk_margin']:,.0f}  SCR {m['scr']:,.0f}  cover {m['cover']:.2f}")
    print("life", {k: round(v / 1e6, 1) for k, v in m["life"].items()}, "interest", {k: round(v / 1e6, 1) for k, v in m["interest"].items()})
    print("checks", {k: v.get("pass") for k, v in out["checks"].items()}, "K1 worst", k1["worst_relative"], "K3", k3)
    for k, s in out["sensitivities"].items():
        print(k, f"SCR {s['scr'] / 1e6:,.1f}m cover {s['cover']:.2f}")


if __name__ == "__main__":
    main()
