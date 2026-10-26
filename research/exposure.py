"""Exposure for the Stats SA run: UN WPP 2024 1 July population by single age and sex (protocol amendment, 26 Oct 2026).

Written for the years whose deaths the DataFirst files hold in full, 1997 to 2022. 2023 is left out because
only its late registrations are on file, and 2024 because WPP ends in 2023. data.statssa merges deaths onto
this file, so a year missing here is a year not fitted.

Writes data/raw/statssa/wpp_population.csv (year, sex, age, population), then cross-checks it against Stats SA's
own projection workbook (P0302, 2002 to 2025, five-year groups ending at 80+) and writes the ratio of WPP to Stats SA
at ages 50 to 79 to research/results/exposure_check.csv.

Then, at the three Stats SA counts by single age (Census 2011, Community Survey 2016, Census 2022, weighted, from
SuperWEB2 as CSV in data/raw/statssa/census), writes the ratio of WPP, interpolated to the count's reference date,
to the count by sex and five-year group to research/results/exposure_census_check.csv. Census counts carry their own
undercount adjustments (Census 2022's post-enumeration survey put it at 31%), so they check WPP, they do not replace it.
"""
from __future__ import annotations

import pandas as pd

from mdingilife import data

OUT = data.RAW / "statssa" / "wpp_population.csv"
P0302 = data.RAW / "statssa" / "p0302_country_projection_2002-2025.xlsx"
CHECK = data.ROOT / "research" / "results" / "exposure_check.csv"
CENSUS = data.RAW / "statssa" / "census"
CENSUS_CHECK = data.ROOT / "research" / "results" / "exposure_census_check.csv"
COUNTS = {"census2011": "2011-10-10", "cs2016": "2016-03-07", "census2022": "2022-02-03"}  # reference nights
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


def count(name: str) -> pd.DataFrame:
    """A SuperWEB2 age-by-sex table (semicolons, decimal commas) as sex, age, population; unspecified age dropped."""
    rows = []
    for line in (CENSUS / f"{name}_age_sex.csv").read_text().splitlines():
        f = [x.strip('"') for x in line.split(";")]
        if len(f) >= 3 and f[0].isdigit():
            rows += [(sex, int(f[0]), float(f[i].replace(",", "."))) for i, sex in ((1, "Male"), (2, "Female"))]
    return pd.DataFrame(rows, columns=["sex", "age", "population"])


def census_check(w: pd.DataFrame) -> pd.DataFrame:
    """WPP over each count, by sex and five-year group from 50 (90+ open), and over all ages."""
    out = []
    for name, night in COUNTS.items():
        at = pd.Timestamp(night)
        y = at.year if at.month >= 7 else at.year - 1
        f = (at - pd.Timestamp(f"{y}-07-01")).days / 365.25
        pop = w[w["year"].isin([y, y + 1])].pivot_table(index=["sex", "age"], columns="year", values="population")
        wpp_at = ((1 - f) * pop[y] + f * pop[y + 1]).rename("wpp").reset_index()
        c = count(name).merge(wpp_at, on=["sex", "age"], how="left")
        c["group"] = pd.cut(c["age"], [0, 50, 55, 60, 65, 70, 75, 80, 85, 90, 200], right=False,
                            labels=["0-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"])
        g = c.groupby(["sex", "group"], observed=True)[["wpp", "population"]].sum()
        tot = c.groupby("sex")[["wpp", "population"]].sum().assign(group="all").set_index("group", append=True)
        g = pd.concat([g, tot])
        out.append((g["wpp"] / g["population"]).rename(name))
    return pd.concat(out, axis=1)


def main() -> None:
    w = data.wpp()
    w = w[w["year"].isin(YEARS)].rename(columns={"exposure": "population"})
    w[["year", "sex", "age", "population"]].to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(data.ROOT)}: {len(w):,} cells, {w['year'].min()}-{w['year'].max()}")
    c = check(w)
    c.round(4).to_csv(CHECK)
    print("\nWPP / Stats SA P0302 population, ages 50 to 79:")
    print(c.map(lambda v: f"{v:.3f}").to_string())
    full = data.wpp().rename(columns={"exposure": "population"})
    cc = census_check(full)
    cc.round(4).to_csv(CENSUS_CHECK)
    print("\nWPP / Stats SA census counts, at each count's reference night:")
    print(cc.map(lambda v: f"{v:.3f}").to_string())


if __name__ == "__main__":
    main()
