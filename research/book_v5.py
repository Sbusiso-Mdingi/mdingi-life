"""v5's funeral book (research/PROTOCOL_v5.md, "Funeral on the table" and "The rising-benefit option"): v3's policies,
each level or rising, repriced on the v5 table along the cohort from the valuation date.

    python -m research.book_v5 [--write]

Prints C3 (premiums rise with entry age 18 to 64) and the premiums per R10,000 beside v3's. With --write, writes
data/book/funeral_v5.csv; v3's data/book/funeral.csv is left as it is. Refuses to run until PROTOCOL_v5.md is frozen.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from mdingilife import data, sam, table_v5 as t5
from mdingilife.inflation_v5 import PRICING_GROWTH
from mdingilife.protocol import PROTOCOL_V5, require_frozen
from research import book_v3 as b3
from research.backtest import OUT

SEED = 20261028
YEAR = 2026                                  # the valuation date's calendar year (25 September 2026)
TABLE = OUT / "funeral_table_v5.csv"
FUNERAL = b3.BOOK / "funeral_v5.csv"
BENEFITS = ("level", "rising")
ENTRY = np.arange(18, 65)


def grid(years: int = 110) -> dict:
    """{sex: m by calendar year YEAR on (rows) and age 0 to TOP}: the table from YEAR, after its last year each age's
    last pace carried on, to `years` calendar years."""
    tab = pd.read_csv(TABLE)
    out = {}
    for s in data.SEXES:
        d = tab[tab["sex"] == s].pivot(index="year", columns="age", values="m").sort_index()
        last = YEAR + years - 1
        yrs, m = t5.extend(d.to_numpy(), d.index.to_numpy(), last)
        out[s] = m[list(yrs).index(YEAR):]
    return out


def mu_rows(g: dict, sex, age, years: int, adj: float = 1.0) -> np.ndarray:
    """(cells, years): the force along each cell's cohort, mu(x + k, YEAR + k) in projection year k; nobody survives
    past TOP."""
    out = np.full((len(age), years), 1e3)
    k = np.arange(years)
    for s in data.SEXES:
        m = g[s]
        for i in np.flatnonzero(np.asarray(sex) == s):
            x = int(age[i])
            n = min(years, t5.TOP - x + 1)
            out[i, :n] = adj * m[k[:n], x + k[:n]]
    return out


def growth_rows(rising, months: int, growth: float = PRICING_GROWTH) -> np.ndarray:
    """(cells, months): the benefit as a multiple of today's, level within each year from the valuation date."""
    k = np.arange(months) // 12
    return np.where(np.asarray(rising, bool)[:, None], (1 + growth) ** k[None, :], 1.0)


def premiums(g: dict, sex, entry, rising, sum_assured, growth: float = PRICING_GROWTH) -> np.ndarray:
    """Monthly premium as if each policy started on the valuation date at its entry age: (1 - margin) P a = A + E,
    no lapses, flat interest, a rising benefit growing at `growth` on each anniversary."""
    years = t5.TOP - int(np.min(entry)) + 1
    inforce, deaths = sam.project(mu_rows(g, sex, entry, years))
    k = np.arange(12 * years)
    p = b3.PRICING
    v = (1 + p["interest"]) ** -(k / 12)
    v_mid = (1 + p["interest"]) ** -(k / 12 + 1 / 24)
    expenses = b3.EXPENSE["funeral"] / 12 * (1 + p["inflation"]) ** (k / 12)
    a = inforce @ v
    A = np.sum(deaths * growth_rows(rising, 12 * years, growth) * v_mid, axis=1)
    return (np.asarray(sum_assured) * A + inforce @ (expenses * v)) / ((1 - p["margin"]) * a)


def rates(g: dict, growth: float = PRICING_GROWTH) -> pd.DataFrame:
    """Premium per rand of benefit and the fixed part, by sex, entry age 18 to 64 and benefit type."""
    cells = pd.DataFrame([(s, e, bt) for s in data.SEXES for e in ENTRY for bt in BENEFITS],
                         columns=["sex", "entry_age", "benefit"])
    args = (g, cells["sex"].to_numpy(), cells["entry_age"].to_numpy(), (cells["benefit"] == "rising").to_numpy())
    rate = premiums(*args, np.ones(len(cells)), growth)
    fixed = premiums(*args, np.zeros(len(cells)), growth)
    return cells.assign(per_rand=rate - fixed, fixed=fixed)


def book(g: dict, growth: float = PRICING_GROWTH) -> pd.DataFrame:
    """v3's funeral policies (its seed, so the same fields), each level or rising by its own draw, repriced."""
    _, fun = b3.book(pd.read_csv(b3.TABLE))
    fun.insert(6, "benefit", np.random.default_rng(SEED).choice(BENEFITS, len(fun)))
    fun = fun.drop(columns="premium").merge(rates(g, growth), on=["sex", "entry_age", "benefit"], how="left")
    fun["premium"] = (fun["per_rand"] * fun["sum_assured"] + fun["fixed"]).round(2)
    return fun.drop(columns=["per_rand", "fixed"]).sort_values("id").reset_index(drop=True)


def check_c3(r: pd.DataFrame) -> dict:
    out = {}
    for (s, bt), d in r.groupby(["sex", "benefit"]):
        p = (d.sort_values("entry_age")["per_rand"] * 10_000 + d.sort_values("entry_age")["fixed"]).to_numpy()
        falls = ENTRY[1:][np.diff(p) <= 0]
        out[f"{s} {bt}"] = {"pass": bool(len(falls) == 0), "falls_at": [int(a) for a in falls]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    require_frozen(PROTOCOL_V5)
    g = grid()
    r = rates(g)
    c3 = check_c3(r)
    print("C3", c3)
    v3 = pd.read_csv(b3.BOOK / "funeral.csv")
    v3 = v3[v3["sum_assured"] == 10_000].groupby(["sex", "entry_age"])["premium"].first()
    show = r[r["entry_age"].isin([20, 30, 40, 50, 60])].assign(premium=lambda d: d["per_rand"] * 1e4 + d["fixed"])
    tab = show.pivot_table(index="entry_age", columns=["sex", "benefit"], values="premium")
    for s in data.SEXES:
        tab[(s, "v3")] = v3.loc[s].reindex(tab.index).to_numpy()
    print("Monthly premium per R10,000 at entry:")
    print(tab.sort_index(axis=1).round(2).to_string())
    if args.write:
        fun = book(g)
        fun.to_csv(FUNERAL, index=False)
        print(f"wrote {FUNERAL.relative_to(data.ROOT)}: {len(fun):,} policies, {(fun['benefit'] == 'rising').mean():.1%} rising")


if __name__ == "__main__":
    main()
