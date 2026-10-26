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

**The two runs disagree by more than either interval allows.** At 65, the Stats SA price is about 23% above the WPP price, while each run's 95% interval is 7% to 15% wide. The two intervals do not overlap at any age. Most of that gap is the choice of model and window, not the deaths data; see the [decomposition](#decomposition-exploratory). Across discount rates and annuitant factors, the width at 65 is 4.8% to 10.3% for men and 5.3% to 13.3% for women, narrower than on WPP, but these are lower bounds (P3).

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

**Registration drift explains only a small part of the gap**: between a tenth (at 65) and a third (men at 55). The rest comes from what still differs between the runs: model and window, jump-off, and the age pattern of registered deaths. They are separated below.

## Exposure cross-check

WPP 1 July population at ages 50 to 79 over Stats SA's own projection (P0302 workbook, 2002 to 2025, five-year groups):

| | 2002 | 2010 | 2016 | 2019 | 2020 | 2022 |
| --- | --- | --- | --- | --- | --- | --- |
| Men | 0.885 | 0.885 | 0.902 | 0.965 | 0.993 | 1.036 |
| Women | 0.927 | 0.922 | 0.939 | 0.972 | 0.983 | 1.004 |

Until 2016, WPP puts 6% to 12% fewer people aged 50 to 79 than Stats SA does, so rates on WPP exposure are higher. From 2016 to 2019 WPP's population grows about 7% faster for men and 3.5% faster for women, which would make rates on WPP exposure fall faster than on Stats SA's. This is a second drift, in the denominator, of the same size as the completeness drift and in the same direction. It is reported, not corrected: the protocol has no Stats SA single-age exposure to correct it with.

## Decomposition (exploratory)

**Outside the protocol**, added after the results above were known and labelled as such. Two extra WPP runs (`annuities.py --model ... --last-year 2019 --tag ...`) fill the steps between the two pre-registered runs, so each row changes one thing from the row above. Price at 4% and factor 0.7, gap against the WPP run:

| Step | Men 55 | Men 65 | Men 75 | Women 55 | Women 65 | Women 75 |
| --- | --- | --- | --- | --- | --- | --- |
| WPP deaths, CBD full, jump-off 2023 (pre-registered) | 14.04 | 11.04 | 8.14 | 16.03 | 13.02 | 9.84 |
| Same, jump-off 2019 | +4.2% | +7.9% | +13.0% | +5.0% | +8.2% | +13.0% |
| Same, RH post-peak | +8.1% | +27.1% | +37.0% | +6.0% | +18.5% | +41.5% |
| Registered deaths, scaled to WPP's level (pre-registered) | +11.8% | +19.9% | +14.9% | +14.3% | +20.7% | +20.5% |
| Registered deaths, as registered (pre-registered) | +17.6% | +22.6% | +18.6% | +17.9% | +23.3% | +24.9% |

- **Jump-off.** Ending the WPP fit in 2019 instead of 2023 raises prices 4% to 13%: in WPP, life expectancy at 65 in 2023 is still below 2019 (13.2 against 13.8 years for men, 16.3 against 16.9 for women), so a fit that includes 2023 starts from heavier mortality and improves more slowly.
- **Model and window.** On the same WPP deaths, RH from 2006 prices the annuity at 65 about 18% (men) and 10% (women) above CBD from 1997, and at 75 by more. RH's own 95% intervals are 4% to 18% wide and do not contain the CBD price at 65 or 75. This is model risk: the intervals carry parameter and process uncertainty within one model, not the choice between models.
- **Deaths data.** With the model fixed at RH post-peak, swapping WPP's deaths for registered ones scaled to WPP's level raises the price at 55 (3% for men, 8% for women), lowers it at 75 (16% and 15%), and at 65 lowers it 6% for men and raises it 2% for women. Registration drift then adds 2% to 5%.

So the 23% headline gap at 65 is mostly model choice and jump-off. The pre-registered rule picks RH on Stats SA data and CBD on WPP, and that choice alone is worth more than any single interval's width.

## Rolling origins (robustness check)

From the protocol amendment of 26 October 2026, written before any rolling fit (`research/rolling.py`). Jump-offs 2009 to 2016, each scored on the three years after it; ten candidates: LC, CBD and RH fitted from 1997, from 2006 and on a rolling 10-year window, plus B0. Deviance summed over the eight jump-offs; "best of 8" counts the jump-offs where a candidate has the lowest deviance of the ten. Nothing above changes.

**Stats SA registered deaths**

| Candidate | Deviance, men | Best of 8, men | Coverage, men | Deviance, women | Best of 8, women | Coverage, women |
| --- | --- | --- | --- | --- | --- | --- |
| RH post-peak (chosen) | 16,353 | 3 | 53% | 27,821 | 1 | 63% |
| RH rolling | 25,159 | 2 | 55% | 20,479 | 5 | 55% |
| RH full | 26,868 | 2 | 50% | 23,930 | 2 | 64% |
| CBD post-peak | 24,907 | 1 | 49% | 34,779 | 0 | 47% |
| CBD rolling | 33,001 | 0 | 58% | 42,910 | 0 | 57% |
| CBD full | 44,463 | 0 | 65% | 51,251 | 0 | 63% |
| LC post-peak | 43,755 | 0 | 21% | 53,849 | 0 | 29% |
| LC rolling | 51,158 | 0 | 28% | 58,821 | 0 | 37% |
| LC full | 57,144 | 0 | 34% | 72,343 | 0 | 33% |
| B0 | 49,446 | 0 | n/a | 49,326 | 0 | n/a |

- **R1** passes for men (RH post-peak is lowest) and fails for women (RH on a rolling 10-year window is lowest, RH post-peak third). **R2** fails for both: 53% and 63% coverage.
- **The model holds; the window does not.** RH, on some window, is best at 7 of 8 jump-offs for men and all 8 for women. Which window wins moves with the jump-off.
- No improvement (B0) beats every Lee-Carter variant on registered deaths for both sexes. No candidate's 95% bands reach 90% coverage, so P3's failure is not a one-off.

**UN WPP 2024 deaths.** The single split chose CBD full for both sexes. Over eight jump-offs it ranks 7th of 10 for men (17,399) and 9th for women (27,842); LC post-peak is lowest for both (12,902 and 12,478) and best at 3 of 8. R1 and R2 fail for both sexes. On WPP the pre-registered choice was largely the luck of one block.

**Repricing.** A life aged 65 in the year after each jump-off, 4%, factor 0.7, median of 5,000 process-only paths, each model at its protocol window:

| Jump-off | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2019 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Men, B0 | 11.34 | 11.39 | 11.40 | 11.48 | 11.51 | 11.54 | 11.56 | 11.57 | 11.89 |
| Men, LC post-peak | none | none | 11.74 | 11.99 | 11.86 | 11.68 | 11.72 | 11.82 | 12.80 |
| Men, CBD post-peak | 11.09 | 11.70 | 11.41 | 11.58 | 11.75 | 11.56 | 11.59 | 11.55 | 11.85 |
| Men, RH post-peak | none | none | none | none | none | none | 11.66 | 11.46 | 12.42 |
| Women, B0 | 12.72 | 12.84 | 12.89 | 13.00 | 13.04 | 13.07 | 13.07 | 13.09 | 13.31 |
| Women, LC post-peak | none | none | 15.22 | 15.59 | 15.03 | 14.29 | 14.17 | 14.20 | 14.86 |
| Women, CBD post-peak | 13.41 | 14.36 | 13.63 | 13.94 | 14.00 | 13.69 | 13.69 | 13.75 | 13.94 |
| Women, RH post-peak | none | none | none | none | none | none | 13.53 | 13.70 | 14.90 |

- **"None"** is a quote with no price. Fitted on four to nine years from 2006, LC's and RH's loading on the oldest ages comes out negative (b(89) = −0.60 for LC on men's 2006 to 2009, against +0.03 on 2006 to 2019). Rates at 80 to 89 then rise as the rest improve, and on most paths pass 1 before the life reaches 89, where the Kannisto tail cannot be fitted. The share of failed paths falls from 100% to 9% (men's RH at 2013) and 0.3% (women's RH at 2013); any failed path drops the quote, as below.
- Every model's quote jumps from 2016 to 2019: +8% to +9% for RH, +5% to +8% for LC, +1% to +3% for B0 and CBD. Those are the years the WPP population catches up with Stats SA's (see the exposure cross-check), so part of the production price's level comes from the last three years of exposure.
- On WPP the four quotes stay within 10.6 to 12.0 for men and 12.5 to 14.2 for women across 2009 to 2023.

**Blended price.** LC, CBD and RH at their protocol windows, weighted 1 / summed rolling deviance, production paths pooled. At 4% and factor 0.7:

| | Weights (LC, CBD, RH) | 55 | 65 | 75 |
| --- | --- | --- | --- | --- |
| Stats SA men, blend | 18%, 32%, 49% | 15.82 [14.88, 17.50] | 13.11 [11.67, 13.94] | 9.58 [8.49, 11.44] |
| Stats SA men, chosen RH | | 16.51 [15.28, 17.68] | 13.53 [13.11, 14.03] | 9.65 [9.29, 10.12] |
| Stats SA women, blend | 22%, 35%, 43% | 18.11 [16.86, 19.88] | 15.40 [13.76, 16.62] | 12.11 [10.40, 13.15] |
| Stats SA women, chosen RH | | 18.89 [17.42, 20.10] | 16.05 [15.36, 16.70] | 12.29 [11.48, 13.13] |
| WPP men, blend | 41%, 30%, 29% | 14.27 [13.55, 14.63] | 11.30 [10.51, 11.71] | 8.73 [7.57, 9.24] |
| WPP men, chosen CBD | | 14.04 [13.38, 14.83] | 11.04 [10.32, 11.91] | 8.14 [7.39, 9.04] |
| WPP women, blend | 46%, 21%, 33% | 16.17 [15.39, 16.82] | 13.25 [12.50, 13.90] | 10.15 [9.28, 10.90] |
| WPP women, chosen CBD | | 16.03 [15.24, 16.87] | 13.02 [12.15, 14.01] | 9.84 [8.95, 10.90] |

- On Stats SA deaths the blend prices the annuity at 65 3% (men) and 4% (women) below the chosen model. Its interval is 17% and 19% wide against 7% and 8%: pooling the models puts some of the model risk back into the interval.
- On WPP the blend is 2% above CBD at 65, and its interval is narrower (11% against 14%). Pooling does not always widen the interval.
- Even the Stats SA blend's interval does not reach the WPP price at 65 (11.04 and 13.02). The data source and the old-age exposure still move the price beyond what pooling these three models captures.

Fits that did not converge in 20,000 iterations, kept as they ended: RH post-peak, women, Stats SA, jump-offs 2009 and 2010; RH rolling, women, WPP, 2011 and 2016.

## Still to do

- Rerun on Stats SA single-age mid-year estimates if SuperWEB comes back, as the protocol first intended.
- v2: replace the flat discount rate with the fitted government bond curve.
