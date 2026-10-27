"""v5's funeral mortality table (research/PROTOCOL_v5.md, "The mortality table"), 2024 to 2050 at ages 0 to 120.

Deaths by underlying cause come from the DataFirst 2010-2020 causes table, read in place from its zip (--causes-zip,
nothing extracted), linked on SerialNo to the 2010-2020 deceased table in data/raw/statssa/mcd; the 2021-2023 file
holds its own causes. Only deaths from START on are needed. The tally is cached in data/raw/statssa/causes/ (not
committed). Stillbirths are dropped. Exposure is the repository's population with WPP 2024's 2024 added.

Writes research/results/funeral_table_v5.csv (sex, year, age, m) and funeral_table_v5.json (phi, smoothing levels,
drifts, cohorts, checks). --check-against DIR compares with the table built outside the repository (C2).

Source: Statistics South Africa, Mortality and Causes of Death, unit records, produced by Stats SA and distributed
by DataFirst, University of Cape Town (CC BY); UN World Population Prospects 2024 (CC BY 3.0 IGO).
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from mdingilife import data, table_v5 as t5
from mdingilife.protocol import PROTOCOL_V5, require_frozen
from research.exposure import OUT as POPULATION
from research.mcd import MCD, OUT as DEATHS

CAUSES_ZIP = Path.home() / ".Trash" / "mcd-2010-2020-v1.1.zip"
OLD_NAME = "2010-2020"
NEW_FILE = MCD / "mcd-statssa-2021-2023-v1.1.csv"
CACHE = data.RAW / "statssa" / "causes" / "cause_tally.csv"
OUT = data.ROOT / "research" / "results" / "funeral_table_v5.csv"
SUMMARY = OUT.with_suffix(".json")
CHUNK = 1_000_000


def _deceased(f: Path, extra=()) -> pd.DataFrame:
    parts = []
    for d in pd.read_csv(f, usecols=["SerialNo", "DeathType", "AgeYear", "Sex", "DeathYear", *extra], dtype=str,
                         encoding="latin-1", chunksize=CHUNK):
        d = d[(d["DeathType"] == "Individual death") & d["Sex"].isin(data.SEXES)]
        d = d.assign(age=pd.to_numeric(d["AgeYear"], errors="coerce"), year=pd.to_numeric(d["DeathYear"], errors="coerce"))
        d = d.dropna(subset=["age", "year"])
        parts.append(d[d["year"] >= t5.START].drop(columns=["DeathType", "AgeYear", "DeathYear"]))
    return pd.concat(parts)


def cause_tally(causes_zip: Path) -> pd.DataFrame:
    """Deaths by year (START on), sex, age and the underlying cause's first three characters; sex and age known."""
    if CACHE.exists():
        return pd.read_csv(CACHE, keep_default_na=False, dtype={"code": str})
    d = _deceased(MCD / f"mcd-{OLD_NAME}-deceased-v1.csv")
    with zipfile.ZipFile(causes_zip) as zf, zf.open(f"mcd-{OLD_NAME}-v1.1/mcd-{OLD_NAME}-causes-v1.csv") as cf:
        c = pd.read_csv(cf, usecols=["SerialNo", "UnderlyingCause"], dtype=str, encoding="latin-1")
    d = d.merge(c.drop_duplicates("SerialNo"), on="SerialNo", how="left")
    print(f"{OLD_NAME}: {len(d):,} deaths from {t5.START}, {d['UnderlyingCause'].isna().sum():,} without a cause record")
    tallies = [d]
    d = _deceased(NEW_FILE, ["UnderlyingCause"])
    print(f"2021-2023 file: {len(d):,} deaths")
    tallies.append(d)
    t = pd.concat(tallies)
    t = (t.assign(code=t["UnderlyingCause"].fillna("").str[:3]).groupby(["year", "Sex", "age", "code"]).size()
         .rename("deaths").reset_index().rename(columns={"Sex": "sex"}).astype({"year": int, "age": int}))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(CACHE, index=False)
    return pd.read_csv(CACHE, keep_default_na=False, dtype={"code": str})


def panel() -> dict[str, data.Rates]:
    """The Stats SA panel, ages 0 to 99, with WPP 2024's 2024 population added."""
    q = pd.read_csv(data.WPP / "wpp2024_zaf_population_2024.csv", usecols=["Time", "AgeGrp", "PopMale", "PopFemale"])
    q = q[(q["Time"] == 2024) & (q["AgeGrp"] != "100+")].astype({"AgeGrp": int})
    add = pd.concat([pd.DataFrame({"year": 2024, "sex": s, "age": q["AgeGrp"], "population": 1000 * q[f"Pop{s}"]})
                     for s in data.SEXES])
    pop = pd.concat([pd.read_csv(POPULATION), add], ignore_index=True)
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "population.csv"
        pop.to_csv(f, index=False)
        df = data.statssa(deaths=DEATHS, population=f)
    return {s: data.panel(df, s) for s in data.SEXES}


def build(causes_zip: Path) -> tuple[pd.DataFrame, dict]:
    P, sh = panel(), t5.shares(cause_tally(causes_zip))
    rows, notes = [], {}
    for s in data.SEXES:
        p = P[s]
        ages, years = np.asarray(p.ages), np.asarray(p.years)
        phi = t5.overdispersion(ages, years, p.D, p.E)
        j = list(years).index(t5.LAST)
        g = t5.graduate(p.D[:, j], p.E[:, j], phi)

        cols = [i for i, y in enumerate(years) if y >= t5.START and y not in t5.LEFT_OUT]
        a = ages <= t5.LC_TOP
        D, E, yr = p.D[a][:, cols], p.E[a][:, cols], years[cols]
        ix = pd.MultiIndex.from_product([yr, [s], ages[a]])
        h = sh["hiv"].reindex(ix).fillna(0).to_numpy().reshape(len(yr), -1).T
        e = sh["ext"].reindex(ix).fillna(0).to_numpy().reshape(len(yr), -1).T
        Ds = {"hiv": D * h, "ext": D * e, "other": D * (1 - h - e)}
        fit = t5.fit_cause_lc(Ds, E, ages[a], yr)
        lc = t5.project(fit, ages[a], yr)
        m = t5.table(g["m"], lc)
        out_years = np.arange(t5.LAST, t5.END + 1)                             # after END: t5.extend, in the valuation
        rows.append(pd.DataFrame({"sex": s, "year": np.repeat(out_years, t5.TOP + 1),
                                  "age": np.tile(np.arange(t5.TOP + 1), len(out_years)), "m": m.ravel()}))
        notes[s] = {"phi": phi, "wh_levels": list(g["lam"]), "wh_trace": g["trace"], "tail_slope": g["slope"],
                    "lc_levels": {k: list(v["lam"]) for k, v in fit["groups"].items()},
                    "drift": {k: (v["k"][-1] - v["k"][0]) / (yr[-1] - yr[0]) for k, v in fit["groups"].items()},
                    "cohorts": [int(fit["cohorts"][0]), int(fit["cohorts"][-1])],
                    "C1_2024_vs_graduated": float(np.max(np.abs(m[0] / g["m"] - 1)))}
    return pd.concat(rows, ignore_index=True), notes


def check_against(table: pd.DataFrame, folder: Path) -> dict:
    """C2: the largest relative difference from lcc_{sex}_table.csv, by sex."""
    res = {}
    for s in data.SEXES:
        old = pd.read_csv(folder / f"lcc_{s.lower()}_table.csv")
        new = table[table["sex"] == s].merge(old, on=["year", "age"], suffixes=("", "_old"))
        r = (new["m"] / new["m_old"] - 1).abs()
        worst = new.loc[r.idxmax()]
        res[s] = {"cells": len(new), "max_rel": float(r.max()), "at": [int(worst["year"]), int(worst["age"])]}
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--causes-zip", type=Path, default=CAUSES_ZIP)
    ap.add_argument("--check-against", type=Path)
    args = ap.parse_args()
    commit = require_frozen(PROTOCOL_V5)
    table, notes = build(args.causes_zip)
    table.to_csv(OUT, index=False, float_format="%.10g")
    summary = {"protocol_commit": commit, "by_sex": notes}
    for s in data.SEXES:
        print(f"{s}: phi {notes[s]['phi']:.3f}; C1 max |2024 / graduated - 1| {notes[s]['C1_2024_vs_graduated']:.2e}")
    if args.check_against:
        summary["C2"] = check_against(table, args.check_against)
        for s, r in summary["C2"].items():
            print(f"{s}: C2 max relative difference {r['max_rel']:.2e} at {r['at']} over {r['cells']} cells")
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float))
    print(f"wrote {OUT.relative_to(data.ROOT)} and {SUMMARY.relative_to(data.ROOT)}")


if __name__ == "__main__":
    main()
