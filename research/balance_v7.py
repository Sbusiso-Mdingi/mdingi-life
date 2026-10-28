"""v7 balance sheet (research/PROTOCOL_v7.md): v6's, on v7's funeral book (a level or an age-rated premium, the
benefit fixed), with lapses by premium type, SAM default risk on the premiums held by collectors and the cash at a
bank (FSI 4.1 §9), and a sovereign reverse stress outside SAM. The book's size and mix by v6's two rules.

    python -m research.balance_v7 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv [--grids-cache PATH]

Needs research.book_v7 --write. Writes research/results/balance_v7.json. Refuses to run until the v1 to v3 and v5 to v7
protocols are frozen. With --grids-cache, as research.mix_v6.

With no rising benefit, v5's inflation model, its hedge and its volatility charge have nothing to act on, so they are
left out; the annuities are v3's.
"""
from __future__ import annotations

import argparse
import copy
import json

import numpy as np
import pandas as pd

from mdingilife import sam
from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V5, PROTOCOL_V6, PROTOCOL_V7, require_frozen
from research import balance_v3 as b3
from research import balance_v5 as b5
from research import book_v5 as bk5
from research import book_v7 as bk
from research import mix_v6 as mx
from research.annuities_v2 import KEYS, bump, tent
from research.backtest import OUT
from research.balance_v3 import (BASE, BILL, INDUSTRY_COVER, LIFE_STRESSES, OWN_FUNDS, RATE_STRESSES, YEARS, Basis,
                                 Curves, annuitant_rows, asset_value, bond_book, totals)
from research.book_v3 import BOOK, EXPENSE, lapse_rate

RESULT = OUT / "balance_v7.json"
MONTHS = 12 * YEARS
SPIKE = 0.10                            # the extra lapse in an age-rated policy's review year
SPIKES = (0.0, 0.20)                    # the sensitivity
REVIEW = 5                              # a review on every fifth anniversary
RECEIVABLE_MONTHS = 1                   # premiums held by collectors, type 2 (§9.7 a)
CASH_MONTHS = 3                         # cash at a bank, type 3 (§9.8), of the first year's expected outgo
TYPE2 = 0.15                            # §9.26, none past due
STEP = 12                               # the bank's credit quality step, a stated judgement
FACTORS = {1: 0.0010, 2: 0.0019, 3: 0.0027, 4: 0.0049, 5: 0.0068, 6: 0.0080, 7: 0.0108, 8: 0.0137, 9: 0.0206,
           10: 0.0256, 11: 0.0327, 12: 0.0435, 13: 0.0568, 14: 0.0796, 15: 0.1010, 16: 0.1447, 17: 0.1538,
           18: 0.1586}                  # §9.28, type 3 by credit quality step
PD_STEP = {12: 0.0139}                  # §9.18, the step used
STRESSED = 1 + sam.MORTALITY_UP         # the review variant prices on this times the force


def review_year(policy_year) -> np.ndarray:
    """Policy years (from 1) that start at a review: 6, 11, 16 and so on."""
    py = np.asarray(policy_year)
    return (py > 1) & ((py - 1) % REVIEW == 0)


def lapse_rows(years_in_force, rated, spike: float = SPIKE, years: int = YEARS) -> np.ndarray:
    """(cells, years): v3's rate by policy year, plus `spike` in an age-rated cell's review years, at most 1."""
    py = np.asarray(years_in_force)[:, None] + 1 + np.arange(years)
    extra = spike * (np.asarray(rated, bool)[:, None] & review_year(py))
    return np.minimum(lapse_rate(py) + extra, 1.0)


class Book(b3.Book):
    """v3's annuities with v7's funeral cells (sex, age, years in force, premium type): rates along v5's cohort, each
    cell's total monthly premium by projection year in `prem`, lapses by premium type."""

    KEYS = ["sex", "age", "years_in_force", "premium_type"]

    def __init__(self, grids: dict, fgrid: dict, basis: Basis, spike: float = SPIKE,
                 funeral: pd.DataFrame | None = None, sched: pd.DataFrame | None = None):
        ann = pd.read_csv(BOOK / "annuities.csv")
        fun = pd.read_csv(bk.FUNERAL) if funeral is None else funeral
        sched = pd.read_csv(bk.SCHEDULE) if sched is None else sched
        ann["new"] = ann["years_since_purchase"] == 0
        self.ann = ann.groupby(["sex", "age", "type", "new"], as_index=False).agg(
            income=("income", "sum"), count=("id", "size"))
        self.fun = fun.groupby(self.KEYS, as_index=False).agg(
            sum_assured=("sum_assured", "sum"), premium=("premium", "sum"), count=("id", "size"))
        self.cell = fun.groupby(self.KEYS).ngroup().to_numpy()
        self.policies, self.sched, self.fgrid, self.fun_scale = fun, sched, fgrid, 1.0
        self.prem = self.cell_sum(bk.rows(sched, fun, YEARS))
        self.n_ann, self.n_fun = len(ann), len(fun)
        self.basis, self.spike = basis, spike
        a, f = self.ann, self.fun
        self.mu_ann = {lv: annuitant_rows(grids, a["sex"], a["age"].to_numpy(), basis.annuitant_adj, lv)
                       for lv in (False, True)}
        self.mu_fun = bk5.mu_rows(fgrid, f["sex"].to_numpy(), f["age"].to_numpy(), YEARS, basis.funeral_adj)
        self.rated = (f["premium_type"] == "age-rated").to_numpy()
        self.lapse = lapse_rows(f["years_in_force"].to_numpy(), self.rated, spike)
        self.ilb = (a["type"] == "inflation-linked").to_numpy()
        self.t = np.arange(MONTHS) / 12

    def cell_sum(self, x: np.ndarray) -> np.ndarray:
        out = np.zeros((len(self.fun), x.shape[1]))
        np.add.at(out, self.cell, x)
        return out

    def review_prem(self) -> np.ndarray:
        """The review variant's premium rows: each age-rated policy's schedule repriced on STRESSED times the force
        from its next review after the valuation date (projection year k >= 1 with n + k a multiple of REVIEW), its
        own schedule before it."""
        fun = self.policies
        n = fun["years_in_force"].to_numpy()
        start = 1 + (-(n + 1)) % REVIEW
        stressed = bk.rows(bk.schedule(self.fgrid, STRESSED), fun, YEARS, start)
        rows = np.where(np.isnan(stressed), bk.rows(self.sched, fun, YEARS), stressed)
        return self.cell_sum(rows) * self.fun_scale


def scaled(b: Book, ann: float = 1.0, fun: float = 1.0) -> Book:
    """v6's scaling (research.mix_v6.scaled) of v7's book, the premium rows with the funeral line."""
    out = copy.copy(b)
    out.ann = b.ann.assign(income=b.ann["income"] * ann, count=b.ann["count"] * ann)
    out.fun = b.fun.assign(sum_assured=b.fun["sum_assured"] * fun, premium=b.fun["premium"] * fun,
                           count=b.fun["count"] * fun)
    out.prem, out.fun_scale = b.prem * fun, b.fun_scale * fun
    out.n_ann, out.n_fun = b.n_ann * ann, b.n_fun * fun
    return out


def with_prem(b: Book, prem: np.ndarray) -> Book:
    out = copy.copy(b)
    out.prem = prem
    return out


def liabilities(b: Book, cv: Curves, sc, e: float | None = None) -> dict:
    """v3's BEL per cell, by part, the premiums from each cell's rows (research.balance_v3.liabilities)."""
    return b3.liabilities(b, cv, sc, e)


def by_type(b: Book, L: dict) -> dict:
    fun = L["claims"] + L["fun_expenses"] - L["premiums"]
    return {"level": float(fun[~b.rated].sum()), "age-rated": float(fun[b.rated].sum())}


# --- v6's two rules on v7's book (research.mix_v6, on these liabilities) ----------------------------------------------

def moved(b: Book, factor) -> Book:
    out = copy.copy(b)
    f = np.broadcast_to(np.asarray(factor, float), (YEARS,))
    out.mu_ann = {lv: m * f for lv, m in b.mu_ann.items()}
    out.mu_fun = b.mu_fun * f
    return out


def bel(b: Book, cv: Curves) -> dict:
    return totals(liabilities(b, cv, BASE))


def exposures(b: Book, cv: Curves, h: float = mx.STEP) -> dict:
    up, dn = bel(moved(b, 1 + h), cv), bel(moved(b, 1 - h), cv)
    return {k: (up[k] - dn[k]) / (2 * h) for k in ("annuities", "funeral", "total")}


def trend(b: Book, cv: Curves, faster: float = mx.FASTER) -> dict:
    base, fast = bel(b, cv), bel(moved(b, (1 - faster) ** np.arange(YEARS)), cv)
    return {k: fast[k] - base[k] for k in ("annuities", "funeral", "total")}


def book_risk(b: Book, cv: Curves) -> dict:
    value = lambda fn, fr: bel(b, Curves(fn, fr))["total"]
    fn, fr = cv.fwd["nominal"], cv.fwd["real"]
    v = value(fn, fr)
    dv = {("nominal", k): v - value(bump(fn, tent(k)), fr) for k in KEYS}
    dv |= {("real", k): v - value(fn, bump(fr, tent(k))) for k in KEYS}
    return {"value": v, "dv01": dv}


def match_book(b: Book, cv: Curves, bonds: dict, settle) -> dict:
    return b5.key_rate_units(book_risk(b, cv), cv, bonds, settle)


# --- credit ------------------------------------------------------------------------------------------------------------

def credit_exposures(b: Book, cv: Curves) -> dict:
    """At par: one month of the funeral premiums in force (type 2), and three months of the first projection year's
    expected outgo, nominal and undiscounted (type 3): annuity payments, inflation-linked ones indexed at the
    breakeven, funeral claims, and expenses rising at the breakeven, as in the valuation."""
    nom, real = cv.get(BASE)
    e = sam.breakeven(nom, real)
    t = b.t[:12]
    grow = (1 + e) ** t
    inf_a, _ = sam.project(b.mu_ann[False][:, :1])
    inf_f, deaths = sam.project(b.mu_fun[:, :1], b.lapse[:, :1])
    inc = b.ann["income"].to_numpy() / 12
    income = float(inc[b.ilb] @ (inf_a[b.ilb] @ grow) + inc[~b.ilb] @ inf_a[~b.ilb].sum(1))
    expenses = float(b.ann["count"].to_numpy() * EXPENSE["annuity"] / 12 @ (inf_a @ grow)
                     + b.fun["count"].to_numpy() * EXPENSE["funeral"] / 12 @ (inf_f @ grow))
    claims = float(b.fun["sum_assured"].to_numpy() @ deaths.sum(1))
    outgo = income + expenses + claims
    return {"receivable": RECEIVABLE_MONTHS * float(b.prem[:, 0].sum()), "cash": CASH_MONTHS / 12 * outgo,
            "outgo": {"annuity income": income, "expenses": expenses, "claims": claims, "total": outgo}}


def market(interest: float, default: float, a: float) -> float:
    """§4.7 with interest rate and spread and default risk only."""
    return float(np.sqrt(interest ** 2 + 2 * a * interest * default + default ** 2))


def sovereign(own_funds: float, scr: float, government: float) -> dict:
    """The fall in the price of every government bond and bill held, liabilities and the SCR held, at which cover
    reaches 1 and at which own funds reach 0."""
    return {"government_assets": government, "cover_one": (own_funds - scr) / government,
            "own_funds_zero": own_funds / government}


# --- the SCR ------------------------------------------------------------------------------------------------------------

def run(grids: dict, fgrid: dict, basis: Basis, curves: dict, bonds: dict, settle, book: Book | None = None,
        matched: bool = True, assets: float | None = None, holdings: dict | None = None, scale: float = 1.0,
        step: int = STEP, credit: float = 1.0, default: bool = True, review: bool = False) -> dict:
    """v5's run (research.balance_v5.run) on v7's book, the whole book matched as v6, with default risk on the two
    exposures (times `credit`) taken from the bill. `holdings`, if given, are carried as they are (v4 without
    rematching). `default` False: market risk is interest rate risk alone, the exposures not held. `review`: the
    mortality stress with the review of age-rated schedules (reported only)."""
    b = book or Book(grids, fgrid, basis)
    cv = Curves(curves[basis.curve]["nominal"], curves[basis.curve]["real"])
    L0 = liabilities(b, cv, BASE)
    bel_ = totals(L0)
    m = None
    if holdings is None:
        m = match_book(b, cv, bonds, settle) if matched else None
        holdings = {k: {code: n * scale for code, n in u.items()} for k, u in m["units"].items()} if m else {}
    cashflows = {code: bonds[code].cashflows(settle) for units in holdings.values() for code in units}
    matched_value = asset_value(holdings, cashflows, 0.0, cv, BASE)

    losses = {}
    for name, sc in LIFE_STRESSES.items():
        bb = with_prem(b, b.review_prem()) if review and name == "mortality" else b
        T = totals(liabilities(bb, cv, sc))
        losses[name] = {k: T[k] - bel_[k] for k in T}
    up, down = losses["lapse up"]["funeral"], losses["lapse down"]["funeral"]
    level = max(up, 0) if max(up, 0) >= max(down, 0) else max(down, 0)
    mass = max(losses["mass lapse"]["funeral"], 0) if bel_["funeral"] < 0 else 0.0
    combined = np.hypot(mass, level * (1 - 0.5 * sam.MASS_LAPSE)) if mass > 0 else level
    lapse = max(mass, level, combined)
    life = {"mortality": max(losses["mortality"]["funeral"], 0), "longevity": max(losses["longevity"]["annuities"], 0),
            "lapse": lapse, "expense": max(losses["expense"]["total"], 0),
            "catastrophe": max(losses["catastrophe"]["funeral"], 0)}
    vec = [life[k] for k in sam.LIFE]
    scr_life = sam.aggregate(vec, sam.CORR_LIFE)
    alone = {"annuities": sam.aggregate([0, life["longevity"], 0, max(losses["expense"]["annuities"], 0), 0], sam.CORR_LIFE),
             "funeral": sam.aggregate([life["mortality"], 0, lapse, max(losses["expense"]["funeral"], 0),
                                       life["catastrophe"]], sam.CORR_LIFE)}

    earned = 12 * b.fun["premium"].sum() + (L0["income"] + L0["ann_expenses"])[b.ann["new"].to_numpy()].sum()
    op_base = max(sam.OP_PREMIUMS * earned, sam.OP_PROVISIONS * max(bel_["total"], 0))

    scr_ru0 = scr_life + min(sam.OP_CAP * scr_life, op_base)
    w = alone["annuities"] / (alone["annuities"] + alone["funeral"])
    nom, real = cv.get(BASE)
    run_off = b3.runoff(b, nom, real)
    years = np.arange(YEARS)
    scr_ru = scr_ru0 * (w * run_off["annuities"] / run_off["annuities"][0] + (1 - w) * run_off["sum_assured"] / run_off["sum_assured"][0])
    rm = sam.COC * float(np.sum(scr_ru * nom.df(years + 1)))
    rm_annuities = sam.COC * scr_ru0 * w * float(np.sum(run_off["annuities"] / run_off["annuities"][0] * nom.df(years + 1)))

    total_assets = bel_["total"] + rm + OWN_FUNDS if assets is None else assets
    own_funds = total_assets - bel_["total"] - rm
    ex = credit_exposures(b, cv)
    held = credit if default else 0.0
    receivable, cash = held * ex["receivable"], held * ex["cash"]
    bill = (total_assets - matched_value - receivable - cash) / float(nom.df(BILL))
    bof0 = asset_value(holdings, cashflows, bill, cv, BASE) + receivable + cash - bel_["total"]
    rate = {}
    for name, sc in RATE_STRESSES.items():
        bof = asset_value(holdings, cashflows, bill, cv, sc) + receivable + cash - totals(liabilities(b, cv, sc))["total"]
        rate[name] = bof0 - bof
    nominal = max(rate["nominal up"], rate["nominal down"], 0)
    real_ = max(rate["real up"], rate["real down"], 0)
    interest = sam.pair(nominal, real_, sam.CORR_NOMINAL_REAL)
    a = 0.0 if rate["nominal up"] >= rate["nominal down"] else 0.5        # §4.8
    type2, type3 = TYPE2 * receivable, FACTORS[step] * cash
    mkt_def = type2 + type3                                                # §9.15, no type 1 exposures
    mkt = market(interest, mkt_def, a) if default else interest

    def scr_at(d: float) -> dict:
        mk = market(interest, d, a) if default else interest
        bs = sam.pair(mk, scr_life, sam.CORR_MARKET_LIFE)
        o = min(sam.OP_CAP * bs, op_base)
        return {"default": d, "market": mk, "bscr": bs, "op": o, "scr": bs + o, "cover": own_funds / (bs + o)}

    top = scr_at(mkt_def)
    bscr, op, scr = top["bscr"], top["op"], top["scr"]
    government = matched_value + bill * float(nom.df(BILL))
    return {
        "basis": basis.__dict__, "matched": m is not None or bool(holdings), "spike": b.spike, "review": review,
        "policies": {"annuities": b.n_ann, "funeral": b.n_fun}, "inflation": L0["inflation"],
        "bel": bel_, "bel_parts": {k: float(np.sum(v)) for k, v in L0.items() if k != "inflation"},
        "bel_funeral_by_type": by_type(b, L0),
        "life_losses": losses, "life": life, "life_alone": alone, "scr_life": scr_life,
        "lapse": {"up": up, "down": down, "level": level, "mass": mass, "combined": combined},
        "rate_losses": rate,
        "interest": {"nominal": nominal, "real": real_, "curve": interest, "combined": interest},
        "credit": {"receivable": receivable, "cash": cash, "outgo": ex["outgo"], "step": step,
                   "factor": FACTORS[step], "type2": type2, "type3": type3, "default": mkt_def, "A": a,
                   "by_step": {str(s): scr_at(type2 + f * cash) for s, f in FACTORS.items()} if default else {}},
        "market": mkt, "bscr": bscr, "diversification": nominal + real_ + mkt_def + sum(vec) - bscr,
        "op": {"earned_premiums": earned, "premiums": sam.OP_PREMIUMS * earned,
               "provisions": sam.OP_PROVISIONS * max(bel_["total"], 0), "charge": op},
        "scr": scr, "risk_margin": rm, "risk_margin_parts": {"annuities": rm_annuities, "funeral": rm - rm_annuities},
        "scr_ru": {"t0": scr_ru0, "annuity_weight": w, "by_year": list(scr_ru[:60])},
        "assets": {"total": total_assets, "bill": bill * float(nom.df(BILL)), "matched": matched_value,
                   "credit": receivable + cash, "matching": {"book": m} if m else {}, "holdings": holdings},
        "sovereign": sovereign(own_funds, scr, government),
        "own_funds": own_funds, "cover": own_funds / scr,
        "capital_for": {"1.0": scr, str(INDUSTRY_COVER): INDUSTRY_COVER * scr},
    }


# --- checks -------------------------------------------------------------------------------------------------------------

def loop_rated(mu, lapse, sum_assured, prem, count, nom, real, sc) -> float:
    """F1: one cell by a plain loop over months, its premium from its row in each year (research.balance_v3's
    loop_funeral)."""
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
        v += alive * (cost - prem[k // 12] * float(nom.df(t))) + alive * q * sum_assured * float(nom.df(t + 1 / 24))
        if sc.mass and k < 12:
            v += sc.mass * cost
        alive *= (1 - q) * (1 - min(lapse[k // 12] * sc.lapse, 1.0)) ** (1 / 12)
    return v


def check_f1(b: Book, cv: Curves) -> dict:
    """The age-rated cell with the most policies, unstressed and under every stress."""
    j = int(np.argmax(np.where(b.rated, b.fun["count"].to_numpy(), -1)))
    f = b.fun.iloc[j]
    rows, worst = {}, 0.0
    for name, sc in {"base": BASE, **LIFE_STRESSES, **RATE_STRESSES}.items():
        L = liabilities(b, cv, sc)
        nom, real = cv.get(sc)
        lf = loop_rated(b.mu_fun[j], b.lapse[j], f["sum_assured"], b.prem[j], f["count"], nom, real, sc)
        ef = L["claims"][j] + L["fun_expenses"][j] - L["premiums"][j]
        rel = abs(lf - ef) / abs(ef)
        rows[name] = {"loop": lf, "main": ef, "relative": rel}
        worst = max(worst, rel)
    return {"cell": {k: (v.item() if hasattr(v, "item") else v) for k, v in f[Book.KEYS].to_dict().items()},
            "premium_changes": int(np.sum(np.diff(b.prem[j]) != 0)), "review_spikes": int(np.sum(np.diff(b.lapse[j]) > 0)),
            "scenarios": rows, "worst_relative": worst, "pass": bool(worst < 1e-8)}


def check_f3(b: Book) -> dict:
    n = b.fun["years_in_force"].to_numpy()
    same = np.array_equal(lapse_rows(n, np.ones(len(n), bool), 0.0), lapse_rows(n, np.zeros(len(n), bool), SPIKE))
    return {"pass": bool(same)}


def check_f5(r: dict, zero: dict, without: dict) -> dict:
    c = r["credit"]
    want = TYPE2 * c["receivable"] + FACTORS[STEP] * c["cash"]
    rel_def = abs(c["default"] - want) / want
    rel_scr = abs(zero["scr"] - without["scr"]) / without["scr"]
    return {"default_relative": rel_def, "zero_vs_without_relative": rel_scr,
            "pass": bool(rel_def < 1e-12 and rel_scr < 1e-12)}


def check_f6(r: dict, A: float) -> dict:
    v3 = json.loads((OUT / "balance_v3.json").read_text())["main"]
    pairs = {"bel annuities": (r["bel"]["annuities"], A * v3["bel"]["annuities"]),
             "longevity": (r["life"]["longevity"], A * v3["life"]["longevity"])}
    rel = {k: abs(a / b - 1) for k, (a, b) in pairs.items()}
    return {"relative": rel, "pass": bool(max(rel.values()) < 1e-8)}


def check_d1(b: Book, cv: Curves, A: float, F: float) -> dict:
    e = exposures(scaled(b, A, F), cv)
    rel = abs(e["total"]) / (A * abs(exposures(b, cv)["annuities"]))
    return {"total_exposure": e["total"], "relative": rel, "pass": bool(rel < 1e-9)}


def summary(r: dict) -> dict:
    """The headline numbers of a run, for the variants."""
    return {"bel": r["bel"], "bel_funeral_by_type": r["bel_funeral_by_type"], "life": r["life"],
            "scr_life": r["scr_life"], "interest": r["interest"]["combined"], "default": r["credit"]["default"],
            "market": r["market"], "scr": r["scr"], "risk_margin": r["risk_margin"], "own_funds": r["own_funds"],
            "cover": r["cover"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    ap.add_argument("--grids-cache")
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v5": require_frozen(PROTOCOL_V5), "v6": require_frozen(PROTOCOL_V6), "v7": require_frozen(PROTOCOL_V7)}
    for f in (bk.FUNERAL, bk.SCHEDULE):
        if not f.exists():
            raise SystemExit("run python -m research.book_v7 --write first")
    curves, bonds, days, settle = b3.market()
    g = mx.grids(args.deaths, args.population, args.grids_cache)
    fgrid = bk5.grid()
    basis = Basis()
    b = Book(g, fgrid, basis)
    cv = Curves(curves[basis.curve]["nominal"], curves[basis.curve]["real"])
    go = lambda book, **kw: run(g, fgrid, basis, curves, bonds, settle, book=book, **kw)

    e = exposures(b, cv)
    ratio = mx.mix(e)
    A = mx.size(lambda x: go(scaled(b, x, ratio * x))["cover"])
    F = ratio * A
    book = scaled(b, A, F)
    v6 = json.loads(mx.RESULT.read_text())
    out = {"protocol": frozen, "valuation_date": str(days["real"][1].date()), "exposures": e, "mix": ratio,
           "scales": {"annuities": A, "funeral": F},
           "policies": {"annuitants": round(mx.ANNUITANTS * A), "funeral": round(mx.FUNERAL * F)},
           "v6": {"scales": v6["scales"], "policies": v6["policies"], "mix": v6["mix"], "main": {
               k: v6["main"][k] for k in ("bel", "life", "scr_life", "interest", "market", "scr", "risk_margin",
                                           "own_funds", "cover")}},
           "trend": trend(book, cv)}
    out["main"] = main_ = go(book)
    print(f"main: SCR {main_['scr'] / 1e6:,.1f}m, cover {main_['cover']:.4f}", flush=True)
    out["review"] = summary(go(book, review=True))
    out["lapse_spike"] = {f"{s:.2f}": summary(go(scaled(Book(g, fgrid, basis, spike=s), A, F))) for s in SPIKES}
    zero, without = go(book, credit=0.0), go(book, default=False)
    out["without_default"] = summary(without)
    out["checks"] = {"F1": check_f1(book, cv), "F3": check_f3(book), "F5": check_f5(main_, zero, without),
                     "F6": check_f6(main_, A), "D1": check_d1(b, cv, A, F),
                     "D2": {"cover": main_["cover"], "pass": bool(abs(main_["cover"] - INDUSTRY_COVER) < 1e-6)},
                     "D5": mx.check_d5(main_)}
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    m = main_
    mn = lambda d: {k: round(v / 1e6, 1) for k, v in d.items()}
    print(f"exposures {mn(e)}; F / A {ratio:.4f}; A {A:.4f}, F {F:.4f}; policies {out['policies']} (v6 {v6['policies']})")
    print(f"BEL {mn(m['bel'])} funeral by type {mn(m['bel_funeral_by_type'])}  RM {m['risk_margin'] / 1e6:,.1f}  "
          f"SCR {m['scr'] / 1e6:,.1f}  cover {m['cover']:.4f}")
    print("life", mn(m["life"]), "interest", round(m["interest"]["combined"] / 1e6, 1),
          "default", mn({k: m["credit"][k] for k in ("receivable", "cash", "type2", "type3", "default")}), "A", m["credit"]["A"])
    print("review: mortality", round(out["review"]["life"]["mortality"] / 1e6, 1), "cover", round(out["review"]["cover"], 4))
    print("lapse spike", {k: round(v["cover"], 4) for k, v in out["lapse_spike"].items()})
    print("sovereign", {k: round(v, 4) if k != "government_assets" else round(v / 1e6, 1) for k, v in m["sovereign"].items()})
    print("checks", {k: v["pass"] for k, v in out["checks"].items()})


if __name__ == "__main__":
    main()
