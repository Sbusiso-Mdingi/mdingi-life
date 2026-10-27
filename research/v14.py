"""v1.4 (research/PROTOCOL_v1.4.md): the chain of graduated base tables with mortality jumps, against v1.

    python -m research.v14 boot --part 0 --cores 8,4    # on each machine: its share of the bootstrap refits
    python -m research.v14 stage1                       # everything but 2024's deaths, and condition 6's power
    python -m research.v14 stage2                       # the completeness check, then 2024

The refits are split into chunks with their own seeds (SeedSequence(SEED, (job, refit))), so the result does not
depend on how they are spread over machines. `boot` writes research/results/v14_parts/part{n}.pkl; stage 1 reads
every part and writes research/results/v14_stage1.json; stage 2 is the only step that reads 2024's deaths, and
writes research/results/v14.json. --simulated runs the whole thing on simulated panels with a few refits (smoke
test; writes under v14_simulated/). Refuses to run until PROTOCOL_v1.4.md is frozen.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import json
import multiprocessing as mp
import pickle
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from mdingilife import annuity, bootstrap, data, graduation, jumps, kannisto, scores
from mdingilife.data import SEXES, Rates
from mdingilife.models import B0, RenshawHaberman
from mdingilife.protocol import PROTOCOL_V1_4, require_frozen
from research.annuities import ADJ, ENTRY_AGES, RATES, YEAR
from research.backtest import OUT
from research.completeness import SCALED
from research.export import e65
from research.exposure import OUT as POPULATION, P0302
from research.mcd import OUT as DEATHS

SEED, REFITS, PER, C6_PER, SMOKE_REFITS = 20261031, 500, 10, 2, 4
P = {"1/30": 1 / 30, "1/15": 1 / 15, "1/60": 1 / 60}
CENTRAL = "1/30"
GAGES, AGES = np.arange(45, 90), np.arange(50, 90)
LINKS = {  # base years, last fitted year, scored years, jump sizes estimated
    "L1": ((1997, 1999), 1999, (2004, 2005, 2006), False),
    "L2": ((2004, 2006), 2006, (2010, 2011, 2012), False),
    "L3": ((2010, 2012), 2012, (2017, 2018, 2019), False),
    "L4": ((2017, 2019), 2019, (2020, 2021, 2022), False),
    "L5": ((2017, 2019), 2022, (2024,), True),
}
VARIANTS = {"central": {}, "mu_y=0.05": {"mu_y": 0.05}, "mu_y=0.30": {"mu_y": 0.30}, "scaled": {}}
V1_LINKS = {"L3": (2012, (2017, 2018, 2019)), "L45": (2019, (2020, 2021, 2022, 2023, 2024))}
V1_PROD_LAST = 2019                         # v1's production fit: 2006 to 2022 with Covid out
COVERED = {120: (108, 117), 40: (36, 39)}
START = YEAR - 2022 - 1                     # 2026 is the fourth year after 2022
H_PRICE = START + kannisto.TOP - min(ENTRY_AGES) + 1
E65_YEARS = (2026, 2036, 2056)
RISE, POWER, BAND_PP, MIN_RATIO = 0.25, 0.5, 0.02, 0.85
MAX_FAILED = 0.01                           # set 27 October 2026, after seeing one refit fail (post-freeze record)
PRICE65 = [(x, i, a) for x in ENTRY_AGES for i in RATES for a in ADJ].index((65, 0.04, 0.7))
V1_PRICE65 = {"Male": 13.53, "Female": 16.05}   # v1's published production prices (RESULTS.md)
COST = {("J1", False): 0.5, ("decay", False): 1.5, ("J1", True): 3.0, ("decay", True): 16.0, "v1": 2.0}
CAVEAT = ("The 2024 population is WPP 2024's projection, not an estimate; an error in it passes one-for-one into "
          "2024's death rates, and the completeness check uses the same release, so it cannot catch this.")

SIM = False
PANELS: dict = {}
MAINS: dict = {}


def out_dir():
    return OUT / ("v14_simulated" if SIM else ".")


def refits() -> int:
    return SMOKE_REFITS if SIM else REFITS


def rng_for(*key) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=tuple(int(k) for k in key)))


# Data ---------------------------------------------------------------------------------------------------------

def load_panels() -> dict:
    """Registered and completeness-scaled deaths over WPP exposure, ages 45 to 89, 1997 to 2022 (no 2023 or 2024:
    the exposure file ends in 2022, so the merge drops them)."""
    if SIM:
        return simulated_panels()
    out = {}
    for name, path in (("registered", DEATHS), ("scaled", SCALED)):
        p = data.load("statssa", deaths=path, population=POPULATION)
        out[name] = {s: p[s].sub(GAGES, range(1997, 2023)) for s in SEXES}
    return out


def simulated_panels() -> dict:
    from tests.test_v14 import simulate
    out = {"registered": {}, "scaled": {}}
    for i, s in enumerate(SEXES):
        r = simulate(i, jump={2020: 0.10, 2021: 0.30, 2022: 0.08}, hiv=0.2, stream=7)
        r = Rates(s, r.ages, r.years, r.D, r.E)
        out["registered"][s] = r
        out["scaled"][s] = Rates(s, r.ages, r.years, np.round(r.D / 0.9), r.E)
    return out


def wpp_2024(kind: str) -> dict:
    """WPP 2024's medium-variant 2024 population ("Pop") or deaths ("Death") by single age, ages 0 to 100+."""
    if SIM:
        r = PANELS["registered"]
        last = {s: pd.Series(r[s].E[:, -1], index=r[s].ages) for s in SEXES}
        if kind == "Pop":
            return last
        return {s: pd.Series(r[s].D[:, -1] / 0.9, index=r[s].ages) for s in SEXES}
    name = "population" if kind == "Pop" else "deaths"
    f = pd.read_csv(data.WPP / f"wpp2024_zaf_{name}_2024.csv", usecols=["Time", "AgeGrp", f"{kind}Male", f"{kind}Female"])
    f = f[f["Time"] == 2024]
    age = f["AgeGrp"].replace("100+", "100").astype(int).to_numpy()
    return {s: pd.Series(1000 * f[f"{kind}{s}"].to_numpy(float), index=age) for s in SEXES}


def exposure_2024() -> dict:
    pop = wpp_2024("Pop")
    return {s: pop[s].reindex(AGES).to_numpy(float) for s in SEXES}


def statssa_2024(pop: dict) -> dict:
    """Stats SA's 2024 mid-year estimates, summed over population groups, split to single ages in WPP 2024's
    proportions within each five-year group (80+ over WPP's ages 80 and up), ages 50 to 89 kept."""
    if SIM:
        return {s: pop[s].reindex(AGES).to_numpy(float) * 1.01 for s in SEXES}
    p = pd.read_excel(P0302, header=4).iloc[:, :27]
    g = p[p["Population Group"].notna()].groupby(["Sex", "Age"])[2024].sum()
    out = {}
    for s in SEXES:
        w, E = pop[s], []
        for x in AGES:
            lo, hi = (80, 100) if x >= 80 else (5 * (x // 5), 5 * (x // 5) + 4)
            label = "80+" if x >= 80 else f"{lo}-{hi}"
            E.append(g[(s, label)] * w[x] / w.loc[lo:hi].sum())
        out[s] = np.array(E, float)
    return out


def registered_2024() -> dict:
    """2024's registered deaths at ages 50 to 89, unknown ages and sexes spread as for every other year. Stage 2 only."""
    if SIM:
        r = PANELS["registered"]
        rng = rng_for(9, 9, 9)
        return {s: rng.poisson(r[s].E[5:, -1] * np.exp(np.log(r[s].m[5:, 20:23]).mean(1)) * 1.02).astype(float)
                for s in SEXES}
    d = pd.read_csv(DEATHS)
    d = data._spread_sex(d[d["year"] == 2024]).astype({"age": int})
    return {s: d[d["sex"] == s].groupby("age")["deaths"].sum().reindex(AGES).to_numpy(float) for s in SEXES}


def ratios_2019_2022() -> dict:
    """Registered deaths at ages 50 to 89 over WPP's estimated deaths at those ages, 2019 and 2022."""
    out = {}
    r = PANELS["registered"]
    if SIM:
        return {s: {"2019": 0.9, "2022": 0.9} for s in SEXES}
    w = data.wpp()
    w = w[w["age"].isin(AGES)].groupby(["year", "sex"])["deaths"].sum()
    for s in SEXES:
        sub = r[s].sub(AGES)
        out[s] = {str(y): float(sub.D[:, list(sub.years).index(y)].sum() / w[(y, s)]) for y in (2019, 2022)}
    return out


# Jobs and tasks -----------------------------------------------------------------------------------------------

def jobs() -> list[tuple]:
    """(kind, sex, link, model, p, variant), in a fixed order: the index is the job's seed."""
    out = []
    for s in SEXES:
        for link in LINKS:
            for model in ("J1", "decay"):
                for p in P:
                    out.append(("chain", s, link, model, p, "central"))
        for link in ("L1", "L2", "L3", "L4"):
            for v in ("mu_y=0.05", "mu_y=0.30"):
                out.append(("chain", s, link, "J1", CENTRAL, v))
        for link in LINKS:
            out.append(("chain", s, link, "J1", CENTRAL, "scaled"))
        for v in ("central", "scaled"):
            for link in V1_LINKS:
                out.append(("v1", s, link, "RH", None, v))
        out.append(("v1prod", s, "prod", "RH", None, "central"))
    return out


def name(job: tuple) -> str:
    return "|".join(str(x) for x in job if x is not None)


def cost(job: tuple) -> float:
    if job[0] != "chain":
        return COST["v1"]
    est = LINKS[job[2]][3]
    return COST[(job[3], est)] * (0.6 if job[2] in ("L1", "L2") else 1.0)


def tasks() -> list[tuple]:
    """(job index, first refit, last refit + 1), chunks of about a minute of one core."""
    out = []
    for j, job in enumerate(jobs()):
        size = int(np.clip(round(60 / cost(job)), 1, 50))
        out += [(j, lo, min(lo + size, refits())) for lo in range(0, refits(), size)]
    return out


def assign(cores: list[int]) -> list[list[tuple]]:
    """Longest chunks first, each to the machine that would finish it soonest."""
    J = jobs()
    parts, load = [[] for _ in cores], [0.0] * len(cores)
    for t in sorted(tasks(), key=lambda t: (-cost(J[t[0]]) * (t[2] - t[1]), t)):
        c = cost(J[t[0]]) * (t[2] - t[1])
        k = min(range(len(cores)), key=lambda i: (load[i] + c) / cores[i])
        parts[k].append(t)
        load[k] += c
    return parts


# Fits ---------------------------------------------------------------------------------------------------------

def deaths_of(job: tuple) -> str:
    return "scaled" if job[5] == "scaled" else "registered"


def dispersion(panel: Rates, a: np.ndarray, b: np.ndarray, kappa: np.ndarray) -> float:
    """Step 4: Pearson chi-square of the step 1 fit over its residual df ((ages - 1) + years), floored at 1."""
    Dh = panel.E * np.exp(a[:, None] + np.outer(b, kappa))
    chi2 = float(((panel.D - Dh) ** 2 / Dh).sum())
    return max(chi2 / (panel.D.size - (len(a) - 1) - len(kappa)), 1.0)


def chain_fit(job: tuple, r: Rates, lam: float | None = None) -> dict:
    _, s, link, model, p, variant = job
    (b0, b1), last, _, est = LINKS[link]
    base = r.sub(years=range(b0, b1 + 1))
    g = graduation.graduate(base.D.sum(1), base.E.sum(1), lam)
    panel = r.sub(AGES, range(1997, last + 1))
    fixed = jumps.PRIOR | VARIANTS[variant]
    f = jumps.fit(panel, g["log_m"][5:], P[p], model, est, fixed)
    return {"g": g, "f": f, "panel": panel, "base": base}


def main_fit(j: int) -> dict:
    job = jobs()[j]
    r = PANELS[deaths_of(job)][job[1]]
    if job[0] == "chain":
        m = chain_fit(job, r)
        f = m["f"]
        m["phi"] = dispersion(m["panel"], f.a, f.extra["b"], f.extra["kappa"])
        m["checks"] = graduation.checks(m["base"].D.sum(1), m["base"].E.sum(1), m["g"]["log_m"], GAGES)
        return m
    last = V1_LINKS[job[2]][0] if job[0] == "v1" else V1_PROD_LAST
    fit = r.sub(AGES, range(2006, last + 1))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        m = RenshawHaberman().fit(fit)
    return {"model": m, "panel": fit, "phi": bootstrap.dispersion(m), "converged": bool(m.converged),
            "warnings": len(w)}


def project(f: jumps.JumpFit, h: int, n: int, rng, p: float):
    """K from K hat(T) as a random walk with the fit's drift and volatility, and jump draws I ~ Bernoulli(p),
    Y ~ Normal(mu_y, sd_y^2). Returns (K, walk, jumps J = I Y)."""
    s = f.series
    walk = np.cumsum(s.mu + s.sd * rng.standard_normal((n, h)), axis=1)
    J = (rng.random((n, h)) < p) * (s.mu_y + s.sd_y * rng.standard_normal((n, h)))
    return f.K[-1] + walk, walk, J


def jump_effect(f: jumps.JumpFit, J: np.ndarray, carry: bool = True) -> np.ndarray:
    """N over the projection: J itself for J1; for the decaying variant, rho N(t-1) + J(t), from N hat(T)."""
    if f.model == "J1":
        return J
    N, level = np.empty_like(J), np.full(J.shape[0], f.N[-1] if carry else 0.0)
    for t in range(J.shape[1]):
        level = f.series.rho * level + J[:, t]
        N[:, t] = level
    return N


def log_m(f: jumps.JumpFit, K: np.ndarray, N: np.ndarray, b=None) -> np.ndarray:
    b = f.b if b is None else b
    return f.a[None, :, None] + b[None, :, None] * K[:, None, :] + f.bJ[None, :, None] * N[:, None, :]


def pricing(lm: np.ndarray, jump_off: int, start: int) -> dict:
    """Per path: the 27 annuity factors (age, rate, annuitant factor) and e65 in E65_YEARS."""
    ages, full = kannisto.extend(lm, AGES)
    fac = np.stack([annuity.factor(annuity.cohort(full, ages, x, start), i, a)
                    for x in ENTRY_AGES for i in RATES for a in ADJ], axis=1)
    e = e65(lm, AGES)
    return {"factors": fac.astype(np.float32),
            "e65": e[:, [y - jump_off - 1 for y in E65_YEARS]].astype(np.float32)}


def chain_refit(j: int, i: int) -> dict:
    job = jobs()[j]
    _, s, link, model, p, variant = job
    M = MAINS[j]
    f, g, phi = M["f"], M["g"], M["phi"]
    (b0, b1), last, scored, est = LINKS[link]
    rng = rng_for(j, i)
    r = PANELS[deaths_of(job)][s].sub(years=range(1997, last + 1))
    D = r.D.copy()
    D[5:] = bootstrap.draw(r.E[5:] * np.exp(f.log_m(True)), phi, rng)
    cols = np.isin(r.years, range(b0, b1 + 1))
    D[:5, cols] = bootstrap.draw(r.E[:5, cols] * np.exp(g["log_m"][:5])[:, None], phi, rng)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        fj = chain_fit(job, Rates(s, r.ages, r.years, D, r.E), g["lam"])["f"]
    h = max(scored) - last
    yc = [y - last - 1 for y in scored]
    K, walk, J = project(fj, h, PER, rng, P[p])
    lm = log_m(fj, K, jump_effect(fj, J))
    sr = fj.series
    out = {"sims": lm[:, :, yc].astype(np.float32), "warnings": len(w),
           "params": {"mu": sr.mu, "sd": sr.sd, "mu_y": sr.mu_y, "sd_y": sr.sd_y, "rho": sr.rho, "cap": sr.cap,
                      "left_out": sr.left_out, "flagged": fj.flagged, "F": fj.F}}
    if link == "L4":
        out["nojump"] = log_m(fj, K, np.zeros_like(J))[:, :, yc].astype(np.float32)
    if link == "L5":
        if model == "J1":
            # condition 6: the permanent-shift model on the same walk and jump draws, from kappa(2022) with b0
            k0 = fj.extra["kappa"][-1] + walk[:C6_PER]
            out["c6_j1"] = out["sims"][:C6_PER, :, 0]
            out["c6_shift"] = log_m(fj, k0, J[:C6_PER], fj.extra["b"])[:, :, -1].astype(np.float32)
        K, _, J = project(fj, H_PRICE, PER, rng, P[p])
        out["trend_only"] = pricing(log_m(fj, K, jump_effect(fj, np.zeros_like(J))), last, START)
        out["with_jumps"] = pricing(log_m(fj, K, jump_effect(fj, J)), last, START)
    return out


def v1_refit(j: int, i: int) -> dict:
    job = jobs()[j]
    M = MAINS[j]
    m, fit = M["model"], M["panel"]
    rng = rng_for(j, i)
    mu = fit.E * np.exp(m.fitted())
    # v1.1's bootstrap (dispersion phi) for the scores; v1's own Poisson bootstrap for its production figures
    D = bootstrap.draw(mu, M["phi"], rng) if job[0] == "v1" else rng.poisson(mu).astype(float)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mj = RenshawHaberman().fit(Rates(fit.sex, fit.ages, fit.years, D, fit.E))
    if job[0] == "v1":
        last, scored = V1_LINKS[job[2]]
        sims = mj.forecast(max(scored) - last, PER, rng)
        return {"sims": sims[:, :, [y - last - 1 for y in scored]].astype(np.float32), "warnings": len(w),
                "converged": bool(mj.converged)}
    h = YEAR - V1_PROD_LAST - 1 + kannisto.TOP - min(ENTRY_AGES) + 1
    lm = mj.forecast(h, PER, rng)
    return {"prod": pricing(lm, V1_PROD_LAST, YEAR - V1_PROD_LAST - 1), "warnings": len(w),
            "converged": bool(mj.converged)}


def run_task(t: tuple) -> tuple:
    j, lo, hi = t
    kind = jobs()[j][0]
    res = {}
    for i in range(lo, hi):
        try:
            res[i] = (chain_refit if kind == "chain" else v1_refit)(j, i)
        except Exception as e:  # reported before anything is scored, never silently dropped
            res[i] = {"error": f"{type(e).__name__}: {e}"}
    return t, res


# Stage 0: the bootstrap ---------------------------------------------------------------------------------------

def boot(part: int, cores: list[int]) -> None:
    global MAINS
    mine = assign(cores)[part]
    need = sorted({t[0] for t in mine})
    ctx = mp.get_context("fork")
    t0 = time.time()
    with ProcessPoolExecutor(cores[part], mp_context=ctx) as ex:
        MAINS = dict(zip(need, ex.map(main_fit, need)))
    print(f"part {part}: {len(need)} main fits in {time.time() - t0:.0f}s; {len(mine)} chunks", flush=True)
    results, done, total = {}, 0.0, sum(cost(jobs()[t[0]]) * (t[2] - t[1]) for t in mine)
    with ProcessPoolExecutor(cores[part], mp_context=ctx) as ex:
        for k, (t, res) in enumerate(ex.map(run_task, mine)):
            results[t] = res
            done += cost(jobs()[t[0]]) * (t[2] - t[1])
            if k % 25 == 0 or k == len(mine) - 1:
                el = time.time() - t0
                print(f"part {part}: {k + 1}/{len(mine)} chunks, {el / 60:.1f} min, about "
                      f"{el * (total / done - 1) / 60:.0f} min left", flush=True)
    d = out_dir() / "v14_parts"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"part{part}.pkl", "wb") as fh:
        pickle.dump({"part": part, "cores": cores, "mains": MAINS, "results": results}, fh)
    print(f"part {part}: done in {(time.time() - t0) / 60:.1f} min", flush=True)


def gather() -> tuple[dict, dict, dict]:
    """Every part's main fits and refits, each job's good refits in order, and the failed ones. Stops if any chunk
    is missing. Failed refits are recorded and left out (added 27 October 2026, after seeing one fail: see the
    post-freeze record); a cell with more than MAX_FAILED of its refits failed is not scored."""
    mains, refit = {}, {}
    for path in sorted((out_dir() / "v14_parts").glob("part*.pkl")):
        with open(path, "rb") as fh:
            part = pickle.load(fh)
        mains |= part["mains"]
        for (j, lo, hi), res in part["results"].items():
            refit.setdefault(j, {}).update(res)
    J = jobs()
    missing = [name(J[j]) for j in range(len(J)) if len(refit.get(j, {})) != refits()]
    if missing:
        print(json.dumps({"missing": missing}, indent=1))
        sys.exit("refits are missing: nothing is scored. Report this before any fix.")
    failed = {name(J[j]): {"failed": [{"refit": i, "seed": [SEED, j, i], "error": r["error"]}
                                      for i, r in sorted(refit[j].items()) if "error" in r]} for j in refit}
    failed = {k: v for k, v in failed.items() if v["failed"]}
    for v in failed.values():
        v["refits_used"] = f"{refits() - len(v['failed'])} of {refits()} refits"
        v["scored"] = len(v["failed"]) <= MAX_FAILED * refits()
    print(json.dumps({"failed_refits": failed}, indent=1))
    good = {j: [refit[j][i] for i in range(refits()) if "error" not in refit[j][i]] for j in refit}
    return mains, good, failed


def unscored(failed: dict, key: str) -> bool:
    return key in failed and not failed[key]["scored"]


def label(failed: dict, key: str, res: dict) -> dict:
    """Marks a cell scored on fewer than all its refits ("499 of 500 refits")."""
    if key in failed:
        res = {"refits_used": failed[key]["refits_used"], "failed_refits": failed[key]["failed"]} | res
    return res


# Scores -------------------------------------------------------------------------------------------------------

def score(obs: Rates, sims: np.ndarray, noisy: np.ndarray, b0_dev: float) -> dict:
    lo_obs = np.log(obs.m)
    med = np.median(sims, axis=0)
    lo, hi = np.quantile(noisy, [0.025, 0.975], axis=0)
    inside = (lo_obs >= lo) & (lo_obs <= hi)
    err = scores.annuity_error(med, lo_obs, obs.ages)
    out = {"deviance": scores.deviance(obs.D, obs.E * np.exp(med)), "B0": b0_dev,
           "annuity_error": err.tolist(), "mean_abs_error": float(np.mean(np.abs(err))),
           "coverage": float(inside.mean()), "covered": int(inside.sum()), "cells": int(inside.size),
           "width": float(np.exp(hi - lo).mean())}
    lo_c, hi_c = COVERED[out["cells"]]
    out["tests"] = {"Q1": bool(out["deviance"] < b0_dev), "Q2": bool(lo_c <= out["covered"] <= hi_c),
                    "Q3": bool(out["mean_abs_error"] < 0.02)}
    return out


def b0_deviance(base: Rates, obs: Rates) -> float:
    flat = B0().fit(base.sub(AGES)).log_m
    return scores.deviance(obs.D, obs.E * np.exp(flat)[:, None] * np.ones(len(obs.years)))


def stack(rs: list, key: str) -> np.ndarray:
    return np.concatenate([r[key] for r in rs]).astype(float)


def quantiles(x, q=(0.025, 0.5, 0.975)) -> list:
    x = np.asarray(x, float)
    return np.quantile(x[np.isfinite(x)], q).tolist()


def priced(rs: list, key: str) -> dict:
    fac, e = stack([r[key] for r in rs], "factors"), stack([r[key] for r in rs], "e65")
    prices = [{"age": x, "rate": i, "adj": a, **dict(zip(("lo", "median", "hi"), quantiles(fac[:, k]))),
               "left_out": int((~np.isfinite(fac[:, k])).sum())}
              for k, (x, i, a) in enumerate((x, i, a) for x in ENTRY_AGES for i in RATES for a in ADJ)]
    return {"prices": prices, "price65": prices[PRICE65]["median"],
            "e65": {str(y): dict(zip(("lo", "median", "hi"), quantiles(e[:, k]))) for k, y in enumerate(E65_YEARS)}}


def roughness(x) -> float:
    return float((np.diff(np.asarray(x), 2) ** 2).sum())


def describe(M: dict, rs: list) -> dict:
    """The main fit as the plan's reporting list asks, and the refits' parameter ranges."""
    f, g, s = M["f"], M["g"], M["f"].series
    years = f.years.tolist()
    par = {k: quantiles([r["params"][k] for r in rs]) for k in ("mu", "sd", "mu_y", "sd_y", "rho")}
    return {
        "base": {"lam": g["lam"], "ed": g["ed"], "deviance": g["deviance"], "checks": M["checks"]},
        "phi": M["phi"], "years": years, "b": f.b.tolist(), "bJ": f.bJ.tolist(),
        "b_roughness": roughness(f.b), "bJ_roughness": roughness(f.bJ),
        "kappa_step1": f.extra["kappa"].tolist(), "kappa": f.kappa.tolist(), "K": f.K.tolist(), "N": f.N.tolist(),
        "params": {"mu": s.mu, "sd": s.sd, "mu_y": s.mu_y, "sd_y": s.sd_y, "rho": s.rho, "p": s.p,
                   "estimated": list(s.estimated), "sd_y_at_bound": bool(s.sd_y <= 1.0001e-4 and "sd_y" in s.estimated)},
        "loglik": s.loglik, "posterior": s.prob.tolist(), "flagged": f.flagged, "F": f.F,
        "cap": s.cap, "left_out": s.left_out,
        "refits": {"params": par, "warnings": int(sum(r["warnings"] for r in rs)),
                   "flagged_share": {str(y): float(np.mean([y in r["params"]["flagged"] for r in rs])) for y in years},
                   "cap_6_share": float(np.mean([r["params"]["cap"] == 6 for r in rs])) if f.model == "decay" else None,
                   "max_left_out": max(r["params"]["left_out"] for r in rs) if f.model == "decay" else None},
    }


def medians_2024(f: jumps.JumpFit) -> tuple[np.ndarray, np.ndarray]:
    """Condition 6's two medians: J1 from K hat(2022) + 2 mu, the shift model from kappa(2022) + 2 mu with b0."""
    mu = f.series.mu
    j1 = f.a + f.b * (f.K[-1] + 2 * mu)
    shift = f.a + f.extra["b"] * (f.extra["kappa"][-1] + 2 * mu)
    return j1, shift


def gap(D: np.ndarray, E: np.ndarray, j1: np.ndarray, shift: np.ndarray) -> np.ndarray:
    """G = the shift model's 2024 deviance minus J1's (deaths on the last axis)."""
    dev = lambda mu: 2 * np.where(D > 0, D * np.log(np.where(D > 0, D, 1) / mu), 0.0).sum(-1) - 2 * (D - mu).sum(-1)
    return dev(E * np.exp(shift)) - dev(E * np.exp(j1))


def simulated_gaps(j: int, M: dict, rs: list, E: np.ndarray, salt: int) -> dict:
    j1_med, shift_med = medians_2024(M["f"])
    out = {}
    for k, key in enumerate(("c6_j1", "c6_shift")):
        paths = stack(rs, key)
        D = bootstrap.draw(E * np.exp(paths), M["phi"], rng_for(j, 2_000_000 + salt + k))
        out[key] = gap(D, E, j1_med, shift_med)
    thr = float(np.quantile(out["c6_shift"], 0.95))
    return {"threshold_95_shift": thr, "power": float(np.mean(out["c6_j1"] > thr)), "sets": int(len(out["c6_j1"])),
            "G_under_J1": quantiles(out["c6_j1"]), "G_under_shift": quantiles(out["c6_shift"])}


def gate(p65: dict, e: dict) -> dict:
    rise = {s: e[s]["2036"] - e[s]["2026"] for s in e}
    women = p65["Female"] > p65["Male"]
    rising = all(v >= RISE for v in rise.values())
    return {"price65": p65, "e65": e, "women_above_men": bool(women), "e65_rise_2026_2036": rise,
            "e65_rising": bool(rising), "passes": bool(women and rising)}


# Stage 1 ------------------------------------------------------------------------------------------------------

def stage1() -> dict:
    mains, refit, failed = gather()
    J = jobs()
    E24 = exposure_2024()
    out = {"protocol_v1_4": None if SIM else require_frozen(PROTOCOL_V1_4), "seed": SEED, "refits": refits(),
           "paths": refits() * PER, "simulated": SIM, "failed_refits": failed, "not_scored": [],
           "chain": {}, "v1": {}, "pricing": {}, "condition6_power": {}}
    for j, job in enumerate(J):
        M, rs, key = mains[j], refit[j], name(job)
        if unscored(failed, key):
            out["not_scored"].append(key)
            continue
        if job[0] == "chain":
            _, s, link, model, p, variant = job
            (b0, b1), last, scored, _ = LINKS[link]
            res = describe(M, rs)
            if link == "L5":
                res["separation"] = jumps.separation(M["f"], M["panel"])
                j1_med, shift_med = medians_2024(M["f"])
                res["medians_2024"] = {"J1": j1_med.tolist(), "shift": shift_med.tolist()}
            if link != "L5":
                r = PANELS[deaths_of(job)][s]
                obs = r.sub(AGES, scored)
                sims = stack(rs, "sims")
                b0d = b0_deviance(M["base"], obs)
                res["score"] = score(obs, sims, bootstrap.observe(sims, obs.E, M["phi"], rng_for(j, 1_000_001)), b0d)
                if link == "L4":
                    nj = stack(rs, "nojump")
                    res["nojump"] = score(obs, nj, bootstrap.observe(nj, obs.E, M["phi"], rng_for(j, 1_000_001)), b0d)
                    res["Q2R"] = bool(res["score"]["covered"] >= res["nojump"]["covered"])
            else:
                out["pricing"][key] = label(failed, key, {"trend_only": priced(rs, "trend_only"),
                                                          "with_jumps": priced(rs, "with_jumps")})
                if model == "J1":
                    out["condition6_power"][key] = label(failed, key, simulated_gaps(j, M, rs, E24[s], 0))
            out["chain"][key] = label(failed, key, res)
        elif job[0] == "v1":
            _, s, link, _, _, variant = job
            last, scored = V1_LINKS[link]
            sims = stack(rs, "sims")
            res = {"phi": M["phi"], "converged": M["converged"], "refits_not_converged": int(sum(not r["converged"] for r in rs))}
            if link == "L3":
                parts = {"L3": (scored, None)}
            else:
                parts = {"L4": ((2020, 2021, 2022), None)}
            r = PANELS[deaths_of(job)][s]
            for lk, (yrs, _) in parts.items():
                obs = r.sub(AGES, yrs)
                cols = [scored.index(y) for y in yrs]
                sm = sims[:, :, cols]
                base = r.sub(years=range(*(LINKS[lk][0][0], LINKS[lk][0][1] + 1)))
                res[lk] = score(obs, sm, bootstrap.observe(sm, obs.E, M["phi"], rng_for(j, 1_000_001)),
                                b0_deviance(base, obs))
            out["v1"][key] = label(failed, key, res)
        else:
            out["v1"][key] = {"phi": M["phi"], "converged": M["converged"],
                              "refits_not_converged": int(sum(not r["converged"] for r in rs)),
                              "production": priced(rs, "prod"), "price65_published": V1_PRICE65[job[1]]}
            out["v1"][key] = label(failed, key, out["v1"][key])
    out["gate"] = gates(out)
    path = out_dir() / "v14_stage1.json"
    path.write_text(json.dumps(out, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
    print(json.dumps({"condition6_power": out["condition6_power"], "gate": out["gate"],
                      "not_scored": out["not_scored"]}, indent=1, default=float))
    print(f"wrote {path}")
    return out


def gates(out: dict) -> dict:
    """The plausibility gate on the central pricing projections, and on each mixed set (v1 for the other sex:
    its published price at 65 and its production e65 from this run)."""
    pr = out["pricing"]
    figs = lambda key: {s: (pr[f"chain|{s}|L5|{key}"]["trend_only"]["price65"],
                            {y: pr[f"chain|{s}|L5|{key}"]["trend_only"]["e65"][y]["median"] for y in ("2026", "2036")})
                        for s in SEXES}
    v1 = {s: (V1_PRICE65[s], {y: out["v1"][f"v1prod|{s}|prod|RH|central"]["production"]["e65"][y]["median"]
                              for y in ("2026", "2036")}) for s in SEXES}
    res = {}
    for key in (f"J1|{CENTRAL}|central", f"decay|{CENTRAL}|central", f"J1|{CENTRAL}|scaled"):
        f = figs(key)
        res[key] = gate({s: f[s][0] for s in SEXES}, {s: f[s][1] for s in SEXES})
    f = figs(f"J1|{CENTRAL}|central")
    for s in SEXES:
        other = [x for x in SEXES if x != s][0]
        mix = {s: f[s], other: v1[other]}
        res[f"mixed: {s} on v1.4, {other} on v1"] = gate({x: mix[x][0] for x in SEXES}, {x: mix[x][1] for x in SEXES})
    res["v1"] = gate({s: v1[s][0] for s in SEXES}, {s: v1[s][1] for s in SEXES})
    return res


# Stage 2 ------------------------------------------------------------------------------------------------------

def stage2() -> dict:
    s1 = json.loads((out_dir() / "v14_stage1.json").read_text())
    mains, refit, failed = gather()
    J = jobs()
    pop = wpp_2024("Pop")
    E24, Ess = exposure_2024(), statssa_2024(pop)
    wd = wpp_2024("Death")
    D24 = registered_2024()
    old = ratios_2019_2022()
    comp = {}
    for s in SEXES:
        r24 = float(D24[s].sum() / wd[s].reindex(AGES).sum())
        c = {"2024": r24, **old[s]}
        c["passes"] = bool(r24 >= MIN_RATIO and all(abs(r24 - c[y]) <= BAND_PP for y in ("2019", "2022")))
        comp[s] = c
    scored = all(c["passes"] for c in comp.values())
    out = {"completeness": comp, "L5_scored": scored, "caveat": CAVEAT, "L5": {}, "v1_L5": {}, "condition6": {}}
    for j, job in enumerate(J):
        M, rs, key = mains[j], refit[j], name(job)
        if unscored(failed, key):
            continue
        if job[0] == "chain" and job[2] == "L5":
            s, variant = job[1], job[5]
            D = D24[s] / comp[s]["2024"] if variant == "scaled" else D24[s]
            res = {}
            for pop_name, E, salt in (("wpp", E24[s], 1), ("statssa", Ess[s], 2)):
                obs = Rates(s, AGES, np.array([2024]), D[:, None], E[:, None])
                sims = stack(rs, "sims")
                b0d = b0_deviance(M["base"], obs)
                res[pop_name] = score(obs, sims, bootstrap.observe(sims, obs.E, M["phi"], rng_for(j, 1_000_000 + salt)), b0d)
            out["L5"][key] = label(failed, key, res)
            if job[3] == "J1":
                j1_med, shift_med = medians_2024(M["f"])
                pw = s1["condition6_power"][key]
                G = float(gap(D, E24[s], j1_med, shift_med))
                c6 = {"G": G, "threshold_95_shift": pw["threshold_95_shift"], "passes": bool(G > pw["threshold_95_shift"]),
                      "power": pw["power"], "G_under_J1": pw["G_under_J1"], "G_under_shift": pw["G_under_shift"]}
                D22 = D24[s] * comp[s]["2022"] / comp[s]["2024"]
                if variant == "central":
                    Gs = float(gap(D22, E24[s], j1_med, shift_med))
                    c6["scaled_to_2022"] = {"G": Gs, "passes": bool(Gs > pw["threshold_95_shift"])}
                    c6["flips"] = c6["scaled_to_2022"]["passes"] != c6["passes"]
                ss = simulated_gaps(j, M, rs, Ess[s], 10)
                Gss = float(gap(D, Ess[s], j1_med, shift_med))
                c6["statssa_population"] = ss | {"G": Gss, "passes": bool(Gss > ss["threshold_95_shift"])}
                out["condition6"][key] = label(failed, key, c6)
        elif job[0] == "v1" and job[2] == "L45":
            s, variant = job[1], job[5]
            D = D24[s] / comp[s]["2024"] if variant == "scaled" else D24[s]
            sims = stack(rs, "sims")[:, :, [-1]]
            base = PANELS[deaths_of(job)][s].sub(years=range(2017, 2020))
            res = {}
            for pop_name, E, salt in (("wpp", E24[s], 1), ("statssa", Ess[s], 2)):
                obs = Rates(s, AGES, np.array([2024]), D[:, None], E[:, None])
                res[pop_name] = score(obs, sims, bootstrap.observe(sims, obs.E, M["phi"], rng_for(j, 1_000_000 + salt)),
                                      b0_deviance(base, obs))
            out["v1_L5"][key] = label(failed, key, res)
    out["decision"] = decide(s1, out)
    full = s1 | {"stage2": out}
    path = out_dir() / "v14.json"
    path.write_text(json.dumps(full, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
    print(json.dumps({"completeness": comp, "decision": out["decision"]}, indent=1, default=float))
    print(f"wrote {path}")
    return full


def decide(s1: dict, s2: dict) -> dict:
    ch, v1 = s1["chain"], s1["v1"]
    k = lambda s, link, variant="central", model="J1": f"chain|{s}|{link}|{model}|{CENTRAL}|{variant}"
    lost = [k(s, "L5") for s in SEXES if k(s, "L5") in s1["not_scored"]]
    if lost:  # more than 1% of a primary L5 cell's refits failed: v1.4 does not price
        return {"primary_L5_not_scored": lost, "prices_on": {s: "v1" for s in SEXES}}
    by_sex, hiv = {}, {}
    for s in SEXES:
        l3, l4 = ch[k(s, "L3")], ch[k(s, "L4")]
        l5 = s2["L5"][k(s, "L5")]["wpp"]
        v13, v15 = v1[f"v1|{s}|L3|RH|central"]["L3"], s2["v1_L5"][f"v1|{s}|L45|RH|central"]["wpp"]
        c6 = s2["condition6"][k(s, "L5")]
        sep = ch[k(s, "L5")]["separation"]
        c = {
            "1_L5_scored_and_passes": bool(s2["L5_scored"] and all(l5["tests"].values())),
            "2_L3_Q1_Q3_and_L4_Q2R": bool(all(l3["score"]["tests"].values()) and l4["Q2R"]),
            "3_deviance_L3_L5_below_v1": bool(l3["score"]["deviance"] + l5["deviance"] < v13["deviance"] + v15["deviance"]),
            "4_separation": bool(sep["passes"]),
            "6_jump_not_shift": bool(s2["L5_scored"] and c6["passes"] and c6["power"] >= POWER and not c6["flips"]),
        }
        by_sex[s] = {"conditions": c, "passes_1_to_4_and_6": all(c.values()),
                     "deviance": {"L3": l3["score"]["deviance"], "L5": l5["deviance"],
                                  "v1_L3": v13["deviance"], "v1_L5": v15["deviance"]}}
        hiv[s] = {"passes_Q1_Q3": all(l3["score"]["tests"].values()),
                  "below_v1": bool(l3["score"]["deviance"] < v13["deviance"])}
    ok = [s for s in SEXES if by_sex[s]["passes_1_to_4_and_6"]]
    g = s1["gate"]
    if len(ok) == 2:
        gate_used = g[f"J1|{CENTRAL}|central"]
    elif len(ok) == 1:
        other = [x for x in SEXES if x != ok[0]][0]
        gate_used = g[f"mixed: {ok[0]} on v1.4, {other} on v1"]
    else:
        gate_used = None
    on = {s: ("v1.4" if s in ok and gate_used and gate_used["passes"] else "v1") for s in SEXES}
    both = all(hiv[s]["passes_Q1_Q3"] for s in SEXES)
    hiv_verdict = ("handles the HIV years" if both and all(hiv[s]["below_v1"] for s in SEXES)
                   else "no better than v1" if both else "does not handle the HIV years")
    return {"by_sex": by_sex, "gate_used": gate_used, "primary_L5_not_scored": lost, "prices_on": on, "hiv": hiv | {"verdict": hiv_verdict}}


def main() -> None:
    global SIM, PANELS
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("boot", "stage1", "stage2", "plan"))
    ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--cores", default="8,4")
    ap.add_argument("--simulated", action="store_true")
    a = ap.parse_args()
    SIM = a.simulated
    if not SIM:
        require_frozen(PROTOCOL_V1_4)
    PANELS = load_panels()
    cores = [int(c) for c in a.cores.split(",")]
    if a.step == "plan":
        J = jobs()
        for k, part in enumerate(assign(cores)):
            load = sum(cost(J[t[0]]) * (t[2] - t[1]) for t in part)
            print(f"part {k}: {len(part)} chunks, about {load / cores[k] / 60:.0f} min on {cores[k]} cores")
    elif a.step == "boot":
        boot(a.part, cores)
    elif a.step == "stage1":
        stage1()
    else:
        stage2()


if __name__ == "__main__":
    main()
