"""v5 balance sheet (research/PROTOCOL_v5.md): v3's, with funeral on the v5 table along the cohort, the rising
benefit valued by the inflation model, the interest rate volatility charge (FSI 4.1 §5.16 to 5.18), and the rising
claims hedged with nominal and inflation-linked bonds on key rates.

    python -m research.balance_v5 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Needs research.book_v5 --write and research.inflation_v5 to have been run. Writes research/results/balance_v5.json.
Refuses to run until the v1 to v3 and v5 protocols are frozen. The annuities are v3's, unchanged (C6).
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from mdingilife import data, inflation_v5 as iv, sam
from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V5, require_frozen
from research import balance_v3 as b3
from research import book_v5 as bk
from research.annuities_v2 import BP, KEYS, bond_value, bump, risk, tent
from research.backtest import OUT
from research.balance_v3 import (BASE, BILL, INDUSTRY_COVER, LIFE_STRESSES, OWN_FUNDS, RATE_STRESSES, YEARS, Basis, Curves,
                                 annuitant_rows, asset_value, bond_book, match, totals)
from research.book_v3 import BOOK, EXPENSE, lapse_rate
from research.inflation_v5 import RESULT as INFLATION

RESULT = OUT / "balance_v5.json"
MONTHS = 12 * YEARS
VOL_CORR = 0.5                          # FSI 4.1 §5.3: the curve and volatility charges


@dataclass(frozen=True)
class Scenario(b3.Scenario):
    vol: bool = False                   # the volatility of each year's inflation raised (§5.18)


VOL = Scenario(vol=True)


class Growth:
    """G by month for a rising benefit, from the inflation model's paths, centred on a given f and cached."""

    def __init__(self, model: iv.Model, x: np.ndarray, cap: float | None = iv.CAP, floor: float | None = iv.FLOOR):
        self.model, self.x, self.cap, self.floor = model, x, cap, floor
        self._cache: dict = {}

    @classmethod
    def load(cls, cap: float | None = iv.CAP, floor: float | None = iv.FLOOR) -> "Growth":
        r = json.loads(INFLATION.read_text())
        model = iv.Model(r["phi"], r["sigma_month"])
        return cls(model, iv.paths(model, YEARS, r["C8"]["paths"]), cap, floor)

    def variant(self, cap: float | None = iv.CAP, floor: float | None = iv.FLOOR) -> "Growth":
        return Growth(self.model, self.x, cap, floor)

    def annual(self, f: float, vol: bool = False) -> np.ndarray:
        key = (float(f), vol)
        if key not in self._cache:
            scale = iv.shock_scale(self.model, f, self.x.shape[1]) if vol else None
            self._cache[key] = iv.growth(f, self.x, self.cap, self.floor, scale)
        return self._cache[key]

    def months(self, f: float, vol: bool = False) -> np.ndarray:
        return iv.monthly(self.annual(f, vol), MONTHS)


class Book(b3.Book):
    """v3's book with the v5 funeral policies: benefit type by cell, rates along the cohort."""

    def __init__(self, grids: dict, fgrid: dict, basis: Basis, growth: Growth, funeral: pd.DataFrame | None = None):
        ann = pd.read_csv(BOOK / "annuities.csv")
        fun = pd.read_csv(bk.FUNERAL) if funeral is None else funeral
        ann["new"] = ann["years_since_purchase"] == 0
        self.ann = ann.groupby(["sex", "age", "type", "new"], as_index=False).agg(
            income=("income", "sum"), count=("id", "size"))
        self.fun = fun.groupby(["sex", "age", "years_in_force", "benefit"], as_index=False).agg(
            sum_assured=("sum_assured", "sum"), premium=("premium", "sum"), count=("id", "size"))
        self.n_ann, self.n_fun = len(ann), len(fun)
        self.basis = basis
        a, f = self.ann, self.fun
        self.mu_ann = {lv: annuitant_rows(grids, a["sex"], a["age"].to_numpy(), basis.annuitant_adj, lv)
                       for lv in (False, True)}
        self.mu_fun = bk.mu_rows(fgrid, f["sex"].to_numpy(), f["age"].to_numpy(), YEARS, basis.funeral_adj)
        self.lapse = lapse_rate(f["years_in_force"].to_numpy()[:, None] + 1 + np.arange(YEARS))
        self.ilb = (a["type"] == "inflation-linked").to_numpy()
        self.rising = (f["benefit"] == "rising").to_numpy()
        self.growth = growth
        self.t = np.arange(MONTHS) / 12


def liabilities(b: Book, cv: Curves, sc, e: float | None = None) -> dict:
    """v3's BEL per cell, by part, with rising claims times G centred on the scenario's 30-year breakeven. The
    expense stress raises expense inflation only."""
    L = b3.liabilities(b, cv, sc, e)
    nom, real = cv.get(sc)
    f = sam.breakeven(nom, real)
    lapse = np.minimum(b.lapse * sc.lapse, 1.0)
    _, deaths = sam.project(b.mu_fun * sc.mortality, lapse, mass=sc.mass, cat=sc.cat)
    v_mid = nom.df(b.t + 1 / 24)
    g = b.growth.months(f, getattr(sc, "vol", False))
    sa = b.fun["sum_assured"].to_numpy()
    rising = np.where(b.rising, sa * (deaths @ (v_mid * g)), 0.0)
    L["claims"] = np.where(b.rising, rising, L["claims"])
    L["rising_claims"] = rising
    L["f"] = f
    return L


def _totals(L: dict) -> dict:
    return totals({k: v for k, v in L.items() if k not in ("rising_claims", "f")})


# --- the hedge of the rising claims ---------------------------------------------------------------------------------

def rising_value(b: Book, deaths: np.ndarray, fn: np.ndarray, fr: np.ndarray) -> float:
    """The rising claims' BEL on unshocked forwards, G centred on their 30-year breakeven."""
    nom, real = sam.Curve(fn), sam.Curve(fr, "real")
    g = b.growth.months(sam.breakeven(nom, real))
    sa = b.fun["sum_assured"].to_numpy()[b.rising]
    return float(sa @ (deaths @ (nom.df(b.t + 1 / 24) * g)))


def rising_risk(b: Book, cv: Curves) -> dict:
    """Value and key-rate DV01s on both curves, each curve's key rate moved with the other held."""
    _, deaths = sam.project(b.mu_fun[b.rising], b.lapse[b.rising])
    fn, fr = cv.fwd["nominal"], cv.fwd["real"]
    v = rising_value(b, deaths, fn, fr)
    dv = {("nominal", k): v - rising_value(b, deaths, bump(fn, tent(k)), fr) for k in KEYS}
    dv |= {("real", k): v - rising_value(b, deaths, fn, bump(fr, tent(k))) for k in KEYS}
    return {"value": v, "dv01": dv}


def hedge(b: Book, cv: Curves, bonds: dict, settle, weight: float = 1e3) -> dict:
    """Non-negative holdings in every nominal and inflation-linked bond that match the rising claims' value (a row
    weighted by `weight`) and come nearest their eight key-rate DV01s, then scaled to the value exactly."""
    liab = rising_risk(b, cv)
    book = {}
    for kind in ("nominal", "real"):
        for code, (t, cf) in bond_book(bonds, settle, kind).items():
            r = risk(lambda f, t=t, cf=cf: bond_value(t, cf, f), cv.fwd[kind])
            book[code] = {"kind": kind, "value": r["value"],
                          "dv01": {(k2, k): (r["dv01"][k] if k2 == kind else 0.0) for k2 in ("nominal", "real") for k in KEYS}}
    codes, rows = sorted(book), list(liab["dv01"])
    total = sum(abs(x) for x in liab["dv01"].values())
    A = np.array([[book[c]["dv01"][r] / total for c in codes] for r in rows]
                 + [[weight * book[c]["value"] / liab["value"] for c in codes]])
    y = np.array([liab["dv01"][r] / total for r in rows] + [weight])
    n, _ = nnls(A, y)
    n *= liab["value"] / sum(n[i] * book[c]["value"] for i, c in enumerate(codes))
    units = {}
    for i, c in enumerate(codes):
        if n[i] > 0:
            units.setdefault(book[c]["kind"], {})[c] = float(n[i])
    held = {r: sum(n[i] * book[c]["dv01"][r] for i, c in enumerate(codes)) for r in rows}
    return {"liability": {"value": liab["value"], "dv01": {f"{k} {t}": v for (k, t), v in liab["dv01"].items()}},
            "portfolio_dv01": {f"{k} {t}": v for (k, t), v in held.items()}, "units": units}


def combine(*holdings: dict) -> dict:
    out: dict = {}
    for h in holdings:
        for kind, units in h.items():
            for code, n in units.items():
                out.setdefault(kind, {})[code] = out.get(kind, {}).get(code, 0.0) + n
    return out


# --- the SCR ------------------------------------------------------------------------------------------------------------

def run(grids: dict, fgrid: dict, basis: Basis, curves: dict, bonds: dict, settle, growth: Growth,
        matched: bool = True, hedged: bool = True, method: str = "duration", book: Book | None = None,
        assets: float | None = None, holdings: dict | None = None, scale: float = 1.0,
        funeral: pd.DataFrame | None = None) -> dict:
    """v3's run (research.balance_v3.run), with v5's funeral liabilities, the volatility charge and the hedge.
    `holdings`, if given, are carried as they are (v4 without rematching)."""
    b = book or Book(grids, fgrid, basis, growth, funeral)
    cv = Curves(curves[basis.curve]["nominal"], curves[basis.curve]["real"])
    L0 = liabilities(b, cv, BASE)
    bel = _totals(L0)
    h = None
    if holdings is None:
        m = match(b, cv, bonds, settle, method) if matched else {}
        holdings = {k: {code: n * scale for code, n in v["units"].items()} for k, v in m.items()}
        if hedged and b.rising.any():
            h = hedge(b, cv, bonds, settle)
            holdings = combine(holdings, {k: {c: n * scale for c, n in u.items()} for k, u in h["units"].items()})
        cashflows = {**bond_book(bonds, settle, "real"), **bond_book(bonds, settle, "nominal")}
    else:
        m = {}
        cashflows = {code: bonds[code].cashflows(settle) for units in holdings.values() for code in units}
    matched_value = asset_value(holdings, cashflows, 0.0, cv, BASE)

    losses = {}
    for name, sc in LIFE_STRESSES.items():
        T = _totals(liabilities(b, cv, sc))
        losses[name] = {k: T[k] - bel[k] for k in T}
    up, down = losses["lapse up"]["funeral"], losses["lapse down"]["funeral"]
    level = max(up, 0) if max(up, 0) >= max(down, 0) else max(down, 0)
    mass = max(losses["mass lapse"]["funeral"], 0) if bel["funeral"] < 0 else 0.0
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
    op_base = max(sam.OP_PREMIUMS * earned, sam.OP_PROVISIONS * max(bel["total"], 0))

    scr_ru0 = scr_life + min(sam.OP_CAP * scr_life, op_base)
    w = alone["annuities"] / (alone["annuities"] + alone["funeral"])
    nom, real = cv.get(BASE)
    run_off = runoff(b, nom, real)
    years = np.arange(YEARS)
    scr_ru = scr_ru0 * (w * run_off["annuities"] / run_off["annuities"][0] + (1 - w) * run_off["sum_assured"] / run_off["sum_assured"][0])
    rm = sam.COC * float(np.sum(scr_ru * nom.df(years + 1)))
    rm_annuities = sam.COC * scr_ru0 * w * float(np.sum(run_off["annuities"] / run_off["annuities"][0] * nom.df(years + 1)))

    total_assets = bel["total"] + rm + OWN_FUNDS if assets is None else assets
    own_funds = total_assets - bel["total"] - rm
    bill = (total_assets - matched_value) / float(nom.df(BILL))
    bof0 = asset_value(holdings, cashflows, bill, cv, BASE) - bel["total"]
    rate = {}
    for name, sc in RATE_STRESSES.items():
        bof = asset_value(holdings, cashflows, bill, cv, sc) - _totals(liabilities(b, cv, sc))["total"]
        rate[name] = bof0 - bof
    nominal = max(rate["nominal up"], rate["nominal down"], 0)
    real_ = max(rate["real up"], rate["real down"], 0)
    curve = sam.pair(nominal, real_, sam.CORR_NOMINAL_REAL)
    vol_loss = bof0 - (asset_value(holdings, cashflows, bill, cv, BASE) - _totals(liabilities(b, cv, VOL))["total"])
    vol = max(vol_loss, 0.0)
    market = sam.pair(curve, vol, VOL_CORR)
    bscr = sam.pair(market, scr_life, sam.CORR_MARKET_LIFE)
    op = min(sam.OP_CAP * bscr, op_base)
    scr = bscr + op
    return {
        "basis": basis.__dict__, "matched": matched, "hedged": h is not None, "method": method if matched else None,
        "policies": {"annuities": b.n_ann, "funeral": b.n_fun}, "inflation": L0["inflation"], "f": L0["f"],
        "bel": bel, "bel_parts": {k: float(np.sum(v)) for k, v in L0.items() if k not in ("inflation", "f", "rising_claims")},
        "rising_claims": float(np.sum(L0["rising_claims"])),
        "life_losses": losses, "life": life, "life_alone": alone, "scr_life": scr_life,
        "lapse": {"up": up, "down": down, "level": level, "mass": mass, "combined": combined},
        "rate_losses": rate, "vol_loss": vol_loss,
        "interest": {"nominal": nominal, "real": real_, "curve": curve, "volatility": vol, "combined": market},
        "market": market, "bscr": bscr, "diversification": nominal + real_ + vol + sum(vec) - bscr,
        "op": {"earned_premiums": earned, "premiums": sam.OP_PREMIUMS * earned,
               "provisions": sam.OP_PROVISIONS * max(bel["total"], 0), "charge": op},
        "scr": scr, "risk_margin": rm, "risk_margin_parts": {"annuities": rm_annuities, "funeral": rm - rm_annuities},
        "scr_ru": {"t0": scr_ru0, "annuity_weight": w, "by_year": list(scr_ru[:60])},
        "assets": {"total": total_assets, "bill": bill * float(nom.df(BILL)), "matched": matched_value,
                   "matching": {k: {"liability": v["liability"], "units": v["units"]} for k, v in m.items()},
                   "hedge": h, "holdings": holdings},
        "own_funds": own_funds, "cover": own_funds / scr,
        "capital_for": {"1.0": scr, str(INDUSTRY_COVER): INDUSTRY_COVER * scr},
    }


def runoff(b: Book, nom: sam.Curve, real: sam.Curve) -> dict:
    """v3's run-off, with the funeral sum assured in force including the expected increases G(t)."""
    out = b3.runoff(b, nom, real)
    inf_f, _ = sam.project(b.mu_fun, b.lapse)
    k = 12 * np.arange(YEARS)
    g = b.growth.annual(sam.breakeven(nom, real))[:YEARS]
    sa = b.fun["sum_assured"].to_numpy()[:, None] * np.where(b.rising[:, None], g[None, :], 1.0)
    out["sum_assured"] = np.sum(sa * inf_f[:, k], axis=0)
    return out


# --- checks -------------------------------------------------------------------------------------------------------------

def loop_rising(mu, lapse, sum_assured, premium, count, nom, real, sc, growth: Growth) -> float:
    """C4: one rising cell by a plain loop over months, its benefit G(k) in year k."""
    e = sam.breakeven(nom, real)
    g = growth.annual(e, getattr(sc, "vol", False))
    if sc.inflation:
        e += max(sam.INFLATION_ADD, sam.INFLATION_REL * e)
    alive, v = 1.0 - sc.mass, 0.0
    for k in range(12 * len(mu)):
        t = k / 12
        q = 1 - np.exp(-mu[k // 12] * sc.mortality / 12)
        if sc.cat and k < 3:
            q = min(q + float(sam.cat_addition(q)), 1.0)
        cost = count * EXPENSE["funeral"] * sc.expense / 12 * (1 + e) ** t * float(nom.df(t))
        v += alive * (cost - premium * float(nom.df(t))) + alive * q * sum_assured * g[k // 12] * float(nom.df(t + 1 / 24))
        if sc.mass and k < 12:
            v += sc.mass * cost
        alive *= (1 - q) * (1 - min(lapse[k // 12] * sc.lapse, 1.0)) ** (1 / 12)
    return v


def check_c4(b: Book, cv: Curves) -> dict:
    j = int(np.argmax(np.where(b.rising, b.fun["count"].to_numpy(), -1)))
    f = b.fun.iloc[j]
    rows, worst = {}, 0.0
    for name, sc in {"base": BASE, **LIFE_STRESSES, **RATE_STRESSES, "volatility": VOL}.items():
        L = liabilities(b, cv, sc)
        nom, real = cv.get(sc)
        lf = loop_rising(b.mu_fun[j], b.lapse[j], f["sum_assured"], f["premium"], f["count"], nom, real, sc, b.growth)
        ef = L["claims"][j] + L["fun_expenses"][j] - L["premiums"][j]
        rel = abs(lf - ef) / abs(ef)
        rows[name] = {"loop": lf, "main": ef, "relative": rel}
        worst = max(worst, rel)
    return {"cell": f[["sex", "age", "years_in_force", "benefit"]].to_dict(), "scenarios": rows,
            "worst_relative": worst, "pass": bool(worst < 1e-8)}


def check_c5(b: Book, cv: Curves, fgrid: dict) -> dict:
    """With the cap at 0%: rising premiums equal level ones, and each rising cell's claims its level value. The
    premiums are worked for the same cells both ways, so only the benefit type differs."""
    sex, entry = np.repeat(list(data.SEXES), len(bk.ENTRY)), np.tile(bk.ENTRY, len(data.SEXES))
    sa = np.ones(len(entry))
    level, rising = (bk.premiums(fgrid, sex, entry, np.full(len(entry), r), sa, growth=0.0) for r in (False, True))
    premiums_equal = bool(np.array_equal(level, rising))
    flat = Book.__new__(Book)
    flat.__dict__.update(b.__dict__, growth=b.growth.variant(cap=0.0))
    L = liabilities(flat, cv, BASE)
    lvl = b3.liabilities(flat, cv, BASE)
    bel_equal = bool(np.array_equal(L["claims"], lvl["claims"]))
    return {"premiums_equal": premiums_equal, "claims_equal": bel_equal, "pass": premiums_equal and bel_equal}


def check_c6(r: dict) -> dict:
    v3 = json.loads((OUT / "balance_v3.json").read_text())["main"]
    pairs = {"bel annuities": (r["bel"]["annuities"], v3["bel"]["annuities"]),
             "longevity": (r["life"]["longevity"], v3["life"]["longevity"]),
             "life alone, annuities": (r["life_alone"]["annuities"], v3["life_alone"]["annuities"])}
    rel = {k: abs(a / b - 1) for k, (a, b) in pairs.items()}
    return {"relative": rel, "pass": bool(max(rel.values()) < 1e-8)}


def options(b: Book, cv: Curves) -> dict:
    """The rising claims' BEL with the cap and floor, with neither and with the cap only, on the valuation date."""
    out = {}
    for name, (cap, floor) in {"cap and floor": (iv.CAP, iv.FLOOR), "neither": (None, None),
                               "cap only": (iv.CAP, None)}.items():
        flat = Book.__new__(Book)
        flat.__dict__.update(b.__dict__, growth=b.growth.variant(cap, floor))
        out[name] = float(liabilities(flat, cv, BASE)["rising_claims"].sum())
    out["cap value"] = out["neither"] - out["cap only"]
    out["floor value"] = out["cap and floor"] - out["cap only"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v5": require_frozen(PROTOCOL_V5)}
    for f, how in ((bk.FUNERAL, "research.book_v5 --write"), (INFLATION, "research.inflation_v5")):
        if not f.exists():
            raise SystemExit(f"run python -m {how} first")
    curves, bonds, days, settle = b3.market()
    grids = b3.annuitant_grids(args.deaths, args.population)
    fgrid = bk.grid()
    growth = Growth.load()
    go = lambda basis=Basis(), g=growth, **kw: run(grids, fgrid, basis, curves, bonds, settle, g, **kw)
    out = {"protocol": frozen, "valuation_date": str(days["real"][1].date())}
    out["main"] = main_ = go()
    out["unhedged"] = go(hedged=False)
    out["unmatched"] = go(matched=False, hedged=False)
    if main_["interest"]["volatility"] > 0:
        out["no_floor"] = go(g=growth.variant(floor=None))
    out["sensitivities"] = {"funeral 0.8": go(Basis(funeral_adj=0.8)), "funeral 1.2": go(Basis(funeral_adj=1.2))}
    b = Book(grids, fgrid, Basis(), growth)
    cv = Curves(curves["LI"]["nominal"], curves["LI"]["real"])
    out["options"] = options(b, cv)
    out["checks"] = {"C4": check_c4(b, cv), "C5": check_c5(b, cv, fgrid), "C6": check_c6(main_)}
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    m = main_
    print(f"BEL {m['bel']}  RM {m['risk_margin']:,.0f}  SCR {m['scr']:,.0f}  cover {m['cover']:.3f}")
    print("life", {k: round(v / 1e6, 1) for k, v in m["life"].items()}, "interest", {k: round(v / 1e6, 2) for k, v in m["interest"].items()})
    print("unhedged interest", {k: round(v / 1e6, 2) for k, v in out["unhedged"]["interest"].items()}, "cover", round(out["unhedged"]["cover"], 3))
    print("options", {k: round(v / 1e6, 2) for k, v in out["options"].items()})
    print("checks", {k: v["pass"] for k, v in out["checks"].items()})


if __name__ == "__main__":
    main()
