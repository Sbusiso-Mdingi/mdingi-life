# Results: v4 Scenarios and reporting

Run on 26 October 2026 under `PROTOCOL_v4.md`, frozen at `fedf29aeeebc`, with one amendment (two factors a curve, written before anything was projected; see the protocol's "Changes after freezing"). Valuation date 25 September 2026, on v3's balance sheet with the key-rate matched assets of v3's amendment and R400 million of own funds.

Raw output: `research/results/projection_v4.json`. Built by `research/scenarios_v4.py` and `research/projection_v4.py`, using `mdingilife/esg.py` and `mdingilife/ifrs17.py` with v3's standard formula.

## The answer

**Mdingi Life is not covered with the confidence its board asked for.** On the central path its cover climbs from 1.15 to 1.72 in five years, as the business earns more than the capital it ties up. But in 399 of the 1,000 scenarios cover falls below 1.0 at some year-end, most often in the first two years. Only 60.1% stay covered throughout, against the 95% set beforehand, so **A1 fails**.

Under the named stresses, **A2 fails for three of five.** A rates fall takes cover to 0.68 at once, and it recovers to 1.10 by the second year-end. Pensioners living longer (S2) is the one the company cannot ride out: cover falls to 0.21, the CSM is used up, and R349 million of new capital would be needed. A pandemic year and a lapse wave are absorbed.

Under IFRS 17 the company reports R37 to R53 million of profit a year on the central path, most of it the finance result: investment return on own funds as well as on the assets behind the BEL. The CSM at transition is R83.6 million and grows over the five years, because accretion at the locked-in rates exceeds the release over the annuities' long coverage period.

The reason A1 fails is the one v3 left open. Key-rate matching hedges the BEL, but not the risk margin or the SCR, which both rise when rates fall. With cover at 1.15 there is little room for that.

## The scenario generator

Two factors a curve under the amendment: level and slope, fixed decay τ chosen on the grid, four AR(1)s at a monthly step.

| | Nominal | Real |
| --- | --- | --- |
| Month-ends fitted (2011 to September 2026) | 189 | 178 |
| τ (years) | 4.5 | 0.5, the end of the grid |
| φ, level and slope (monthly) | 0.860, 0.741 | 0.969, 0.859 |
| Innovation SD, level and slope (points a month) | 1.47, 3.40 | 0.31, 3.70 |
| Correlation of level and slope innovations | −0.97 | −0.75 |
| Jump-off level and slope | 10.2%, −3.0% | 4.3%, −3.3% |
| Long-run mean level and slope | 12.6%, −7.7% | 3.9%, −8.6% |

No φ hit the 0.995 cap. The nominal and real levels' innovations are almost uncorrelated (0.10). The level and slope of each kind move against each other: with only 7- to 30-year bonds in the windows, they trade off at the short end.

The 10-year zero rate (annual compounding) across the scenarios:

| | Today | Central, year 5 | 5th to 95th percentile, year 5 |
| --- | --- | --- | --- |
| Nominal | 9.4% | 9.9% | 7.6% to 12.3% |
| Real | 4.3% | 3.7% | 1.8% to 5.5% |

Realised inflation (the one-year breakeven at each year's start) is 4.8% in year 1, then a median of 4.6% to 5.9% a year, with 90% ranges of about 0% to 12%.

- **E1 passes.** The SD of the first year's change in the 10-year rate is 1.32 times history for nominal (1.21 points against 0.92) and 1.16 for real (0.68 against 0.59), both inside 0.75 to 1.33. Nominal is close to the upper bound.
- **E2, context.** The 0.5% quantile of that first-year change is −2.79 points nominal and −2.27 real. SAM's 10-year down shocks at today's rates are −2.58 and −2.37 points. At 10 years the generator's 1-in-200 is as severe as the standard formula's.

## Cover across the scenarios

| Year-end | Central | 5th | 25th | Median | 75th | 95th | Below 1.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026 (t = 0) | 1.15 | 1.15 | 1.15 | 1.15 | 1.15 | 1.15 | 0% |
| 2027 | 1.23 | 0.79 | 1.03 | 1.18 | 1.34 | 1.54 | 22.2% |
| 2028 | 1.35 | 0.80 | 1.08 | 1.29 | 1.52 | 1.80 | 20.1% |
| 2029 | 1.47 | 0.81 | 1.19 | 1.43 | 1.67 | 1.99 | 13.0% |
| 2030 | 1.60 | 0.89 | 1.29 | 1.56 | 1.82 | 2.14 | 8.3% |
| 2031 | 1.72 | 1.00 | 1.39 | 1.66 | 1.93 | 2.37 | 5.0% |

- **A1 fails: 60.1% of scenarios are covered at every year-end, against 95%.** 39.9% fall below 1.0 at least once. The lowest cover in any scenario at any year-end is 0.35.
- The median is a little below the central path from the first year-end (1.18 against 1.23).
- **The central path.** Own funds grow from R400.0 million to R628.1 million and the SCR from R348.2 million to R364.7 million. The annuities run off from 5,000 lives to 4,192 and the funeral book from 50,000 policies to 33,448. Longevity's charge rises from R282.5 million to R299.6 million as the annuitants age.

## Named stresses

| Stress | t = 0 | 2027 | 2028 | 2029 | 2030 | 2031 | Capital to restore 1.0 | A2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 Rates fall | 0.68 | 0.92 | 1.10 | 1.26 | 1.42 | 1.57 | R149.2m | Fail |
| S2 Longevity | 0.21 | 0.27 | 0.31 | 0.36 | 0.41 | 0.47 | R349.0m | Fail |
| S3 Pandemic year | 1.15 | 1.34 | 1.46 | 1.58 | 1.72 | 1.85 | nil | Pass |
| S4 Lapse wave | 1.15 | 1.23 | 1.35 | 1.46 | 1.59 | 1.71 | nil | Pass |
| S5 All at once | 0.67 | 1.02 | 1.20 | 1.37 | 1.54 | 1.69 | R152.3m | Fail |

The worst year-end is t = 0 in every stress, as each is recognised at once.

- **S1** goes through finance, so the CSM is untouched. Cover drops because the risk margin and SCR rise, and comes back as rates revert along the model.
- **S2** raises the annuity fulfilment cash flows by R308.1 million. The CSM absorbs R75.4 million and the remaining R232.8 million is a loss. The funeral CSM (R8.2 million) is all that is left. This is the largest risk in v3 too, at a larger size: the protocol's 20% permanent fall in annuitant mortality is harsher than SAM's 10%.
- **S3**: the 2021 to 2019 crude death-rate ratios, ages 18 to 89, are 1.348 for women and 1.246 for men. A pandemic year is a gain for an annuity book. The year-1 future-service change of −R32.8 million on the annuities raises the CSM, and the funeral experience variance (−R2.5 million) is small.
- **S4** raises the fulfilment cash flows by R10.2 million on the funeral line and R2.5 million on the annuities. The CSM absorbs R10.8 million, and the funeral group, whose CSM was R8.3 million, becomes onerous with a R1.9 million loss.
- **S5** is S1's capital hit, with S3's CSM gain on top.

## IFRS 17

- **Transition (fair value approach).** The risk adjustment equals the risk margin, R125.5 million: R113.0 million annuities and R12.4 million funeral. Read as a quantile, against the reference insurer's 1-in-200 SCR as if it were a normal 99.5% point, it is about an 85% confidence level (84.7%). The CSM at a 10% fair-value cost of capital is R75.4 million for annuities and R8.3 million for funeral, R83.6 million in all.
- **Central path, 10% cost of capital (R million):**

| Year | Profit | Insurance service result | Finance result | CSM at year-end |
| --- | --- | --- | --- | --- |
| 2027 | 37.3 | 6.2 | 31.1 | 86.3 |
| 2028 | 37.8 | 6.7 | 31.1 | 88.9 |
| 2029 | 43.1 | 4.9 | 38.2 | 91.6 |
| 2030 | 44.1 | 5.3 | 38.8 | 94.2 |
| 2031 | 52.5 | 5.7 | 46.8 | 96.8 |

- **The annuity CSM grows.** In year 1 it accretes R6.7 million at the locked-in rate and releases R4.1 million over coverage units, the expected annuity payments of this year over all remaining years. The release is slow because most of the cover lies beyond five years. The annuity RA release turns slightly negative from year 3 (−R0.9 million): the reference SCR rises as longevity risk grows with age, faster than the book runs off.
- **Profit across the scenarios** (the change in own funds less the CSM, which no scenario changes, since only financial variables move): a median of R29 to R52 million a year, with 90% ranges of −R44 million to R74 million in year 1 and −R26 million to R112 million in year 5.
- **Cost-of-capital sensitivity.** At 8% the transition CSM is R41.8 million, at 12% R125.5 million. Profit moves little, R38.6 and R35.9 million in year 1: a larger CSM holds back more of the growth in own funds, as accretion, and releases more as service result.

## Checks

| Check | Result | |
| --- | --- | --- |
| R1, the roll-forward is right | Worst 3.6e-14 relative, against 1e-8 | Pass |
| R2, the books tie | Worst 7.9e-16 relative, against 1e-6 | Pass |
| E1, scenarios move like history | Nominal 1.32, real 1.16, against 0.75 to 1.33 | Pass |
| E2, context | −2.79 and −2.27 points, against SAM's −2.58 and −2.37 | Not a test |
| A1, appetite in the scenarios | 60.1% covered throughout, against 95% | Fail |
| A2, appetite under stress | S3 and S4 pass; S1, S2 and S5 fail | Fail |

## Sensitivities

| | Covered throughout (A1) | Below 1.0 at some year-end | Median cover, 2031 | 5th percentile, 2031 |
| --- | --- | --- | --- | --- |
| Main | 60.1% | 39.9% | 1.66 | 1.00 |
| Calibrated without March to May 2020 | 81.3% | 18.7% | 1.75 | 1.20 |
| No rematching | 56.6% | 43.4% | 1.53 | 0.91 |

- **Without the COVID months**, τ for real rates is 1.0 rather than 0.5, real level persistence rises (φ 0.986), and E1 is 1.28 nominal and 0.84 real. Leaving out three months of 2020 roughly halves the share of scenarios that fall below 1.0. A1 still fails.
- **Holding the t = 0 portfolio**, with coupons and redemptions into the bill, leaves cover lower on the central path too (1.56 rather than 1.72 in 2031) and more scenarios below 1.0. Rematching each year is worth keeping.

## The frozen three-factor generator, as reported

Calibrated and run exactly as frozen, on the same seed: τ 1.5 nominal and 3.5 real, E1 0.96 nominal and **1.62 real (fail)**. Its 0.5% quantile of the first-year change in the 10-year rate is −5.99 points nominal and −3.76 real, about twice SAM's shocks. Across its 1,000 scenarios only 15.0% stay covered throughout. The 5th percentile of cover falls below zero from 2030, and the lowest cover is −5.6. These are artefacts of the factor swings the amendment describes, not plausible rate paths. They are reported so the frozen method is not lost.

## How the run went

- **A trial run, disclosed.** After the amendment and before the full run, the projection was run on 16 scenarios to test the code. It showed that the longevity shock was compounding with the projection year: each year-end shifted t = 0's already-stressed rates forward instead of stressing that year-end's own rates, so the higher improvement ran from t = 0 rather than from the year after the year-end, and the longevity charge reached R377 million by year 3 instead of about R283 million. The stressed rows are now rebuilt at each year-end from the base table, starting at that year-end, which reproduces v3's t = 0 rows exactly. This was a code error, not a method change, and no setting was tuned on the trial's results. The full run then used the frozen seed and 1,000 scenarios.
- **The history in the dashboard** is the September month-end 10-year rate from the Nelson-Siegel fits. Its September 2026 value (9.6% nominal) differs slightly from the t = 0 rate on the valuation curve (9.4%), which every scenario starts from.

## What it points to

The company's risk is now mostly longevity and the parts of the balance sheet the hedge does not reach. Two steps follow, neither modelled here: reinsuring part of the longevity risk, which shrinks both the SCR and the risk margin, and hedging the risk margin's and SCR's rate sensitivity alongside the BEL's. Either would also need its own frozen plan.
