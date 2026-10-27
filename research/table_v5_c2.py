"""C2's diagnosis (research/PROTOCOL_v5.md, "Checks"): the port missed a relative 1e-6 against the table built outside
the repository (1.25e-5 for men, 1.43e-5 for women). That table's scripts wrote every intermediate CSV at %.6g and
the next step read it back. This reruns the port with the same rounding at those five points (life table, smoothed
2024 table, cause split, projection) and compares again. Writes research/results/funeral_table_v5_c2.json."""
import json
import numpy as np, pandas as pd
from mdingilife import data, table_v5 as t5
from research import table_v5 as r5
from pathlib import Path
T = Path.home() / "Temp Sbu Folder"
r6 = lambda v: np.array([float(f"{x:.6g}") for x in np.ravel(v)]).reshape(np.shape(v))
P, sh = r5.panel(), t5.shares(r5.cause_tally(r5.CAUSES_ZIP))
mine = pd.read_csv(r5.OUT)
out = {}
for s in data.SEXES:
    p = P[s]; ages, years = np.asarray(p.ages), np.asarray(p.years)
    phi = float(pd.read_csv(T / "overdispersion.csv", index_col="sex").phi[s.lower()])
    j = list(years).index(2024)
    g = t5.graduate(r6(p.D[:, j]), r6(p.E[:, j]), phi)                     # lifetable_{sex}_2024.csv
    gm = r6(g["m"])                                                        # graduated_{sex}_2024.csv
    cols = [i for i, y in enumerate(years) if y >= t5.START and y not in t5.LEFT_OUT]
    a = ages <= t5.LC_TOP
    D, E, yr = p.D[a][:, cols], p.E[a][:, cols], years[cols]
    ix = pd.MultiIndex.from_product([yr, [s], ages[a]])
    h = sh["hiv"].reindex(ix).fillna(0).to_numpy().reshape(len(yr), -1).T
    e = sh["ext"].reindex(ix).fillna(0).to_numpy().reshape(len(yr), -1).T
    m = D / E                                                              # cause_split.csv
    Er = r6(E)
    Ds = {"hiv": r6(m * h) * Er, "ext": r6(m * e) * Er, "other": r6(m * (1 - h - e)) * Er}
    fit = t5.fit_cause_lc(Ds, Er, ages[a], yr)
    lc = r6(t5.project(fit, ages[a], yr))                                  # lcc_{sex}_projected.csv
    tab = t5.table(gm, lc)
    old = pd.read_csv(T / f"lcc_{s.lower()}_table.csv").sort_values(["year", "age"]).m.to_numpy().reshape(tab.shape)
    new = mine[mine.sex == s].sort_values(["year", "age"]).m.to_numpy().reshape(tab.shape)
    out[s] = {"max_rel_vs_outside": float(np.max(np.abs(tab / old - 1))), "share_equal_at_6g": float(np.mean(r6(tab) == old)),
              "max_rel_vs_full_precision": float(np.max(np.abs(tab / new - 1)))}
    print(f"{s}: rounded-input port vs Temp: max rel {np.max(np.abs(tab / old - 1)):.2e}; "
          f"cells equal after %.6g {np.mean(r6(tab) == old):.4%}; "
          f"rounded-input vs full-precision port: max rel {np.max(np.abs(tab / new - 1)):.2e}")
(data.ROOT / "research" / "results" / "funeral_table_v5_c2.json").write_text(json.dumps(out, indent=2))
