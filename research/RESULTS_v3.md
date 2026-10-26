# Results: v3 Balance sheet

Run on 26 October 2026 under `PROTOCOL_v3.md`, frozen at `545ba7193b24`, with no amendments. Valuation date 25 September 2026, on v2's curves: the inflation-linked curve from that day's auction, and the fixed-rate curve from 22 September. SAM parameters are from the PA's *Financial Soundness Standards for Insurers*, version 1.

Raw output: `research/results/balance_v3.json` and `funeral_table.csv`, with the invented book in `data/book/`. Built by `research/book_v3.py` and `research/balance_v3.py`, using the standard-formula pieces in `mdingilife/sam.py`.

## The answer

With the R400 million of own funds chosen before the run, **Mdingi Life does not cover its SCR: the cover ratio is 0.94.** The SCR is R423 million. Cover of 100% needs R424 million of own funds. The life industry's median of 1.8 needs R762 million.

Longevity drives the result: 80% of the standalone life charges and 47% of all standalone charges before operational risk (R595.8 million). The second largest is a real interest-rate charge that two-bond matching leaves behind.

## Balance sheet (R million)

| Assets | | Liabilities and own funds | |
| --- | --- | --- | --- |
| Inflation-linked bonds (I2038, I2043) | 2,355.6 | BEL, annuities | 3,925.7 |
| Fixed-rate bonds (R2035, R209) | 1,531.5 | BEL, funeral | −45.9 |
| 182-day bill | 518.2 | Risk margin | 125.5 |
| | | Own funds (Tier 1) | 400.0 |
| **Total** | **4,405.3** | **Total** | **4,405.3** |

- **Annuities:** 5,000 lives, R408 million a year of income, worth 9.6 years of income on average. Of the BEL, R38.7 million is expenses.
- **Funeral:** 50,000 policies. Expected premiums (R195.6 million) exceed claims (R67.4 million) plus expenses (R82.2 million), so the funeral line is an asset of R45.9 million. The premiums were priced at a flat 9% with no lapses and a 20% margin, and the market's discount rates are near 9% to 11%. Lapses remove future margin as well as claims.
- **Expense inflation:** 6.87%, the 30-year breakeven on the chosen curves (6.01% on NS).

## SCR (R million)

| Risk | Standalone | Notes |
| --- | --- | --- |
| Longevity | 282.5 | Annuities: rates −10% and improvement +1 point a year |
| Expense | 37.4 | Both lines: +10%, and inflation +2 points (20% of 6.87% is 1.37) |
| Lapse | 22.3 | Funeral: mass lapse 21.9 combined with lapse-down 4.9 (§8.7); lapse-up costs 0.4 |
| Mortality | 9.3 | Funeral: rates +15% |
| Catastrophe | 2.5 | Funeral: three months of the §10.5 addition |
| **Life, diversified** | **298.6** | Sum 354.0 |
| Interest, real | 192.6 | Real rates down |
| Interest, nominal | 49.1 | Nominal rates down |
| **Market, diversified** | **210.4** | |
| **BSCR** | **406.0** | Market and life at 0.25 |
| Operational | 17.5 | 0.45% of BEL; above 4% of earned premiums (13.1) |
| **SCR** | **423.5** | No tax adjustment |

The risk margin is R125.5 million: 6% of the reference insurer's SCR (R316.1 million today, 89% of it from the annuities), run off with the book and discounted.

- **Longevity is the largest life risk (K4).** Most of the life SCR is the annuity line's, and the funeral book adds little. Mortality and longevity have correlation −0.25, but the funeral mortality charge is too small to offset much.
- **The real interest charge is convexity and shape, not duration.** The matching bonds' durations (9.9 and 11.4 years) bracket the annuities' 10.5. But SAM's real shock is a relative one, about 2.4 points at 10 years and 2.75 points beyond 30. The annuity payments run to age 120 and gain more from a fall that size than a pair of bonds near 10 years. Real rates up gains R9.1 million, which confirms it. This is the 30-year gap v2 found ([RESULTS_v2.md](RESULTS_v2.md#matching-the-inflation-linked-annuity-at-65)), at SAM's size of shock.
- **Nominal down is the same effect on the level annuities.** Their value rises R373.6 million and the fixed-rate bonds rise less. With the real curve held, breakeven inflation falls from 6.87% to 2.54%, so expenses are worth slightly less. The funeral line gains R25.5 million, because its future premiums are worth more.
- **Real down also raises expense inflation**, to 9.87%. That adds R37.5 million to the BEL, which no bond hedges. The rest of the R192.6 million is the convexity gap.
- **Mass lapse is the funeral line's largest risk.** The book is profitable, so losing 40% of it at once costs its future margin, and the lapsed policies' expenses run on for a year.

## Matching

| | Matched | Unmatched (all in the bill) |
| --- | --- | --- |
| Real interest | 192.6 | 845.6 |
| Nominal interest | 49.1 | 255.1 |
| Interest, diversified | 210.4 | 942.3 |
| SCR | 423.5 | 1,074.8 |
| Cover on R400 million | 0.94 | 0.37 |

Matching cuts the interest charge by 78%. K3 asks for the matched charge to be under a quarter of the unmatched one: 0.22, a pass, but narrowly. A third and fourth bond at the long end (I2050, I2058) would be the next step.

## Sensitivities

| | BEL | Risk margin | SCR | Cover |
| --- | --- | --- | --- | --- |
| Main | 3,879.8 | 125.5 | 423.5 | 0.94 |
| Funeral adjustment 0.8 | 3,866.9 | 126.3 | 424.9 | 0.94 |
| Funeral adjustment 1.2 | 3,892.2 | 124.7 | 422.3 | 0.95 |
| Annuitant adjustment 0.6 | 4,091.0 | 128.8 | 447.0 | 0.89 |
| Annuitant adjustment 0.8 | 3,693.8 | 121.2 | 402.8 | 0.99 |
| NS curves | 3,887.0 | 127.3 | 425.9 | 0.94 |

- **The funeral basis barely matters.** Lighter funeral mortality makes the book more profitable, which raises the mass-lapse charge about as much as it lowers the mortality charge.
- **The annuitant adjustment matters most.** From 0.6 to 0.8 it moves the BEL by R397 million and the SCR by R44 million. Most of the SCR change is interest, not longevity: a larger, longer book carries more of the convexity gap.
- **NS** moves the SCR by under 1%. Its lower long nominal forward lowers expense inflation to 6.01%.

## Checks

| Check | Result |
| --- | --- |
| K1, the valuation is right | **Pass.** A plain monthly loop for one annuity cell (men 73, level) and one funeral cell (women 41, new) agrees with the engine to 1.3e-14, unstressed and under all 11 stresses |
| K2, the stresses are right | **Pass.** Every parameter in `mdingilife/sam.py` is given with its section and compared with the standards' text. The tests check the shock table at sample terms against FSI 4.1 Attachment 3 |
| K3, matching works | **Pass**, 210.4 against 942.3 (ratio 0.22, under 0.25) |
| K4, longevity leads | **Pass**, 282.5 of 298.6 diversified life SCR |
| K5, context | Cover 0.94 against the industry median of 1.8. Not a test: the R400 million was chosen before the run |

## The funeral table

Force of mortality, Stats SA registered deaths over WPP population, 2017 to 2019:

| Age | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Women | 0.0015 | 0.0036 | 0.0058 | 0.0081 | 0.0146 | 0.0300 | 0.0588 | 0.130 | 0.278 |
| Men | 0.0025 | 0.0054 | 0.0088 | 0.0145 | 0.0259 | 0.0492 | 0.0856 | 0.112 | 0.152 |

Men's rates fall below women's from 89. This is most likely the old-age data problem v1 dealt with, in registration completeness and the population estimates at the oldest ages. The Kannisto tail fitted on 80 to 89 carries it to 120. The oldest funeral policyholder is 79, so it touches only the far tail of the funeral BEL. The monthly premium for R10,000 cover at entry is R41 to R42 at 20, R44 to R48 at 40 and R58 to R71 at 60. The R15 a month of expenses is most of it at young ages.

## Notes

- **Tax is ignored**, so there is no loss-absorbing adjustment and the SCR is overstated.
- **The PA's prescribed risk-free curve is not used.** v2's Treasury curve stands in for it, with flat forwards beyond the longest bond instead of an extrapolation to an ultimate forward rate.
- **The capital needed for a target cover** is the SCR times the target. More own funds would sit in the bill and shift the nominal charge slightly, which the figure ignores.
- The full list of simplifications is in the protocol.
