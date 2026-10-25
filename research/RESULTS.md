# Results: v1 Liabilities

Run on 25 October 2026 under the protocol frozen at `25b5acd95aa5`. **Source: UN WPP 2024 only**, the protocol's fallback, because Stats SA's SuperWEB was down. WPP rates are model estimates and smoother than registered deaths, so every fit below looks better than it will on Stats SA data. The Stats SA run will be added here, not replace this one.

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

## Still to do

- Rerun on Stats SA registered deaths when SuperWEB is reachable, and compare.
- v2: replace the flat discount rate with the fitted government bond curve.
