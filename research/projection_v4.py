"""v4 (PROTOCOL_v4.md): the scenario generator, a five-year projection of v3's balance sheet in each scenario and
named stress, and IFRS 17 on the central path, with the protocol's sensitivities and checks.

    python -m research.projection_v4 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Needs research.book_v3 to have been run. Writes research/results/projection_v4.json. Refuses to run until the v1 to
v4 protocols are frozen.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta

import numpy as np
import pandas as pd

from mdingilife import data, ifrs17, sam
from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, PROTOCOL_V4, require_frozen
from research import curves as rc
from research import scenarios_v4 as sv
from research.backtest import OUT
from research.balance_v3 import (BILL, BASE, Basis, Book, Curves, annuitant_grids, annuitant_rows, asset_value,
                                 auctions, liabilities, market, run)
from research.book_v3 import BOOK, EXPENSE, TABLE

HORIZON = 5
PORTFOLIOS = ("annuities", "funeral")
LONGEVITY_ADJ = 0.56         # S2: annuitant mortality 20% below v3's 0.7
LAPSE_WAVE = 0.30            # S4
RATE_FALL = 0.015            # S1, on β0 of each kind
PANDEMIC = (2019, 2021)      # S3: crude death rates, ages 18 to 89
PANDEMIC_AGES = (18, 89)
COC_FV = (0.08, ifrs17.COC_FAIR_VALUE, 0.12)
EPS = 1e-9

CTX: dict = {}


# --- the book over a year ---------------------------------------------------------------------------------------------

def start(b: Book) -> Book:
    """The book at t = 0 with what the projection tracks: policies in force (`count` is the expense weight once
    costs have risen) and the inflation-linked index."""
    b = copy.copy(b)
    b.ann, b.fun = b.ann.assign(policies=b.ann["count"].astype(float)), b.fun.assign(policies=b.fun["count"].astype(float))
    b.index, b.years = 1.0, 0
    return b


def _shift(x: np.ndarray, pad: float | None) -> np.ndarray:
    return np.concatenate([x[:, 1:], x[:, -1:] if pad is None else np.full((len(x), 1), pad)], axis=1)


def decrements(b: Book, pandemic: dict | None = None):
    """The year's policies in force at the start of each month and at its end (13 columns), and funeral deaths in
    each month, per policy in force at its start. `pandemic`: mortality multipliers by sex for this year."""
    mu_a, mu_f = b.mu_ann[False][:, :2].copy(), b.mu_fun[:, :2].copy()
    if pandemic:
        mu_a[:, 0] *= b.ann["sex"].map(pandemic).to_numpy()
        mu_f[:, 0] *= b.fun["sex"].map(pandemic).to_numpy()
    inf_a, _ = sam.project(mu_a)
    inf_f, deaths = sam.project(mu_f, b.lapse[:, :2])
    return inf_a[:, :13], inf_f[:, :13], deaths[:, :12]


def flows(b: Book, nom: sam.Curve, real: sam.Curve, dec, e: float | None = None) -> dict:
    """The year's cash flows by part, accumulated to its end on the start-of-year curves. Realised (e None): all on the
    nominal curve, costs level within the year. R1 (e given): inflation-linked incomes on the real curve, costs
    rising continuously at e, as in the valuation."""
    inf_a, inf_f, deaths = dec
    s = np.arange(12) / 12
    acc = nom.df(s) / nom.df(1.0)
    acc_mid = nom.df(s + 1 / 24) / nom.df(1.0)
    acc_ilb = real.df(s) / real.df(1.0) if e is not None else acc
    grow = (1 + e) ** s if e is not None else np.ones(12)
    a, f = b.ann, b.fun
    inc = a["income"].to_numpy() / 12
    out = {"income_ilb": float(inc[b.ilb] @ (inf_a[b.ilb, :12] @ acc_ilb)),
           "income_nominal": float(inc[~b.ilb] @ (inf_a[~b.ilb, :12] @ acc)),
           "ann_expenses": float(a["count"].to_numpy() * EXPENSE["annuity"] / 12 @ (inf_a[:, :12] @ (grow * acc))),
           "claims": float(f["sum_assured"].to_numpy() @ (deaths @ acc_mid)),
           "premiums": float(f["premium"].to_numpy() @ (inf_f[:, :12] @ acc)),
           "fun_expenses": float(f["count"].to_numpy() * EXPENSE["funeral"] / 12 @ (inf_f[:, :12] @ (grow * acc)))}
    out["annuities"] = out["income_ilb"] + out["income_nominal"] + out["ann_expenses"]
    out["funeral"] = out["claims"] + out["fun_expenses"] - out["premiums"]
    out["total"] = out["annuities"] + out["funeral"]
    return out


def age(b: Book, dec, ilb_rise: float, cost_rise: float) -> Book:
    """The book a year on: each cell weighted by its survivors in force, a year older and longer in force, rates
    moved a year along, inflation-linked incomes up by `ilb_rise` and costs a policy by `cost_rise`."""
    inf_a, inf_f, _ = dec
    wa, wf = inf_a[:, 12], inf_f[:, 12]
    n = copy.copy(b)
    a = b.ann.copy()
    a["age"] += 1
    a["new"] = False
    a["income"] = a["income"] * wa * np.where(b.ilb, 1 + ilb_rise, 1.0)
    a["count"] = a["count"] * wa * (1 + cost_rise)
    a["policies"] = a["policies"] * wa
    f = b.fun.copy()
    f["age"] += 1
    f["years_in_force"] += 1
    for col in ("sum_assured", "premium", "policies"):
        f[col] = f[col] * wf
    if getattr(b, "rising", None) is not None:     # v5: rising benefits grow by the year's inflation, floored and capped
        lo, hi = CTX["rising_bounds"]
        f["sum_assured"] = f["sum_assured"] * np.where(b.rising, 1 + min(max(ilb_rise, lo), hi), 1.0)
    f["count"] = f["count"] * wf * (1 + cost_rise)
    n.ann, n.fun = a, f
    n.years = b.years + 1
    n.mu_ann = {False: _shift(b.mu_ann[False], 1e3), True: longevity_rows(n)}
    n.mu_fun = _shift(b.mu_fun, 1e3)
    n.lapse = _shift(b.lapse, None)
    if getattr(b, "prem", None) is not None:       # v7: each cell's premiums by projection year, moved a year along
        n.prem = _shift(b.prem * wf[:, None], None)
        f["premium"] = n.prem[:, 0]
    n.index = b.index * (1 + ilb_rise)
    n.n_ann, n.n_fun = float(a["policies"].sum()), float(f["policies"].sum())
    return n


def longevity_rows(b: Book) -> np.ndarray:
    """SAM's longevity stress on the book's annuitant rates from its own date: rates 10% lower and improvements 1 point
    higher from the year after it, not after t = 0 (shifting t = 0's stressed rates would compound the shock)."""
    key = (b.basis.annuitant_adj, b.years)
    cache = CTX.setdefault("longevity", {})
    if key not in cache:
        grids = {s: {**g, "start": g["start"] + b.years} for s, g in CTX["grids"].items()}
        cache[key] = annuitant_rows(grids, b.ann["sex"], b.ann["age"].to_numpy(), b.basis.annuitant_adj, True)
    return cache[key]


def lapse_wave(b: Book, share: float) -> Book:
    n = copy.copy(b)
    f = b.fun.copy()
    for col in ("sum_assured", "premium", "count", "policies"):
        f[col] = f[col] * (1 - share)
    n.fun, n.n_fun = f, float(f["policies"].sum())
    if getattr(b, "prem", None) is not None:
        n.prem = b.prem * (1 - share)
    return n


def units(b: Book, dec=None) -> dict:
    """Coverage units by portfolio: (this year's, this and all later years'). Annuities: expected income payable,
    inflation-linked in today's money; funeral: sum assured in force averaged over each year's months. With `dec`,
    the year's own units come from its actual decrements."""
    inf_a, _ = sam.project(b.mu_ann[False])
    inf_f, _ = sam.project(b.mu_fun, b.lapse)
    inc = b.ann["income"].to_numpy() / 12 * np.where(b.ilb, 1 / b.index, 1.0)
    sa = b.fun["sum_assured"].to_numpy() / 12
    a_all, f_all = inc @ inf_a, sa @ inf_f
    if dec is None:
        return {"annuities": (a_all[:12].sum(), a_all.sum()), "funeral": (f_all[:12].sum(), f_all.sum())}
    a_now, f_now = inc @ dec[0][:, :12], sa @ dec[1][:, :12]
    # Later years from the book at the year-end, which `dec` leads to.
    wa, wf = dec[0][:, 12], dec[1][:, 12]
    inf_a1, _ = sam.project(_shift(b.mu_ann[False], 1e3))
    inf_f1, _ = sam.project(_shift(b.mu_fun, 1e3), _shift(b.lapse, None))
    a_later, f_later = (inc * wa) @ inf_a1, (sa * wf) @ inf_f1
    return {"annuities": (a_now.sum(), a_now.sum() + a_later.sum()), "funeral": (f_now.sum(), f_now.sum() + f_later.sum())}


# --- assets over a year ------------------------------------------------------------------------------------------------

def roll_assets(r: dict, settle, nom0: sam.Curve, nom1: sam.Curve, real1: sam.Curve, rise: float):
    """The year-end value of the bill and the bonds held at the start: every payment in the year accumulated on the
    start nominal curve, the rest valued on the year-end curves, inflation-linked ones indexed by `rise`. Also the
    holdings carried, in year-end units."""
    bonds = CTX["bonds"]
    value = r["assets"]["bill"] / float(nom0.df(1.0)) + r["assets"].get("credit", 0.0)   # v7's credit exposures, at par
    carried = {}
    for kind, held in r["assets"]["holdings"].items():
        end, up = (real1, 1 + rise) if kind == "real" else (nom1, 1.0)
        for code, n in held.items():
            t, cf = bonds[code].cashflows(settle)
            now = t <= 1 + EPS
            value += n * float(np.sum(cf[now] * nom0.df(t[now]))) / float(nom0.df(1.0))
            if (~now).any():
                value += n * up * float(np.sum(cf[~now] * end.df(t[~now] - 1)))
                carried.setdefault(kind, {})[code] = n * up
    return value, carried


def revalue(r: dict, settle, curves: dict) -> float:
    """The position in `r` at its own date, valued on other curves (a shock at t = 0)."""
    cv = Curves(curves["nominal"], curves["real"])
    held = r["assets"]["holdings"]
    cfs = {code: CTX["bonds"][code].cashflows(settle) for units_ in held.values() for code in units_}
    nom, _ = Curves(CTX["fwd0"]["nominal"], CTX["fwd0"]["real"]).get(BASE)
    face = r["assets"]["bill"] / float(nom.df(BILL))
    return asset_value(held, cfs, face, cv, BASE) + r["assets"].get("credit", 0.0)


# --- a path --------------------------------------------------------------------------------------------------------------

def valuation(b: Book, curves: dict, settle, assets=None, holdings=None, matched: bool = True) -> dict:
    if "valuation" in CTX:                         # v5 and later supply their own balance sheet
        return CTX["valuation"](b, curves, settle, assets, holdings, matched)
    return run(CTX["grids"], CTX["table"], b.basis, {b.basis.curve: curves}, CTX["bonds"], settle, matched=matched,
               method="key", book=b, assets=assets, holdings=holdings, scale=CTX.get("scale", 1.0))


def slim(r: dict) -> dict:
    return {"bel": r["bel"], "bel_parts": r["bel_parts"], "risk_margin": r["risk_margin"],
            "risk_margin_parts": r["risk_margin_parts"], "scr": r["scr"], "scr_life": r["scr_life"],
            "market": r["market"], "op": r["op"]["charge"], "life": r["life"], "interest": r["interest"],
            "assets": {k: r["assets"][k] for k in ("total", "bill", "matched")}, "own_funds": r["own_funds"],
            "cover": r["cover"], "policies": r["policies"], "inflation": r["inflation"]}


def inflation(curves: dict) -> float:
    nom, real = Curves(curves["nominal"], curves["real"]).get(BASE)
    return float((1 + nom.spot(1.0)) / (1 + real.spot(1.0)) - 1)


def path(curves: list[dict], book0: Book, r0: dict | None = None, assets0: float | None = None,
         holdings0: dict | None = None, rematch: bool = True, pandemic: dict | None = None, keep: bool = False) -> dict:
    """Year-ends t = 0 to 5 on `curves` (t = 0 to 5). At t = 0 either the valuation `r0` already done, or the book
    valued with `assets0` and `holdings0` (a shock to the t = 0 position). `pandemic` applies in year 1.
    `keep`: also return the books, decrements and flows for IFRS 17."""
    settle0 = CTX["settle"]
    b = book0
    r = r0 or valuation(b, curves[0], settle0, assets0, holdings0)
    rows, books, decs, cash = [slim(r)], [b], [], []
    for t in range(HORIZON):
        settle = settle0 + timedelta(days=365 * t)
        nom0, real0 = Curves(curves[t]["nominal"], curves[t]["real"]).get(BASE)
        nom1, real1 = Curves(curves[t + 1]["nominal"], curves[t + 1]["real"]).get(BASE)
        infl = inflation(curves[t])
        dec = decrements(b, pandemic if t == 0 else None)
        cf = flows(b, nom0, real0, dec)
        value, carried = roll_assets(r, settle, nom0, nom1, real1, infl)
        assets = value - cf["total"]
        b_next = age(b, dec, infl, infl)
        r = valuation(b_next, curves[t + 1], settle + timedelta(days=365), assets, None if rematch else carried)
        row = slim(r)
        row.update(inflation_realised=infl, cash_flows=cf, assets_rolled=value)
        rows.append(row)
        if keep:
            books.append(b_next), decs.append(dec), cash.append(cf)
        b = b_next
    out = {"years": rows, "cover": [x["cover"] for x in rows], "own_funds": [x["own_funds"] for x in rows],
           "scr": [x["scr"] for x in rows]}
    if keep:
        out.update(books=books, decs=decs, cash=cash)
    return out


# --- IFRS 17 ---------------------------------------------------------------------------------------------------------

def locked(k: int) -> dict:
    """The transition curves rolled forward k years."""
    return {kind: np.concatenate([f[k:], np.full(k, f[-1])]) for kind, f in CTX["fwd0"].items()}


def fcf_locked(b: Book, k: int) -> dict:
    """Fulfilment cash flows by portfolio on the locked-in curves k years after transition."""
    r = valuation(b, locked(k), CTX["settle"] + timedelta(days=365 * k), matched=False)
    return {p: r["bel"][p] + r["risk_margin_parts"][p] for p in PORTFOLIOS} | {
        "ra": dict(r["risk_margin_parts"])}


def ifrs(p: dict, ra_transition: dict, coc_fv: float, change0: dict | None = None, change1: dict | None = None,
         variance1: dict | None = None) -> dict:
    """The CSM roll-forward and profit along a kept path. `change0`: future-service changes in fulfilment cash flows
    at t = 0 (after transition, before year 1) by portfolio; `change1` at the end of year 1, with the year's experience
    variance (expected less actual outflows) in `variance1`."""
    fwd = CTX["fwd0"]["nominal"]
    csm0 = {q: ifrs17.transition_csm(ra_transition[q], sam.COC, coc_fv) for q in PORTFOLIOS}
    years = p["years"]
    ra = [dict(y["risk_margin_parts"]) for y in years]
    fs_ra0 = (change0 or {}).get("ra", {q: 0.0 for q in PORTFOLIOS})
    fs_ra1 = (change1 or {}).get("ra", {q: 0.0 for q in PORTFOLIOS})
    csm = {}
    loss0 = {}
    for q in PORTFOLIOS:
        x = csm0[q] - (change0 or {}).get(q, 0.0)
        loss0[q], csm[q] = max(-x, 0.0), max(x, 0.0)
    roll = {q: [] for q in PORTFOLIOS}
    for t in range(HORIZON):
        u = units(p["books"][t], p["decs"][t])
        for q in PORTFOLIOS:
            end = -(change1 or {}).get(q, 0.0) if t == 0 else 0.0
            r = ifrs17.roll(csm[q], float(np.expm1(fwd[t])), u[q][0], u[q][1], end=end)
            fs_ra = fs_ra1[q] if t == 0 else 0.0
            r["ra_release"] = ra[t][q] - ra[t + 1][q] + fs_ra
            r["experience"] = (variance1 or {}).get(q, 0.0) if t == 0 else 0.0
            r["service_result"] = r["release"] + r["ra_release"] + r["experience"] - r["loss"]
            roll[q].append(r)
            csm[q] = r["close"]
    csm_t = [sum(max(csm0[q] - (change0 or {}).get(q, 0.0), 0.0) for q in PORTFOLIOS)]
    csm_t += [sum(roll[q][t]["close"] for q in PORTFOLIOS) for t in range(HORIZON)]
    equity = [y["own_funds"] - c for y, c in zip(years, csm_t)]
    profit = list(np.diff(equity))
    service = [sum(roll[q][t]["service_result"] for q in PORTFOLIOS) for t in range(HORIZON)]
    # What the CSM absorbed of the future-service changes (positive: used up), beyond which they were losses.
    used = sum((change0 or {}).get(q, 0.0) - loss0[q] for q in PORTFOLIOS) - sum(
        roll[q][0]["adjustment"] + roll[q][0]["loss"] for q in PORTFOLIOS)
    r2 = max(abs((y["own_funds"] - e) - c) / max(abs(c), 1.0) for y, e, c in zip(years, equity, csm_t))
    return {"coc": coc_fv, "csm_transition": csm0, "fs_change_t0": change0, "loss_t0": loss0, "fs_change_t1": change1,
            "experience_t1": variance1, "fs_ra_t0": fs_ra0, "roll": roll, "csm": csm_t, "equity": equity,
            "csm_used": used, "losses": sum(loss0.values()) + sum(r["loss"] for q in PORTFOLIOS for r in roll[q]),
            "profit": profit, "service_result": service, "finance_result": [a - s for a, s in zip(profit, service)],
            "R2_relative": r2}


# --- workers ---------------------------------------------------------------------------------------------------------

def _init(ctx: dict) -> None:
    CTX.update(ctx)


def _scenario(job) -> dict:
    betas, cal_key, rematch = job
    cal = CTX["cal"][cal_key]
    curves = [sv.forwards(cal, CTX["fwd0"], beta) for beta in betas]
    p = path(curves, CTX["book0"], CTX["r0"], rematch=rematch)
    return {"cover": p["cover"], "own_funds": p["own_funds"], "scr": p["scr"],
            "inflation": [y.get("inflation_realised") for y in p["years"][1:]]}


def scenarios(sims: np.ndarray, cal_key: str, rematch: bool, ctx: dict) -> list[dict]:
    jobs = [(s, cal_key, rematch) for s in sims]
    with ProcessPoolExecutor(os.cpu_count(), initializer=_init, initargs=(ctx,)) as ex:
        return list(ex.map(_scenario, jobs, chunksize=8))


# --- checks and summaries --------------------------------------------------------------------------------------------

def check_r1(book0: Book) -> dict:
    """R1: year-1 curves the valuation curves rolled a year, inflation held at t = 0's breakeven."""
    fwd0 = CTX["fwd0"]
    cv0 = Curves(fwd0["nominal"], fwd0["real"])
    nom, real = cv0.get(BASE)
    L0 = liabilities(book0, cv0, BASE)
    e = L0["inflation"]
    dec = decrements(book0)
    cf = flows(book0, nom, real, dec, e=e)
    b1 = age(book0, dec, 0.0, e)
    one = locked(1)
    L1 = liabilities(b1, Curves(one["nominal"], one["real"]), BASE, e=e)
    ilb = book0.ilb
    parts = {"income_ilb": (L0["income"][ilb].sum(), L1["income"][b1.ilb].sum(), real),
             "income_nominal": (L0["income"][~ilb].sum(), L1["income"][~b1.ilb].sum(), nom),
             **{k: (L0[k].sum(), L1[k].sum(), nom) for k in ("ann_expenses", "claims", "premiums", "fun_expenses")}}
    rel = {k: float(abs(v1 + cf[k] - v0 / float(c.df(1.0))) / abs(v0 / float(c.df(1.0)))) for k, (v0, v1, c) in parts.items()}
    return {"relative": rel, "worst": max(rel.values()), "pass": bool(max(rel.values()) < 1e-8)}


def pandemic_ratio(deaths: str, population: str) -> dict:
    d = data.statssa(deaths, population)
    d = d[d["age"].between(*PANDEMIC_AGES) & d["year"].isin(PANDEMIC)]
    g = d.groupby(["year", "sex"])[["deaths", "exposure"]].sum()
    rate = g["deaths"] / g["exposure"]
    return {s: float(rate[PANDEMIC[1], s] / rate[PANDEMIC[0], s]) for s in rate.index.get_level_values("sex").unique()}


def pct(x, q=(5, 25, 50, 75, 95)) -> dict:
    x = np.asarray(x, float)
    return {str(k): list(np.percentile(x, k, axis=0)) for k in q}


def ten_year(cal: dict, betas: np.ndarray) -> dict:
    """Annual 10-year spot rates of each kind at the year-ends: (..., 6) for factors (..., 6, factors)."""
    out = {}
    for i, k in enumerate(sv.KINDS):
        z0 = float(sam.Curve(CTX["fwd0"][k]).zt(10.0)) / 10
        tau = cal["tau"][k]
        dz = sv.ten(sv.kind(cal, betas, i), tau) - sv.ten(sv.kind(cal, cal["beta0"], i), tau)
        out[k] = np.expm1(z0 + dz)
    return out


def esg_checks(cal: dict, sims: np.ndarray) -> dict:
    e1, e2 = {}, {}
    for i, k in enumerate(sv.KINDS):
        z = sv.ten(sv.kind(cal, sims, i), cal["tau"][k])
        change = z[:, 1] - z[:, 0]
        ratio = float(change.std(ddof=1) / cal["hist_sd_12m"][k])
        e1[k] = {"scenario_sd": float(change.std(ddof=1)), "history_sd": cal["hist_sd_12m"][k], "ratio": ratio,
                 "pass": bool(0.75 <= ratio <= 1.33)}
        spot = float(sam.Curve(CTX["fwd0"][k]).spot(10.0))
        shock = float(np.interp(10.0, sam.TERMS, sam.NOMINAL_DOWN if k == "nominal" else -sam.REAL)) * spot
        e2[k] = {"scenario_q005": float(np.quantile(change, 0.005)), "sam_down_10y": shock, "spot_10y": spot}
    return {"E1": e1, "E2": e2}


def spread(res: list[dict]) -> dict:
    cover = np.array([r["cover"] for r in res])
    return {"cover": pct(cover), "below_one_share": float(np.mean((cover < 1.0).any(axis=1))),
            "below_one_by_year": list(np.mean(cover < 1.0, axis=0)), "worst": float(cover.min()),
            "A1": {"share_covered": float(np.mean((cover >= 1.0).all(axis=1))),
                   "pass": bool(np.mean((cover >= 1.0).all(axis=1)) >= 0.95)}}


# --- main ------------------------------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3),
              "v4": require_frozen(PROTOCOL_V4)}
    if not (BOOK / "funeral.csv").exists():
        raise SystemExit("run python -m research.book_v3 first")

    bonds = rc.book()
    a = auctions(bonds)
    curves, bonds, days, settle = market(a)
    grids = annuitant_grids(args.deaths, args.population)
    out = compute(a, curves, bonds, days, settle, grids, args.deaths, args.population)
    out = {"protocol": frozen, **out}
    (OUT / "projection_v4.json").write_text(json.dumps(out, indent=1, default=float))
    s = out["scenarios"]
    print("cover p5/p50/p95 by year", [np.round(s["cover"][q], 3) for q in ("5", "50", "95")])
    print("below one", s["below_one_share"], "A1", s["A1"], "R1", out["checks"]["R1"]["worst"], "R2", out["checks"]["R2"])
    print("E1", {k: round(v["ratio"], 3) for k, v in out["checks"]["E1"].items()})


def compute(a, curves, bonds, days, settle, grids, deaths: str, population: str, n: int = sv.N,
            make_book=None) -> dict:
    """`make_book(basis)`, if given, builds the book (v5 and later); by default v3's book on v3's table."""
    table = pd.read_csv(TABLE)
    fwd0 = curves["LI"]
    CTX.update(grids=grids, table=table, bonds=bonds, settle=settle, fwd0=fwd0)
    make_book = make_book or (lambda basis: Book(grids, table, basis))

    # The scenario generator.
    points = sv.month_points(a)
    jump = {k: rc.window(a[a["kind"] == kind], days[k][1], rc.WINDOW, inclusive=True) for k, kind in sv.KINDS.items()}
    cal = sv.calibrate(points, jump)
    cal_covid = sv.calibrate(points, jump, exclude=sv.COVID)
    cal_frozen = sv.calibrate(points, jump, n=3)
    sims, central = sv.paths(cal, n)
    sims_covid, _ = sv.paths(cal_covid, n)
    sims_frozen, _ = sv.paths(cal_frozen, n)
    print("tau", cal["tau"], "phi", np.round(cal["ar"].phi, 4), "capped", cal["ar"].capped, flush=True)

    book0 = start(make_book(Basis()))
    r0 = valuation(book0, fwd0, settle)
    CTX.update(book0=book0, r0=r0, cal={"main": cal, "covid": cal_covid, "frozen": cal_frozen})
    print(f"t=0 cover {r0['cover']:.4f}", flush=True)

    # The central path and the named stresses.
    fw = lambda betas, c=cal: [sv.forwards(c, fwd0, beta) for beta in betas]
    central_curves = fw(central)
    base = path(central_curves, book0, r0, keep=True)
    ra0 = dict(r0["risk_margin_parts"])
    fcf0 = fcf_locked(book0, 0)

    fall = cal["beta0"].copy()
    fall[[0, cal["n"]]] -= RATE_FALL
    fall_curves = fw(cal["ar"].central(fall, sv.MONTHS)[::12])
    ratio = pandemic_ratio(deaths, population)
    long_book = start(make_book(Basis(annuitant_adj=LONGEVITY_ADJ)))
    wave_book = lapse_wave(book0, LAPSE_WAVE)
    stresses = {
        "S1 Rates fall": dict(curves=fall_curves, book=book0),
        "S2 Longevity": dict(curves=central_curves, book=long_book),
        "S3 Pandemic year": dict(curves=central_curves, book=book0, pandemic=ratio),
        "S4 Lapse wave": dict(curves=central_curves, book=wave_book),
        "S5 All at once": dict(curves=fall_curves, book=wave_book, pandemic=ratio),
    }
    stressed, stressed_ifrs = {}, {}
    for name, s in stresses.items():
        assets0 = revalue(r0, settle, s["curves"][0])
        p = path(s["curves"], s["book"], assets0=assets0, holdings0=r0["assets"]["holdings"],
                 pandemic=s.get("pandemic"), keep=True)
        change0 = None
        if s["book"] is not book0:
            after = fcf_locked(s["book"], 0)
            change0 = {q: after[q] - fcf0[q] for q in PORTFOLIOS}
            change0["ra"] = {q: after["ra"][q] - fcf0["ra"][q] for q in PORTFOLIOS}
        change1 = variance1 = None
        if s.get("pandemic"):
            b = s["book"]
            nom0, real0 = Curves(s["curves"][0]["nominal"], s["curves"][0]["real"]).get(BASE)
            infl = inflation(s["curves"][0])
            dec_exp = decrements(b)
            expected = age(b, dec_exp, infl, infl)
            got, want = fcf_locked(p["books"][1], 1), fcf_locked(expected, 1)
            change1 = {q: got[q] - want[q] for q in PORTFOLIOS}
            change1["ra"] = {q: got["ra"][q] - want["ra"][q] for q in PORTFOLIOS}
            cf_exp = flows(b, nom0, real0, dec_exp)
            variance1 = {q: cf_exp[q] - p["cash"][0][q] for q in PORTFOLIOS}
        stressed_ifrs[name] = ifrs(p, ra0, ifrs17.COC_FAIR_VALUE, change0, change1, variance1)
        cover = p["cover"]
        short = [max(y["scr"] - y["own_funds"], 0.0) for y in p["years"]]
        stressed[name] = {"cover": cover, "own_funds": p["own_funds"], "scr": p["scr"],
                          "years": p["years"], "capital_to_restore": max(short),
                          "worst_year": int(np.argmin(cover)),
                          "csm_used": stressed_ifrs[name]["csm_used"], "losses": stressed_ifrs[name]["losses"],
                          "A2": bool(min(cover) >= 1.0)}
        print(name, np.round(cover, 3), flush=True)

    ifrs_central = {str(c): ifrs(base, ra0, c) for c in COC_FV}
    no_rematch_central = path(central_curves, book0, r0, rematch=False)

    # The scenarios.
    ctx = {k: CTX[k] for k in ("grids", "table", "bonds", "settle", "fwd0", "book0", "r0", "cal") + CTX.get("extra", ())}
    res = scenarios(sims, "main", True, ctx)
    print("scenarios done", flush=True)
    res_covid = scenarios(sims_covid, "covid", True, ctx)
    res_hold = scenarios(sims, "main", False, ctx)
    res_frozen = scenarios(sims_frozen, "frozen", True, ctx)

    csm_central = ifrs_central[str(ifrs17.COC_FAIR_VALUE)]["csm"]
    of = np.array([r["own_funds"] for r in res])
    profit = np.diff(of - np.array(csm_central), axis=1)
    rates = ten_year(cal, sims)
    rates_central = ten_year(cal, central)
    hist = {k: {"dates": [str(d.date()) for d in v.index], "rate": list(np.expm1(v.to_numpy()))} for k, v in cal["z10"].items()}

    out = {
        "valuation_date": str(days["real"][1].date()), "settle": str(settle),
        "esg": {**sv.summary(cal), "checks": esg_checks(cal, sims),
                "ten_year": {k: {"central": list(rates_central[k]), **pct(v)} for k, v in rates.items()},
                "history": hist, "covid_excluded": {**sv.summary(cal_covid), "checks": esg_checks(cal_covid, sims_covid)},
                "frozen_three_factor": {**sv.summary(cal_frozen), "checks": esg_checks(cal_frozen, sims_frozen),
                                        "ten_year": {k: pct(v) for k, v in ten_year(cal_frozen, sims_frozen).items()},
                                        "history": {k: list(np.expm1(v.to_numpy())) for k, v in cal_frozen["z10"].items()},
                                        "cover": spread(res_frozen)}},
        "t0": slim(r0),
        "central": {"years": base["years"], "cover": base["cover"]},
        "ifrs17": ifrs_central,
        "transition": {"ra": ra0, "confidence": ifrs17.confidence(r0["risk_margin"], r0["scr_ru"]["t0"]),
                       "csm": ifrs_central[str(ifrs17.COC_FAIR_VALUE)]["csm_transition"]},
        "scenarios": {**spread(res), "profit": pct(profit), "own_funds": pct(of),
                      "inflation": pct(np.array([r["inflation"] for r in res]))},
        "stresses": stressed, "stresses_ifrs17": stressed_ifrs, "pandemic_ratio": ratio,
        "sensitivities": {"covid_excluded": spread(res_covid), "no_rematch": spread(res_hold),
                          "no_rematch_central": {"cover": no_rematch_central["cover"]}},
        "checks": {"R1": check_r1(book0),
                   "R2": {"worst_relative": max([v["R2_relative"] for v in ifrs_central.values()]
                                                + [v["R2_relative"] for v in stressed_ifrs.values()])},
                   **esg_checks(cal, sims),
                   "A1": spread(res)["A1"],
                   "A2": {k: v["A2"] for k, v in stressed.items()}},
    }
    out["checks"]["R2"]["pass"] = bool(out["checks"]["R2"]["worst_relative"] < 1e-6)
    return out


if __name__ == "__main__":
    main()
