"""Tally Stats SA unit death records (DataFirst, Mortality and Causes of Death) by year of death, sex and age.

Files may hold late registrations of earlier deaths (the 2021-2023 file is split by the year Stats SA processed
the records). Every file in data/raw/statssa/mcd is read, stillbirths are dropped, and deaths
are counted by year of death. Sex is left blank where Stats SA has "Unspecified" or "Undeterminable", and age
where it is missing, for data.statssa to spread pro rata.

Writes data/raw/statssa/mcd_deaths.csv and prints, for each year of death, which files it came
from and how registered deaths compare with UN WPP 2024 deaths (a completeness check, not a rate).
"""
from __future__ import annotations

import pandas as pd

from mdingilife import data

MCD = data.RAW / "statssa" / "mcd"
OUT = data.RAW / "statssa" / "mcd_deaths.csv"
COLS = ["DeathType", "AgeYear", "Sex", "DeathYear"]
BANDS = [0, 15, 50, 65, 80, 90, 100]
MAIN = 100_000  # a year of death is compared only where a file holds its main registrations


def counts(chunk: int = 1_000_000) -> pd.DataFrame:
    """Individual deaths by file, year of death, sex and age, read in chunks (the 1997-2009 file is 2.6 GB).

    Older files put the deceased, dates and causes in separate tables; only the deceased table is linked in.
    Text columns are read as Latin-1 because the 1997-2009 CSVs are not UTF-8.
    """
    files = sorted(MCD.glob("*.csv"))
    if not files:
        raise SystemExit(f"no DataFirst CSVs in {MCD}")
    parts = []
    for f in files:
        for d in pd.read_csv(f, usecols=COLS, dtype=str, encoding="latin-1", chunksize=chunk):
            d = d[d["DeathType"] == "Individual death"]
            d = pd.DataFrame({"file": f.stem, "year": pd.to_numeric(d["DeathYear"], errors="coerce"),
                              "sex": d["Sex"].where(d["Sex"].isin(data.SEXES)),
                              "age": pd.to_numeric(d["AgeYear"], errors="coerce")})
            parts.append(d.groupby(["file", "year", "sex", "age"], dropna=False).size().rename("deaths"))
    return pd.concat(parts).groupby(level=[0, 1, 2, 3], dropna=False).sum().reset_index()


def main() -> None:
    c = counts()
    n = lambda m: f"{c.loc[m, 'deaths'].sum():,.0f}"
    print(f"{n(slice(None))} individual deaths; sex unknown {n(c['sex'].isna())}, age unknown "
          f"{n(c['age'].isna())}, year unknown {n(c['year'].isna())} (dropped)")
    print("\nDeaths by year of death (rows) and file (columns):")
    print(c.pivot_table(index="year", columns="file", values="deaths", aggfunc="sum", fill_value=0)
          .astype(int).to_string())

    tidy = (c.dropna(subset=["year"]).groupby(["year", "sex", "age"], dropna=False)["deaths"].sum()
            .reset_index().astype({"year": int}))
    tidy.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(data.ROOT)}: {len(tidy):,} cells")

    w = data.wpp()
    known = tidy.dropna(subset=["sex", "age"])
    per_year = known.groupby("year")["deaths"].sum()
    both = sorted(set(per_year[per_year >= MAIN].index) & set(w["year"]))
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
