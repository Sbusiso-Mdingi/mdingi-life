"""HTTP service for the Mdingi Life dashboard: the research record and annuity prices from its precomputed grid.

Nothing is fitted here. Prices are looked up in data/research.json, written by research/export.py.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[2]))
STATIC = ROOT / "dashboard" / "dist"
ALLOWED_ORIGINS = ["https://mdingi.co.za", "https://www.mdingi.co.za", "http://localhost:3000",
                   "http://localhost:4321", "http://localhost:5173"]
FRAME_ANCESTORS = "'self' https://mdingi.co.za https://www.mdingi.co.za http://localhost:*"

RESEARCH_BYTES = (ROOT / "data" / "research.json").read_bytes()
RESEARCH = json.loads(RESEARCH_BYTES)
SEXES = {s.lower(): s for s in RESEARCH["annuities"] if s in ("Male", "Female")}
PRICES = {(s, p["age"], round(p["rate"], 4), round(p["adj"], 4)): p
          for s in SEXES.values() for p in RESEARCH["annuities"][s]["prices"]}
AGES = sorted({k[1] for k in PRICES})
RATES = sorted({k[2] for k in PRICES})
ADJS = sorted({k[3] for k in PRICES})

app = FastAPI(title="Mdingi Life", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = f"frame-ancestors {FRAME_ANCESTORS}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "public, max-age=300"
    return response


@app.get("/healthz")
@app.get("/api/health")
def health():
    return {"ok": True, "protocol": RESEARCH["protocol"], "source": RESEARCH["source"]}


@app.get("/api/research")
def research():
    return Response(RESEARCH_BYTES, media_type="application/json")


def _pick(value: float, grid: list[float], name: str) -> float:
    for g in grid:
        if abs(value - g) < 1e-9:
            return g
    raise HTTPException(400, f"{name} must be one of {grid}")


@app.get("/api/price")
def price(sex: str, age: int, rate: float, adj: float):
    s = SEXES.get(sex.strip().lower())
    if s is None:
        raise HTTPException(400, f"sex must be one of {sorted(SEXES.values())}")
    if age not in AGES:
        raise HTTPException(400, f"age must be one of {AGES}")
    key = (s, age, _pick(rate, RATES, "rate"), _pick(adj, ADJS, "adj"))
    p = PRICES[key]
    chosen = RESEARCH["backtest"]["tests"]["chosen"][s]
    p3 = RESEARCH["backtest"]["tests"]["P3"][s]  # failed P3: the interval is a lower bound
    return {"sex": s, "age": age, "rate": key[2], "adj": key[3], "model": chosen,
            "jump_off": RESEARCH["annuities"][s]["jump_off"],
            "median": p["median"], "lo": p["lo"], "hi": p["hi"], "width_pct": p["width_pct"],
            "lower_bound": not p3}


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = (STATIC / path).resolve()
        ok = path and f.is_file() and f.is_relative_to(STATIC.resolve())
        return FileResponse(f if ok else STATIC / "index.html")
