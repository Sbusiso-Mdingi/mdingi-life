"""Heaping check for PROTOCOL_v1.3: are round ages, or round birth years, over-represented in registered deaths?

Ages 50 to 89. For each cell, deaths over the mean of the centred five cells around it (ages, or birth years along
the diagonal), averaged by last digit; 1.00 means no heaping. Birth year in the 1997-2020 files is year of death
minus age (they hold no date of birth); death years ending in 0 or 5 are left out of the birth-year index, where a
round age and a round birth year coincide. The 2021-2023 file records the date of birth, so its birth-year digits,
and the share of 1 January and missing dates, are tabulated directly.

Writes research/results/heaping.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mdingilife import data
from research.backtest import OUT
from research.mcd import MCD

AGES, YEARS = range(50, 90), range(1997, 2020)
NEW = "mcd-statssa-2021-2023-v1.1"


def tally(chunk: int = 1_000_000):
    old, new = [], []
    for f in sorted(MCD.glob("*.csv")):
        cols = ["DeathType", "AgeYear", "Sex", "DeathYear"] + (["BirthYear", "BirthMonth", "BirthDay"] if f.stem == NEW else [])
        for d in pd.read_csv(f, usecols=cols, dtype=str, encoding="latin-1", chunksize=chunk):
            d = d[(d["DeathType"] == "Individual death") & d["Sex"].isin(data.SEXES)]
            age, year = pd.to_numeric(d["AgeYear"], errors="coerce"), pd.to_numeric(d["DeathYear"], errors="coerce")
            if f.stem != NEW:
                old.append(pd.DataFrame({"sex": d["Sex"], "year": year, "age": age}).groupby(["sex", "year", "age"]).size())
            else:
                b = pd.DataFrame({"sex": d["Sex"], "age": age, "by": d["BirthYear"], "bm": d["BirthMonth"], "bd": d["BirthDay"]})
                new.append(b[b["age"].between(45, 94)].value_counts(dropna=False))
    old = pd.concat(old).groupby(level=[0, 1, 2]).sum()
    new = pd.concat(new).groupby(level=[0, 1, 2, 3, 4], dropna=False).sum()
    return old, new


def ratio(s: pd.Series) -> pd.Series:
    """Each value over the mean of the centred five around it."""
    return s / s.rolling(5, center=True).mean()


def main() -> None:
    cache = Path("/tmp/heaping_tally.pkl")
    if cache.exists():
        old, new = pd.read_pickle(cache)
    else:
        old, new = tally()
        pd.to_pickle((old, new), cache)
    out = {}
    for sex in data.SEXES:
        o = old.loc[sex].unstack("age").reindex(index=list(YEARS)).fillna(0)
        by_age = ratio(o.loc[:, 48:91].sum(axis=0)).loc[list(AGES)]
        rows = []
        for y in YEARS:
            if y % 5 == 0:
                continue
            row = o.loc[y, 48:91]
            coh = pd.Series(row.values, index=y - row.index.astype(int)).sort_index()
            r = ratio(coh).loc[[y - a for a in AGES]]
            rows.append(r)
        by_coh = pd.concat(rows)
        n = new.loc[sex].reset_index()
        n = n[n["age"].between(50, 89)]
        n["byn"] = pd.to_numeric(n["by"], errors="coerce")
        tot = n["count"].sum()
        known = n[n["byn"].notna()]
        j1 = (pd.to_numeric(known["bm"], errors="coerce") == 1) & (pd.to_numeric(known["bd"], errors="coerce") == 1)
        r21 = ratio(known.groupby(known["byn"].astype(int))["count"].sum())
        out[sex] = {
            "age_digit": by_age.groupby(by_age.index.astype(int) % 10).mean().round(3).to_dict(),
            "age_round": {int(a): round(float(by_age[a]), 3) for a in (60, 65, 70, 75, 80, 85)},
            "birth_digit_1997_2019": by_coh.groupby(by_coh.index % 10).mean().round(3).to_dict(),
            "birth_round": {int(c): round(float(by_coh[by_coh.index == c].mean()), 3) for c in (1920, 1925, 1930, 1935, 1940, 1945, 1950)},
            "recorded_2021_2023": {
                "deaths": int(tot),
                "birth_year_missing": round(float(n.loc[n["byn"].isna(), "count"].sum() / tot), 4),
                "birth_year_digit_share": (known.groupby(known["byn"].astype(int) % 10)["count"].sum() / known["count"].sum()).round(4).to_dict(),
                "birth_round": {int(c): round(float(r21[c]), 3) for c in (1935, 1940, 1945, 1950, 1955, 1960)},
                "jan_1_by_digit": (known[j1].groupby(known.loc[j1, "byn"].astype(int) % 10)["count"].sum()
                                   / known.groupby(known["byn"].astype(int) % 10)["count"].sum()).round(4).to_dict(),
                "jan_1": round(float(n.loc[(pd.to_numeric(n["bm"], errors="coerce") == 1) & (pd.to_numeric(n["bd"], errors="coerce") == 1), "count"].sum() / tot), 4),
            },
        }
    (OUT / "heaping.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
