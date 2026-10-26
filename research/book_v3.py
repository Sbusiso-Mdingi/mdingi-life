"""v3's invented book (PROTOCOL_v3.md, The book and Bases): the funeral mortality table, 5,000 annuitants and 50,000
funeral policies with their premiums.

    python -m research.book_v3 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Writes research/results/funeral_table.csv, data/book/annuities.csv and data/book/funeral.csv. Refuses to run until
PROTOCOL_v3.md is frozen.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from mdingilife import data, kannisto, sam
from mdingilife.protocol import PROTOCOL_V3, require_frozen
from research.backtest import OUT

SEED = 20261026
BOOK = data.ROOT / "data" / "book"
TABLE = OUT / "funeral_table.csv"
YEARS = (2017, 2018, 2019)
AGES = np.arange(18, 90)
TOP = kannisto.TOP
LAPSE = (0.20, 0.12, 0.08, 0.06)  # policy years 1, 2, 3 and from 4
SUMS, SUM_WEIGHTS = (10_000, 15_000, 20_000, 30_000), (0.30, 0.30, 0.25, 0.15)
EXPENSE = {"annuity": 600.0, "funeral": 180.0}  # a policy a year
PRICING = {"interest": 0.09, "inflation": 0.05, "margin": 0.20}


def lapse_rate(policy_year: np.ndarray) -> np.ndarray:
    """Annual lapse rate in policy year 1, 2, ... (array of ints)."""
    return np.asarray(LAPSE)[np.minimum(np.asarray(policy_year) - 1, len(LAPSE) - 1)]


def table(deaths: str, population: str) -> pd.DataFrame:
    """Force of mortality by sex and age 18 to 120: registered deaths over WPP population summed over 2017 to 2019,
    log rates smoothed over five ages, Kannisto from 90 (fitted on the smoothed 80 to 89)."""
    df = data.statssa(deaths, population)
    df = df[df["year"].isin(YEARS)].groupby(["sex", "age"])[["deaths", "exposure"]].sum().reset_index()
    rows = []
    for s in data.SEXES:
        d = df[df["sex"] == s].set_index("age").sort_index()
        crude = np.log(d["deaths"] / d["exposure"])
        smooth = crude.rolling(5, center=True).mean().reindex(AGES)
        if smooth.isna().any():
            raise ValueError(f"{s}: ages missing for the smoothing")
        ages, full = kannisto.extend(smooth.to_numpy()[:, None], AGES)
        rows.append(pd.DataFrame({"sex": s, "age": ages, "mu": np.exp(full[:, 0]),
                                  "crude": np.exp(crude.reindex(ages)).to_numpy()}))
    return pd.concat(rows, ignore_index=True)


def mu_rows(tab: pd.DataFrame, sex, age, years: int, adj: float = 1.0) -> np.ndarray:
    """(cells, years): the table's force from each cell's age onwards, a year older each year; nobody survives past
    TOP."""
    out = np.full((len(age), years), 1e3)
    for s in data.SEXES:
        m = tab.loc[tab["sex"] == s].set_index("age")["mu"].reindex(range(TOP + 1)).to_numpy()
        for i in np.flatnonzero(np.asarray(sex) == s):
            n = min(years, TOP - int(age[i]) + 1)
            out[i, :n] = adj * m[int(age[i]):int(age[i]) + n]
    return out


def premiums(tab: pd.DataFrame, sex, entry, sum_assured) -> np.ndarray:
    """Monthly premium at entry on the pricing basis: (1 - margin) P a = A + E, no lapses, flat interest."""
    years = TOP - int(np.min(entry)) + 1
    inforce, deaths = sam.project(mu_rows(tab, sex, entry, years))
    k = np.arange(12 * years)
    v = (1 + PRICING["interest"]) ** -(k / 12)
    v_mid = (1 + PRICING["interest"]) ** -(k / 12 + 1 / 24)
    expenses = EXPENSE["funeral"] / 12 * (1 + PRICING["inflation"]) ** (k / 12)
    a = inforce @ v
    return (np.asarray(sum_assured) * (deaths @ v_mid) + inforce @ (expenses * v)) / ((1 - PRICING["margin"]) * a)


def book(tab: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    n = 5_000
    bought = np.rint(rng.triangular(55, 65, 75, n)).astype(int)
    since = rng.integers(0, 16, n)
    ann = pd.DataFrame({
        "id": np.arange(1, n + 1), "sex": rng.choice(data.SEXES, n), "age_at_purchase": bought,
        "years_since_purchase": since, "age": bought + since,
        "type": rng.choice(["inflation-linked", "level"], n),
        "income": np.minimum(np.exp(rng.normal(np.log(60_000), 0.8, n)), 1e6).round(2)})

    n = 50_000
    entry = np.clip(np.rint(rng.normal(38, 10, n)), 18, 64).astype(int)
    durations = np.arange(16)
    w = np.concatenate([[1.0], np.cumprod(1 - lapse_rate(durations[:-1] + 1))])
    fun = pd.DataFrame({
        "id": np.arange(1, n + 1), "sex": rng.choice(["Female", "Male"], n, p=[0.55, 0.45]), "entry_age": entry,
        "years_in_force": rng.choice(durations, n, p=w / w.sum()),
        "sum_assured": rng.choice(SUMS, n, p=SUM_WEIGHTS)})
    fun.insert(4, "age", fun["entry_age"] + fun["years_in_force"])
    cells = fun[["sex", "entry_age"]].drop_duplicates().reset_index(drop=True)
    rate = premiums(tab, cells["sex"].to_numpy(), cells["entry_age"].to_numpy(), np.ones(len(cells)))
    fixed = premiums(tab, cells["sex"].to_numpy(), cells["entry_age"].to_numpy(), np.zeros(len(cells)))
    cells["per_rand"], cells["fixed"] = rate - fixed, fixed
    fun = fun.merge(cells, on=["sex", "entry_age"], how="left")
    fun["premium"] = (fun["per_rand"] * fun["sum_assured"] + fun["fixed"]).round(2)
    return ann, fun.drop(columns=["per_rand", "fixed"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    require_frozen(PROTOCOL_V3)
    tab = table(args.deaths, args.population)
    tab.to_csv(TABLE, index=False, float_format="%.8g")
    ann, fun = book(tab)
    BOOK.mkdir(parents=True, exist_ok=True)
    ann.to_csv(BOOK / "annuities.csv", index=False)
    fun.to_csv(BOOK / "funeral.csv", index=False)
    print(tab[tab["age"].isin([20, 30, 40, 50, 60, 70, 80, 90, 100])].pivot(index="age", columns="sex", values="mu"))
    print(ann.describe().round(1).to_string())
    print(fun.describe().round(1).to_string())
    print("Monthly premium for R10,000 at entry:")
    print(fun[fun["sum_assured"] == 10_000].groupby(["sex", "entry_age"])["premium"].first()
          .unstack(0).loc[[20, 30, 40, 50, 60]])


if __name__ == "__main__":
    main()
