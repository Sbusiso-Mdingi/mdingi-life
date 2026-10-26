# Protocol: v3 Balance sheet

Written on 26 October 2026, before any part of the v3 book was generated or valued. Done beforehand, and disclosed here: the Prudential Authority's *Financial Soundness Standards for Insurers* (FSI, version 1, in force from 1 July 2018) were read for their parameters, and the PA's published industry figures were looked up (below). Nothing was computed.

Frozen at commit: (not yet)

The question: on the Solvency Assessment and Management (SAM) standard formula, how much capital does a small South African life insurer need for an annuity book matched with government bonds and a funeral book, and what drives it?

## Sources

- **SAM rules.** FSI 2.2 (technical provisions and the risk margin), FSI 2.3 (own funds), FSI 4 (the SCR and its aggregation), FSI 4.1 (market risk), FSI 4.2 (life underwriting risk) and FSI 4.4 (operational risk), each cited by section where it is used. Read from the PA's zip of the standards (resbank.co.za, through the Internet Archive's copy of 20 April 2022, since resbank.co.za does not answer from this machine). The PDFs are not stored in this repository; parameters are quoted with their section. The Internet Archive's index of the PA's publications, searched on 26 October 2026, holds no amendment to FSI 2.2, 4, 4.1, 4.2 or 4.4, only guidance notices, so version 1 is used.
- **Curves.** v2's chosen curves on v2's valuation date, unchanged (`RESULTS_v2.md`).
- **Mortality.** v1's production fit for annuitants. For funeral cover, Stats SA registered deaths over WPP population at all adult ages (below). Both public.
- **Industry context.** SARB *Financial Stability Review*, first edition 2026, Table B.2 (source: PA): median SCR cover of life insurers 1.7 (2021), 1.7 (2022), 1.9 (2023), 1.8 (2024), 1.8 (2025).
- **Not used.** The PA's published risk-free curve. FSI 2.2 §13.1 requires it, but its files are SARB material that may not be republished, and it is built from JSE bond data. v2's curve from Treasury auctions stands in for it, as a listed simplification.

## The book

Invented, generated once from a fixed seed (20261026) and committed as `data/book/`. Every policy is in force on the valuation date (25 September 2026). All amounts are in Rand.

**Annuities: 5,000 single lives**, no guarantee period, no spouse's pension, paid monthly in advance.

- Sex: half men, half women.
- Age at purchase: triangular from 55 to 75, mode 65, rounded to whole years. Years since purchase: uniform from 0 to 15. Age on the valuation date is their sum.
- Type: half inflation-linked (income rises with CPI), half level.
- Income: lognormal, median R60,000 a year, σ = 0.8, capped at R1 million.

Years since purchase and years in force are whole numbers; a policy with 0 was taken out in the year before the valuation date.

**Funeral: 50,000 main-member policies**, whole of life, level monthly premiums payable for life, no extended family, no waiting period, no surrender value.

- Sex: 55% women.
- Age at entry: normal, mean 38, standard deviation 10, rounded to whole years and held to 18 to 64. Years in force: drawn from the lapse assumption's survivors, 0 to 15 years.
- Sum assured: R10,000, R15,000, R20,000 or R30,000, with weights 30%, 30%, 25% and 15%.
- Premium: set at entry on the pricing basis below and never reviewed.

## Bases

**Best estimate**, used for the technical provisions and every stress:

| | Annuities | Funeral |
| --- | --- | --- |
| Mortality | v1's production fit (Stats SA, RH post-peak, jump-off 2019), median projected rates, annuitant adjustment 0.7 | Funeral table below, adjustment 1.0, no improvement |
| Lapse | None | 20% a year in the first year in force, 12% in the second, 8% in the third, 6% from the fourth |
| Expenses | R600 a policy a year | R180 a policy a year |
| Expense inflation | Breakeven: the 30-year nominal zero rate minus the 30-year real zero rate, held flat at every term | Same |
| Discounting | Real curve for inflation-linked, nominal curve for level | Nominal curve |

Expense inflation is taken from the 30-year point and not term by term because the bootstrap's forwards jump between segments (v2 found a 12.45% nominal forward beyond 18 years); a breakeven read forward by forward would inherit those jumps.

**Projection.** Monthly, from the valuation date, with ages and policy years as whole years on that date (each moves up by one every 12 months). In each month: premiums, annuity payments and expenses at the start, for policies in force; deaths at mid-month, with probability 1 − exp(−μ/12) from the year's force of mortality μ; lapses at the end of the month among the survivors, with probability 1 − (1 − L)^(1/12) from the policy year's annual rate L. Death claims are paid at mid-month. Discounting is on each curve's zero rates, from the yearly forwards with the zero rate times term linear within each year, as in v2. For annuitants, μ is v1's median simulated rate in each year of age and calendar year along the cohort, times the annuitant adjustment.

**Funeral table.** Registered deaths over WPP 1 July population, by sex and single age 18 to 89, summed over 2017 to 2019 (the three years before Covid, ending at v1's jump-off). The log rates are smoothed by a five-age moving average. From 90 to 120 the rates follow v1's Kannisto extension, fitted on the smoothed rates at 80 to 89. Nobody survives past 120, as in v1. No completeness adjustment, as in v1's primary run. This is population mortality, HIV-era hump included; insured lives may differ, and adjustments of 0.8 and 1.2 are reported as sensitivities.

**Funeral pricing basis.** Used once, to set each policy's premium at entry: the funeral table, interest at a flat 9% a year, the best-estimate expenses inflating at 5% a year, no lapses, and a profit margin of 20% of premium. The premium P solves (1 − 0.2) P ä = A + E, with ä the expected value of premiums paid, A the expected value of the sum assured and E the expected value of expenses.

## Assets

- **Annuities.** The income of the inflation-linked annuities is matched with inflation-linked bonds and the income of the level annuities with fixed-rate bonds, both by v2's method: the two bonds in issue whose effective durations sit nearest either side of the income's, on the unshocked curve, in amounts matching its best-estimate value and effective duration. Bonds are valued on their kind's curve as in v2.
- **Everything else** (the annuities' expenses, the funeral BEL, the risk margin and own funds) is held in a 182-day zero-coupon government bill, valued on the nominal curve.
- **Own funds** on the valuation date: R400 million, all ordinary share capital and so Tier 1 (FSI 2.3). Chosen now, before any SCR is computed. The capital needed for cover of 100% and of 1.8 is reported, so the result can be scaled.

## Technical provisions (FSI 2.2)

- **Best-estimate liability (BEL).** Expected cash flows on the best-estimate basis, discounted on the curves, policy by policy. Monthly steps; deaths and lapses at mid-month. The funeral BEL may be negative, since future premiums exceed future claims and expenses, and it is not floored.
- **Risk margin.** Cost of capital at 6% (§14.14): 6% × Σ_t SCR_RU(t) / (1 + r_(t+1))^(t+1) over whole years t ≥ 0, r being the nominal annual spot rate, with no illiquidity premium (§14.7). The reference insurer's SCR covers life underwriting and operational risk (§14.3, §14.9). Unavoidable market risk is taken as nil: the annuities' durations are well below that of the longest inflation-linked bond (§14.10, footnote 18). SCR_RU(0) is the life SCR plus operational risk on it. Later years use the simplification of §14.18 to §14.19: SCR_RU(t) = SCR_RU(0) × [w · BEL_ann(t) / BEL_ann(0) + (1 − w) · S(t) / S(0)], where BEL_ann(t) is the annuities' BEL at t, S(t) the expected sum assured of funeral policies in force at t, and w the annuities' share of the two lines' standalone life SCRs at the valuation date. The funeral BEL is not used as the driver because it may be negative.
- **No illiquidity premium** on the annuities (§13.8).

## SCR (FSI 4, standard formula)

Each stress is applied to the best-estimate balance sheet. A risk's capital is the fall in assets minus BEL that it causes, floored at zero.

**Life underwriting (FSI 4.2):**

| Risk | Stress | Applies to |
| --- | --- | --- |
| Mortality (§5.3) | Mortality rates +15%, permanently | Funeral |
| Longevity (§6.3) | Mortality rates −10%, and improvement rates +1 percentage point a year, permanently | Annuities |
| Lapse (§8) | max(A, B, C) of §8.4: A, a mass lapse of 40% at once, applied only if the funeral line has a positive surrender strain (BEL below its nil surrender value), with the lapsed policies' expenses still paid for 12 months (§8.5); B, the costlier of lapse rates +50% (capped at 100%) and −50% (§8.6); C = √(A² + (B · (1 − 0.5 · 0.4))²) (§8.7) | Funeral |
| Expense (§9.4) | Expenses +10%, and expense inflation up by the greater of 2 points and 20% of itself | Both |
| Catastrophe (§10.5) | For the next three months, each monthly mortality rate q (per thousand) rises by 4 · min[max(0.2q + 0.105, 0.125), 0.3] per thousand | Funeral |

Every stress is applied at the line (product type) level that §5.2, §6.2, §8.2, §9.2 and §10.3 ask for, to the line it hurts. Mortality, longevity and catastrophe are not applied to the line they help. No management actions are assumed. Disability and retrenchment risk are nil: neither line covers them. The five are aggregated with the §4.9 correlation matrix (mortality–longevity −0.25; mortality–expense, mortality–catastrophe, longevity–lapse, longevity–expense, lapse–catastrophe and expense–catastrophe 0.25; mortality–lapse, longevity–catastrophe and lapse–expense 0).

**Market (FSI 4.1):**

- **Interest rate (§5, Attachment 3).** Each curve's annual spot rate i_t at term t is multiplied by 1 + s(t), with s(t) the Attachment 3 shock interpolated linearly between its terms, held at the 0.25-year value below it and at the 30-year value beyond (nominal up +50.57%, down −39.79%; real ±68.02%). The change is at least 1 percentage point either way (§5.11); a nominal rate pushed below 0% is set to 0%, a real rate is not floored. The nominal curve is shocked with the real curve held, and the real curve with the nominal held (§5.8, §5.10), so a nominal shock moves breakeven inflation and with it expense inflation. Each of nominal and real is max(up, down, 0) (§5.7, §5.9), and the two are combined with correlation 0.25 (§5.6). There are no options, so interest rate volatility risk is nil (§5.3).
- **Spread, concentration and currency:** nil. Every asset is a Rand bond issued by the South African government, which carries no spread or concentration charge (Attachment 4 B.1, Attachment 1 C.1), and nothing is held in foreign currency.
- Equity and property: nil, none held.

**Aggregation (FSI 4 §6.3):** BSCR from the market and life SCRs with correlation 0.25.

**Operational risk (FSI 4.4):** both lines are non-investment business (FSI 2.2 Attachment 1: funeral 1g, annuities 2a(i)), so SCR_Op = min(30% of BSCR, max(4% of the last year's premiums, 0.45% of max(BEL, 0))) (§4.5, §5.1, §5.2, §5.5). The last year's premiums are 12 months of the funeral premiums in force plus the single premiums of annuities bought in the year before the valuation date, taken as their BEL on the valuation date (§5.4). The growth term is nil: the book has no premium history.

**SCR** = BSCR + operational risk. There is no loss-absorbing adjustment: tax is ignored throughout, which overstates the SCR.

## Reported

- The balance sheet: assets, BEL by line, risk margin, own funds.
- The SCR by risk, before and after diversification, and the cover ratio: own funds over SCR.
- The interest-rate SCR with the annuities unmatched (all assets in short bonds), beside the matched figure.
- Sensitivities: funeral adjustment 0.8 and 1.2; annuitant adjustment 0.6 and 0.8; prices on NS instead of the chosen curves.

## Checks

- **K1, the valuation is right.** One annuitant and one funeral policy are valued by a separate, plain loop over months. It agrees with the main code to within 1e-8 of the BEL, unstressed and under every stress.
- **K2, the stresses are right.** Every SAM parameter in the code is listed with its section, and each is compared with the standard's text before the run.
- **K3, matching works.** The matched interest-rate SCR is under a quarter of the unmatched one. Expected to pass: v2 left the women's book exposed only at 30 years.
- **K4, longevity leads.** Longevity is the largest life risk. Expected to pass, because the annuities are about ten times the funeral book's value.
- **K5, context.** Where the cover ratio sits against the industry's median of 1.8. Not a test: it depends on the invented R400 million.

Passing or failing does not change the method. Every result is reported.

## Simplifications

- v2's Treasury curve instead of the PA's prescribed curve, with v2's flat forwards beyond the longest bond instead of the PA's extrapolation to an ultimate forward rate.
- Mortality, longevity and lapse stresses applied to a whole line, not policy by policy.
- Risk margin from SCRs projected in proportion to BEL.
- No tax, no illiquidity premium, no MCR, no own-funds tiers beyond Tier 1.
- Inflation-linked cash flows treated as real, as in v2.
- Expense inflation flat at the 30-year breakeven.
- Ages and policy durations as whole years on the valuation date.
