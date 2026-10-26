"""v1.4's graduation and jump model, on simulated data only (research/PROTOCOL_v1.4.md, "Unit tests").

The simulation tests run 200 series each, in parallel. Their summaries are written to
research/results/v14_tests.json for the plan's pre-freeze record.
"""
from __future__ import annotations

import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pytest
from scipy.special import logsumexp
from scipy.stats import multivariate_normal

from mdingilife import graduation, jumps
from mdingilife.data import ROOT, Rates

SEED, SERIES = 20261031, 200
GAGES, AGES, YEARS = np.arange(45, 90), np.arange(50, 90), np.arange(1997, 2023)
# WPP-sized exposures for South African men: about 330,000 at 45, falling to about 5,000 at 89
SIZE = np.geomspace(3.3e5, 5e3, len(GAGES))[:, None]
DRIFT, VOL = -0.01, 0.02               # of K, in average log rate (K units are 40 times these)
BJ_RISING = np.linspace(0.5, 1.5, len(AGES))
OUT = ROOT / "research" / "results" / "v14_tests.json"
RESULTS: dict = {}


def truth():
    """Gompertz-plus-hump a(x) at the 2017 to 2019 base, and a b(x) that falls with age (sum 1 over 50 to 89)."""
    x = GAGES
    a = -5.2 + 0.075 * (x - 45) + 0.15 * np.exp(-((x - 55) / 6.0) ** 2)
    b = np.linspace(1.5, 0.5, len(x))
    return a, b / b[5:].sum()


def hiv_hump(years: np.ndarray, peak: float = 0.35) -> np.ndarray:
    """A raised cosine in average log rate: 0 in 1997, `peak` in 2006, 0 from 2016."""
    return np.where(years <= 2016, peak * (1 - np.cos(2 * np.pi * (years - 1997) / 19)) / 2, 0.0)


def simulate(i: int, jump: dict | None = None, rho: float = 0.0, hiv: float = 0.0, bJ=None,
             shift: dict | None = None, stream: int | None = None) -> Rates:
    """Series i: Poisson deaths at ages 45 to 89 for 1997 to 2022. `shift` raises the trend K permanently from each
    year given (in average log rate). `stream` gives seeds apart from the tests' (for calibration)."""
    rng = np.random.default_rng([SEED, i] if stream is None else [SEED, stream, i])
    a, b = truth()
    n, c = len(YEARS), 1 / b[5:].mean()
    K = np.cumsum(np.r_[0, c * (DRIFT + VOL * rng.standard_normal(n - 1))])
    K -= K[(YEARS >= 2017) & (YEARS <= 2019)].mean()
    for t, size in (shift or {}).items():
        K += c * size * (YEARS >= t)
    N, level = np.zeros(n), 0.0
    for j, t in enumerate(YEARS):
        level = rho * level + (jump or {}).get(int(t), 0.0)
        N[j] = level
    bj = b / b[5:].mean() if bJ is None else np.r_[np.full(5, bJ[0]), bJ]
    log_m = a[:, None] + np.outer(b, K) + np.outer(b / b[5:].mean(), hiv_hump(YEARS, hiv)) + np.outer(bj, N)
    E = SIZE * np.ones(n)
    return Rates("Male", GAGES, YEARS, rng.poisson(E * np.exp(log_m)).astype(float), E)


def pipeline(r: Rates, model: str = "J1", estimate: bool = True, cutoff: float | None = None):
    """Graduation, then steps 1 to 3 as for L5 (or with the jump prior fixed, as for L1 to L4)."""
    base = r.sub(years=range(2017, 2020))
    g = graduation.graduate(base.D.sum(1), base.E.sum(1))
    panel = r.sub(ages=AGES)
    f = jumps.fit(panel, g["log_m"][5:], 1 / 30, model, estimate, cutoff=cutoff)
    return f, jumps.separation(f, panel), g


SCENARIOS = {
    "j1_recovery": ({"jump": {2021: 0.3}, "bJ": BJ_RISING}, "J1", True),
    "decay_recovery": ({"jump": {2021: 0.3}, "rho": 0.5, "bJ": BJ_RISING}, "decay", True),
    "decay_on_j1_data": ({"jump": {2021: 0.3}, "bJ": BJ_RISING}, "decay", True),
    "plain": ({}, "J1", True),
    "hiv": ({"hiv": 0.35}, "J1", True),
    "plain_prior_fixed": ({}, "J1", False),
    "hiv_prior_fixed": ({"hiv": 0.35}, "J1", False),
    "covid_shaped": ({"jump": {2020: 0.10, 2021: 0.30, 2022: 0.08}}, "J1", True),
    "permanent_shift": ({"shift": {2020: 0.10, 2021: 0.20}}, "J1", True),
}


def one(args):
    name, i = args
    kw, model, estimate = SCENARIOS[name]
    f, s, g = pipeline(simulate(i, **kw), model, estimate)
    y = list(f.years)
    return {
        "flagged": f.flagged,
        "N": {t: float(f.N[y.index(t)]) for t in jumps.COVID},
        "bJ_corr": float(np.corrcoef(f.bJ, BJ_RISING)[0, 1]) if f.F else None,
        "rho": f.series.rho, "mu_y": f.series.mu_y, "sd_y": f.series.sd_y, "sd": f.series.sd,
        "cap": f.series.cap, "left_out": f.series.left_out, "lam": g["lam"],
        "separation": s["passes"], "absorbed_share": s["absorbed_share"], "pass_absorbed": s["pass_absorbed"],
        "pass_trend": s["pass_trend"],
    }


@lru_cache(maxsize=None)
def scenario(name: str) -> tuple:
    with ProcessPoolExecutor() as ex:
        return tuple(ex.map(one, [(name, i) for i in range(SERIES)], chunksize=4))


def record(name: str, **summary):
    RESULTS[name] = summary
    OUT.parent.mkdir(exist_ok=True)
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old.update(RESULTS)
    OUT.write_text(json.dumps(old, indent=1, default=float))


def share(runs, cond) -> float:
    return float(np.mean([bool(cond(r)) for r in runs]))


# Whittaker-Henderson -------------------------------------------------------------------------------------------

def pooled(seed=SEED):
    a, _ = truth()
    E = 3 * SIZE[:, 0]
    return a, np.random.default_rng(seed).poisson(E * np.exp(a)).astype(float), E


def test_graduation_recovers_a_known_curve():
    a, D, E = pooled()
    g = graduation.graduate(D, E)
    err = np.abs(g["log_m"] - a)[5:]
    record("graduation", lam=g["lam"], ed=g["ed"], max_error_50_89=float(err.max()))
    assert err.max() < 0.05


def test_very_large_lambda_gives_a_gompertz_line():
    _, D, E = pooled()
    eta = graduation.graduate(D, E, 1e12)["log_m"]
    assert np.abs(np.diff(eta, 2)).max() < 1e-4


def test_zero_lambda_returns_the_crude_rates():
    _, D, E = pooled()
    assert graduation.graduate(D, E, 0.0)["log_m"] == pytest.approx(np.log(D / E), abs=1e-8)


# The jump likelihood ------------------------------------------------------------------------------------------

N_TEST, C, SD, MU_Y, SD_Y, P = 10 - 1, 40.0, 0.8, 0.10, 0.05, 1 / 30


def brute(d, rho):
    """Every jump pattern, each a direct multivariate normal: (log likelihood, posterior probs, E[N])."""
    n = len(d)
    g = jumps._loadings(n, rho)
    lev = np.tril(rho ** np.clip(np.arange(n)[:, None] - np.arange(n)[None, :], 0, None))
    w, en, pats = [], [], []
    for I in itertools.product([0, 1], repeat=n):
        S = [i for i in range(n) if I[i]]
        G = g[S].T if S else np.zeros((n, 0))
        cov = SD ** 2 * np.eye(n) + (C * SD_Y) ** 2 * G @ G.T
        mean = C * MU_Y * G.sum(1)
        w.append(multivariate_normal.logpdf(d, mean, cov) + len(S) * np.log(P) + (n - len(S)) * np.log1p(-P))
        EY = MU_Y + C * SD_Y ** 2 * G.T @ np.linalg.solve(cov, d - mean)
        en.append(lev[:, S] @ EY if S else np.zeros(n))
        pats.append(I)
    w = np.array(w)
    post = np.exp(w - logsumexp(w))
    return logsumexp(w), post @ np.array(pats), post @ np.array(en)


def changes(seed=7):
    d = np.random.default_rng(seed).normal(0, SD, N_TEST)
    d[4] += C * 0.3
    d[5] -= C * 0.15
    return d


def test_j1_blocks_match_brute_force():
    d = changes()
    ll, prob, EN = jumps.j1_posterior(d, C, SD, MU_Y, SD_Y, P)
    bl, bp, be = brute(d, 0.0)
    assert ll == pytest.approx(bl, abs=1e-8)
    assert prob == pytest.approx(bp, abs=1e-8) and EN == pytest.approx(be, abs=1e-8)


@pytest.mark.parametrize("rho", [0.0, 0.5])
def test_decaying_sum_matches_brute_force_with_cap_at_series_length(rho):
    d = changes()
    ll, prob, EN = jumps.decay_posterior(d, C, SD, MU_Y, SD_Y, rho, P, cap=len(d))
    bl, bp, be = brute(d, rho)
    assert ll == pytest.approx(bl, abs=1e-8)
    assert prob == pytest.approx(bp, abs=1e-8) and EN == pytest.approx(be, abs=1e-8)


# Simulated series -------------------------------------------------------------------------------------------------

def test_j1_recovers_a_one_year_jump():
    runs = scenario("j1_recovery")
    flag = share(runs, lambda r: 2021 in r["flagged"])
    n21 = float(np.median([r["N"][2021] for r in runs]))
    corr = float(np.median([r["bJ_corr"] if r["bJ_corr"] is not None else np.nan for r in runs]))
    sep = share(runs, lambda r: r["separation"])
    record("j1_recovery", flagged_2021=flag, median_N2021=n21, median_bJ_corr=corr, separation_passes=sep,
           pass_absorbed=share(runs, lambda r: r["pass_absorbed"]), pass_trend=share(runs, lambda r: r["pass_trend"]),
           any_other_flag=share(runs, lambda r: set(r["flagged"]) - {2021}))
    assert flag >= 0.9
    assert abs(n21 - 0.3) <= 0.05
    assert corr >= 0.9
    assert sep >= 0.8


def test_decaying_variant_recovers_rho():
    runs = scenario("decay_recovery")
    rho = float(np.median([r["rho"] for r in runs]))
    record("decay_recovery", median_rho=rho, flagged_2021=share(runs, lambda r: 2021 in r["flagged"]),
           cap_6=share(runs, lambda r: r["cap"] == 6), max_left_out=max(r["left_out"] for r in runs))
    assert abs(rho - 0.5) <= 0.15


def test_decaying_variant_finds_no_decay_in_one_year_jumps():
    runs = scenario("decay_on_j1_data")
    rho = float(np.median([r["rho"] for r in runs]))
    record("decay_on_j1_data", median_rho=rho, max_left_out=max(r["left_out"] for r in runs))
    assert rho < 0.15


def _false(name):
    runs = scenario(name)
    any_flag = share(runs, lambda r: r["flagged"])
    counts = np.bincount([len(r["flagged"]) for r in runs]).tolist()
    years = np.bincount([t - 1997 for r in runs for t in r["flagged"]], minlength=len(YEARS)).tolist()
    record(name, any_flag=any_flag, flags_per_series=counts, flags_by_year=dict(zip(YEARS.tolist(), years)))
    return any_flag


def test_no_false_jumps_on_plain_data():
    assert _false("plain") <= 0.10


def test_no_false_jumps_on_an_hiv_like_hump():
    assert _false("hiv") <= 0.10


def test_reported_false_jumps_with_the_prior_fixed():
    """Reported only: the same no-jump data with the jump prior fixed, as at L1 to L4."""
    _false("plain_prior_fixed")
    _false("hiv_prior_fixed")


def _separation(name):
    runs = scenario(name)
    passes = share(runs, lambda r: r["separation"])
    record(name, **{f"flagged_{t}": share(runs, lambda r, t=t: t in r["flagged"]) for t in jumps.COVID},
           separation_passes=passes,
           pass_absorbed=share(runs, lambda r: r["pass_absorbed"]), pass_trend=share(runs, lambda r: r["pass_trend"]),
           median_absorbed_share=float(np.nanmedian([r["absorbed_share"] for r in runs])),
           median_N={t: float(np.median([r["N"][t] for r in runs])) for t in jumps.COVID})
    return passes


def test_separation_passes_covid_shaped_jumps():
    """The correct model, with jumps of 0.10, 0.30 and 0.08 in 2020 to 2022: the rule passes in at least 80%."""
    assert _separation("covid_shaped") >= 0.80


def test_reported_separation_on_a_permanent_shift():
    """Reported only: the same rise kept permanently in the trend (+0.10 in 2020, +0.30 from 2021). Data to 2022
    cannot tell this from jumps in 2021 and 2022, so there is no pass mark."""
    _separation("permanent_shift")
