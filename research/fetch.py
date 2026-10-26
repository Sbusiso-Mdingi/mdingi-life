"""Download UN WPP 2024 single-age files and keep South Africa only.

`python -m research.fetch projection` downloads the medium-variant projection from 2024 instead, for v1.4's 2024
link (research/PROTOCOL_v1.4.md, "2024"), and keeps South Africa's rows for 2024 only.

The global files (about 500 MB) stay in data/raw/wpp and are git-ignored; the South African extracts are kept.
Stats SA files are downloaded by hand into data/raw/statssa (the site blocks scripted access).
"""
from __future__ import annotations

import gzip
import io
import urllib.request

import pandas as pd

from mdingilife.data import WPP

BASE = "https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/"
ZAF = 710
FILES = {
    "deaths": "WPP2024_DeathsBySingleAgeSex_Medium_1950-2023.csv.gz",
    "population": "WPP2024_PopulationBySingleAgeSex_Medium_1950-2023.csv.gz",
    "life_tables": ["WPP2024_Life_Table_Complete_Medium_Male_1950-2023.csv.gz",
                    "WPP2024_Life_Table_Complete_Medium_Female_1950-2023.csv.gz"],
}
PROJECTION = {
    "deaths": "WPP2024_DeathsBySingleAgeSex_Medium_2024-2100.csv.gz",
    "population": "WPP2024_PopulationBySingleAgeSex_Medium_2024-2100.csv.gz",
}


def get(name: str) -> pd.DataFrame:
    path = WPP / name
    if not path.exists():
        print("downloading", name)
        with urllib.request.urlopen(BASE + name, timeout=900) as r:
            path.write_bytes(r.read())
    with gzip.open(path, "rb") as f:
        df = pd.read_csv(io.BytesIO(f.read()), encoding="utf-8-sig", low_memory=False)
    return df[df["LocID"] == ZAF]


def main(projection: bool = False) -> None:
    WPP.mkdir(parents=True, exist_ok=True)
    for key, names in (PROJECTION if projection else FILES).items():
        names = names if isinstance(names, list) else [names]
        df = pd.concat([get(n) for n in names], ignore_index=True)
        if projection:
            df = df[df["Time"] == 2024]
        out = WPP / (f"wpp2024_zaf_{key}_2024.csv" if projection else f"wpp2024_zaf_{key}_1950-2023.csv")
        df.to_csv(out, index=False)
        print(f"{out.name}: {len(df)} rows")


if __name__ == "__main__":
    import sys

    main(projection=sys.argv[1:] == ["projection"])
