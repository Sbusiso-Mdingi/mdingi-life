"""Completeness-scaled deaths for the Stats SA sensitivity (protocol amendment, 26 Oct 2026).

Completeness is registered deaths at ages 50 to 89 over UN WPP 2024 deaths at the same ages, by year and sex,
after unknown ages and sexes are spread. Every age's deaths in that year and sex are divided by it, which lifts
the 50 to 89 total to WPP's level and keeps the registered age pattern.

Writes data/raw/statssa/mcd_deaths_scaled.csv (year, sex, age, deaths) and research/results/completeness.csv.
"""
from __future__ import annotations

import pandas as pd

from mdingilife import data
from research.backtest import AGES, OUT
from research.exposure import OUT as POPULATION
from research.mcd import OUT as DEATHS

SCALED = data.RAW / "statssa" / "mcd_deaths_scaled.csv"


def main() -> None:
    d = data.statssa(DEATHS, POPULATION)
    w = data.wpp()
    band = lambda f: f[f["age"].isin(AGES)].groupby(["year", "sex"])["deaths"].sum()
    c = (band(d) / band(w)).dropna().rename("completeness")
    c.unstack("sex").round(4).to_csv(OUT / "completeness.csv")
    d = d.join(c, on=["year", "sex"])
    d["deaths"] /= d["completeness"]
    d[["year", "sex", "age", "deaths"]].to_csv(SCALED, index=False)
    print(c.unstack("sex").map(lambda v: f"{v:.1%}").to_string())
    print(f"wrote {SCALED.relative_to(data.ROOT)}")


if __name__ == "__main__":
    main()
