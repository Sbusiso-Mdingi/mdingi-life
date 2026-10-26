"""v1.2 (research/PROTOCOL_v1.2.md): v1.1 with each sex choosing its own fitting window per model.

    python -m research.v12

Writes research/results/v12.json. Refuses to run until PROTOCOL_v1.2.md is frozen.
"""
from __future__ import annotations

import json
import time

import numpy as np

from mdingilife import average
from mdingilife.protocol import PROTOCOL_V1_2, require_frozen
from research import v11
from research.backtest import OUT, WINDOWS

SEED = 20261029


def by_sex(d: dict) -> dict[str, dict]:
    """Windows, weights and inverse weights for each sex from its own design deviances."""
    out = {}
    for s, sc in d["scores"].items():
        windows = {n: min(WINDOWS, key=lambda w: sc[f"{n} {w}"]["deviance"]) for n in v11.NAMES}
        dev = {n: sc[f"{n} {windows[n]}"]["deviance_anchored"] for n in v11.NAMES}
        phi = float(np.mean([sc[f"{n} {windows[n]}"]["phi"] for n in v11.NAMES]))
        out[s] = {"windows": windows, "weights": {s: average.weights(dev, phi)},
                  "inverse_weights": {s: average.inverse(dev)}}
    return out


def main() -> None:
    frozen = require_frozen(PROTOCOL_V1_2)
    load = lambda deaths: v11.data.load("statssa", deaths=deaths, population=v11.POPULATION)
    panels = {"scaled": load(v11.SCALED), "registered": load(v11.DEATHS)}
    rng = np.random.default_rng(SEED)
    out = {"protocol_v1_2": frozen, "seed": SEED}
    t = time.time()
    d = v11.design(panels["scaled"], rng)
    ds = by_sex(d)
    out["design"] = {"scores": d["scores"], "by_sex": ds}
    print(json.dumps({s: {"windows": x["windows"], "weights": x["weights"][s]} for s, x in ds.items()}, default=float))
    val = {s: v11.validation({s: r}, ds[s], rng) for s, r in panels["scaled"].items()}
    out["validation"] = {s: val[s][s] for s in val}
    out["validation"]["tests"] = {q: {s: val[s]["tests"][q][s] for s in val} for q in ("Q1", "Q2", "Q3", "Q4")}
    print("tests", out["validation"]["tests"], f"{time.time() - t:.0f}s", flush=True)
    out["prices"] = {}
    for name, spec in v11.RUNS.items():
        if spec["models"] == "v1":
            continue  # v1.1's anchor step does not depend on the windows
        out["prices"][name] = {s: v11.price(r, spec, ds[s], s, rng) for s, r in panels[spec["data"]].items()}
        print(name, f"{time.time() - t:.0f}s", flush=True)
        (OUT / "v12.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
