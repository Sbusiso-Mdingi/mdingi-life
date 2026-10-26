# Results: v1.3 Liabilities, a smoothed cohort term

Run on 26 October 2026 under `PROTOCOL_v1.3.md`, frozen at `e4e524b44d96`, on the Mac in about twelve minutes. Seed 20261030. Raw output: `research/results/v13.json`, built by `research/v13.py`. This was the last mortality iteration. v1, v1.1 and v1.2 stand as reported.

## The answer

- **v1.3 fails for both sexes.** Its 95% intervals are too wide at both origins (98.3% to 100% coverage, against the 90% to 98% allowed), and its e65 forecasts fail the plausibility gate (men's falls by 0.02 years from 2020 to 2030, women's rises by 0.14, against the 0.25 required).
- **Both fallbacks fail, as the plan said they would.** v1.2 passes every test at origin B for both sexes but fails the gate (women's price at 65 of 13.18 is below men's 13.24, and women's e65 falls). CBD fails Q2 at origin A (120 of 120 cells) and fails the gate.
- **So both sexes stay on v1, with their ranges marked as lower bounds.** The site already shows v1 for both, and says so. The combined set (v1 for both) passes the gate: women's 16.05 is above men's 13.53, and e65 rises by 0.80 years for men and 1.40 for women from 2020 to 2030. The mortality model is now final, and there is no further iteration.
- **Smoothing removed the jump-off, as designed, and took most of RH's fit with it.** The move in e65 from fitted 2019 to 2020 with the period index held falls from 0.17 to 0.00 for men and from 0.25 to 0.04 for women. But the smoothed RH fits much worse: in-sample deviance 3,812 against 811 for men and 20,201 against 2,344 for women on the production windows. Its dispersion φ rises from about 2 to 10 to 13 for men and 29 to 32 for women. The design weights then move: men's v1.3 is **CBD post-peak at 100%**, and women's is 88% smoothed RH and 12% CBD. So men's "v1.3" has no cohort term at all.

## Tests, both origins (the anchored v1.3 average)

Origin A fits to 2016 and scores 2017 to 2019. Origin B fits to 2013 and scores 2014 to 2016, inside the design period. Q2 passes at 108 to 117 of 120 cells. Width is the 95% interval's upper over lower rate, averaged over cells.

| | Men, A | Men, B | Women, A | Women, B |
| --- | --- | --- | --- | --- |
| Q1, deviance against B0 | Pass (3,296 against 6,450) | Pass (2,687 against 4,605) | Pass (2,463 against 5,822) | Pass (3,169 against 5,238) |
| **Q2, coverage** | **Fail, 98.3% (118)** | **Fail, 99.2% (119)** | **Fail, 100% (120)** | **Fail, 99.2% (119)** |
| Mean interval width | 1.51 | 1.56 | 1.65 | 1.75 |
| Q3, annuity error at 65 | Pass (0.36%) | Pass (0.71%) | Pass (1.43%) | Pass (0.90%) |
| Q4, the anchor lowers deviance (reported only) | Pass | Pass | Pass | Pass |

## Coverage and width, every candidate

| | Men, A | | Men, B | | Women, A | | Women, B | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | Coverage | Width | Coverage | Width | Coverage | Width | Coverage | Width |
| **v1.3** | 98.3% (118) | 1.51 | 99.2% (119) | 1.56 | 100% (120) | 1.65 | 99.2% (119) | 1.75 |
| v1.2 (A as published, B rescored) | 93.3% | n/a | **91.7% (110)** | 1.27 | 75.8% | n/a | **93.3% (112)** | 1.29 |
| CBD post-peak alone (the women's fallback) | 98.3% (118) | 1.51 | 99.2% (119) | 1.56 | 100% (120) | 1.96 | 100% (120) | 2.13 |
| Smoothed RH alone | 90.8% (109) | 1.37 | 94.2% (113) | 1.47 | 98.3% (118) | 1.56 | 98.3% (118) | 1.63 |
| LC post-peak alone | 80.8% (97) | 1.38 | 87.5% (105) | 1.43 | 94.2% (113) | 1.52 | 95.0% (114) | 1.60 |
| Inverse-deviance average (sensitivity) | 100% (120) | 1.52 | 99.2% (119) | 1.59 | 100% (120) | 1.78 | 100% (120) | 1.93 |

v1.2's widths at origin A were not computed in v1.2's run.

## Every model's other scores

| | Men, A | | Men, B | | Women, A | | Women, B | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | Deviance | Error | Deviance | Error | Deviance | Error | Deviance | Error |
| B0 | 6,450 | | 4,605 | | 5,822 | | 5,238 | |
| **v1.3** | 3,296 | 0.36% | 2,687 | 0.71% | 2,463 | 1.43% | 3,169 | 0.90% |
| v1.2 | 1,529 | 1.66% | 1,361 | 1.35% | 1,901 | 1.87% | 1,402 | 0.98% |
| CBD | 3,296 | 0.36% | 2,687 | 0.71% | 2,582 | 0.67% | 4,329 | 0.43% |
| Smoothed RH | 3,516 | 2.46% | 3,784 | 1.13% | 2,666 | 1.55% | 3,397 | 0.93% |
| LC | 5,396 | 2.63% | 4,514 | 1.14% | 4,477 | 0.84% | 4,383 | 0.64% |
| Inverse average | 2,722 | 1.31% | 2,014 | 0.81% | 2,167 | 0.84% | 2,770 | 0.56% |

**v1.2 at origin B** passes Q1 to Q3 for both sexes: men 110 cells, error 1.35%; women 112 cells, error 0.98%. With origin A, men's v1.2 passes at both origins and women's fails at A (75.8%). Neither can price, because v1.2 fails the gate.

## Design weights (with the smoothed RH)

| | LC | CBD | RH, smoothed |
| --- | --- | --- | --- |
| Anchored design deviance, men | 8,773 | 3,517 | 5,768 (v1.2's RH: 1,458) |
| Anchored design deviance, women | 7,880 | 4,520 | 4,335 (v1.2's RH: 2,494) |
| Weight, men | 0% | **100%** | 0% |
| Weight, women | 0% | 12.5% | 87.5% |
| Inverse-deviance weight, men | 19.9% | 49.7% | 30.3% |
| Inverse-deviance weight, women | 21.9% | 38.2% | 39.9% |

## The plausibility gate

Each version's own production run: price at 65 (4%, annuitant factor 0.7) and median e65.

| Version | Men's price | Women's price | Women above men | e65 rise 2020 to 2030, men | Women | Passes |
| --- | --- | --- | --- | --- | --- | --- |
| **v1.3** | 11.18 | 13.12 | Yes | **−0.02** | **0.14** | **No** |
| v1.2 | 13.24 | 13.18 | **No** | 0.73 | **−0.15** | No |
| CBD fallback | 11.16 | 13.54 | Yes | **−0.06** | 0.86 | No |
| v1 | 13.53 | 16.05 | Yes | 0.80 | 1.40 | Yes |

**Pricing set:** men on v1 and women on v1, both with ranges marked as lower bounds. Checked as a set, it passes the gate: women's price (16.05) is above men's (13.53), and e65 rises for each sex (0.80 and 1.40).

## Convergence

Every main fit converged and passed the protocol's checks: design, both origins, and production, for both sexes. Iterations ran from 160 to 673. The two starts agreed to within 1.1 × 10⁻⁷, and the smoothed deviance was above the unsmoothed one in every case. No smoothed RH refit failed to converge (0 of 500 at each origin for each sex, and 0 of 438 in women's production). Men's v1.3 production has no RH refits, because RH has no weight.

## Prices (4%, annuitant factor 0.7, median and 95% interval)

Shown for the record. None of these goes on the site.

| | 55 | 65 | 75 |
| --- | --- | --- | --- |
| Men, v1.3 | 14.40 (13.56 to 15.32) | 11.18 (10.21 to 12.29) | 8.16 (7.08 to 9.39) |
| Women, v1.3 | 15.98 (15.22 to 17.18) | 13.12 (12.63 to 14.23) | 9.74 (9.34 to 11.12) |
| Men, v1 (on the site) | | 13.53 (13.11 to 14.03) | |
| Women, v1 (on the site) | | 16.05 (15.36 to 16.70) | |
| Sensitivity, registered deaths: men; women | 15.27; 16.29 | 12.05; 13.45 | 8.91; 10.12 |
| Sensitivity, inverse weights: men; women | 14.57; 16.41 | 11.68; 13.33 | 9.03; 9.89 |

**Paths left out of the Kannisto tail.** For men's v1.3, which is CBD, 564 of 5,000 at 55 (11%), 209 at 65 and 53 at 75. CBD's logit trend reaches rates of 1 at ages 80 to 89 on long horizons. For women's v1.3: 1 at 55, none at 65 or 75.

## Life expectancy at 65, forecast median and 95% interval

| | 2020 | 2030 | 2050 |
| --- | --- | --- | --- |
| Men, v1.3 | 13.94 (13.3 to 14.7) | 13.93 (12.1 to 16.0) | 13.89 (11.4 to 17.0) |
| Women, v1.3 | 16.73 (16.5 to 17.5) | 16.87 (16.3 to 19.1) | 17.52 (15.6 to 21.6) |
| Men, v1.2 | 14.38 | 15.11 | 18.08 |
| Women, v1.2 | 16.88 | 16.73 | 17.34 |

Observed in 2019, on scaled deaths: men 14.00, women 16.80.

## The cohort term, before and after smoothing (production fits)

| | AR coefficient of Δγ | γ, 1929, 1930, 1931 | γ, 1939, 1940, 1941 | Jump-off move in e65 (largest age) |
| --- | --- | --- | --- | --- |
| Men, v1.2 | 0.03 | −0.10, +0.01, −0.16 | +0.08, +0.20, +0.10 | 0.168 (age 89: 0.145) |
| Men, smoothed | 0.67 | −0.05, −0.08, −0.10 | +0.07, +0.06, +0.06 | 0.001 |
| Women, v1.2 | 0.01 | −0.01, +0.14, −0.11 | −0.13, +0.06, −0.08 | 0.249 (age 89: 0.159) |
| Women, smoothed | 0.38 | +0.01, −0.04, −0.07 | −0.09, −0.08, −0.07 | 0.040 |

As the plan warned, smoothing raised the AR coefficient (0.03 to 0.67 for men, 0.01 to 0.38 for women). The heaped spikes are gone. The full γ series by birth year is in `v13.json`.

## What it shows

- The smoothing did what it was built to do (it removed the heaping spikes and the jump-off), but it cost the cohort term most of its fit. RH's low φ in v1.1 and v1.2 was partly heaping noise absorbed into γ, and partly real cohort structure. Smoothing returned both to the residuals. For women on the full window, the in-sample deviance rose ninefold. This is consistent with the pre-freeze recovery test, where smoothing absorbed part of a real cohort effect.
- Once the cohort term was weakened, no candidate in the pricing chain gave intervals inside 90% to 98% at both origins and also passed the gate. Inside the bounds at both origins were v1.2 (both sexes at B; men also at A), the smoothed RH alone for men, and LC alone for women. v1.2 fails the gate, and neither single model was a candidate, so nothing is chosen on them.
- Men's v1.3 is CBD, whose forecast of e65 is flat for 30 years. That is the HIV-era rise and fall in the post-peak window seen through a model with no cohort term. The gate was set to catch exactly this.
- **Final mortality model: v1, for both sexes, with ranges marked as lower bounds.** The v1.1 to v1.3 revisions are published as they came out. None of them prices anything.
