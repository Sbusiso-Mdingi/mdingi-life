# Protocol: v1 Liabilities

Written on 25 October 2026, before any model in this repository was fitted. UN WPP 2024 life tables have been downloaded and six values were read off to check the file (male life expectancy at birth and at 65 in 2006, 2019 and 2021). The WPP deaths and population files were then loaded and their coverage checked (years, ages, missing and zero cells), and one rate (male, 65, 2019: deaths over population 0.0381, against the life table's 0.0390) was computed to confirm the units. Nothing else has been computed. This file is frozen, and its commit hash recorded here, before the first fit. Later changes are listed at the end with their dates and reasons.

Frozen at commit: `25b5acd95aa5`

The question: how much does uncertainty about future South African mortality move the price of a life annuity, and which models can be trusted to say so?

## Data

- **Primary.** Registered deaths by single year of age, sex and year of death from Statistics South Africa (*Mortality and causes of death*, P0309.3), 1997 to the latest release. Exposure: Stats SA mid-year population estimates (P0302) by single age and sex. Central death rate m(x,t) = deaths / mid-year population.
- **Cross-check.** UN World Population Prospects 2024, South Africa, 1950 to 2023 (CC BY 3.0 IGO): deaths by single age and sex over the 1 July population, both published in thousands and multiplied by 1,000. The open age group 100+ is dropped; it is outside the fitted ages anyway. These are model estimates, not registrations, so they are smoother than the truth. Fits on them are reported separately and never mixed with the primary series.
- **Fallback.** If Stats SA single-age data cannot be obtained, v1 runs on WPP alone, with that labelled on every chart, and the tests below are read as tests on a smoothed series.
- **Deaths with unknown age or sex** are spread pro rata within year (and sex, where known).
- **Old ages.** Registration completeness and age reporting both get worse at old ages. Models are fitted on ages 50 to 89. Above 89, rates are extended to 120 with a Kannisto curve fitted to ages 80 to 89 of each forecast year. The same treatment applies to every model.

## Years

- **Covid-19.** 2020 to 2022 are excluded from every fit and shown as observed points against the forecast fans. A model is not penalised for missing a pandemic. The forecast fans show how far outside them the pandemic fell.
- **Design period.** Fit on data up to 2012, score 2013 to 2016. Used to choose the fitting window and to debug.
- **Validation period.** Fit on data up to 2016, score 2017 to 2019. Run once, after the design choices are fixed.
- **Production fit.** Data up to 2019, plus any year after 2022 that has been released. Jump-off is the last year fitted. Because 2020 to 2022 are missing, a step of g years in a period index carries g times the drift and g times the variance.

## Models

| Model | Structure |
| --- | --- |
| B0, no improvement | m(x,t) frozen at the average of the last three fitted years |
| LC, Lee-Carter | log m(x,t) = a(x) + b(x) k(t); k(t) a random walk with drift; fitted by Poisson maximum likelihood |
| CBD, Cairns-Blake-Dowd | logit q(x,t) = k1(t) + (x − x̄) k2(t); (k1, k2) a bivariate random walk with drift |
| RH, Renshaw-Haberman | LC plus a cohort term with unit loading, a(x) + b(x) k(t) + γ(t − x) (the Haberman-Renshaw 2011 form), Σγ = 0; cohorts seen in fewer than three cells are not estimated; γ an ARIMA(1,1,0) |

Each model is fitted by sex.

**Fitting window.** Two candidates for LC, CBD and RH: *full* (1997 onwards) and *post-peak* (2006 onwards, after population mortality peaked with HIV). One window per model is chosen on design-period deviance, summed over both sexes, and then fixed. Nothing else is tuned.

**Chosen model.** After the windows are fixed, the model with the lowest validation deviance for each sex is the chosen model for that sex. It is the one tested in P1, P3 and P4 and used for the annuity prices.

## Scores

On ages 50 to 89, for each scored year:

1. **Poisson deviance** of observed deaths against forecast deaths (forecast rate × observed exposure).
2. **Annuity factor error.** Percentage difference between the period annuity factor at 65 computed from the forecast rates and from the observed rates, at 4% a year.
3. **Interval coverage.** Share of observed log m(x,t) that falls inside the model's 95% forecast interval.

## Tests (validation period)

- **P1, improvement is real.** The best model beats B0 on deviance for both sexes. Expected to pass: adult mortality fell over 2017 to 2019.
- **P2, the HIV hump.** LC on the post-peak window beats LC on the full window on deviance. Expected to pass: the rise to 2006 flattens the full-window drift.
- **P3, honest intervals.** The chosen model's 95% intervals cover at least 90% of observed rates. Intervals here reflect process uncertainty only (simulated period and cohort indices, parameters fixed). Expected to fail for LC, whose intervals only reflect uncertainty in k(t). If it fails, the annuity intervals below are reported as lower bounds.
- **P4, the annuity price.** The chosen model's absolute annuity factor error at 65 averages under 2% for both sexes.

Passing or failing does not change the method. Every result is reported.

## Annuity prices

From the production fit, for a single life aged 55, 65 and 75 in 2026, by sex. The cohort's rates come from the forecast diagonal.

- **Product.** Level annuity of 1 a year, paid monthly in advance, no guarantee period.
- **Discount rate.** Flat 4% a year (real, standing in for an inflation-linked annuity), with 2% and 6% as sensitivities. v2 replaces this with the fitted government bond curve.
- **Annuitant adjustment.** People who buy annuities have lighter mortality than the population. v1 multiplies population rates by a flat factor of 0.6, 0.7 or 0.8, shown side by side. These are **assumptions, not estimates**: no public South African annuitant experience is used.
- **Uncertainty.** 5,000 simulated paths of the period index (process uncertainty), each with parameters from a semiparametric bootstrap of deaths (parameter uncertainty, 500 refits). Reported as the median and a 95% interval of the annuity factor, and the interval's width as a percentage of the median. That width is the v1 headline.

## Changes after freezing

### 26 October 2026: Stats SA deaths from DataFirst, WPP exposure

Written before any model was fitted on Stats SA data. Done beforehand, and disclosed here: the DataFirst unit records were tallied by year of death, sex and single age (`research/mcd.py`), and registered deaths at ages 50 to 89 were divided by WPP deaths at the same ages, by year and sex, as a completeness check. No rates were computed and no model was fitted.

- **Deaths.** Stats SA *Mortality and Causes of Death* unit records from DataFirst (UCT): catalogue 830, 1997 to 2020, version 1.1, and catalogue 1074, version 1.1. Stillbirths are dropped and deaths are counted by year of death. These are the records P0309.3 is built from. The 1074 file holds the records processed in 2021, 2022 and 2024, so it covers deaths in 2021, 2022 and 2024 but only late registrations for 2023. 2023 is not used.
- **Exposure.** UN WPP 2024 1 July population by single age and sex. Stats SA mid-year estimates by single age could not be obtained: SuperWEB and Nesstar were down, and the P0302 projection workbook gives five-year groups ending at 80+. That workbook (2002 to 2025) is used only as a cross-check of the WPP exposure, aggregated to the same groups. Death rates therefore pair registered deaths with a modelled population, and are labelled that way.
- **Years.** The WPP population ends in 2023, so 2024 has no exposure and is not used. The production fit is 1997 to 2019, jump-off 2019. Design and validation periods are unchanged.
- **Completeness.** Registered deaths at ages 50 to 89 are not a constant share of WPP's estimate. For men, the share rises from 83% in 1997 to about 99% from 2003 to 2010, then falls to 90% by 2019. For women, it goes from 76% to about 93%, then 89%. A falling share makes registered mortality look as if it is improving faster than it is. WPP is itself a model, so part of the drift may be WPP's.
- **Primary run.** Registered deaths are used unadjusted, as already registered. Windows, chosen models and tests P1 to P4 are decided on this run alone, and it is reported next to the WPP run, never mixed with it.
- **One sensitivity.** Deaths at every age are divided by that year's completeness at ages 50 to 89, by sex. This lifts each year's total at 50 to 89 to WPP's level while keeping the registered age pattern. It reuses the primary run's windows and models and reports annuity prices only. It measures how much of the price comes from the registration drift and changes nothing else.

Reason: the protocol's primary source could not be fetched as written. This keeps Stats SA's registered deaths, which were the point of the primary series, and takes the only single-age exposure available.

### 26 October 2026: rolling-origin backtest and a blended price

Written after the Stats SA validation results above were seen, and before any rolling fit. It is a robustness check, not a re-selection: windows, chosen models, tests P1 to P4 and the chosen-model prices stay as they are. Reason: on Stats SA deaths the chosen model rests on one three-year validation block, and the model and window choice moves the price at 65 by more than the chosen model's own interval (see RESULTS.md, Decomposition). One block cannot say whether that choice is stable.

- **Origins.** Jump-off T = 2009, 2010, ..., 2016. Each origin is scored on T + 1 to T + 3, so every scored year is in 2010 to 2019 and the Covid years never enter. Both sources, both sexes, ages 50 to 89.
- **Windows.** At each origin: *full* (1997 to T), *post-peak* (2006 to T) and *rolling* (the 10 years T − 9 to T). LC, CBD and RH are fitted on all three; B0 uses the last three years to T. That is ten candidates per origin and sex.
- **Scores.** Those of the protocol: Poisson deviance, annuity factor error at 65, 95% interval coverage with process uncertainty only, by origin and horizon. Same simulation size (5,000 paths).
- **Summaries.** For each sex and candidate: deviance summed over origins, how many of the 8 origins it has the lowest deviance of the ten, mean absolute annuity error and mean coverage.
- **Two readings, which change nothing.** R1: the chosen model, at its window, has the lowest summed rolling deviance of the ten candidates. R2: the chosen model's mean rolling coverage is at least 90%.
- **Repricing.** At each origin and at the production jump-off, the price a life aged 65 would have been quoted in the year after jump-off (4%, factor 0.7, median of 5,000 process-only paths), for B0 and for LC, CBD and RH at their protocol windows. It shows how far the price moves when the insurer refits every year.
- **Blended price.** For each sex, a mixture of LC, CBD and RH at their protocol windows, with weights proportional to 1 / summed rolling deviance at those windows. B0 is left out: it is the no-improvement benchmark, not a forecast. Each model's 5,000 production paths (bootstrap, as in the annuity prices) are pooled, round(weight × 5,000) paths drawn from each, and the median, 95% interval and width are reported for every age, rate and factor. It is shown next to the chosen model's price, labelled as the blend, never in its place.
