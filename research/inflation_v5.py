"""v5's inflation model (research/PROTOCOL_v5.md, "Inflation model"): phi and the volatility of the one-year breakeven
from v4's two-factor curve fits at month-ends, January 2011 to September 2026, and G(n) on the valuation date with
the cap and floor, with neither and with the cap only; checks C7 and C8.

    python -m research.inflation_v5

Writes research/results/inflation_v5.json. Used by research.balance_v5. Refuses to run until PROTOCOL_v5.md is frozen.
Source: National Treasury bond auction results (non-commercial use, with acknowledgement).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from mdingilife import inflation_v5 as iv, sam
from mdingilife.curves import ns
from mdingilife.protocol import PROTOCOL_V5, require_frozen
from research import curves as rc
from research import scenarios_v4 as sv
from research.backtest import OUT
from research.balance_v3 import YEARS, Curves, BASE, auctions, market

RESULT = OUT / "inflation_v5.json"
SE_LIMIT, SE_YEARS = 0.002, 50
SHOW = (1, 2, 5, 10, 20, 30, 50)


def one_year_breakeven(cal: dict) -> pd.Series:
    """(1 + nominal 1-year spot) / (1 + real 1-year spot) - 1 from the month-end factors (NaN where a kind has none)."""
    F, n = cal["factors"], cal["n"]
    z = {}
    for k in sv.KINDS:
        b = [F[f"{k[0]}{name}"].to_numpy() if j < n else 0.0 for j, name in enumerate(sv.NAMES)]
        z[k] = ns(1.0, *b, cal["tau"][k])
    return pd.Series(np.expm1(z["nominal"] - z["real"]), index=F.index)


def calibrate(a: pd.DataFrame | None = None, days: dict | None = None) -> tuple[iv.Model, pd.Series]:
    bonds = rc.book()
    a = auctions(bonds) if a is None else a
    if days is None:
        _, _, days, _ = market(a)
    jump = {k: rc.window(a[a["kind"] == kind], days[k][1], rc.WINDOW, inclusive=True) for k, kind in sv.KINDS.items()}
    cal = sv.calibrate(sv.month_points(a), jump)
    i = one_year_breakeven(cal)
    return iv.Model.fit(i.to_numpy()), i


def enough_paths(model: iv.Model, f: float) -> tuple[np.ndarray, int, dict]:
    """C8: paths doubled from iv.PATHS until G's standard error is below SE_LIMIT of G at every n to SE_YEARS."""
    n = iv.PATHS
    while True:
        x = iv.paths(model, YEARS, n)
        g, se = iv.growth(f, x, se=True)
        worst = float(np.max((se / g)[1:SE_YEARS + 1]))
        if worst < SE_LIMIT:
            return x, n, {"paths": n, "worst_se_share": worst, "pass": True}
        n *= 2


def main() -> None:
    commit = require_frozen(PROTOCOL_V5)
    curves, bonds, days, settle = market()
    model, i = calibrate(days=days)
    nom, real = Curves(curves["LI"]["nominal"], curves["LI"]["real"]).get(BASE)
    f = sam.breakeven(nom, real)
    x, n, c8 = enough_paths(model, f)
    g = {"cap and floor": iv.growth(f, x), "neither": iv.growth(f, x, None, None), "cap only": iv.growth(f, x, floor=None)}
    g_flat = iv.growth(f, np.zeros_like(x))
    c7 = float(np.max(np.abs(g_flat / (1 + min(max(f, iv.FLOOR), iv.CAP)) ** np.arange(YEARS + 1) - 1)))
    shocked = iv.growth(f, x, scale=iv.shock_scale(model, f, YEARS))
    out = {"protocol_commit": commit, "months": int(i.notna().sum()), "first": str(i.dropna().index[0].date()),
           "last": str(i.dropna().index[-1].date()), "phi": model.phi, "sigma_month": model.sigma,
           "sd_long_run": model.sigma / np.sqrt(1 - model.phi ** 2), "mean_history": float(i.mean()), "f": f,
           "history": {str(d.date()): float(v) for d, v in i.dropna().items()},
           "G": {k: list(v) for k, v in g.items()}, "G_vol_shocked": list(shocked),
           "C7": {"max_rel": c7, "pass": bool(c7 < 1e-12)}, "C8": c8}
    RESULT.write_text(json.dumps(out, indent=1))
    print(f"one-year breakeven, {out['months']} months {out['first']} to {out['last']}: mean {out['mean_history']:.4f}; "
          f"phi {model.phi:.4f} a month, sigma {model.sigma:.4f}, long-run sd {out['sd_long_run']:.4f}; f {f:.4f}")
    print(f"C7 {c7:.1e}; C8 {c8}")
    for k, v in {**g, "vol shocked": shocked}.items():
        print(f"  G {k:14s}" + "  ".join(f"{n_}: {v[n_]:.4f}" for n_ in SHOW))


if __name__ == "__main__":
    main()
