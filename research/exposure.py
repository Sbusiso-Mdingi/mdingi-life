"""Exposure for the Stats SA run: UN WPP 2024 1 July population by single age and sex (protocol amendment, 26 Oct 2026).

Written for the years whose deaths the DataFirst files hold in full, 1997 to 2022. 2023 is left out because
only its late registrations are on file, and 2024 because WPP ends in 2023. data.statssa merges deaths onto
this file, so a year missing here is a year not fitted.

Writes data/raw/statssa/wpp_population.csv (year, sex, age, population), then cross-checks it against Stats SA's
own projection workbook (P0302, 2002 to 2025, five-year groups ending at 80+) and writes the ratio of WPP to Stats SA
at ages 50 to 79 to research/results/exposure_check.csv.
"""
from __future__ import annotations

import pandas as pd

from mdingilife import data

OUT = data.RAW / "statssa" / "wpp_population.csv"
P0302 = data.RAW / "statssa" / "p0302_country_projection_2002-2025.xlsx"
CHECK = data.ROOT / "research" / "results" / "exposure_check.csv"
YEARS = range(1997, 2023)
GROUPS = [f"{a}-{a + 4}" for a in range(50, 80, 5)]


def check(w: pd.DataFrame) -> pd.DataFrame:
    """WPP over Stats SA population at ages 50 to 79, by year and sex (80+ is open in P0302, so it is left out)."""
    p = pd.read_excel(P0302, header=4).iloc[:, :27]
    p = p[p["Population Group"].notna() & p["Age"].isin(GROUPS)]
    years = [y for y in YEARS if y in p.columns]
    p = p.melt(id_vars=["Sex", "Age"], value_vars=years, var_name="year").groupby(["year", "Sex"])["value"].sum()
    w = w[w["age"].between(50, 79) & w["year"].isin(years)].groupby(["year", "sex"])["population"].sum()
    return (w / p.rename_axis(["year", "sex"])).unstack("sex")


def main() -> None:
    w = data.wpp()
    w = w[w["year"].isin(YEARS)].rename(columns={"exposure": "population"})
    w[["year", "sex", "age", "population"]].to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(data.ROOT)}: {len(w):,} cells, {w['year'].min()}-{w['year'].max()}")
    c = check(w)
    c.round(4).to_csv(CHECK)
    print("\nWPP / Stats SA P0302 population, ages 50 to 79:")
    print(c.map(lambda v: f"{v:.3f}").to_string())


if __name__ == "__main__":
    main()
