"""Tally Stats SA unit death records (DataFirst, Mortality and Causes of Death) by year of death, sex and age.

The DataFirst files are split by the year Stats SA processed the records, not the year of death: each holds late
registrations of earlier deaths. Every file in data/raw/statssa/mcd is read, stillbirths are dropped, and deaths
are counted by year of death. Sex is left blank where Stats SA has "Unspecified" or "Undeterminable", and age
where it is missing, for data.statssa to spread pro rata.

Writes data/raw/statssa/mcd_deaths.csv and prints, for each year of death, which processing years it came
from and how registered deaths compare with UN WPP 2024 deaths (a completeness check, not a rate).
"""
from __future__ import annotations

import pandas as pd

from mdingilife import data

MCD = data.RAW / "statssa" / "mcd"
OUT = data.RAW / "statssa" / "mcd_deaths.csv"
COLS = ["DeathType", "AgeYear", "Sex", "DeathYear", "ProcessingYear"]
BANDS = [0, 15, 50, 65, 80, 90, 100]
MAIN = 100_000  # a year of death is compared only where a file holds its main registrations


def records() -> pd.DataFrame:
    files = sorted(MCD.glob("*.csv"))
    if not files:
        raise SystemExit(f"no DataFirst CSVs in {MCD}")
    d = pd.concat([pd.read_csv(f, usecols=COLS, dtype=str).assign(file=f.name) for f in files], ignore_index=True)
    d = d[d["DeathType"] == "Individual death"]
    d["sex"] = d["Sex"].where(d["Sex"].isin(data.SEXES))
    d["age"] = pd.to_numeric(d["AgeYear"], errors="coerce")
    d["year"] = pd.to_numeric(d["DeathYear"], errors="coerce").astype("Int64")
    return d


def main() -> None:
    d = records()
    print(f"{len(d):,} individual deaths; sex unknown {d['sex'].isna().sum():,}, age unknown "
          f"{d['age'].isna().sum():,}, year unknown {d['year'].isna().sum():,} (dropped)")
    print("\nDeaths by year of death (rows) and processing year (columns):")
    print(pd.crosstab(d["year"], d["ProcessingYear"]).tail(15).to_string())

    tidy = (d.dropna(subset=["year"]).groupby(["year", "sex", "age"], dropna=False).size()
            .rename("deaths").reset_index())
    tidy.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(data.ROOT)}: {len(tidy):,} cells")

    w = data.wpp()
    known = tidy.dropna(subset=["sex", "age"])
    counts = known.groupby("year")["deaths"].sum()
    both = sorted(set(counts[counts >= MAIN].index) & set(w["year"]))
    print("\nRegistered deaths as a share of WPP 2024 deaths, ages under 100 (unknown sex not spread):")
    known = known[known["age"] < 100]
    for y in both:
        r, u = known[known["year"] == y], w[w["year"] == y]
        band = lambda f: pd.cut(f["age"], BANDS, right=False, labels=[f"{a}-{b - 1}" for a, b in zip(BANDS, BANDS[1:])])
        ratio = (r.groupby(["sex", band(r)], observed=True)["deaths"].sum()
                 / u.groupby(["sex", band(u)], observed=True)["deaths"].sum()).unstack()
        print(f"\n{y}  (all ages: {r['deaths'].sum() / u['deaths'].sum():.1%})")
        print(ratio.map(lambda v: f"{v:.1%}").to_string())


if __name__ == "__main__":
    main()
