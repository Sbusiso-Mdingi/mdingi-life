"""v1.3's recovery test (research/PROTOCOL_v1.3.md, "Reporting") run once on v1.2's fitted men's values: a, b and k
of v1.2's production fit for men (RH, 2006 to 2019, scaled deaths) and its real exposures, with the test's known
cohort effect. Needs the Stats SA data, so it is a script, not a unit test.

    python -m research.v13_recovery
"""
from __future__ import annotations

import json

import numpy as np

from mdingilife.models import RenshawHaberman
from research import v11
from research.backtest import OUT, WINDOWS
from tests.test_v13 import AGES, draw, known_g, recovery_error


def main() -> None:
    r = v11.years(v11.data.load("statssa", deaths=v11.SCALED, population=v11.POPULATION)["Male"], WINDOWS["post-peak"])
    v12 = RenshawHaberman().fit(r)
    c = np.arange(v12.c0, v12.c0 + len(v12.g))
    g = known_g(c)
    sim = draw(v12.a, v12.b, v12.k, c, g, r.years, r.E)
    miss, fit, want = recovery_error(sim, c, g)
    out = {"years": [int(r.years[0]), int(r.years[-1])], "miss": miss, "bump_fitted": fit, "bump_target": want,
           "tolerance": 0.03, "passes": miss < 0.03}
    (OUT / "v13_recovery.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    main()
