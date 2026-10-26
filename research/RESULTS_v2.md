# Results: v2 Assets

Run on 26 October 2026 under `PROTOCOL_v2.md` and its four amendments. Data: National Treasury's weekly auction results, April 2010 to September 2026, 4,610 usable clearing yields. Source: National Treasury, Republic of South Africa, investor.treasury.gov.za, used for non-commercial purposes with acknowledgement.

Raw output: `research/results/curves_design.json`, `curves_validation.json` (with their `_predictions.csv`) and `annuities_v2.json`. Built by `research/treasury.py`, `curves.py` and `annuities_v2.py`.

## What was seen before the choice

Disclosed in the protocol's amendments, in the order they happened:

1. **28-day window** (`curves_design_28.json`). Too few bonds per window: NSS could be fitted on half the fixed-rate days and 1% of the inflation-linked days. The window became 91 days, and NSS was dropped for inflation-linked bonds.
2. **91 days on misparsed yields** (`curves_design_91_misparsed.json`). Most 2012–16 workbooks store yields as percentage cells, which were read as 0.0887 for 8.87%; about 945 yields were 100 times too small. Its scores (fixed-rate RMSE 52 to 88bp) measured the parse, not the curves. The parser was fixed and the design run repeated.
3. **The corrected design run** chose LI for both kinds. LI is not a zero curve, so a zero curve through the same bonds was set out before validation (amendment 4).

## Design period (April 2010 to December 2017), RMSE in basis points

| | n | LI | NS | NSS | B0 |
| --- | --- | --- | --- | --- | --- |
| Fixed-rate, curves only | 1,041 | **27.9** | 28.9 | 30.3 | |
| Fixed-rate, with B0 | 993 | 27.4 | 26.7 | 27.4 | 27.7 |
| Inflation-linked, curves only | 891 | **11.2** | 13.6 | | |
| Inflation-linked, with B0 | 875 | 11.0 | 13.1 | | 11.1 |

The choice is made on the first row of each kind, which has more auctions. Nine yields were screened out by the 100bp rule across the whole sample.

## Validation (January 2018 to September 2026, run once)

| | n | LI (chosen) | NS | NSS | B0 |
| --- | --- | --- | --- | --- | --- |
| Fixed-rate | 1,245 | 35.4 | 32.9 | 33.3 | 36.0 |
| Fixed-rate, without March to May 2020 | 1,212 | 28.9 | 26.5 | 26.6 | 29.5 |
| Inflation-linked | 1,150 | 23.0 | 21.2 | | 23.2 |
| Inflation-linked, without March to May 2020 | 1,119 | 18.2 | 17.3 | | 18.3 |

On all the auctions the chosen curve could price (fixed-rate n = 1,282, inflation-linked n = 1,172), LI scores 38.2 and 23.5. The 182-day sensitivity changes little: fixed-rate LI 35.7, NS 34.6, NSS 34.0; inflation-linked LI 23.5, NS 21.2.

| Test | Fixed-rate | Inflation-linked |
| --- | --- | --- |
| C1, the curve beats B0 | **Pass**, 35.4 against 36.0 | **Pass**, 23.0 against 23.2 |
| C2, NSS beats NS | **Fail**, 63.6 against 56.4 | not tested |
| C3, RMSE under 25bp | **Fail**, 38.2 | **Pass**, 23.5 |

- **The curve adds little over each bond's own last yield.** C1 passes by under 1bp on both kinds. Treasury auctions the same few bonds week after week, so most bonds' last yields are recent and a curve has little to add.
- **NS would have done slightly better out of sample**, by 2 to 2.5bp, and by more with Covid in (NS 32.9 against LI 35.4 on the common set). The design period preferred LI; the choice stands as made. NS's RMSE on its own auctions (56.4) is inflated by a few large misses; its mean absolute error is the lowest of the three.
- **Covid.** March to May 2020 adds 6 to 9bp to the fixed-rate RMSE and about 5bp to the inflation-linked RMSE.

## The curves on the valuation date

Inflation-linked: 25 September 2026, the latest inflation-linked auction. Fixed-rate: 22 September 2026, the closest fixed-rate auction before it. Each is fitted on the 91 days up to and including that day.

| Real forwards (%) | 1y | 5y | 10y | 15y | 20y | 25y | 30y | 40y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LI zero curve | 3.88 | 4.21 | 4.56 | 3.99 | 4.27 | 4.09 | 3.55 | 3.55 |
| NS | 3.31 | 4.40 | 4.46 | 4.23 | 4.03 | 3.91 | 3.84 | 3.83 |

| Nominal forwards (%) | 1y | 5y | 10y | 15y | 20y | 25y | 30y | 40y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LI zero curve | 8.56 | 8.56 | 9.87 | 6.15 | 12.45 | 12.45 | 12.45 | 12.45 |
| NS | 7.87 | 8.98 | 9.83 | 10.32 | 10.55 | 10.55 | 10.55 | 10.55 |

Seven inflation-linked bonds (I2031 to I2058, 4 to 31 years, real yields 3.9% to 4.3%) and seven fixed-rate bonds (R2033 to R2044, 6.5 to 18 years, 8.75% to 9.44%) are in the windows. The bootstrap reprices every one exactly.

The nominal LI forwards show the weakness the amendment named: R2042 (9.21%) and R2044 (9.39%) mature less than three years apart, and R2044 is repaid in three instalments from 2043 to 2045. The last segment carries a 12.45% forward, which is then held flat beyond 18 years. NS gives 10.55% there. The real curve's longest bond is 31 years, and its forwards stay between 3.5% and 4.6%.

## Annuity prices

Per 1 a year paid monthly in advance, from the Stats SA run's production mortality (RH post-peak for both sexes, jump-off 2019), annuitant adjustment 0.7. Medians with 95% intervals, which carry mortality uncertainty only. The flat columns are v1's prices: the flat 4% reproduces `annuities_statssa.json` to within 1e-14.

| | Flat 2% | Flat 4% | Flat 6% | Inflation-linked, real curve | Implied flat rate | Level, nominal curve | Implied flat rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Men 55 | 21.96 | 16.51 | 13.07 | 16.08 (14.89 to 17.22) | 4.21% | 9.23 (8.91 to 9.48) | 9.85% |
| Men 65 | 17.01 | 13.53 | 11.17 | 13.22 (12.81 to 13.71) | 4.23% | 8.39 (8.26 to 8.52) | 9.69% |
| Men 75 | 11.43 | 9.65 | 8.33 | 9.48 (9.14 to 9.93) | 4.23% | 6.72 (6.60 to 6.84) | 9.50% |
| Women 55 | 26.93 | 18.89 | 14.35 | 18.43 (16.99 to 19.62) | 4.16% | 9.65 (9.37 to 9.85) | 9.95% |
| Women 65 | 21.61 | 16.05 | 12.66 | 15.67 (14.99 to 16.30) | 4.19% | 8.96 (8.85 to 9.07) | 9.84% |
| Women 75 | 15.49 | 12.29 | 10.15 | 12.02 (11.24 to 12.83) | 4.21% | 7.67 (7.49 to 7.86) | 9.70% |

- **v1's flat 4% real rate was close to the market.** The real curve is worth a flat 4.16% to 4.23%, and it prices inflation-linked annuities 2% to 2.5% below v1's 4% prices. The mortality interval (about ±4% at 65) is wider than that difference.
- **A level annuity costs about 55% to 65% of an inflation-linked one**, at nominal yields near 9.5% to 10%.
- **On NS** (all adjustments in `annuities_v2.json`), inflation-linked prices move by under 0.7%, and level prices rise 0.7% to 1.9% (0.6% to 2.0% across all adjustments), mostly because NS's long nominal forward is lower than the bootstrap's 12.45%.

## Matching the inflation-linked annuity at 65

On the real LI zero curve, adjustment 0.7. DV01 is the value lost for a 1bp rise, per R10,000 a year of annuity income.

| | Men | Women |
| --- | --- | --- |
| Value per 1 a year | 13.23 | 15.66 |
| Effective duration (years) | 10.7 | 13.6 |
| DV01 at 5 / 10 / 20 / 30 years | 21 / 39 / 44 / 38 | 22 / 43 / 55 / 93 |
| Matching bonds (duration) | I2038 (9.9), I2043 (11.4) | I2043 (11.4), I2046 (14.6) |
| Portfolio DV01 at 5 / 10 / 20 / 30 | 12 / 83 / 47 / 0 | 13 / 47 / 153 / 0 |

Two bonds match the annuity's value and duration, but not its shape. The annuity's payments run to age 120, and a third to a half of its interest-rate risk sits at the 20- and 30-year key rates. The portfolio has nothing at 30 years and piles its risk at 10 years (men) or 20 years (women). A parallel move leaves the book matched. A steepening of the real curve beyond 20 years does not: the annuity's value moves and the portfolio's does not. For women the 30-year mismatch is 93 per R10,000 a year per basis point. Closing it needs I2050 and I2058, the bonds whose durations are longest, which a two-bond, duration-only match does not reach. That is v3's starting point: under SAM's interest-rate shocks the same gap costs R193 million of capital ([RESULTS_v3.md](RESULTS_v3.md#scr-r-million)).

## Notes

- **Coupon dates** come from each bond's final redemption date, stepping back six months. One schedule disagrees: R2030 is listed as paying on 28/02 and 31/08, but its redemption on 31 January implies 31/01 and 31/07. The implied dates are used.
- **Settlement dates.** Three auctions with a settlement lag outside 1 to 10 days were given their kind's median lag.
- **Simplifications** as set out in the protocol: ex-coupon periods, accrued-interest conventions and the inflation index ratio are ignored, and inflation-linked cash flows are treated as real.
- **Curves per auction day, not per calendar day.** A curve exists on each day Treasury auctions that kind of bond, usually weekly.
