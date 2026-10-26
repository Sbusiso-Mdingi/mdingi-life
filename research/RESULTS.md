# Results: v1 Liabilities

Two runs under the protocol frozen at `25b5acd95aa5`, reported side by side and never mixed:

1. **UN WPP 2024** (25 October 2026), the protocol's cross-check series, run first because Stats SA's SuperWEB was down. WPP rates are model estimates and smoother than registered deaths.
2. **Stats SA registered deaths over WPP exposure** (26 October 2026), under the amendment of that date: deaths from the DataFirst unit records, population from WPP. See [below](#stats-sa-registered-deaths).

# UN WPP 2024

Raw output: `research/results/backtest_wpp.json` and `annuities_wpp.json`.

## Fitting windows (design period, deviance summed over both sexes)

| Model | Full (1997 on) | Post-peak (2006 on) | Chosen |
| --- | --- | --- | --- |
| LC | 8,757 | 3,975 | post-peak |
| CBD | 5,495 | 6,783 | full |
| RH | 4,357 | 6,336 | full |

For women, Lee-Carter fitted from 1997 had more than three times the deviance of the fit from 2006 (6,695 against 1,841): the HIV-era rise bends the single trend. CBD and RH cope better with the longer window.

## Validation (fit to 2016, scored 2017 to 2019, ages 50 to 89)

| Model | Deviance, men | Deviance, women | 95% coverage, men | 95% coverage, women | Mean annuity error at 65, men | Mean annuity error at 65, women |
| --- | --- | --- | --- | --- | --- | --- |
| B0 no improvement | 4,716 | 3,421 | n/a | n/a | 1.6% | 1.6% |
| LC post-peak | 2,887 | 1,877 | 29% | 44% | 1.7% | 0.5% |
| **CBD full** | **2,370** | **1,142** | 68% | 90% | 0.4% | 0.3% |
| RH full | 3,973 | 2,431 | 15% | 47% | 2.1% | 1.5% |

Annuity errors are negative in 23 of 24 model-years: forecast rates were slightly too high, so the forecast annuity factor was slightly too low. Only RH misses by more than 2% on average, for men. The chosen model is CBD for both sexes.

## Tests

| Test | Men | Women | Expected |
| --- | --- | --- | --- |
| P1, improvement is real | Pass | Pass | Pass |
| P2, the HIV hump | Pass | Pass | Pass |
| P3, honest intervals (≥ 90%) | **Fail** (68%) | Pass (90%, at the line) | Fail for LC |
| P4, annuity factor error under 2% | Pass | Pass | Pass |

P3 behaved as expected for Lee-Carter (29% and 44%) and also failed for the chosen model for men. As the protocol requires, the annuity intervals below are therefore reported as **lower bounds** for men. For women the pass is exactly at the line and should not be leaned on.

## Annuity prices

Production fit: CBD, 1997 to 2023 without 2020 to 2022, jump-off 2023. Life annuity of 1 a year, monthly in advance, bought in 2026. Median and 95% interval from 500 bootstrap refits and 5,000 paths.

At 4% and an annuitant factor of 0.7:

| Age | Men | Interval width | Women | Interval width |
| --- | --- | --- | --- | --- |
| 55 | 14.04 [13.38, 14.83] | 10.3% | 16.03 [15.24, 16.87] | 10.2% |
| 65 | 11.04 [10.32, 11.91] | 14.5% | 13.02 [12.15, 14.01] | 14.3% |
| 75 | 8.14 [7.39, 9.04] | 20.4% | 9.84 [8.95, 10.90] | 19.8% |

**Headline.** Mortality uncertainty alone moves the price of a South African life annuity at 65 across a range about 14% wide, and 20% at 75. Across discount rates of 2% to 6% and annuitant factors of 0.6 to 0.8, the width at 65 runs from 11% to 19% for men and 10% to 20% for women. For men these are lower bounds (P3).

The relative width grows with age because an older annuitant's price rests on fewer, nearer years, where CBD's age-slope uncertainty bites hardest.

**The annuitant assumption matters as much as the model.** At 65 and 4%, moving the factor from 0.6 to 0.8 changes the male price from 11.69 to 10.48, a 10% swing, comparable to the whole model interval. That factor is an assumption with no public South African data behind it.

# Stats SA registered deaths

Run on 26 October 2026 under the amendment of that date. Deaths: Stats SA *Mortality and Causes of Death* unit records (DataFirst), 1997 to 2022, by year of death; 2023 and 2024 are not used. Exposure: WPP 2024 1 July population, because Stats SA's single-age estimates could not be obtained. These rates pair registered deaths with a modelled population.

Raw output: `research/results/backtest_statssa.json`, `annuities_statssa.json`, `annuities_statssa_scaled.json`, `completeness.csv` and `exposure_check.csv`. Built by `research/mcd.py`, `exposure.py` and `completeness.py`.

## Fitting windows (design period, deviance summed over both sexes)

| Model | Full (1997 on) | Post-peak (2006 on) | Chosen |
| --- | --- | --- | --- |
| LC | 26,006 | 15,829 | post-peak |
| CBD | 14,510 | 9,225 | post-peak |
| RH | 7,106 | 4,790 | post-peak |

Every model prefers the post-peak window here; on WPP only Lee-Carter did. Deviances are 1.6 to 3 times the WPP values: registered deaths carry real year-to-year noise that WPP smooths away.

## Validation (fit to 2016, scored 2017 to 2019, ages 50 to 89)

| Model | Deviance, men | Deviance, women | 95% coverage, men | 95% coverage, women | Mean annuity error at 65, men | Mean annuity error at 65, women |
| --- | --- | --- | --- | --- | --- | --- |
| B0 no improvement | 6,835 | 5,174 | n/a | n/a | 2.6% | 1.6% |
| LC post-peak | 4,657 | 3,648 | 27% | 38% | 1.9% | 0.4% |
| CBD post-peak | 3,359 | 2,249 | 45% | 68% | 0.8% | 0.1% |
| **RH post-peak** | **1,648** | **793** | 55% | 79% | 1.6% | 0.8% |

The chosen model is RH for both sexes, not CBD as on WPP. RH has the lowest deviance by a wide margin. CBD still has the smaller annuity error, but the protocol chooses on deviance. As on WPP, most errors are negative (14 of 18 model-years): forecasts were slightly too pessimistic.

## Tests

| Test | Men | Women | WPP run |
| --- | --- | --- | --- |
| P1, improvement is real | Pass | Pass | Pass, Pass |
| P2, the HIV hump | Pass | Pass | Pass, Pass |
| P3, honest intervals (≥ 90%) | **Fail** (55%) | **Fail** (79%) | Fail, Pass |
| P4, annuity factor error under 2% | Pass (1.6%) | Pass (0.8%) | Pass, Pass |

P3 fails for both sexes, so every Stats SA annuity interval below is a **lower bound**.

## Annuity prices

Production fit: RH, 2006 to 2019, jump-off 2019 (WPP: CBD, 1997 to 2023, jump-off 2023). Same product, bootstrap and paths as the WPP run.

At 4% and an annuitant factor of 0.7:

| Age | Men | Width | Women | Width | Men vs WPP | Women vs WPP |
| --- | --- | --- | --- | --- | --- | --- |
| 55 | 16.51 [15.28, 17.68] | 14.5% | 18.89 [17.42, 20.10] | 14.2% | +17.6% | +17.9% |
| 65 | 13.53 [13.11, 14.03] | 6.8% | 16.05 [15.36, 16.70] | 8.3% | +22.6% | +23.3% |
| 75 | 9.65 [9.29, 10.12] | 8.6% | 12.29 [11.48, 13.13] | 13.4% | +18.6% | +24.9% |

**The data source moves the price more than the model's own uncertainty does.** At 65, the Stats SA price is about 23% above the WPP price, while each run's 95% interval is 7% to 15% wide. The two intervals do not overlap at any age. Across discount rates and annuitant factors, the width at 65 is 4.8% to 10.3% for men and 5.3% to 13.3% for women, narrower than on WPP, but these are lower bounds (P3).

## Registration completeness

Registered deaths at ages 50 to 89 as a share of WPP's deaths, after unknown ages and sexes are spread:

| | 1997 | 2000 | 2003 to 2010 | 2013 | 2016 | 2019 | 2020 | 2022 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Men | 87% | 96% | 99% to 101% | 92% | 94% | 91% | 86% | 81% |
| Women | 79% | 91% | 92% to 95% | 87% | 91% | 89% | 86% | 83% |

The share peaks during 2003 to 2010 and falls after. A falling share makes registered mortality look as if it improves faster. The post-peak window (2006 on) starts at the top of that decline.

**Sensitivity (pre-registered).** Each year's deaths divided by that year's share, by sex, keeping the primary run's RH post-peak models. Annuity prices only:

| Age | Men | Women | Gap to WPP, men | Gap to WPP, women |
| --- | --- | --- | --- | --- |
| 55 | 15.70 [14.38, 16.97] | 18.32 [16.76, 19.66] | +17.6% → +11.8% | +17.9% → +14.3% |
| 65 | 13.23 [12.81, 13.73] | 15.72 [14.92, 16.50] | +22.6% → +19.9% | +23.3% → +20.7% |
| 75 | 9.35 [9.02, 9.82] | 11.85 [10.91, 12.92] | +18.6% → +14.9% | +24.9% → +20.5% |

**Registration drift explains only a small part of the gap**: between a tenth (at 65) and a third (men at 55). The rest comes from what still differs between the runs: model and window (RH post-peak against CBD full), jump-off (2019 against 2023) and the age pattern of registered deaths. These were not separated; doing so would be analysis outside the protocol.

## Exposure cross-check

WPP 1 July population at ages 50 to 79 over Stats SA's own projection (P0302 workbook, 2002 to 2025, five-year groups):

| | 2002 | 2010 | 2016 | 2019 | 2020 | 2022 |
| --- | --- | --- | --- | --- | --- | --- |
| Men | 0.885 | 0.885 | 0.902 | 0.965 | 0.993 | 1.036 |
| Women | 0.927 | 0.922 | 0.939 | 0.972 | 0.983 | 1.004 |

Until 2016, WPP puts 6% to 12% fewer people aged 50 to 79 than Stats SA does, so rates on WPP exposure are higher. From 2016 to 2019 WPP's population grows about 7% faster for men and 3.5% faster for women, which would make rates on WPP exposure fall faster than on Stats SA's. This is a second drift, in the denominator, of the same size as the completeness drift and in the same direction. It is reported, not corrected: the protocol has no Stats SA single-age exposure to correct it with.

## Still to do

- Rerun on Stats SA single-age mid-year estimates if SuperWEB comes back, as the protocol first intended.
- v2: replace the flat discount rate with the fitted government bond curve.
