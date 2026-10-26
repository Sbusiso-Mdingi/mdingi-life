# Protocol: v1.1 Liabilities, revised

Written on 26 October 2026, after v1 was run and reported, and before any v1.1 model was fitted. This is a revision made in response to v1's results, not a fresh test. v1 stays frozen at `6335c9c5c418` and its results stay the reported v1 results. Every v1.1 result is reported next to v1's.

Frozen at commit: (not yet frozen)

Seen beforehand, and disclosed here, because each one shaped a fix below:

- v1's validation deviance on Stats SA deaths: 1,648 for men and 793 for women, over 120 cells. A Poisson model expects about 120. Part of the excess is forecast error, but it points to deaths that vary several times as much as v1's Poisson bootstrap assumes.
- v1's P3 coverage: 55% for men and 79% for women, against 90%.
- Registration completeness at ages 50 to 89, against WPP (`research/results/completeness.csv`): for men, 99% to 101% from 2003 to 2010, then 91% by 2019; for women, 92% to 95%, then 89%.
- v1's completeness-scaled sensitivity prices, and v1's decomposition, in which the choice of model and window (RH against CBD) moves the price at 65 by about 18%.
- v1's exported forecast for men: observed period life expectancy at 65 of 14.9 years in 2019, a forecast median of 15.3 in 2020 and 19.7 in 2050.

The question is v1's: how much does uncertainty about future South African mortality move the price of a life annuity? v1.1 asks it again with four changes, one for each weakness above.

## What stays as v1

Ages 50 to 89, with the Kannisto extension to 120 from ages 80 to 89. 2020 to 2022 left out of every fit. The design period (fit to 2012, score 2013 to 2016) and the validation period (fit to 2016, score 2017 to 2019). The production fit, 1997 to 2019 with jump-off 2019. The four models and their structure. The two fitting windows and the rule that picks one per model on design deviance. The scores. The product, the 4% discount rate (2% and 6% as sensitivities) and the annuitant factors 0.6, 0.7 and 0.8. WPP 1 July population as exposure.

## Change 1: overdispersion

- **Dispersion.** For each fitted model and sex, φ = Pearson χ² / (cells − parameters), where Pearson χ² = Σ (D − D̂)² / D̂ over the fitted cells. Parameters: LC 2A + T − 2, CBD 2T, RH 2A + T − 2 + (cohorts estimated − 1), for A ages and T years. If φ comes out below 1, it is set to 1. The fits themselves do not change: the quasi-Poisson estimates are the Poisson ones.
- **Bootstrap.** Deaths are redrawn as gamma-Poisson with mean D̂ and variance φ D̂ (gamma shape D̂ / (φ − 1), scale φ − 1), instead of Poisson. With φ = 1 this is v1's Poisson bootstrap.
- **Observation noise.** An observed rate is the true rate plus the noise of a finite, overdispersed count. Wherever a forecast is compared with observed rates (P3's coverage and the dashboard's backtest fans), each simulated rate m is turned into a simulated observation: deaths drawn as gamma-Poisson with mean E m and the model's φ, at the observed exposure E, and divided by E. Price and life-expectancy fans are about the true rates and carry no observation noise.
- **P3's intervals** now carry all three sources: parameter uncertainty (bootstrap refits), process uncertainty (simulated indices) and observation noise. v1's P3, with process uncertainty only, is also reported on the same fits.

## Change 2: completeness-scaled deaths as the primary run

- **Primary run.** Deaths at every age divided by that year's completeness at ages 50 to 89, by sex: v1's sensitivity (`research/completeness.py`, `data/raw/statssa/mcd_deaths_scaled.csv`), unchanged. Windows, weights and tests are decided on this run.
- **Sensitivity.** Registered deaths unadjusted, with the primary run's windows and weights, prices only.
- **What this assumes.** The total at 50 to 89 each year is WPP's, and only the age pattern within it is Stats SA's. The trend in the total is therefore WPP's trend, and WPP is a model. The scaling removes the registration drift; it does not make the data independent of WPP.

## Change 3: a jump-off anchored to observed rates

v1 forecast from the model's fitted rates in the jump-off year, which can sit above or below what was observed. v1.1 adds to every forecast a fixed offset by age, the model's recent error, smoothed:

- r(x) = the mean over the last three fitted years of log m_observed(x, t) − log m_fitted(x, t);
- then a centred five-age moving average of r(x) over ages 50 to 89, shortened at the ends (ages 50 and 89 use three ages, 51 and 88 four);
- the forecast is log m(x, T + s) = model forecast + r(x), for every path and every year ahead.

So the first forecast year starts near the last three years of observed rates, not the model's fitted line, and the model's improvement runs on from there. The offset is the same in every year ahead and does not fade. It is computed on each bootstrap refit's own data and fit. B0 is unchanged: it is already the average of the last three observed years.

## Change 4: an average of LC, CBD and RH

- **Windows** are chosen per model on design deviance, as in v1.
- **Weights.** On the design period, with the chosen windows and the anchored forecast, for each sex: w_m ∝ exp(−(D_m − D_min) / (2 φ̄)), where D_m is model m's design deviance (summed over 2013 to 2016), D_min the smallest of the three, and φ̄ the mean of the three models' φ on the design fit. This is the out-of-sample quasi-likelihood weight: deviance is scaled by the dispersion before it is compared, so differences that the noise alone could make count for little. B0 gets no weight.
- **Fixed after the design period.** The weights are not re-estimated on the validation period or the production fit. The validation tests then score the average on years the weights never saw.
- **The average is a mixture**, not an average of rates. Of the 5,000 paths, model m contributes round(5,000 w_m), from ceil(500 × its share) bootstrap refits (at least one if it has any paths). The point forecast is the mixture's median.
- **Sensitivity.** Weights in proportion to 1 / D_m, prices and tests reported, nothing chosen on it.

## Tests (validation period, primary run, the anchored average)

- **Q1, improvement is real.** The average beats B0 on deviance, for both sexes. Expected to pass.
- **Q2, honest intervals.** The average's 95% intervals, with all three sources of uncertainty, cover at least 90% of observed rates, for both sexes. This is v1's P3 with its pass mark, on intervals that now include everything the data can show. Expected to pass for women, uncertain for men.
- **Q3, the annuity price.** The average's absolute annuity factor error at 65 averages under 2%, for both sexes. v1's P4.
- **Q4, the anchor helps.** The anchored average beats the same average without the anchor on deviance, for both sexes. Expected to pass.

Passing or failing does not change the method. Every result is reported, including the tests run on each single model and on v1's unanchored, Poisson set-up.

## Annuity prices

As v1, from the production fit of the anchored average: ages 55, 65 and 75 in 2026, by sex, at each rate and annuitant factor, with the median, the 95% interval and its width as a share of the median. 500 refits and 5,000 paths, split by weight as above. Seed 20261028. A path whose rates at ages 80 to 89 reach 1 or more cannot take the Kannisto extension (its logit is undefined). Such paths are left out of that price or life expectancy, and how many were left out is reported. In a test on simulated data with extreme overdispersion (φ about 120), the cohort term of Renshaw-Haberman produced such paths.

## Reporting against v1

- A table of v1's P1, P3 and P4 next to Q1, Q2 and Q3.
- The price at 65 (4%, factor 0.7), and its 95% interval, as each change is added one at a time in this fixed order: v1; with completeness scaling; with the anchor; with the average; with overdispersion (which moves the interval, not the median). Each step keeps the ones before it.
- The forecast median of period life expectancy at 65 in 2020, 2030 and 2050, by sex, for v1 and v1.1, with WPP 2024's estimate for 2019 to 2023 alongside.

## What follows

v2 to v4 were built on v1's prices and annuitant rates. Whether they are rerun on v1.1 is decided after v1.1 is reported. If they are, the frozen v1 to v4 results stay, and both sets are shown.

## Where it runs

On the Mac. One Renshaw-Haberman fit takes about 0.15 seconds (timed once on the production window, nothing scored), so 500 refits per model are affordable without the cloud machine. Script `research/v11.py`, output `research/results/v11.json`.
