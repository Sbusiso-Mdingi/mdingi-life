"""v7's funeral book (research/PROTOCOL_v7.md, "The product"): v5's policies, the benefit fixed, each paying a level
premium for life or an age-rated premium by its own schedule, set by v5's benefit draw ("rising" now age-rated).

    python -m research.book_v7 [--write]

Prints F2 (level premiums are v5's to the cent) and F4 (every schedule premium satisfies its year's equation), and
monthly premiums per R10,000 by age for each type. With --write, writes data/book/funeral_v7.csv (each policy's
premium in the current policy year) and research/results/funeral_schedule_v7.csv (the age-rated rates by sex, entry
age and policy year). Refuses to run until PROTOCOL_v7.md is frozen.

Policy year j counts from 0 here (policy year j + 1 in the protocol's lapse numbering): for entry age e, year j is
age e + j in calendar year 2026 + j, priced as if the policy started on the valuation date, as v5's level premium.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from mdingilife import data, sam, table_v5 as t5
from mdingilife.protocol import PROTOCOL_V7, require_frozen
from research import book_v3 as b3
from research import book_v5 as bk
from research.backtest import OUT

FUNERAL = b3.BOOK / "funeral_v7.csv"
SCHEDULE = OUT / "funeral_schedule_v7.csv"
TYPES = {"level": "level", "rising": "age-rated"}      # v5's benefit draw, reused as the premium type
TOP = t5.TOP


def year_parts(g: dict, sex, entry, adj: float = 1.0) -> dict:
    """(cells, years) each: the expected value of the year's monthly premiums of 1 (a), death claims per rand (A) and
    expenses (E) for each policy year, on the pricing basis, discounted to the start of the year, with survival
    within the year only. `adj` multiplies the force (the review variant prices on the stressed force)."""
    years = TOP - int(np.min(entry)) + 1
    mu = bk.mu_rows(g, sex, entry, years, adj)
    cells = len(mu)
    inforce, deaths = sam.project(mu.reshape(-1, 1))           # each (cell, year) on its own, 12 months
    p = b3.PRICING
    m = np.arange(12)
    v = (1 + p["interest"]) ** -(m / 12)
    v_mid = (1 + p["interest"]) ** -(m / 12 + 1 / 24)
    j = np.arange(years)
    cost = b3.EXPENSE["funeral"] / 12 * (1 + p["inflation"]) ** (j[:, None] + m[None, :] / 12)   # (years, 12)
    a = (inforce @ v).reshape(cells, years)
    A = (deaths @ v_mid).reshape(cells, years)
    E = np.sum(inforce.reshape(cells, years, 12) * cost[None] * v[None, None], axis=2)
    return {"a": a, "A": A, "E": E}


def schedule(g: dict, adj: float = 1.0) -> pd.DataFrame:
    """The age-rated rates: monthly premium per rand of benefit and the fixed part, by sex, entry age 18 to 64 and
    policy year j = 0 to TOP - entry, (1 - margin) P_j a_j = A_j + E_j."""
    sex, entry = np.repeat(list(data.SEXES), len(bk.ENTRY)), np.tile(bk.ENTRY, len(data.SEXES))
    y = year_parts(g, sex, entry, adj)
    margin = b3.PRICING["margin"]
    per_rand, fixed = y["A"] / ((1 - margin) * y["a"]), y["E"] / ((1 - margin) * y["a"])
    rows = []
    for i, (s, e) in enumerate(zip(sex, entry)):
        n = TOP - int(e) + 1
        rows.append(pd.DataFrame({"sex": s, "entry_age": int(e), "policy_year": np.arange(n),
                                  "per_rand": per_rand[i, :n], "fixed": fixed[i, :n]}))
    return pd.concat(rows, ignore_index=True)


def rows(sched: pd.DataFrame, fun: pd.DataFrame, years: int, start=None) -> np.ndarray:
    """(policies, years): each policy's monthly premium in projection year k, rounded to the cent. Level policies pay
    their premium throughout; age-rated ones their schedule's policy year n + k (n years in force), the last year's
    rate carried past TOP, where nobody is left. With `start` (a projection year per policy), an age-rated row is
    nan before its start, for the caller to fill (the review variant)."""
    out = np.repeat(fun["premium"].to_numpy(float)[:, None], years, axis=1)
    rated = (fun["premium_type"] == "age-rated").to_numpy()
    if not rated.any():
        return out
    sexes = list(data.SEXES)
    width = TOP - int(bk.ENTRY.min()) + 1
    tab = {c: np.full((len(sexes), len(bk.ENTRY), width), np.nan) for c in ("per_rand", "fixed")}
    si = sched["sex"].map(sexes.index).to_numpy()
    ei = sched["entry_age"].to_numpy() - bk.ENTRY.min()
    for c in tab:
        tab[c][si, ei, sched["policy_year"].to_numpy()] = sched[c].to_numpy()
        last = np.where(np.isnan(tab[c]), -np.inf, np.arange(width)).argmax(axis=2)       # the last priced year
        tab[c] = np.where(np.isnan(tab[c]), np.take_along_axis(tab[c], last[..., None], 2), tab[c])
    f = fun[rated]
    s_, e_ = f["sex"].map(sexes.index).to_numpy(), f["entry_age"].to_numpy() - bk.ENTRY.min()
    j = np.minimum(f["years_in_force"].to_numpy()[:, None] + np.arange(years)[None, :], width - 1)
    sa = f["sum_assured"].to_numpy(float)[:, None]
    out[rated] = np.round(tab["per_rand"][s_[:, None], e_[:, None], j] * sa + tab["fixed"][s_[:, None], e_[:, None], j], 2)
    if start is not None:
        out[rated] = np.where(np.arange(years)[None, :] >= np.asarray(start)[rated][:, None], out[rated], np.nan)
    return out


def book(g: dict, sched: pd.DataFrame | None = None) -> pd.DataFrame:
    """v5's policies with the premium type from v5's benefit draw; level premiums as v5's level benefit, age-rated
    ones the schedule's current policy year."""
    v5 = bk.book(g)
    fun = v5.rename(columns={"benefit": "premium_type"})
    fun["premium_type"] = fun["premium_type"].map(TYPES)
    level = bk.rates(g)
    level = level[level["benefit"] == "level"].drop(columns="benefit")
    fun = fun.drop(columns="premium").merge(level, on=["sex", "entry_age"], how="left")
    fun["premium"] = (fun["per_rand"] * fun["sum_assured"] + fun["fixed"]).round(2)
    fun = fun.drop(columns=["per_rand", "fixed"]).sort_values("id").reset_index(drop=True)
    sched = schedule(g) if sched is None else sched
    fun["premium"] = rows(sched, fun, 1)[:, 0]
    return fun


def check_f2(fun: pd.DataFrame) -> dict:
    """F2: level premiums equal v5's level-benefit premiums to the cent, policy by policy."""
    v5 = pd.read_csv(bk.FUNERAL).set_index("id")
    lv = fun[fun["premium_type"] == "level"].set_index("id")
    same_draw = bool((v5.loc[fun["id"], "benefit"].map(TYPES).to_numpy() == fun["premium_type"].to_numpy()).all())
    diff = np.abs(lv["premium"] - v5.loc[lv.index, "premium"])
    return {"policies": int(len(lv)), "largest_difference": float(diff.max()), "same_draw": same_draw,
            "pass": bool(diff.max() < 0.005 and same_draw)}


def check_f4(g: dict, sched: pd.DataFrame, sums=b3.SUMS) -> dict:
    """F4: each schedule premium, for every sum assured, against its year's equation worked by a plain loop over the
    year's months: |(1 - margin) P a - A - E| / (A + E)."""
    p = b3.PRICING
    worst, n = 0.0, 0
    for (s, e), d in sched.groupby(["sex", "entry_age"]):
        m = g[s]
        for j, pr, fx in zip(d["policy_year"], d["per_rand"], d["fixed"]):
            x, yr = int(e) + int(j), int(j)
            mu = m[yr, x] if x <= TOP else 1e3
            alive, a, A, E = 1.0, 0.0, 0.0, 0.0
            for k in range(12):
                q = 1 - np.exp(-mu / 12)
                a += alive * (1 + p["interest"]) ** (-k / 12)
                A += alive * q * (1 + p["interest"]) ** (-(k / 12 + 1 / 24))
                E += alive * b3.EXPENSE["funeral"] / 12 * (1 + p["inflation"]) ** (j + k / 12) * (1 + p["interest"]) ** (-k / 12)
                alive *= 1 - q
            for sa in sums:
                P = pr * sa + fx
                worst = max(worst, abs((1 - p["margin"]) * P * a - (sa * A + E)) / (sa * A + E))
                n += 1
    return {"premiums": n, "worst_relative": worst, "pass": bool(worst < 1e-10)}


def table(g: dict, sched: pd.DataFrame, ages=(20, 30, 40, 50, 60)) -> pd.DataFrame:
    """Monthly premium per R10,000 by sex: level at each entry age, and age-rated for entry at 18 at each age."""
    lv = bk.rates(g)
    lv = lv[lv["benefit"] == "level"].set_index(["sex", "entry_age"])
    out = {}
    for s in data.SEXES:
        out[(s, "level at entry")] = [lv.loc[(s, a), "per_rand"] * 1e4 + lv.loc[(s, a), "fixed"] for a in ages]
        d = sched[(sched["sex"] == s)]
        at = d.assign(age=d["entry_age"] + d["policy_year"]).query("entry_age == 18").set_index("age")
        out[(s, "age-rated at age")] = [at.loc[a, "per_rand"] * 1e4 + at.loc[a, "fixed"] for a in ages]
    return pd.DataFrame(out, index=pd.Index(ages, name="age"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    require_frozen(PROTOCOL_V7)
    g = bk.grid()
    sched = schedule(g)
    fun = book(g, sched)
    print("F2", check_f2(fun))
    print("F4", check_f4(g, sched))
    print("Monthly premium per R10,000 (age-rated: entry at 18, the premium in the year of each age):")
    print(table(g, sched).round(2).to_string())
    if args.write:
        fun.to_csv(FUNERAL, index=False)
        sched.to_csv(SCHEDULE, index=False)
        print(f"wrote {FUNERAL.relative_to(data.ROOT)}: {len(fun):,} policies, "
              f"{(fun['premium_type'] == 'age-rated').mean():.1%} age-rated; {SCHEDULE.relative_to(data.ROOT)}")


if __name__ == "__main__":
    main()
