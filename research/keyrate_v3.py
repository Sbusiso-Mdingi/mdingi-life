"""v3 with the annuities matched on key rates instead of duration (PROTOCOL_v3.md, amendment of 26 October 2026).

    python -m research.keyrate_v3 --deaths data/raw/statssa/mcd_deaths.csv \\
        --population data/raw/statssa/wpp_population.csv

Main basis only, everything else as in balance_v3. Writes research/results/keyrate_v3.json, with K6 against the
two-bond result in balance_v3.json.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from mdingilife.protocol import PROTOCOL_V2, PROTOCOL_V3, require_frozen
from research.backtest import OUT
from research.balance_v3 import Basis, annuitant_grids, market, run
from research.book_v3 import TABLE


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deaths", required=True)
    ap.add_argument("--population", required=True)
    args = ap.parse_args()
    frozen = {"v1": require_frozen(), "v2": require_frozen(PROTOCOL_V2), "v3": require_frozen(PROTOCOL_V3)}
    duration = json.loads((OUT / "balance_v3.json").read_text())["main"]
    curves, bonds, _, settle = market()
    grids = annuitant_grids(args.deaths, args.population)
    key = run(grids, pd.read_csv(TABLE), Basis(), curves, bonds, settle, method="key")
    k6 = {"key_rate": key["interest"]["combined"], "duration": duration["interest"]["combined"]}
    k6["pass"] = bool(k6["key_rate"] < k6["duration"])
    out = {"protocol": frozen, "key_rate": key, "checks": {"K6": k6},
           "same_liabilities": abs(key["bel"]["total"] - duration["bel"]["total"]) < 1e-3
           and abs(key["risk_margin"] - duration["risk_margin"]) < 1e-3}
    (OUT / "keyrate_v3.json").write_text(json.dumps(out, indent=1, default=float))
    M = lambda x: f"{x / 1e6:,.1f}"
    for kind, v in key["assets"]["matching"].items():
        print(kind, {c: (round(v["bonds"][c]["duration"], 1), M(n * v["bonds"][c]["value"])) for c, n in v["units"].items()})
    print("interest", {k: M(v) for k, v in key["interest"].items()}, "rates", {k: M(v) for k, v in key["rate_losses"].items()})
    print(f"SCR {M(key['scr'])} cover {key['cover']:.3f}  (duration: SCR {M(duration['scr'])} cover {duration['cover']:.3f})",
          "K6", k6["pass"], "same liabilities", out["same_liabilities"])


if __name__ == "__main__":
    main()
