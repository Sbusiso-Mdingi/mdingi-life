# Results: v1.2 Liabilities, windows by sex

Run on 26 October 2026 under `PROTOCOL_v1.2.md`, frozen at `1dc85fcda492`, on the Mac in about nine minutes. Seed 20261029. Raw output: `research/results/v12.json`, built by `research/v12.py`. Everything is v1.1's method except that each sex chooses its own fitting windows. v1 and v1.1 stand as reported. Nothing here is on the dashboard yet.

## The answer

- **Men now pass all four tests.** With their own windows (post-peak for every model), the average is RH post-peak, at 100% weight. Validation deviance halves (1,529, against 3,409 in v1.1), the 95% intervals cover 93.3% of observed rates, and the annuity error at 65 averages 1.66%. Two caveats belong with this. The 2017 to 2019 hold-out has now guided three versions, so it is no longer a clean test. And v1.2's windows were chosen after v1.1's design scores had been seen.
- **Women are unchanged.** Their windows were already v1.1's (RH full). Q2 still fails, at 75.8%.
- **Men's price at 65 goes back up** to 13.24 (v1.1 12.09, v1 13.53). Women stay at 13.18 (v1 16.05).
- **The forecasts differ by sex, as the data asks.** Men improve steadily: e65 of 14.4 in 2020, 15.1 in 2030 and 18.1 in 2050. Women barely improve for a decade: 16.9, 16.7, then 17.3 in 2050. That follows from the women's full window, which spans the HIV-era rise and fall.
- **The jump-off is not fully fixed, for either sex.** See below. This also corrects what v1.1 reported.

## Tests (validation period, primary run, the anchored average)

| Test | Men | Women | Men, v1.1 |
| --- | --- | --- | --- |
| Q1, beats B0 on deviance | Pass (1,529 against 6,450) | Pass (1,901 against 5,822) | Pass |
| Q2, 95% intervals cover at least 90% | **Pass (93.3%)** | **Fail (75.8%)** | Fail (73.3%) |
| Q3, annuity error at 65 under 2% | **Pass (1.66%)** | Pass (1.87%) | Fail (2.54%) |
| Q4, the anchor lowers deviance | Pass (1,529 against 1,537) | Pass (1,901 against 1,922) | Pass |

Annuity errors by year, men: −1.2%, −2.1%, −1.7%; women: −1.5%, −1.9%, −2.2%. Both still forecast too little improvement for 2017 to 2019, men less so than in v1.1.

## Windows and weights (design period, by sex)

| | LC | CBD | RH |
| --- | --- | --- | --- |
| Window, men | post-peak | post-peak | post-peak |
| Window, women | post-peak | post-peak | full |
| Weight, men | 0% | 0% | 100% |
| Weight, women | 0% | 0% | 100% |
| Inverse-deviance weight (sensitivity), men | 10.6% | 26.1% | 63.4% |
| Inverse-deviance weight (sensitivity), women | 17.1% | 29.4% | 53.5% |

## Every model on the validation period

| | Men | | | Women | | |
| --- | --- | --- | --- | --- | --- | --- |
| | Deviance | Coverage | Error | Deviance | Coverage | Error |
| B0 | 6,450 | | | 5,822 | | |
| LC post-peak, anchored | 5,383 | 80.8% | 2.58% | 4,456 | 93.3% | 0.81% |
| CBD post-peak, anchored | 3,309 | 98.3% | 0.35% | 2,592 | 100% | 0.66% |
| RH, anchored (post-peak men, full women) | 1,529 | 93.3% | 1.66% | 1,901 | 75.8% | 1.87% |
| RH, v1 set-up | 1,538 | 48.3% | 1.63% | 1,961 | 40.0% | 1.88% |
| **Average (the rule)** | **1,529** | **93.3%** | **1.66%** | **1,901** | **75.8%** | **1.87%** |
| Inverse-deviance average (sensitivity) | 1,273 | 100% | 1.44% | 1,242 | 100% | 1.56% |

## Annuity prices at 65 (4%, annuitant factor 0.7)

| | Men | 95% interval | Width | Women | 95% interval | Width |
| --- | --- | --- | --- | --- | --- | --- |
| v1 | 13.53 | 13.11 to 14.03 | 6.8% | 16.05 | 15.36 to 16.70 | 8.3% |
| v1.1 | 12.09 | 11.85 to 12.33 | 4.0% | 13.18 | 12.97 to 13.39 | 3.2% |
| v1.2, Poisson bootstrap | 13.23 | 12.82 to 13.73 | 6.9% | 13.18 | 13.02 to 13.34 | 2.4% |
| **v1.2** | **13.24** | **12.76 to 13.85** | **8.2%** | **13.18** | **12.97 to 13.39** | **3.2%** |
| Sensitivity: registered deaths, unscaled | 13.53 | 13.08 to 14.09 | 7.5% | 13.52 | 13.10 to 13.94 | 6.2% |
| Sensitivity: inverse-deviance weights | 13.02 | 10.55 to 13.79 | 24.9% | 13.25 | 12.52 to 15.08 | 19.3% |

At 55: men 15.70, women 16.01. At 75: men 9.36, women 9.87.

Men's and women's prices at 65 are now almost the same. That is not plausible on its face (women outlive men at 65 by close to three years). It comes from the women's flat trend against the men's improving one. v1.2's women's price rests on RH's full window, which fails Q2.

Paths left out of the Kannisto tail (all at entry age 55): none for men, 6 for women, 164 for men in the inverse-weight sensitivity.

## Period life expectancy at 65, forecast median and 95% interval

| | 2020 | 2030 | 2050 |
| --- | --- | --- | --- |
| Men, v1 | 15.31 | 16.11 | 19.65 |
| Men, v1.1 | 14.07 | 14.07 | 15.07 |
| **Men, v1.2** | **14.38 (14.2 to 14.6)** | **15.11 (14.5 to 15.7)** | **18.08 (15.3 to 20.5)** |
| Women, v1 | 18.29 | 19.69 | 25.60 |
| **Women, v1.1 and v1.2** | **16.88 (16.8 to 17.0)** | **16.73 (16.5 to 17.0)** | **17.34 (13.0 to 20.2)** |

Observed on scaled deaths in 2019: men 14.00, women 16.80.

## The jump-off, corrected

v1.1 reported the jump-off as fixed, because the forecast for 2020 sat close to 2019's observed value. On closer inspection that was partly coincidence. Checked after this run, on the production fits:

| | Observed 2019 | RH fitted 2019 | 2020, period index held at 2019 | 2020 forecast median |
| --- | --- | --- | --- | --- |
| Men (RH post-peak) | 14.00 | 14.12 | 14.29 | 14.38 |
| Women (RH full) | 16.80 | 16.63 | 16.88 | 16.88 |

With the period index frozen, moving one year along the cohort diagonals alone lifts e65 by 0.17 for men and 0.25 for women. Most of it comes from the oldest cohorts, seen in only three to five cells, whose estimated cohort effects are large and poorly identified (up to +0.63 for women). They leave the 50 to 89 age range in 2020. *Corrected 26 October 2026: this explanation is wrong. The cohorts at ages 65 to 89 in 2019 (born 1930 to 1954) are seen in 14 to 23 cells each. Split by age, almost all of the jump comes from age 89, where the 1931 cohort replaces the 1930 cohort, and γ spikes at round birth years (1930, 1940). See `PROTOCOL_v1.3.md`, "Seen beforehand". Added the same day: a check of the unit records (`research/heaping.py`) confirms heaping of birth years ending in 0 on death records, of a size that matches these spikes; ages and years ending in 5 are not heaped.* The anchor is an offset by age, so it cannot undo a shift that runs along cohorts. For women the cohort jump happened to land the forecast on the observed value; for men it overshoots it by 0.38.

## What it points to

- For **men**, v1.2 is the first version to pass every test. Its remaining flaw is the cohort jump at the start of the forecast, which adds about 0.2 to 0.4 years to e65.
- For **women**, the full-window RH still fails Q2. It forecasts almost no improvement for a decade, which makes women's price at 65 the same as men's.
- Both problems point at RH's cohort term: poorly identified at the old end, and absorbing the noise that the dispersion estimate then misses (φ is 2 to 3 for RH, against 12 to 70 for the others).

A next step would need its own frozen plan. The obvious candidate is a stricter rule for estimating cohorts (more than three cells, or smoothing γ over birth years). *(After the correction above, only smoothing addresses the cause.)* Measuring dispersion out of sample, and a weight rule that keeps more than one model, also remain open.
