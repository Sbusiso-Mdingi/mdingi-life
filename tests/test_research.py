"""The research scripts end to end on simulated panels (never on real data before the protocol is frozen)."""
from __future__ import annotations

import numpy as np
import pytest

from mdingilife.data import Rates
from mdingilife import protocol
from research import annuities, backtest

AGES, YEARS = np.arange(50, 90), np.arange(1997, 2024)


def fake(sex, seed):
    rng = np.random.default_rng(seed)
    a = -9.5 + 0.09 * AGES
    b = np.full(len(AGES), 1 / len(AGES))
    k = np.cumsum(-1.5 + 0.8 * rng.standard_normal(len(YEARS)))
    E = np.full((len(AGES), len(YEARS)), 5e5)
    D = rng.poisson(E * np.exp(a[:, None] + np.outer(b, k - k.mean()))).astype(float)
    return Rates(sex, AGES, YEARS, D, E)


@pytest.fixture
def panels(monkeypatch):
    monkeypatch.setattr(backtest, "PATHS", 300)
    monkeypatch.setattr(annuities, "REFITS", 3)
    monkeypatch.setattr(annuities, "PATHS", 60)
    return {"Male": fake("Male", 1), "Female": fake("Female", 2)}


def test_backtest_runs_and_reports_every_test(panels):
    out = backtest.run(panels)
    assert set(out["windows"]) == {"LC", "CBD", "RH"}
    assert set(out["tests"]) == {"chosen", "P1", "P2", "P3", "P4"}
    for key, res in out["validation"].items():
        assert set(res) == {"Male", "Female"}
        assert len(res["Male"]["annuity_error"]) == 3


def test_annuity_prices_have_intervals(panels):
    out = annuities.price(panels["Male"], "LC post-peak", "post-peak", np.random.default_rng(0))
    assert out["jump_off"] == 2023
    assert len(out["prices"]) == 3 * 3 * 3
    for p in out["prices"]:
        assert p["lo"] <= p["median"] <= p["hi"]
    by = {(p["age"], p["rate"], p["adj"]): p["median"] for p in out["prices"]}
    assert by[(55, 0.04, 0.6)] > by[(65, 0.04, 0.6)] > by[(75, 0.04, 0.6)]
    assert by[(65, 0.02, 0.7)] > by[(65, 0.04, 0.7)] > by[(65, 0.06, 0.7)]


@pytest.mark.parametrize("line", ["Frozen at commit: (filled in at freeze)", "Frozen at commit: `0123456789ab`"])
def test_guard_blocks_until_frozen(tmp_path, monkeypatch, line):
    (tmp_path / "PROTOCOL.md").write_text(f"# Protocol\n\n{line}\n")
    monkeypatch.setattr(protocol, "PROTOCOL", tmp_path / "PROTOCOL.md")
    assert protocol.frozen_hash() is None
    with pytest.raises(SystemExit):
        protocol.require_frozen()


def test_guard_passes_once_frozen(tmp_path, monkeypatch):
    (tmp_path / "PROTOCOL.md").write_text("# Protocol\n\nFrozen at commit: `25b5acd95aa5`\n")
    monkeypatch.setattr(protocol, "PROTOCOL", tmp_path / "PROTOCOL.md")
    assert protocol.require_frozen() == "25b5acd95aa5"


def test_rolling_windows_end_at_the_origin():
    from research import rolling
    assert rolling.start("rolling", 2016) == 2007
    assert rolling.start("post-peak", 2009) == 2006
    assert len(rolling.candidates()) == 10


def test_rolling_scores_every_origin_and_weights_sum_to_one(panels, monkeypatch):
    from research import rolling
    monkeypatch.setattr(rolling, "ORIGINS", range(2012, 2015))
    monkeypatch.setattr(rolling, "PATHS", 60)
    rng = np.random.default_rng(0)
    scores = rolling.backtest(panels, rng)
    windows = {"LC": "post-peak", "CBD": "full", "RH": "full"}
    chosen = {"Male": "CBD full", "Female": "LC post-peak"}
    s = rolling.summarise(scores, panels, chosen, windows)
    for sex in panels:
        assert sum(v["wins"] for k, v in s["by_sex"][sex].items() if not k.startswith("_")) == 3
        assert sum(s["weights"][sex].values()) == pytest.approx(1)
    b = rolling.blend(panels, chosen, windows, s["weights"], rng)
    for p in b["Male"]["prices"]:
        assert p["lo"] <= p["median"] <= p["hi"]
