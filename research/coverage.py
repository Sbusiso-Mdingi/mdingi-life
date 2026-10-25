"""Coverage check: which years, ages and sexes each source has, and any holes. Computes no rates or models."""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from mdingilife import data


def report(df: pd.DataFrame, label: str) -> None:
    print(f"== {label}")
    for s, d in df.groupby("sex"):
        years, ages = np.sort(d["year"].unique()), np.sort(d["age"].unique())
        full = len(years) * len(ages)
        gaps = sorted(set(range(years.min(), years.max() + 1)) - set(years))
        print(f"{s}: years {years.min()}-{years.max()} ({len(years)}{', gaps ' + str(gaps) if gaps else ''}), "
              f"ages {ages.min()}-{ages.max()} ({len(ages)}), cells {len(d)}/{full}")
        print(f"  missing deaths {d['deaths'].isna().sum()}, missing exposure {d['exposure'].isna().sum()}, "
              f"zero deaths {(d['deaths'] == 0).sum()}, zero exposure {(d['exposure'] == 0).sum()}")
        fit = d[d["age"].between(50, 89) & d["year"].between(1997, 2023)]
        print(f"  ages 50-89, 1997-2023: {len(fit)} cells, smallest deaths {fit['deaths'].min():.0f}, "
              f"smallest exposure {fit['exposure'].min():.0f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="wpp", choices=["wpp", "statssa"])
    ap.add_argument("--deaths")
    ap.add_argument("--population")
    a = ap.parse_args()
    if a.source == "wpp":
        raw = pd.read_csv(data.WPP / "wpp2024_zaf_deaths_1950-2023.csv", usecols=["Time", "AgeGrp"])
        open_ = sorted(g for g in raw["AgeGrp"].unique() if not str(g).isdigit())
        print(f"WPP age groups: {raw['AgeGrp'].nunique()}, open group {open_} (dropped)")
        report(data.wpp(), "UN WPP 2024, South Africa")
    else:
        report(data.statssa(a.deaths, a.population), "Stats SA")


if __name__ == "__main__":
    main()
