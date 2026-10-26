"""Exposure for the Stats SA run: UN WPP 2024 1 July population by single age and sex (protocol amendment, 26 Oct 2026).

Written for the years whose deaths the DataFirst files hold in full, 1997 to 2022. 2023 is left out because
only its late registrations are on file, and 2024 because WPP ends in 2023. data.statssa merges deaths onto
this file, so a year missing here is a year not fitted.

Writes data/raw/statssa/wpp_population.csv (year, sex, age, population).
"""
from __future__ import annotations

from mdingilife import data

OUT = data.RAW / "statssa" / "wpp_population.csv"
YEARS = range(1997, 2023)


def main() -> None:
    w = data.wpp()
    w = w[w["year"].isin(YEARS)].rename(columns={"exposure": "population"})
    w[["year", "sex", "age", "population"]].to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(data.ROOT)}: {len(w):,} cells, {w['year'].min()}-{w['year'].max()}")


if __name__ == "__main__":
    main()
