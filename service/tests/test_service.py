"""The service answers from the precomputed grid and refuses anything off it."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
R = json.loads((ROOT / "data" / "research.json").read_text())
client = TestClient(app)


def test_health():
    for path in ("/healthz", "/api/health"):
        r = client.get(path)
        assert r.status_code == 200 and r.json()["ok"]
        assert r.json()["protocol"] == R["protocol"]


def test_research_is_the_file():
    r = client.get("/api/research")
    assert r.status_code == 200
    assert r.json() == R
    assert "frame-ancestors" in r.headers["content-security-policy"]


@pytest.mark.parametrize("sex", ["Male", "Female"])
def test_every_grid_point_matches_research(sex):
    for p in R["annuities"][sex]["prices"]:
        r = client.get("/api/price", params={"sex": sex, "age": p["age"], "rate": p["rate"], "adj": p["adj"]})
        assert r.status_code == 200
        got = r.json()
        for k in ("median", "lo", "hi", "width_pct"):
            assert got[k] == pytest.approx(p[k])
        assert got["lo"] < got["median"] < got["hi"]


def test_headline_and_lower_bound():
    men = client.get("/api/price?sex=male&age=65&rate=0.04&adj=0.7").json()
    women = client.get("/api/price?sex=Female&age=65&rate=0.040&adj=0.70").json()
    assert 13 < men["width_pct"] < 16 and 13 < women["width_pct"] < 16
    assert men["lower_bound"] is (not R["backtest"]["tests"]["P3"]["Male"])
    assert women["lower_bound"] is (not R["backtest"]["tests"]["P3"]["Female"])


@pytest.mark.parametrize("query", [
    "sex=other&age=65&rate=0.04&adj=0.7",
    "sex=Male&age=60&rate=0.04&adj=0.7",
    "sex=Male&age=65&rate=0.05&adj=0.7",
    "sex=Male&age=65&rate=0.04&adj=1",
    "sex=Male&age=65&rate=4&adj=0.7",
])
def test_off_grid_is_400(query):
    r = client.get(f"/api/price?{query}")
    assert r.status_code == 400
    assert "must be one of" in r.json()["detail"]


def test_missing_or_malformed_is_rejected():
    assert client.get("/api/price?sex=Male&age=65&rate=0.04").status_code == 422
    assert client.get("/api/price?sex=Male&age=old&rate=0.04&adj=0.7").status_code == 422
