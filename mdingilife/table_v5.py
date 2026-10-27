"""v5's funeral mortality table (research/PROTOCOL_v5.md, "The mortality table"): a graduated 2024 level, changed by
a Poisson Lee-Carter by cause group with a shared cohort term, a Kannisto tail tied at 80.5, and each age's 2050 pace
carried on after 2050.

Arrays are ages x years unless stated. Every step is deterministic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# HIV-related causes: Groenewald et al. (AIDS 2005; 19:193-201) Tables 1 and 2, then D84, E86 and J09
HIV_CODES = """B20-B24 C46 | A15-A19 B90 J90 | J09-J18 J20-J22 | A00-A04 A06-A09 | A39 G00-G03 |
J30-J39 J47 J60-J68 J70 J80 J82-J84 J92-J98 | K50-K52 |
A05 A20-A28 A31 A32 A38 A42-A49 A65-A69 A70-A74 A75-A79 A81-A89 A90-A99 B00-B02 B04 B07-B09 B25-B34 B35-B37 B38-B45
B46-B49 B57-B64 B66-B73 B75 B82-B89 B94-B99 | D50-D53 D64 | E40-E46 | D84 E86"""
GROUPS = ("hiv", "ext", "other")

FIT_TOP, TOP, SLOPE = 80, 120, 20            # graduation and table: fitted to 80, Kannisto to 120, slope over 61-80
WH_FROM, CHILD = 2, 14                        # ages 0 and 1 crude; childhood smoothing level up to 14
WH_GRID = 10.0 ** np.arange(-2, 6.01, 0.25)

LC_TOP, START, LAST, END = 85, 2012, 2024, 2050
LEFT_OUT = (2020, 2021)
FREE = 2                                      # a and b unpenalised below this age
LC_GRID = 10.0 ** np.arange(-1, 10.01, 0.5)
OLD, NO_DRIFT = 75, ("ext",)                  # other: b floored at 0 from OLD; external projected without drift
COHORT_FROM, MIN_CELLS = 50, 3
ROUNDS, TOL = 500, 1e-9

PHI_CENTRES, PHI_HALF, PHI_SKIP = range(2010, 2018), 2, (2020, 2021, 2023)

logit = lambda m: np.log(m / (1 - m))
kannisto = lambda eta: eta - np.log1p(np.exp(eta))       # log m from the logit


# ---- causes ----------------------------------------------------------------------------------------------------

def hiv_related(code: pd.Series) -> pd.Series:
    """True where the underlying cause's first three characters fall in HIV_CODES."""
    letter, num = code.str[0], pd.to_numeric(code.str[1:3], errors="coerce")
    hit = pd.Series(False, index=code.index)
    for r in HIV_CODES.replace("|", " ").split():
        lo, hi = (r.split("-") + [r])[:2]
        hit |= (letter == lo[0]) & num.between(int(lo[1:]), int(hi[1:]))
    return hit


def kind(code: pd.Series) -> np.ndarray:
    """ill (R00-R99), hiv, ext (V01-Y98) or other."""
    return np.where(code.str[0] == "R", "ill", np.where(hiv_related(code), "hiv",
                    np.where(code.str[0].isin(list("VWXY")), "ext", "other")))


def shares(tally: pd.DataFrame) -> pd.DataFrame:
    """Each group's share of a cell's deaths (year, sex, age), ill-defined shared out pro rata. tally: year, sex, age,
    code, deaths."""
    c = tally.assign(kind=kind(tally["code"])).groupby(["year", "sex", "age", "kind"])["deaths"].sum()
    c = c.unstack(fill_value=0)
    known = c["hiv"] + c["ext"] + c["other"]
    return pd.DataFrame({"hiv": c["hiv"] / known, "ext": c["ext"] / known})


# ---- overdispersion and the 2024 graduation ---------------------------------------------------------------------

def _poisson_line(t, D, E):
    X = np.column_stack([np.ones_like(t), t])
    b = np.array([np.log(D.sum() / E.sum()), 0.0])
    for _ in range(50):
        mu = E * np.exp(X @ b)
        b = b + np.linalg.solve(X.T @ (mu[:, None] * X), X.T @ (D - mu))
    return E * np.exp(X @ b)


def overdispersion(ages, years, D, E) -> float:
    """phi: Pearson chi-squared over degrees of freedom of Poisson straight lines in time, at each age 1 to 80, over
    five-year windows centred on 2010 to 2017 (2020, 2021 and 2023 left out), pooled."""
    years, ages = np.asarray(years), list(ages)
    chi2 = df = 0.0
    for c in PHI_CENTRES:
        w = [i for i, t in enumerate(years) if abs(t - c) <= PHI_HALF and t not in PHI_SKIP]
        for a in range(1, FIT_TOP + 1):
            d, e = D[ages.index(a), w], E[ages.index(a), w]
            mu = _poisson_line((years[w] - c).astype(float), d, e)
            chi2 += np.sum((d - mu) ** 2 / mu)
            df += len(w) - 2
    return chi2 / df


def whittaker_ubre(y, D, x, phi):
    """Whittaker-Henderson on y = log m, weights D, second differences: one level for differences centred at ages
    up to CHILD and one above, chosen together by UBRE, sum D (y - z)^2 / phi + 2 trace. Returns z, levels, trace."""
    n = len(y)
    Dm = np.diff(np.eye(n), 2, axis=0)
    child = x[1:-1] <= CHILD
    W = np.diag(D)
    best = None
    for la in WH_GRID:
        for lc in WH_GRID:
            H = np.linalg.solve(W + Dm.T @ np.diag(np.where(child, lc, la)) @ Dm, W)
            z, tr = H @ y, np.trace(H)
            ubre = np.sum(D * (y - z) ** 2) / phi + 2 * tr
            if best is None or ubre < best[0]:
                best = (ubre, z, (lc, la), tr)
    return best[1:]


def tail(log_m, slope):
    """log m at 0 to FIT_TOP as given; Kannisto from FIT_TOP + 1 to TOP, meeting it at FIT_TOP + 0.5 in value and
    slope: d = slope / (1 - m)."""
    lh = log_m[FIT_TOP] + 0.5 * slope
    d = slope / (1 - np.exp(lh))
    xo = np.arange(FIT_TOP + 1, TOP + 1)
    return np.r_[log_m[:FIT_TOP + 1], kannisto(logit(np.exp(lh)) + d * (xo - (FIT_TOP + 0.5)))]


def tail_slope(log_m):
    x = np.arange(FIT_TOP - SLOPE + 1, FIT_TOP + 1)
    return np.polyfit(x, log_m[x], 1)[0]


def graduate(D, E, phi) -> dict:
    """One year's table, ages 0 to TOP, from deaths and exposures at ages 0 to 99: 0 and 1 crude, Whittaker-Henderson
    on 2 to 80, Kannisto tied above. Crude rates above 80 are not used."""
    x = np.arange(len(D), dtype=float)
    lg = np.log(D / E)
    s = (x >= WH_FROM) & (x <= FIT_TOP)
    z, lam, tr = whittaker_ubre(lg[s], D[s], x[s], phi)
    lg = np.r_[lg[:WH_FROM], z]
    slope = tail_slope(lg)
    return {"m": np.exp(tail(lg, slope)), "lam": lam, "trace": tr, "slope": slope}


# ---- Lee-Carter by cause ---------------------------------------------------------------------------------------

def poisson_lc(D, E, lam=(0.0, 0.0), start=None, tol=1e-10, it=5000):
    """Poisson Lee-Carter, a and b penalised by lam times their squared second differences from age FREE. Returns
    a, b, k (b sums to 1, k to 0), the deviance, the effective parameters and the fitted deaths."""
    if start is None:
        L = np.log(D / E)
        a = L.mean(axis=1)
        U, S, Vt = np.linalg.svd(L - a[:, None], full_matrices=False)
        b, k = U[:, 0] / U[:, 0].sum(), S[0] * Vt[0] * U[:, 0].sum()
    else:
        a, b, k = (v.copy() for v in start)
    n = len(a)
    Dm = np.diff(np.eye(n), 2, axis=0)[FREE - 1:]
    Pen = Dm.T @ Dm
    dev = lambda Dh: 2 * np.sum(D * np.log(D / Dh) - (D - Dh))
    fitted = lambda: E * np.exp(a[:, None] + np.outer(b, k))
    old = np.inf
    for _ in range(it):
        Dh = fitted()
        w = Dh.sum(axis=1)
        a = np.linalg.solve(np.diag(w) + lam[0] * Pen, w * a + (D - Dh).sum(axis=1))
        Dh = fitted()
        k = k + ((D - Dh) * b[:, None]).sum(axis=0) / (Dh * b[:, None] ** 2).sum(axis=0)
        Dh = fitted()
        w = (Dh * k ** 2).sum(axis=1)
        b = np.linalg.solve(np.diag(w) + lam[1] * Pen, w * b + ((D - Dh) * k).sum(axis=1))
        a, k = a + b * k.mean(), k - k.mean()
        b, k = b / b.sum(), k * b.sum()
        new = dev(fitted()) + lam[0] * a @ Pen @ a + lam[1] * b @ Pen @ b
        if old - new < tol * new:
            break
        old = new
    Dh = fitted()
    wa, wb = Dh.sum(axis=1), (Dh * k ** 2).sum(axis=1)
    ed = (np.trace(np.linalg.solve(np.diag(wa) + lam[0] * Pen, np.diag(wa)))
          + np.trace(np.linalg.solve(np.diag(wb) + lam[1] * Pen, np.diag(wb))) + len(k) - 2)
    return a, b, k, dev(Dh), ed, Dh


def smoothing_levels(D, E):
    """lam for a and b on LC_GRID by UBRE, deviance / phi + 2 ED, phi the Pearson overdispersion of the
    unpenalised fit. Returns (a, b, k) at the chosen levels, and the levels."""
    a0, b0, k0, _, ed0, Dh0 = poisson_lc(D, E)
    phi = np.sum((D - Dh0) ** 2 / Dh0) / (D.size - ed0)
    best = None
    for la in LC_GRID:
        for lb in LC_GRID:
            a, b, k, dv, ed, _ = poisson_lc(D, E, (la, lb), (a0, b0, k0))
            u = dv / phi + 2 * ed
            if best is None or u < best[0]:
                best = (u, (a, b, k), (la, lb))
    return best[1], best[2]


def cohort_index(ages, years):
    """Cohort of each cell at ages COHORT_FROM and over, among cohorts seen at least MIN_CELLS times (-1 elsewhere)."""
    born = years[None, :] - ages[:, None]
    seen = pd.Series(born[ages >= COHORT_FROM].ravel()).value_counts()
    cohorts = np.sort(seen.index[seen >= MIN_CELLS].to_numpy())
    C = np.where((ages[:, None] >= COHORT_FROM) & np.isin(born, cohorts), np.searchsorted(cohorts, born), -1)
    return cohorts, C


def fit_cause_lc(Ds: dict, E, ages, years) -> dict:
    """The three groups' Lee-Carter with the shared cohort term c, fitted in turn: each group with c as an offset,
    then c by a Newton step on all groups' deaths (sums to 0, no linear trend). Smoothing levels are chosen once,
    given the c of the unsmoothed joint fit."""
    cohorts, C = cohort_index(ages, years)
    yb = np.arange(len(cohorts)) - (len(cohorts) - 1) / 2
    u = C >= 0
    c = np.zeros(len(cohorts))
    offset = lambda c: np.exp(np.where(u, c[np.clip(C, 0, None)], 0.0))

    def joint(c, lams, starts):
        D = sum(Ds.values())
        for _ in range(ROUNDS):
            off = offset(c)
            res = {g: poisson_lc(Ds[g], E * off, lams[g], starts[g]) for g in GROUPS}
            Dh = sum(r[5] for r in res.values())
            new = c + np.bincount(C[u], (D - Dh)[u], len(cohorts)) / np.bincount(C[u], Dh[u], len(cohorts))
            new = new - new.mean() - yb * (yb @ new) / (yb @ yb)
            starts = {g: res[g][:3] for g in GROUPS}
            done = np.max(np.abs(new - c)) < TOL
            c = new
            if done:
                break
        return c, res

    c, _ = joint(c, {g: (0.0, 0.0) for g in GROUPS}, {g: None for g in GROUPS})
    picked = {g: smoothing_levels(Ds[g], E * offset(c)) for g in GROUPS}
    c, res = joint(c, {g: picked[g][1] for g in GROUPS}, {g: picked[g][0] for g in GROUPS})
    return {"groups": {g: dict(zip(("a", "b", "k"), res[g][:3]), lam=picked[g][1]) for g in GROUPS},
            "cohorts": cohorts, "c": c, "C": C}


def project(fit: dict, ages, years) -> np.ndarray:
    """Total m (years LAST to END x ages): each k a random walk with drift (k(LAST) - k(START)) / span from the
    fitted LAST, external without drift, other's b floored at 0 from OLD, c of each age's LAST cohort held."""
    C, c = fit["C"], fit["c"]
    c_last = np.where(C[:, -1] >= 0, c[np.clip(C[:, -1], 0, None)], 0.0)
    h = np.arange(END - LAST + 1)
    span = years[-1] - years[0]
    m = 0.0
    for g in GROUPS:
        a, b, k = (fit["groups"][g][q] for q in ("a", "b", "k"))
        drift = 0.0 if g in NO_DRIFT else (k[-1] - k[0]) / span
        bp = np.where(ages >= OLD, np.maximum(b, 0), b) if g == "other" else b
        m = m + np.exp(a + b * k[-1] + c_last + np.outer(drift * h, bp))
    return m


def table(base_m, lc_m) -> np.ndarray:
    """Years LAST to END x ages 0 to TOP: base_m (graduated LAST, ages 0 to TOP) times the change in lc_m (ages 0 to
    LC_TOP) from LAST, to FIT_TOP; Kannisto above, tied each year at the held LAST slope."""
    slope = tail_slope(np.log(base_m))
    ratio = lc_m[:, :FIT_TOP + 1] / lc_m[:1, :FIT_TOP + 1]
    return np.exp(np.array([tail(np.log(base_m[:FIT_TOP + 1] * r), slope) for r in ratio]))


def extend(m, years, to: int) -> tuple[np.ndarray, np.ndarray]:
    """Rows of m (years x ages) after its last year to `to`, each age's last-year pace carried on:
    ln m(x, T + n) = ln m(x, T) + n [ln m(x, T) - ln m(x, T - 1)]."""
    years = np.asarray(years)
    pace = np.log(m[-1]) - np.log(m[-2])
    n = np.arange(1, to - years[-1] + 1)
    later = np.exp(np.log(m[-1])[None, :] + n[:, None] * pace[None, :])
    return np.r_[years, years[-1] + n], np.vstack([m, later])
