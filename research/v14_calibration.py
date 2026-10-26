"""Calibrate v1.4's flag cutoff and absorbed-share threshold on simulated data only (research/PROTOCOL_v1.4.md,
"Pre-freeze change"). Seeds are apart from the unit tests' (stream 1), so the tests stay an independent check.

1. Flag cutoff: the lowest on CUTOFFS that flags at most 10% of plain series (L5 setting) and the 0.30 jump in
   2021 in at least 90% of series.
2. The 2022 trend test's band, at that cutoff: kept at 2 sd sqrt(3) if it passes at least 80% of correct-model
   series (Covid-shaped one-year jumps). Otherwise the narrowest band passing 90% of them (the 90th percentile of
   |K hat(2022) - trend| / (sd sqrt(3)), rounded up to 0.01), and no wider.
3. Absorbed-share threshold, at that cutoff and band: the highest on THRESHOLDS at which the whole rule (share and
   trend test) passes at least 80% of correct-model series. The wrong model (the same rise, kept permanently in
   the trend) is reported beside it at every step; it is not a pass requirement, because data to 2022 cannot
   tell a permanent shift from jumps in 2021 and 2022.

Writes research/results/v14_calibration.json.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mdingilife import jumps
from tests.test_v14 import BJ_RISING, ROOT, SERIES, pipeline, simulate

STREAM = 1
CUTOFFS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.975, 0.99]
THRESHOLDS = np.round(np.arange(0.30, 0.951, 0.05), 2).tolist()
CASES = {
    "plain": {},
    "recovery": {"jump": {2021: 0.3}, "bJ": BJ_RISING},
    "correct": {"jump": {2020: 0.10, 2021: 0.30, 2022: 0.08}},
    "wrong": {"shift": {2020: 0.10, 2021: 0.20}},      # +0.10 in 2020, +0.30 from 2021, kept in the trend
}
OUT = ROOT / "research" / "results" / "v14_calibration.json"


def one(args):
    case, i, cutoff = args
    f, s, _ = pipeline(simulate(i, stream=STREAM, **CASES[case]), "J1", True, cutoff=cutoff)
    return {"prob": f.series.prob.tolist(), "share": s["absorbed_share"], "pass_trend": s["pass_trend"],
            "z": abs(s["K2022_minus_trend"]) / (f.series.sd * np.sqrt(3))}


def run(case, cutoff=None):
    with ProcessPoolExecutor() as ex:
        return list(ex.map(one, [(case, i, cutoff) for i in range(SERIES)], chunksize=4))


def main():
    years = list(range(1997, 2023))
    plain, rec = run("plain"), run("recovery")
    grid = []
    for c in CUTOFFS:
        false = float(np.mean([any(p > c for p in r["prob"]) for r in plain]))
        hit = float(np.mean([r["prob"][years.index(2021)] > c for r in rec]))
        grid.append({"cutoff": c, "plain_any_flag": false, "recovery_flags_2021": hit})
    ok = [g for g in grid if g["plain_any_flag"] <= 0.10 and g["recovery_flags_2021"] >= 0.90]
    cutoff = ok[0]["cutoff"] if ok else None
    out = {"stream": STREAM, "series": SERIES, "cutoff_grid": grid, "cutoff": cutoff}
    if cutoff is not None:
        cases = {k: run(k, cutoff) for k in ("correct", "wrong")}
        out["series_results"] = cases

        def trend(k, z):
            return float(np.mean([r["z"] <= z for r in cases[k]]))

        band = jumps.BAND
        out["trend_at_2"] = {k: trend(k, 2.0) for k in cases}
        if out["trend_at_2"]["correct"] < 0.80:
            band = float(np.ceil(np.quantile([r["z"] for r in cases["correct"]], 0.90) * 100) / 100)
        out["band"] = band
        out["trend_at_band"] = {k: trend(k, band) for k in cases}
        rows = []
        for t in THRESHOLDS:
            row = {"threshold": t}
            for k, rs in cases.items():
                row[f"{k}_share"] = float(np.mean([r["share"] >= t for r in rs]))
                row[f"{k}_passes"] = float(np.mean([r["share"] >= t and r["z"] <= band for r in rs]))
            rows.append(row)
        out["threshold_grid"] = rows
        out["median_share"] = {k: float(np.nanmedian([r["share"] for r in rs])) for k, rs in cases.items()}
        good = [r for r in rows if r["correct_passes"] >= 0.80]
        out["threshold"] = good[-1]["threshold"] if good else None
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "series_results"}, indent=1))


if __name__ == "__main__":
    main()
