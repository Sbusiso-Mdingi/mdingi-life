# Protocol: v1.3 Liabilities, a smoothed cohort term

Written on 26 October 2026, after v1.2 was run and reported (`RESULTS_v1.2.md`), and before any v1.3 code was written or run. A revision made in response to v1.2's results. v1, v1.1 and v1.2 stay as reported. **This is the last mortality iteration.** Whatever it shows is published, and the mortality model is then final.

Amended on 26 October 2026, after review and before any v1.3 code was written: the heaping check ("Seen beforehand"), the smoother's ends and convergence checks, the simulated recovery test, and an upper bound on Q2.

Frozen at commit: (not yet frozen)

## Seen beforehand, and disclosed

- Everything in `RESULTS_v1.2.md`.
- After v1.2, the cohort effects γ of v1.2's two production fits (RH post-peak for men, RH full for women) were read off, and the move in e65 from 2019 to 2020 was split by age. No other model or rule was fitted. Almost all of the 2020 jump (0.15 of 0.17 years for men, 0.16 of 0.25 for women) comes from age 89, where the 1931 cohort replaces the 1930 cohort. γ spikes at round birth years: for men, 1929 −0.10, **1930 +0.01**, 1931 −0.16, and 1940 +0.20 against +0.08 and +0.10 either side; for women, 1929 −0.01, **1930 +0.14**, 1931 −0.11, and 1940 +0.06 against −0.13 and −0.08. These cohorts are seen in 14 to 23 cells each, so they are not sparse.
- *Added 26 October 2026, after review and before any v1.3 code.* **A heaping check on the unit records**, `research/heaping.py`, output `research/results/heaping.json`. Individual deaths at ages 50 to 89. Each cell's deaths are divided by the mean of the centred five cells around it (1.00 means no heaping), and averaged by last digit. In 1997 to 2020 the files hold no date of birth, so birth year is year of death minus age; death years ending in 0 or 5 are left out of the birth-year index, where round ages and round birth years coincide. The 2021 to 2023 file records the date of birth. Results:

  | | Men | Women |
  | --- | --- | --- |
  | Ages ending in 0, 1997 to 2019 (ages ending in 5) | 1.00 (1.00) | 1.00 (1.00) |
  | Birth years ending in 0, 1997 to 2019 (other digits) | **1.10** (0.97 to 1.02) | **1.14** (0.92 to 1.02) |
  | Born 1930, 1940, 1950 | 1.15, 1.10, 1.05 | 1.22, 1.18, 1.07 |
  | Born 1925, 1935, 1945 | 1.06, 0.94, 0.96 | 1.08, 0.96, 0.97 |
  | Recorded birth year 1940, 1950, 2021 to 2023 | 1.17, 1.06 | 1.26, 1.10 |
  | Dates of birth on 1 January, 2021 to 2023 (chance: 0.27%) | 1.9% | 1.8% |
  | of which, birth years ending in 0 (others) | 2.6% (1.6% to 2.0%) | 2.2% (1.7% to 1.9%) |

  **Heaping is confirmed, at birth years ending in 0 only.** Ages are not heaped, and neither are birth years ending in 5. The 1 January excess, largest for round years, points to unknown dates of birth filled in as round dates. Exposure (WPP) is smooth, so the excess goes straight into the death rates. Its size matches the γ spikes: log 1.15 = 0.14 against men's 1930 γ, about 0.14 above its neighbours; log 1.22 = 0.20 against women's 1930, about 0.20; log 1.10 = 0.09 against men's 1940, about 0.11; log 1.18 = 0.16 against women's 1940, about 0.16. Neighbours' ratios read 2% to 8% low, because their five-year means include the heaped year.
- v1.2's results said the jump came from the oldest, sparsely observed cohorts. That was wrong, and a dated correction is added there.

## Hold-out reuse

The 2017 to 2019 validation period has now guided three versions (v1.1, v1.2 and this one), and v1.2's windows were chosen after v1.1's design scores had been seen. It is no longer a clean test. So v1.3 adds a second backtest origin (below), and a version passes only if it passes at both.

## The one change: the cohort term is smoothed over birth years

In the Renshaw-Haberman fit, after each update of γ and its re-centring, γ over the estimated cohorts is replaced by its **centred five-year moving average over birth years**, then re-centred to sum to zero. The fit iterates to convergence with this step inside it. So γ is the fixed point of "update, then smooth": a cohort effect that is smooth on a five-year scale.

**The parameter: a span of 5 birth years, equal weights.** A spike at a round year is shared with four neighbours that are not heaped, which cuts it to a fifth. The check above found heaping only at years ending in 0, so a span of 3 would also contain one heaped year; five is kept, as approved, because it also damps the year-to-year noise in γ that RH's low φ points to, and is still narrow enough to keep real differences between cohorts a decade apart (the HIV-era cohorts). It is fixed now and not varied.

**The ends, stated exactly.** The estimated cohorts are a contiguous run of birth years c₁ to c_K (each seen in at least three cells; the two oldest and two youngest birth years in each window are not estimated and stay at 0, as now). The smoothed γ(c_j) is the equal-weight mean of γ over the estimated cohorts within two years of c_j. The window is cut, not padded or reflected:

| Cohort | Averaged over | Cohorts |
| --- | --- | --- |
| c₁ (oldest) | c₁ to c₃ | 3 |
| c₂ | c₁ to c₄ | 4 |
| c₃ to c_K−2 | c_j−2 to c_j+2 | 5 |
| c_K−1 | c_K−3 to c_K | 4 |
| c_K (youngest) | c_K−2 to c_K | 3 |

So the end values are one-sided and lean toward the interior. At the young end this matters: c_K is the cohort γ's forecast starts from, and its smoothed value is the mean of the last three. Cohorts that are not estimated never enter an average.

**Convergence, checked for every fit.** The stopping rule stays v1.2's (the largest change in fitted log rates under 10⁻⁹, at most 20,000 iterations). With smoothing inside, the iteration may converge more slowly or cycle, so for every fit the run records whether it converged, the number of iterations and the final change. Two further checks on each production and backtest fit (not the refits): started again from γ = 0 and from v1.2's unsmoothed γ, smoothed, the two fitted log rates agree to within 10⁻⁶; and the smoothed fit's deviance is not below the unsmoothed fit's (a restriction cannot fit better). **Decided now:** if any production or backtest fit fails to converge, or fails either check, v1.3 fails for that sex. Refits that do not converge are kept, counted and reported; if more than 5% of a sex's refits do not converge, v1.3 fails for that sex.

**Dispersion.** φ keeps v1.1's parameter count for RH (one per estimated cohort, less one), though smoothing leaves fewer free. That overstates the parameters a little and so slightly raises φ. Fixed now.

Unchanged: the minimum of three cells for a cohort to be estimated, the ARIMA(1,1,0) for γ's forecast (now fitted to the smoothed γ), the unit cohort loading, and everything else in v1.1 and v1.2.

**A risk, stated now.** Smoothing makes successive changes in γ move together, so the ARIMA's AR coefficient will rise. Future cohorts' effects (those born after the last estimated cohort) then carry recent trends further. This matters most for the price at 55. It is reported, not tuned.

**Why not a minimum cell count, or a fix to the data.** The cohorts behind the jump are each seen in 14 or more cells, so raising the minimum from 3 would not touch them. Redistributing the heaped deaths in the data would be a second change, and the plan allows one.

## Windows

As v1.2, for each sex: post-peak (2006) for LC, CBD and RH for men; post-peak for LC and CBD and full (1997) for RH for women. Not re-chosen.

## Two backtest origins

- **Origin A**: fit to 2016, score 2017 to 2019 (v1's validation period).
- **Origin B**: fit to 2013, score 2014 to 2016. Each sex's v1.2 windows, so men's fits use 2006 to 2013 (eight years) and women's RH 1997 to 2013. Origin B's scored years lie inside the design period (2013 to 2016), on which the windows and weights were chosen. So it is a second check of stability, not an independent hold-out. No earlier origin works: the post-peak window would have too few years.
- **Weights** are set on the design period, as in v1.1, with the smoothed cohort term. They are the same at both origins.

## Tests and how the origins combine

Q1 (beats B0 on deviance) and Q3 (mean absolute annuity error at 65 under 2%) are v1.1's, with v1.1's pass marks. **Q2 gets an upper bound**, written now, before any v1.3 result: the 95% intervals must cover **between 90% and 98%** of observed rates. With 40 ages and 3 years there are 120 cells, so a pass is 108 to 117 cells covered. An interval that covers more than 98% is too wide to price with, however well placed. Beside every coverage figure the run reports the interval's mean width (upper over lower rate, averaged over cells), for information; the pass rests on the bounds alone.

**A version passes for a sex only if Q1, Q2 and Q3 all pass at both origins.** Q4 (the anchor lowers deviance) is reported at both origins but is not part of the pass, because it compares two versions of the same model and says nothing about whether the forecast is fit to price with. The same tests, bounds and origins apply to v1.2 at origin B and to the CBD fallback.

In the same run, three things are scored by sex at both origins:

1. v1.3, the average with the smoothed cohort term;
2. v1.2, as frozen, scored again at origin B (it has so far been tested only at origin A);
3. for women, the fallback below.

## Women's fallback, decided now

If v1.3 fails for women, the planned alternative is **CBD post-peak on its own** (100% weight), with v1.1's anchor, overdispersion and scaled deaths. CBD is the best-scoring model without a cohort term. Its anchored design deviance for women was 4,541, against 7,854 for LC post-peak, and on v1.2's validation run it had the lower deviance as well (2,592 against 4,456). This choice is made before the run.

**What the upper bound means for it, known now.** CBD has no cohort term, so v1.3 does not change it, and its origin A result is already v1.2's: 100% coverage for women (120 of 120 cells, φ near 70). Under the 90% to 98% bound it **fails Q2 at origin A before the run**. So the fallback cannot price women, and the women's chain below in effect reads: v1.3, else v1 with lower bounds. The fallback is still scored at both origins and reported. It is kept in the plan rather than swapped for another model, because choosing a new fallback now, with its origin A scores in view, would be choosing on the hold-out. The same holds for men's CBD (98.3%, 118 cells), which is not in the men's chain.

## Which version prices each sex

Decided now, applied after the run with no other choice:

- **Men:** v1.3 if it passes. Otherwise v1.2, if v1.2 passes at both origins. Otherwise v1, with men's ranges marked as lower bounds.
- **Women:** v1.3 if it passes. Otherwise the CBD fallback, if it passes. Otherwise v1, with women's ranges marked as lower bounds, the failure published, and no further iteration.

Until this run is reported, the site keeps v1's prices for both sexes. v1.1's and v1.2's prices are not put on the site. Where a sex is priced on v1, the site says so. Where the two sexes are priced on different versions, the site says that too.

## Reporting

As v1.1 and v1.2, at both origins, with v1.2 alongside: the tests, every model's scores, γ before and after smoothing (by birth year), the AR coefficient of γ, the e65 forecasts in 2020, 2030 and 2050, and prices at 55, 65 and 75. Also: the move in e65 from 2019 (fitted) to 2020 with the period index held, split by age, as in the diagnosis above. Seed 20261030. Script `research/v13.py`, output `research/results/v13.json`, on the Mac. Unit tests come before the freeze:

- the smoother on its own: a lone spike is cut to a fifth in the interior; the end rows match the table above; non-estimated cohorts are untouched; γ sums to zero;
- **recovery of a known cohort effect on simulated data**: deaths drawn as Poisson from an RH model with v1.2's men's a, b and k, the 2006 to 2019 window and WPP-sized exposures, and a known smooth γ (a linear trend plus a bump 10 years wide, of size 0.15). The smoothed fit converges, and its γ matches the five-year mean of the true γ to within 0.03 at every interior cohort. Then a heaped version (deaths at birth years ending in 0 scaled up by 15%): the smoothed fit's spikes at those years are under a third of the unsmoothed fit's;
- convergence from the two starts agrees, as above.

## After mortality is final

Everything downstream moves with the annuitant rates: v2's prices, v3's balance sheet and SCR, v4's projection and its 60.1%, and the capital grid. These are not rerun after each mortality version. Once v1.3 is reported and the pricing version for each sex is settled, the chain is rerun **once**, with the capital grid at R400m, R500m and R627m only. The cost and time are estimated and agreed before it starts. Until then, the site says the capital results use the v1 mortality model, and the crossing stays worded as R500m to R627m.
