"""Deaths and exposures by single age, sex and year.

Every source is reduced to the same shape: a `Rates` panel of deaths D and exposure E with ages in rows and
years in columns. The models never see which source a panel came from.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
WPP = RAW / "wpp"
SEXES = ("Male", "Female")


@dataclass
class Rates:
    sex: str
    ages: np.ndarray
    years: np.ndarray
    D: np.ndarray
    E: np.ndarray

    @property
    def m(self) -> np.ndarray:
        return self.D / self.E

    def sub(self, ages=None, years=None) -> "Rates":
        a = np.ones(len(self.ages), bool) if ages is None else np.isin(self.ages, list(ages))
        y = np.ones(len(self.years), bool) if years is None else np.isin(self.years, list(years))
        return Rates(self.sex, self.ages[a], self.years[y], self.D[np.ix_(a, y)], self.E[np.ix_(a, y)])


def spread_unknown(df: pd.DataFrame, key: list[str], value: str = "deaths") -> pd.DataFrame:
    """Spread rows whose age is missing over the known ages of the same key, in proportion to them."""
    known = df[df["age"].notna()].copy()
    lost = df[df["age"].isna()].groupby(key)[value].sum().rename("unknown")
    share = known.groupby(key)[value].transform(lambda s: s / s.sum())
    known = known.join(lost, on=key)
    known[value] += share * known["unknown"].fillna(0)
    return known.drop(columns="unknown")


def panel(df: pd.DataFrame, sex: str) -> Rates:
    """Tidy frame (year, sex, age, deaths, exposure) to a Rates panel for one sex."""
    d = df[df["sex"] == sex]
    D = d.pivot(index="age", columns="year", values="deaths").sort_index().sort_index(axis=1)
    E = d.pivot(index="age", columns="year", values="exposure").reindex_like(D)
    if D.isna().any().any() or E.isna().any().any():
        raise ValueError(f"{sex}: missing cells in the panel")
    return Rates(sex, D.index.to_numpy(int), D.columns.to_numpy(int), D.to_numpy(float), E.to_numpy(float))


def wpp() -> pd.DataFrame:
    """UN WPP 2024 for South Africa. Deaths over the calendar year; exposure is the 1 July population.

    Both files are in thousands. The open age group 100+ is dropped: no model uses ages above 89.
    """
    keep = ["Time", "AgeGrp"]
    d = pd.read_csv(WPP / "wpp2024_zaf_deaths_1950-2023.csv", usecols=keep + ["DeathMale", "DeathFemale"])
    p = pd.read_csv(WPP / "wpp2024_zaf_population_1950-2023.csv", usecols=keep + ["PopMale", "PopFemale"])
    df = d.merge(p, on=keep, validate="one_to_one")
    df = df[df["AgeGrp"] != "100+"].astype({"AgeGrp": int})
    rows = []
    for s in SEXES:
        rows.append(pd.DataFrame({"year": df["Time"], "sex": s, "age": df["AgeGrp"],
                                  "deaths": 1000 * df[f"Death{s}"], "exposure": 1000 * df[f"Pop{s}"]}))
    return pd.concat(rows, ignore_index=True)


def statssa(deaths: Path, population: Path) -> pd.DataFrame:
    """Stats SA registered deaths (P0309.3) over mid-year estimates (P0302), from tidy CSVs.

    deaths: year, sex, age, deaths, with age blank where unknown. population: year, sex, age, population.
    Deaths with unknown sex are spread over the sexes the same way as unknown ages over ages.
    """
    d = _spread_sex(pd.read_csv(deaths))
    p = pd.read_csv(population).rename(columns={"population": "exposure"})
    return d.astype({"age": int}).merge(p, on=["year", "sex", "age"], validate="one_to_one")


def _spread_sex(d: pd.DataFrame) -> pd.DataFrame:
    """Unknown ages within year and sex first, then deaths of unknown sex over all cells of the year."""
    known = spread_unknown(d[d["sex"].notna()], ["year", "sex"])
    lost = d[d["sex"].isna()].groupby("year")["deaths"].sum().rename("unknown")
    share = known.groupby("year")["deaths"].transform(lambda s: s / s.sum())
    known = known.join(lost, on="year")
    known["deaths"] += share * known["unknown"].fillna(0)
    return known.drop(columns="unknown")


def load(source: str = "wpp", **paths) -> dict[str, Rates]:
    df = wpp() if source == "wpp" else statssa(**paths)
    return {s: panel(df, s) for s in SEXES}
