"""v2 backtest: predict each auction's clearing yields from the curve of the 91 days before it (PROTOCOL_v2.md,
as amended: the frozen 28 days held too few bonds).

    python -m research.curves --period design       # chooses the curve for each kind; writes curves_design.json
    python -m research.curves --period validation   # once, after design; writes curves_validation.json

Validation refuses to run until the design file exists, and uses the curves it chose. Refuses to run until
PROTOCOL_v2.md is frozen.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta

import numpy as np
import pandas as pd

from mdingilife import curves as c
from mdingilife.protocol import PROTOCOL_V2, require_frozen
from research.backtest import OUT
from research.treasury import AUCTIONS, BONDS

WINDOW, SENSITIVITY, B0_DAYS, SCREEN = 91, 182, 91, 0.0100
DESIGN_END = pd.Timestamp("2017-12-31")
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-05-31"))
CURVES = {"fixed": ("LI", "NS", "NSS"), "ilb": ("LI", "NS")}  # NSS is not fitted on inflation-linked bonds


def book() -> dict[str, c.Bond]:
    ref = pd.read_csv(BONDS, parse_dates=["redemption"])
    return {b: c.Bond(b, float(g["coupon"].iloc[0]),
                      tuple((r.date(), float(s)) for r, s in zip(g["redemption"], g["share"])))
            for b, g in ref.groupby("bond")}


def coupon_check(bonds: dict[str, c.Bond]) -> list[str]:
    """Bonds whose schedule coupon dates differ from the ones implied by their final redemption."""
    ref = pd.read_csv(BONDS).drop_duplicates("bond").set_index("bond")["coupon_dates"]
    out = []
    for code, b in bonds.items():
        implied = sorted({f"{d.day:02d}/{d.month:02d}" for d in b.coupon_dates()[-2:]}, key=lambda x: x[3:])
        if "&".join(implied) != ref[code]:
            out.append(f"{code}: schedule {ref[code]}, implied {'&'.join(implied)}")
    return out


def load(bonds: dict[str, c.Bond]) -> tuple[pd.DataFrame, dict]:
    a = pd.read_csv(AUCTIONS, parse_dates=["auction_date", "settlement_date"])
    notes = {"rows": int(len(a))}
    a = a[(a["status"] == "ok") & (a["clearing"] > 0)].copy()
    notes["usable"] = int(len(a))
    lag = (a["settlement_date"] - a["auction_date"]).dt.days
    bad = ~lag.between(1, 10)
    usual = lag[~bad].groupby(a["kind"]).median()
    a.loc[bad, "settlement_date"] = a.loc[bad, "auction_date"] + pd.to_timedelta(a.loc[bad, "kind"].map(usual), "D")
    notes["settlement_repaired"] = int(bad.sum())
    final = a["bond"].map(lambda b: max(d for d, _ in bonds[b].redemptions))
    keep = (pd.to_datetime(final) - a["settlement_date"]).dt.days / 365 >= c.FLOOR
    notes["under_one_year"] = int((~keep).sum())
    a = a[keep].sort_values(["kind", "auction_date", "bond"]).reset_index(drop=True)
    a["y"] = a["clearing"] / 100
    cfs = [bonds[b].cashflows(s.date()) for b, s in zip(a["bond"], a["settlement_date"])]
    a["point"] = [c.Point(b, t, cf, y) for b, (t, cf), y in zip(a["bond"], cfs, a["y"])]
    return a, notes


def window(a: pd.DataFrame, end: pd.Timestamp, days: int, inclusive: bool) -> list[c.Point]:
    """Latest point of each bond auctioned in the `days` days up to `end` (including `end` if `inclusive`)."""
    last = end if inclusive else end - timedelta(days=1)
    w = a[(a["auction_date"] > end - timedelta(days=days)) & (a["auction_date"] <= last)]
    return list(w.sort_values("auction_date").groupby("bond")["point"].last())


def fit(name: str, pts: list[c.Point]):
    """A curve with the protocol's screen: drop bonds missed by more than 100 basis points and refit once."""
    model = c.MODELS[name]
    if len(pts) < model.n_params:
        return None
    curve = model.fit(pts)
    keep = [q for q in pts if abs(curve.bond_yield(q.t, q.cf) - q.y) <= SCREEN]
    if len(keep) < len(pts) and len(keep) >= model.n_params:
        curve = model.fit(keep)
    return curve


def screen(a: pd.DataFrame) -> pd.Series:
    """Flag, in date order, each auction NS misses by more than 100 basis points on its own day's window."""
    flagged = pd.Series(False, index=a.index)
    for kind, g in a.groupby("kind"):
        for d in sorted(g["auction_date"].unique()):
            live = g[~flagged.loc[g.index]]
            pts = window(live, d, WINDOW, inclusive=True)
            if len(pts) < c.NS.n_params:
                continue
            ns = c.NS.fit(pts)
            for i, q in live[live["auction_date"] == d]["point"].items():
                if abs(ns.bond_yield(q.t, q.cf) - q.y) > SCREEN:
                    flagged.loc[i] = True
    return flagged


def _day(job) -> list[dict]:
    kind, d, g, days = job
    pts = window(g, d, days, inclusive=False)
    fitted = {n: fit(n, pts) for n in CURVES[kind]}
    rows = []
    for _, r in g[g["auction_date"] == d].iterrows():
        q = r["point"]
        row = {"kind": kind, "date": d, "bond": r["bond"], "y": q.y, "n_window": len(pts)}
        for n in CURVES["fixed"]:
            f = fitted.get(n)
            row[n] = f.bond_yield(q.t, q.cf) if f is not None else np.nan
        prev = g[(g["bond"] == r["bond"]) & (g["auction_date"] < d) & (g["auction_date"] >= d - timedelta(days=B0_DAYS))]
        row["B0"] = prev.sort_values("auction_date")["y"].iloc[-1] if len(prev) else np.nan
        rows.append(row)
    return rows


def predict(a: pd.DataFrame, days: int, period: str) -> pd.DataFrame:
    in_period = a["auction_date"] <= DESIGN_END if period == "design" else a["auction_date"] > DESIGN_END
    jobs = []
    for kind, g in a.groupby("kind"):
        for d in sorted(g.loc[in_period, "auction_date"].unique()):
            near = g[(g["auction_date"] > d - timedelta(days=max(days, B0_DAYS))) & (g["auction_date"] <= d)]
            jobs.append((kind, d, near, days))
    with ProcessPoolExecutor() as pool:
        return pd.DataFrame([r for rows in pool.map(_day, jobs, chunksize=8) for r in rows])


def scores(p: pd.DataFrame, models, extra=()) -> dict:
    """RMSE and mean absolute error in basis points, by kind, on the auctions every model compared priced.
    `models` is a tuple, or a dict of tuples by kind; `extra` is added to every kind."""
    out = {}
    for kind, g in p.groupby("kind"):
        ms = tuple(models[kind] if isinstance(models, dict) else models) + tuple(extra)
        g = g.dropna(subset=list(ms))
        models_k = ms
        e = {m: 1e4 * (g[m] - g["y"]) for m in models_k}
        out[kind] = {"n": int(len(g)), **{m: {"rmse": float(np.sqrt((v ** 2).mean())), "mae": float(v.abs().mean())}
                                         for m, v in e.items()}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", required=True, choices=["design", "validation"])
    period = ap.parse_args().period
    frozen = require_frozen(PROTOCOL_V2)
    if period == "validation" and not (OUT / "curves_design.json").exists():
        raise SystemExit("run --period design first")
    bonds = book()
    a, notes = load(bonds)
    flagged = screen(a)
    notes["screened"] = int(flagged.sum())
    notes["screened_rows"] = a.loc[flagged, ["kind", "auction_date", "bond", "clearing"]].astype(str).to_dict("records")
    a = a[~flagged]
    out = {"protocol": frozen, "period": period, "data": notes, "coupon_check": coupon_check(bonds)}

    p = predict(a, WINDOW, period)
    p.drop(columns=[]).to_csv(OUT / f"curves_{period}_predictions.csv", index=False)
    out["curves"] = scores(p, CURVES)
    out["all"] = scores(p, CURVES, ("B0",))
    if period == "design":
        out["chosen"] = {k: min(CURVES[k], key=lambda m: v[m]["rmse"]) for k, v in out["curves"].items()}
    else:
        design = json.loads((OUT / "curves_design.json").read_text())
        chosen = out["chosen"] = design["chosen"]
        calm = p[~p["date"].between(*COVID)]
        out["without_covid"] = {"curves": scores(calm, CURVES), "all": scores(calm, CURVES, ("B0",))}
        tests = {}
        for kind, m in chosen.items():
            vs_b0 = scores(p[p["kind"] == kind], (m, "B0"))[kind]
            tests[kind] = {
                "C1": vs_b0[m]["rmse"] < vs_b0["B0"]["rmse"], "C1_rmse": {m: vs_b0[m]["rmse"], "B0": vs_b0["B0"]["rmse"]},
                "C3": out["curves"][kind][m]["rmse"] < 25, "C3_rmse": out["curves"][kind][m]["rmse"],
            }
            if "NSS" in CURVES[kind]:  # C2 is tested on fixed-rate bonds only (amendment of 26 October 2026)
                vs_ns = scores(p[p["kind"] == kind], ("NS", "NSS"))[kind]
                tests[kind] |= {"C2": vs_ns["NSS"]["rmse"] < vs_ns["NS"]["rmse"],
                                "C2_rmse": {k2: vs_ns[k2]["rmse"] for k2 in ("NS", "NSS")}}
        out["tests"] = tests
        s = predict(a, SENSITIVITY, period)
        out[f"sensitivity_{SENSITIVITY}_days"] = {"curves": scores(s, CURVES), "all": scores(s, CURVES, ("B0",))}
    (OUT / f"curves_{period}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in out if k not in ("data",)}, indent=1, default=str)[:4000])
    print(json.dumps({k: v for k, v in notes.items() if k != "screened_rows"}, indent=1))


if __name__ == "__main__":
    main()
