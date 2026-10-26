# Results: v1.1 Liabilities, revised

Run on 26 October 2026 under `PROTOCOL_v1.1.md`, frozen at `785cd61cc5ab`, on the Mac in about six and a half minutes. Seed 20261028. Raw output: `research/results/v11.json`, built by `research/v11.py`. v1's results (`RESULTS.md`) stand as v1's. Nothing here has been put on the dashboard yet.

Primary data: Stats SA registered deaths scaled to WPP's total at ages 50 to 89 each year, over WPP exposure. Deviances are not comparable with v1's, which were on unscaled deaths.

## The answer

- **The jump-off is fixed.** Period life expectancy at 65 in the first forecast year now starts where the observed rates are: men 14.07 in 2020 against 14.00 observed in 2019 (v1: 15.31 against 14.95), women 16.88 against 16.80 (v1: 18.29).
- **Completeness scaling** lowers observed e65 for men in 2019 from 14.95 to 14.00, close to WPP's 13.8, and lowers the price at 65 by about 2%.
- **The average is not an average.** The weight rule puts 99.3% on RH for men and all of it on RH for women. Design deviances differ by thousands, against a mean dispersion of 10 to 40, so the rule treats the gap as real. In practice v1.1's model is RH on the full window.
- **That window is what moves the price most.** On scaled deaths RH's window is chosen as full (summed design deviance 5,889 against 6,579 for post-peak), though men alone prefer post-peak (1,458 against 3,240). From 1997 the period index carries the HIV-era rise and fall, so its drift is close to nil: e65 is flat from 2020 to 2030 (men 14.07 and 14.07, women 16.88 and 16.73) and only the cohort term lifts it later. The price at 65 falls 9% for men and 16% for women. v1 was too steep (men's e65 19.7 in 2050); v1.1 is close to no improvement for a decade.
- **Q2 still fails, and the reason has changed.** RH's in-sample dispersion is only 2.3 for men and 2.7 for women, because its cohort term soaks up the year-to-year noise. Out of sample, its deviance is about 28 times what Poisson noise would give. So overdispersion measured on the fit does not reach the forecast error, which is mostly bias in the trend, not noise.

## Tests (validation period, primary run, the anchored average)

| Test | Men | Women | v1 equivalent (unscaled, RH post-peak) |
| --- | --- | --- | --- |
| Q1, beats B0 on deviance | Pass (3,409 against 6,450) | Pass (1,907 against 5,822) | P1 pass, both |
| Q2, 95% intervals cover at least 90% | **Fail (73.3%)** | **Fail (76.7%)** | P3 fail: 55% and 79%, process only |
| Q3, annuity error at 65 under 2% | **Fail (2.54%)** | Pass (1.87%) | P4 pass, both |
| Q4, the anchor lowers deviance | Pass (3,409 against 3,419) | Pass (1,907 against 1,920) | n/a |

The annuity errors are negative in every year (men −1.9%, −3.0%, −2.8%; women −1.6%, −1.9%, −2.2%): the forecast's mortality is too high, so it misses improvement that happened in 2017 to 2019.

## Weights and windows (design period)

| | LC | CBD | RH |
| --- | --- | --- | --- |
| Window chosen | post-peak | post-peak | full |
| Anchored design deviance, men | 8,766 | 3,532 | 3,410 |
| Anchored design deviance, women | 7,854 | 4,541 | 2,494 |
| Dispersion φ, men | 10.9 | 23.9 | 1.9 |
| Dispersion φ, women | 23.8 | 86.6 | 2.6 |
| Weight, men | 0.0% | 0.7% | 99.3% |
| Weight, women | 0.0% | 0.0% | 100% |
| Inverse-deviance weight (sensitivity), men | 16.5% | 41.0% | 42.5% |
| Inverse-deviance weight (sensitivity), women | 17.0% | 29.4% | 53.6% |

## Every model on the validation period

Deviance, 95% coverage with all three sources of uncertainty, and mean absolute annuity error at 65. "v1 set-up" is the same fit with process uncertainty only, unanchored, as v1's P3 read it.

| | Men | | | Women | | |
| --- | --- | --- | --- | --- | --- | --- |
| | Deviance | Coverage | Error | Deviance | Coverage | Error |
| B0 | 6,450 | | | 5,822 | | |
| LC, anchored (φ 12.3 men, 22.0 women) | 5,396 | 80.8% | 2.56% | 4,512 | 93.3% | 0.79% |
| CBD, anchored (φ 23.1, 69.6) | 3,358 | 98.3% | 0.40% | 2,556 | 100% | 0.62% |
| RH, anchored (φ 2.3, 2.7) | 3,434 | 70.8% | 2.55% | 1,907 | 76.7% | 1.87% |
| RH, v1 set-up | 3,496 | 35.0% | 2.57% | 1,939 | 39.2% | 1.88% |
| **Average (the v1.1 rule)** | **3,409** | **73.3%** | **2.54%** | **1,907** | **76.7%** | **1.87%** |
| Inverse-deviance average (sensitivity) | 2,380 | 100% | 1.89% | 1,266 | 100% | 1.58% |

- Overdispersion lifts RH's coverage from 35% to 71% for men and 39% to 77% for women on the same fits, but not to 90%.
- CBD, with large φ, covers nearly everything; its intervals are wide rather than well placed.
- **The inverse-deviance average** would pass all four tests and has the lowest deviance of anything here: its median beats every single model. It is a sensitivity, set beforehand, and nothing is chosen on it. Its 100% coverage says its intervals are too wide.

## Annuity prices at 65 (4%, annuitant factor 0.7), each change added in turn

| | Men | 95% interval | Width | Women | 95% interval | Width |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | 13.53 | 13.11 to 14.03 | 6.8% | 16.05 | 15.36 to 16.70 | 8.3% |
| + completeness scaling | 13.23 | 12.81 to 13.73 | 7.0% | 15.72 | 14.92 to 16.50 | 10.0% |
| + anchor (still v1's RH post-peak) | 13.24 | 12.82 to 13.74 | 6.9% | 15.73 | 14.92 to 16.48 | 10.0% |
| + average (RH full in practice) | 12.10 | 11.88 to 12.29 | 3.4% | 13.18 | 13.02 to 13.34 | 2.5% |
| **+ overdispersion = v1.1** | **12.09** | **11.85 to 12.33** | **4.0%** | **13.18** | **12.97 to 13.39** | **3.2%** |
| Sensitivity: registered deaths, unscaled | 12.62 | 12.27 to 12.95 | 5.4% | 13.52 | 13.10 to 13.94 | 6.2% |
| Sensitivity: inverse-deviance weights | 11.86 | 10.44 to 12.33 | 16.0% | 13.26 | 12.60 to 15.04 | 18.4% |

At 55: v1.1 14.60 men and 15.98 women; at 75: 8.89 and 9.87.

- **The anchor barely moves the price.** It shifts the start of the forecast, and RH post-peak's fitted line was already close to the last three years once deaths are scaled.
- **The intervals got narrower, not wider.** The full-window RH has a small drift variance, and its φ is small. The model risk the average was meant to carry is not in the v1.1 interval, because the rule gave the other models no weight.

## Period life expectancy at 65, forecast median and 95% interval

| | 2020 | 2030 | 2050 |
| --- | --- | --- | --- |
| Men, v1 | 15.31 | 16.11 | 19.65 |
| Men, v1.1 | 14.07 (14.0 to 14.2) | 14.07 (13.9 to 14.2) | 15.07 (10.5 to 18.4) |
| Women, v1 | 18.29 | 19.69 | 25.60 |
| Women, v1.1 | 16.88 (16.8 to 17.0) | 16.73 (16.5 to 17.0) | 17.34 (13.0 to 20.1) |

Observed on scaled deaths, 2017 to 2019: men 13.93, 14.11, 14.00; women 16.69, 16.74, 16.80. WPP 2024's e65 for men in 2019 is about 13.8.

## Paths left out

As the protocol set out, paths whose rates at 80 to 89 reach 1 cannot take the Kannisto tail. All of them are at entry age 55, the longest horizon, and come from RH's cohort term: in v1.1, 22 of 5,000 for men and 13 for women; in the inverse-weight sensitivity, 262 for men (5.2%). None at ages 65 or 75, and none in the e65 figures.

## What it points to

v1.1 fixed what it could fix by construction: the jump-off, and the registration drift in the level. It did not make the forecasts trustworthy. Two problems remain, and both are about the trend, not the noise:

1. **The window decides the trend.** Full window: almost no improvement for a decade. Post-peak: v1's fast improvement. The data from 1997 to 2019 cannot say which is right, because the HIV epidemic and the roll-out of treatment dominate both. The single window for both sexes forced men onto the window their own design deviance rejected.
2. **The weight rule is too sharp.** Scaling deviance by the in-sample φ treats the models' differences as signal, so the "average" is a selection. The inverse-deviance mixture, which keeps all three, scored best on validation.

A v1.2 would need its own frozen plan. Candidates: windows chosen per sex; dispersion measured out of sample (on the design period's forecast errors) rather than on the fit; and weights that keep more than one model.
