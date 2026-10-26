# Protocol: v1.3 Liabilities, a smoothed cohort term

Written on 26 October 2026, after v1.2 was run and reported (`RESULTS_v1.2.md`), and before any v1.3 code was written or run. A revision made in response to v1.2's results. v1, v1.1 and v1.2 stay as reported. **This is the last mortality iteration.** Whatever it shows is published, and the mortality model is then final.

Frozen at commit: (not yet frozen)

## Seen beforehand, and disclosed

- Everything in `RESULTS_v1.2.md`.
- After v1.2, the cohort effects γ of v1.2's two production fits (RH post-peak for men, RH full for women) were read off, and the move in e65 from 2019 to 2020 was split by age. No other model or rule was fitted. Almost all of the 2020 jump (0.15 of 0.17 years for men, 0.16 of 0.25 for women) comes from age 89, where the 1931 cohort replaces the 1930 cohort. γ spikes at round birth years: for men, 1929 −0.10, **1930 +0.01**, 1931 −0.16, and 1940 +0.20 against +0.08 and +0.10 either side; for women, 1929 −0.01, **1930 +0.14**, 1931 −0.11, and 1940 +0.06 against −0.13 and −0.08. These cohorts are seen in 14 to 23 cells each, so they are not sparse. The pattern is what heaping of birth years on death records (unknown dates of birth recorded as round years) would produce. The mechanism has not been checked in the unit records.
- v1.2's results said the jump came from the oldest, sparsely observed cohorts. That was wrong, and a dated correction is added there.

## Hold-out reuse

The 2017 to 2019 validation period has now guided three versions (v1.1, v1.2 and this one), and v1.2's windows were chosen after v1.1's design scores had been seen. It is no longer a clean test. So v1.3 adds a second backtest origin (below), and a version passes only if it passes at both.

## The one change: the cohort term is smoothed over birth years

In the Renshaw-Haberman fit, after each update of γ and its re-centring, γ over the estimated cohorts is replaced by its **centred five-year moving average over birth years**, shortened at the ends (the first and last estimated cohorts use three, the next ones four), then re-centred to sum to zero. The fit iterates to convergence with this step inside it, as now. So γ is the best-fitting cohort effect among those that are smooth on a five-year scale.

**The parameter: a span of 5 birth years, equal weights.** A spike at a round year is shared with four neighbours that are not heaped, which cuts it to a fifth. Five is the narrowest odd span that does this for heaping on years ending in 0 and 5, and narrow enough to keep real differences between cohorts a decade apart (the HIV-era cohorts). It is fixed now and not varied.

Unchanged: the minimum of three cells for a cohort to be estimated, the ARIMA(1,1,0) for γ's forecast (now fitted to the smoothed γ), the unit cohort loading, and everything else in v1.1 and v1.2.

**A risk, stated now.** Smoothing makes successive changes in γ move together, so the ARIMA's AR coefficient will rise. Future cohorts' effects (those born after the last estimated cohort) then carry recent trends further. This matters most for the price at 55. It is reported, not tuned.

**Why not a minimum cell count.** The cohorts behind the jump are each seen in 14 or more cells, so raising the minimum from 3 would not touch them.

## Windows

As v1.2, for each sex: post-peak (2006) for LC, CBD and RH for men; post-peak for LC and CBD and full (1997) for RH for women. Not re-chosen.

## Two backtest origins

- **Origin A**: fit to 2016, score 2017 to 2019 (v1's validation period).
- **Origin B**: fit to 2013, score 2014 to 2016. Each sex's v1.2 windows, so men's fits use 2006 to 2013 (eight years) and women's RH 1997 to 2013. Origin B's scored years lie inside the design period (2013 to 2016), on which the windows and weights were chosen. So it is a second check of stability, not an independent hold-out. No earlier origin works: the post-peak window would have too few years.
- **Weights** are set on the design period, as in v1.1, with the smoothed cohort term. They are the same at both origins.

## Tests and how the origins combine

Q1 (beats B0 on deviance), Q2 (95% intervals cover at least 90% of observed rates) and Q3 (mean absolute annuity error at 65 under 2%) are v1.1's, with v1.1's pass marks. **A version passes for a sex only if Q1, Q2 and Q3 all pass at both origins.** Q4 (the anchor lowers deviance) is reported at both origins but is not part of the pass, because it compares two versions of the same model and says nothing about whether the forecast is fit to price with.

In the same run, three things are scored by sex at both origins:

1. v1.3, the average with the smoothed cohort term;
2. v1.2, as frozen, scored again at origin B (it has so far been tested only at origin A);
3. for women, the fallback below.

## Women's fallback, decided now

If v1.3 fails for women, the planned alternative is **CBD post-peak on its own** (100% weight), with v1.1's anchor, overdispersion and scaled deaths. CBD is the best-scoring model without a cohort term. Its anchored design deviance for women was 4,541, against 7,854 for LC post-peak, and on v1.2's validation run it had the lower deviance as well (2,592 against 4,456). Its intervals look too wide (100% coverage at origin A with φ near 70). This choice is made before the run.

## Which version prices each sex

Decided now, applied after the run with no other choice:

- **Men:** v1.3 if it passes. Otherwise v1.2, if v1.2 passes at both origins. Otherwise v1, with men's ranges marked as lower bounds.
- **Women:** v1.3 if it passes. Otherwise the CBD fallback, if it passes. Otherwise v1, with women's ranges marked as lower bounds, the failure published, and no further iteration.

Until this run is reported, the site keeps v1's prices for both sexes. v1.1's and v1.2's prices are not put on the site. Where a sex is priced on v1, the site says so. Where the two sexes are priced on different versions, the site says that too.

## Reporting

As v1.1 and v1.2, at both origins, with v1.2 alongside: the tests, every model's scores, γ before and after smoothing (by birth year), the AR coefficient of γ, the e65 forecasts in 2020, 2030 and 2050, and prices at 55, 65 and 75. Also: the move in e65 from 2019 (fitted) to 2020 with the period index held, split by age, as in the diagnosis above. Seed 20261030. Script `research/v13.py`, output `research/results/v13.json`, on the Mac. Unit tests of the smoothing on simulated data (a heaped cohort is damped; a smooth cohort trend is kept; γ still sums to zero) come before the freeze.

## After mortality is final

Everything downstream moves with the annuitant rates: v2's prices, v3's balance sheet and SCR, v4's projection and its 60.1%, and the capital grid. These are not rerun after each mortality version. Once v1.3 is reported and the pricing version for each sex is settled, the chain is rerun **once**, with the capital grid at R400m, R500m and R627m only. The cost and time are estimated and agreed before it starts. Until then, the site says the capital results use the v1 mortality model, and the crossing stays worded as R500m to R627m.
