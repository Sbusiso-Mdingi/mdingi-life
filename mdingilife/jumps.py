"""v1.4's trend with mortality jumps (research/PROTOCOL_v1.4.md, "The model" and "Estimation").

  log m(x,t) = a(x) + b(x) K(t) + bJ(x) N(t)

a(x) is a graduated base, held fixed; sum b = 1; mean bJ = 1, so N reads as the average rise in log rates.
K is a random walk with drift mu and volatility sd. I(t) ~ Bernoulli(p), Y(t) ~ Normal(mu_y, sd_y^2), and

  J1 (primary, Liu and Li's Model J1):   N(t) = I(t) Y(t)
  decaying variant (reported only):      N(t) = rho N(t-1) + I(t) Y(t)

Step 1 fits a free period index kappa with a(x) fixed. Step 2 fits the jump time series to the changes in
kappa, where a jump of size Y adds c * Y to kappa (c = 1 / mean b), and the first year is jump-free. Step 3
fits bJ on the flagged years in 2020 to 2022 and refits step 1 with the jump as an offset.
"""
from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from mdingilife.data import Rates

MAX_ITER, TOL = 20000, 1e-9
CUTOFF = 0.95                   # a year is flagged if its posterior jump probability is above this
ABSORBED = 0.45                 # the separation rule's absorbed-share threshold
BAND = 2.31                     # the 2022 trend test's band, in units of sd * sqrt(3)
COVID = (2020, 2021, 2022)
CAP, CAP_WIDE, LEFT_OUT = 4, 6, 0.01
PRIOR = {"mu_y": 0.10, "sd_y": 0.05, "rho": 0.5}
LOG2PI = np.log(2 * np.pi)


# Step 1 ------------------------------------------------------------------------------------------------------

def period_index(D: np.ndarray, E: np.ndarray, a: np.ndarray, offset: np.ndarray | None = None):
    """Poisson ML of log m = a(x) + offset + b(x) kappa(t), with a fixed and sum b = 1. Returns (b, kappa)."""
    off = a[:, None] + (0 if offset is None else offset)
    b = np.full(len(a), 1 / len(a))
    k = (np.log(np.maximum(D, 0.5) / E) - off).sum(0)
    prev = off + np.outer(b, k)
    for _ in range(MAX_ITER):
        Dh = E * np.exp(off + np.outer(b, k))
        k += ((D - Dh) * b[:, None]).sum(0) / (Dh * b[:, None] ** 2).sum(0)
        Dh = E * np.exp(off + np.outer(b, k))
        b += ((D - Dh) * k).sum(1) / (Dh * k ** 2).sum(1)
        s = b.sum()
        b, k = b / s, k * s
        eta = off + np.outer(b, k)
        if np.abs(eta - prev).max() < TOL:
            break
        prev = eta
    else:
        warnings.warn("period index did not converge")
    return b, k


# Step 2, J1: exact likelihood by blocks ------------------------------------------------------------------------

def _windows(x: np.ndarray, L: int) -> np.ndarray:
    return np.lib.stride_tricks.sliding_window_view(x, L) if L <= len(x) else np.empty((0, L))


def _block(L: int, m: int) -> np.ndarray:
    """L x m loading of m consecutive jump sizes on L consecutive changes in kappa: +1 in the jump's year, -1 the
    year after (if inside the block)."""
    Dm = np.zeros((L, m))
    for i in range(m):
        Dm[i, i] = 1
        if i + 1 < L:
            Dm[i + 1, i] = -1
    return Dm


def j1_blocks(d: np.ndarray, c: float, sd: float, mu_y: float, sd_y: float):
    """Every block's Gaussian log density and posterior mean jump sizes.

    d are the changes in kappa less the drift, d_1..d_n (I_0 = 0). A block (s, m, end) holds jumps in years
    s..s+m-1; if not `end`, year s+m is jump-free and the block covers d_s..d_{s+m}; if `end`, it runs to d_n.
    Yields (s, m, end, logL array over s, EY array over s x m). s is 1-indexed.
    """
    n = len(d)
    for m in range(0, n + 1):
        for end in (False, True):
            if end and m == 0:
                continue
            if end:
                L, starts = m, np.array([n - m + 1])
            else:
                L = m + 1
                if L > n:
                    continue
                starts = np.arange(1, n - m + 1)
            Dm = _block(L, m)
            S = sd ** 2 * np.eye(L) + (c * sd_y) ** 2 * Dm @ Dm.T
            Ch = np.linalg.cholesky(S)
            logdet = 2 * np.log(np.diag(Ch)).sum()
            W = _windows(d, L)[starts - 1] - c * mu_y * Dm.sum(1)
            Si_r = np.linalg.solve(S, W.T).T
            logL = -0.5 * (L * LOG2PI + logdet + (W * Si_r).sum(1))
            EY = mu_y + c * sd_y ** 2 * Si_r @ Dm
            yield starts, m, end, logL, EY


def j1_posterior(d: np.ndarray, c: float, sd: float, mu_y: float, sd_y: float, p: float):
    """Log likelihood of d, each year's posterior jump probability and posterior mean jump E[N] (years 1..n)."""
    n = len(d)
    lp, lq = np.log(p), np.log1p(-p)
    blocks = list(j1_blocks(d, c, sd, mu_y, sd_y))
    A = np.full(n + 1, -np.inf)
    A[0] = 0.0
    by_end: dict[int, list] = {}
    for starts, m, end, logL, EY in blocks:
        for i, s in enumerate(starts):
            k = n + 1 if end else s + m              # n + 1 marks "ends the series"
            by_end.setdefault(k, []).append((s, m, logL[i] + m * lp + (0 if end else lq), EY[i]))
    for k in range(1, n + 1):
        A[k] = logsumexp([A[s - 1] + w for s, m, w, _ in by_end.get(k, [])])
    total = logsumexp([A[n]] + [A[s - 1] + w for s, m, w, _ in by_end.get(n + 1, [])])
    B = np.full(n + 1, -np.inf)
    B[n] = 0.0
    by_start: dict[int, list] = {}
    for k, lst in by_end.items():
        for s, m, w, ey in lst:
            by_start.setdefault(s, []).append((k, m, w, ey))
    for j in range(n - 1, -1, -1):
        B[j] = logsumexp([w + (0.0 if k == n + 1 else B[k]) for k, m, w, _ in by_start.get(j + 1, [])])
    prob, EN = np.zeros(n), np.zeros(n)
    for s, lst in by_start.items():
        for k, m, w, ey in lst:
            if m == 0:
                continue
            post = np.exp(A[s - 1] + w + (0.0 if k == n + 1 else B[k]) - total)
            prob[s - 1:s - 1 + m] += post
            EN[s - 1:s - 1 + m] += post * ey
    return float(total), prob, EN


# Step 2, decaying variant: sum over jump sets of at most `cap` years ---------------------------------------------

def _loadings(n: int, rho: float) -> np.ndarray:
    """g[s, t]: the effect of a unit jump in year s on the change in kappa in year t (both 0-indexed here)."""
    t = np.arange(n)
    lag = t[None, :] - t[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(lag == 0, 1.0, np.where(lag > 0, rho ** np.maximum(lag - 1, 0) * (rho - 1), 0.0))
    return g


def decay_sizes(d, c, sd, mu_y, sd_y, rho, p, sizes, chunk=40000):
    """For each jump-set size k in `sizes`: (k, sets, log weight of each set incl. prior, E[N] per set)."""
    n = len(d)
    g = _loadings(n, rho)
    lev = np.tril(rho ** np.clip(np.arange(n)[:, None] - np.arange(n)[None, :], 0, None))  # N_t = sum lev[t,s] Y_s
    tau2 = (c * sd_y) ** 2
    for k in sizes:
        if k == 0:
            w = -0.5 * (n * LOG2PI + n * np.log(sd ** 2) + d @ d / sd ** 2) + n * np.log1p(-p)
            yield 0, np.empty((1, 0), int), np.array([w]), np.zeros((1, n))
            continue
        allsets = np.array(list(itertools.combinations(range(n), k)), int)
        for lo in range(0, len(allsets), chunk):
            sets = allsets[lo:lo + chunk]
            G = np.transpose(g[sets], (0, 2, 1))                     # (sets, n, k)
            r = d[None, :] - c * mu_y * G.sum(2)
            GtG = np.einsum("snk,snj->skj", G, G)
            M = sd ** 2 / tau2 * np.eye(k) + GtG
            Gtr = np.einsum("snk,sn->sk", G, r)
            v = np.linalg.solve(M, Gtr[..., None])[..., 0]
            quad = ((r * r).sum(1) - (Gtr * v).sum(1)) / sd ** 2
            logdet = n * np.log(sd ** 2) + k * np.log(tau2 / sd ** 2) + np.linalg.slogdet(M)[1]
            w = -0.5 * (n * LOG2PI + logdet + quad) + k * np.log(p) + (n - k) * np.log1p(-p)
            Si_r = (r - np.einsum("snk,sk->sn", G, v)) / sd ** 2
            EY = mu_y + c * sd_y ** 2 * np.einsum("snk,sn->sk", G, Si_r)
            EN = np.einsum("stk,sk->st", np.transpose(lev[:, sets], (1, 0, 2)), EY)
            yield k, sets, w, EN


def decay_posterior(d, c, sd, mu_y, sd_y, rho, p, cap=CAP):
    """Log likelihood (summed over sets of at most `cap` jumps), posterior jump probabilities and E[N]."""
    n = len(d)
    parts = list(decay_sizes(d, c, sd, mu_y, sd_y, rho, p, range(min(cap, n) + 1)))
    total = logsumexp(np.concatenate([w for _, _, w, _ in parts]))
    prob, EN = np.zeros(n), np.zeros(n)
    for k, sets, w, en in parts:
        post = np.exp(w - total)
        EN += post @ en
        for j in range(k):
            np.add.at(prob, sets[:, j], post)
    return float(total), prob, EN


def decay_left_out(d, c, sd, mu_y, sd_y, rho, p, cap=CAP) -> float:
    """The share of posterior probability outside the cap, estimated as the mass on sets of cap + 1 jumps out of
    all sets of at most cap + 1."""
    if cap >= len(d):
        return 0.0
    w = {}
    for k, _, ww, _ in decay_sizes(d, c, sd, mu_y, sd_y, rho, p, range(cap + 2)):
        w.setdefault(k > cap, []).append(ww)
    inside, outside = (logsumexp(np.concatenate(w[key])) for key in (False, True))
    return float(np.exp(outside - np.logaddexp(inside, outside)))


# Step 2: estimation ----------------------------------------------------------------------------------------

@dataclass
class Series:
    """Step 2's fit to the period index. prob and EN run over every fitted year (the first is 0 by assumption)."""
    model: str
    p: float
    mu: float
    sd: float
    mu_y: float
    sd_y: float
    rho: float
    estimated: tuple
    loglik: float
    prob: np.ndarray
    EN: np.ndarray
    cap: int | None = None
    left_out: float | None = None


def _posterior(model, d, c, sd, mu_y, sd_y, rho, p, cap):
    if model == "J1":
        return j1_posterior(d, c, sd, mu_y, sd_y, p)
    return decay_posterior(d, c, sd, mu_y, sd_y, rho, p, cap)


def fit_series(kappa: np.ndarray, c: float, p: float, model: str = "J1", jump: bool = False,
               fixed: dict = PRIOR, cap: int = CAP) -> Series:
    """Maximum likelihood of the jump time series on the changes in kappa. mu and sd are always estimated; with
    `jump`, so are mu_y and sd_y (and rho for the decaying variant). Otherwise they are held at `fixed`."""
    dk = np.diff(kappa)
    names = ["mu", "sd"] + (["mu_y", "sd_y"] + (["rho"] if model == "decay" else []) if jump else [])
    base = {"mu_y": fixed["mu_y"], "sd_y": fixed["sd_y"], "rho": 0.0 if model == "J1" else fixed["rho"]}
    bounds = {"mu": (None, None), "sd": (1e-4, None), "mu_y": (None, None), "sd_y": (1e-4, None),
              "rho": (0.0, 0.99)}

    def unpack(x):
        v = dict(base, **dict(zip(names, x)))
        return v["mu"], v["sd"], v["mu_y"], v["sd_y"], v["rho"]

    def nll(x, cap_):
        mu, sd, mu_y, sd_y, rho = unpack(x)
        return -_posterior(model, dk - mu, c, sd, mu_y, sd_y, rho, p, cap_)[0]

    med = float(np.median(dk))
    mad = max(1.4826 * float(np.median(np.abs(dk - med))), 1e-3)
    starts = []
    for my in ({fixed["mu_y"], max(float((dk - med).max()) / c, fixed["mu_y"])} if jump else {None}):
        x0 = {"mu": med, "sd": mad, "mu_y": my, "sd_y": fixed["sd_y"], "rho": fixed["rho"]}
        starts.append([x0[k] for k in names])

    def run(cap_):
        best = None
        for x0 in starts:
            res = minimize(nll, x0, args=(cap_,), method="L-BFGS-B", bounds=[bounds[k] for k in names])
            if best is None or res.fun < best.fun:
                best = res
        return best

    use = cap if model == "decay" else None
    res = run(use)
    left = None
    if model == "decay":
        left = decay_left_out(dk - unpack(res.x)[0], c, *unpack(res.x)[1:], p, cap)
        if left > LEFT_OUT and cap < CAP_WIDE:
            use = CAP_WIDE
            res = run(use)
            left = decay_left_out(dk - unpack(res.x)[0], c, *unpack(res.x)[1:], p, use)
    mu, sd, mu_y, sd_y, rho = unpack(res.x)
    ll, prob, EN = _posterior(model, dk - mu, c, sd, mu_y, sd_y, rho, p, use)
    return Series(model, p, mu, sd, mu_y, sd_y, rho, tuple(names), ll,
                  np.concatenate([[0.0], prob]), np.concatenate([[0.0], EN]), use, left)


# Step 3 and the whole fit ------------------------------------------------------------------------------------

def age_pattern(D: np.ndarray, E: np.ndarray, base: np.ndarray, bJ: np.ndarray):
    """Poisson ML of log m = base + bJ(x) N(t) on the given years, with mean bJ = 1. Returns (bJ, N)."""
    bJ = bJ / bJ.mean()
    N = (np.log(np.maximum(D, 0.5) / E) - base).mean(0)
    prev = base + np.outer(bJ, N)
    for _ in range(MAX_ITER):
        Dh = E * np.exp(base + np.outer(bJ, N))
        N += ((D - Dh) * bJ[:, None]).sum(0) / (Dh * bJ[:, None] ** 2).sum(0)
        Dh = E * np.exp(base + np.outer(bJ, N))
        bJ = bJ + ((D - Dh) * N).sum(1) / (Dh * N ** 2).sum(1)
        s = bJ.mean()
        bJ, N = bJ / s, N * s
        eta = base + np.outer(bJ, N)
        if np.abs(eta - prev).max() < TOL:
            break
        prev = eta
    else:
        warnings.warn("jump age pattern did not converge")
    return bJ, N


@dataclass
class JumpFit:
    model: str
    years: np.ndarray
    a: np.ndarray
    b: np.ndarray
    kappa: np.ndarray            # the final step 1 index (with the jump offset in F)
    K: np.ndarray                # the jump-free trend, K hat
    N: np.ndarray                # N hat: step 3's fit in F, step 2's posterior mean elsewhere
    bJ: np.ndarray               # the jump age pattern (b / mean b if F is empty)
    F: list
    flagged: list
    series: Series
    extra: dict = field(default_factory=dict)

    def loading(self) -> np.ndarray:
        """Each year's age pattern of N: bJ in F, b / mean b elsewhere (ages x years)."""
        L = np.repeat((self.b / self.b.mean())[:, None], len(self.years), 1)
        for t in self.F:
            L[:, self.years == t] = self.bJ[:, None]
        return L

    def log_m(self, jump: bool = True) -> np.ndarray:
        trend = self.a[:, None] + np.outer(self.b, self.K)
        return trend + self.loading() * self.N if jump else trend


def fit(r: Rates, a: np.ndarray, p: float, model: str = "J1", jump: bool = False, fixed: dict = PRIOR,
        cap: int = CAP, cutoff: float | None = None) -> JumpFit:
    """Steps 1 to 3 on one panel (ages 50 to 89, every year of the link's window), with a(x) the graduated base."""
    D, E, years = r.D, r.E, r.years
    b, kappa = period_index(D, E, a)
    c = 1 / b.mean()
    s = fit_series(kappa, c, p, model, jump, fixed, cap)
    flagged = [int(t) for t in years[s.prob > (CUTOFF if cutoff is None else cutoff)]]
    step2 = {"b": b, "kappa": kappa}
    F = [t for t in flagged if t in COVID]
    if model == "decay" and F:
        F = [t for t in COVID if min(F) <= t <= max(years)]
    F = [t for t in F if t in years]
    K, N, bJ = kappa - c * s.EN, s.EN.copy(), b / b.mean()
    if F:
        cols = np.isin(years, F)
        bJ, NF = age_pattern(D[:, cols], E[:, cols], a[:, None] + np.outer(b, K[cols]), b.copy())
        offset = np.zeros_like(D)
        offset[:, cols] = np.outer(bJ, NF)
        b, kappa = period_index(D, E, a, offset)
        c = 1 / b.mean()
        K = kappa - c * s.EN
        K[cols] = kappa[cols]
        N[cols] = NF
    return JumpFit(model, years, a, b, kappa, K, N, bJ, F, flagged, s, step2)


def separation(f: JumpFit, r: Rates, last_trend: int = 2019, threshold: float | None = None,
               band_z: float | None = None) -> dict:
    """The Covid separation rule on a fit whose window includes 2020 to 2022.

    The absorbed share uses step 2 only: the posterior mean jump effect, with no flags. On step 1's index kappa,
    the jump-free trend is K0 = kappa - c E[N], the trend line runs on from K0(last_trend) at the drift, and the
    jump term adds the deaths between a + b kappa and a + b K0. The trend test uses the final K hat in 2022.
    """
    y = list(f.years)
    i0 = y.index(last_trend)
    cols = np.isin(f.years, COVID)
    b0, k0 = f.extra["b"], f.extra["kappa"]
    K0 = k0 - f.series.EN / b0.mean()
    T = K0[i0] + f.series.mu * (f.years[cols] - last_trend)
    E, D = r.E[:, cols], r.D[:, cols]
    trend_d = E * np.exp(f.a[:, None] + np.outer(b0, T))
    with_j = E * np.exp(f.a[:, None] + np.outer(b0, k0[cols]))
    without = E * np.exp(f.a[:, None] + np.outer(b0, K0[cols]))
    excess, added = (D - trend_d).sum(0), (with_j - without).sum(0)
    share = float(added.sum() / excess.sum()) if excess.sum() > 0 else float("nan")
    T22 = f.K[i0] + f.series.mu * (2022 - last_trend)
    dev = float(f.K[y.index(2022)] - T22)
    band = float((BAND if band_z is None else band_z) * f.series.sd * np.sqrt(3))
    out = {
        "absorbed_share": share,
        "flagged_covid": [t for t in f.flagged if t in COVID],
        "pass_absorbed": bool(share >= (ABSORBED if threshold is None else threshold)),
        "K2022_minus_trend": dev,
        "band": band,
        "pass_trend": bool(abs(dev) <= band),
        "years": {int(yy): {"posterior": float(f.series.prob[y.index(yy)]), "N": float(f.N[y.index(yy)]),
                            "EN": float(f.series.EN[y.index(yy)]),
                            "absorbed_share": float(added[j] / excess[j]) if excess[j] > 0 else float("nan"),
                            "K_minus_trend": float(f.K[y.index(yy)] - (f.K[i0] + f.series.mu * (yy - last_trend)))}
                  for j, yy in enumerate(f.years[cols])},
    }
    out["passes"] = out["pass_absorbed"] and out["pass_trend"]
    if f.model == "decay":
        out["N2030"] = float(f.series.rho ** (2030 - 2022) * f.N[y.index(2022)])
    return out
