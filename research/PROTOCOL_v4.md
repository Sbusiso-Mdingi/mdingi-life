# Protocol: v4 Scenarios and reporting

Written on 26 October 2026, before any v4 scenario was generated or any part of the book was projected. Done beforehand, and disclosed here: one v3 SCR was timed (0.53 seconds, so 1,000 scenarios over five years are affordable), and the number of bonds in each month-end's 91-day auction window was counted (at least five from April 2010 for fixed-rate bonds and June 2010 for inflation-linked; as few as three in some later months). No curve was fitted for v4 and nothing was projected.

Frozen at commit: `fedf29aeeebc`

The question: over the next five years, how likely is Mdingi Life to stay covered on the R400 million it has, what profit does it report under IFRS 17, and which shocks would break it?

Everything in v3 stands: the book, the bases, the valuation date (25 September 2026), the standard formula and the key-rate matched assets of v3's amendment, which are the company's position on the valuation date. v4 adds three things: an economic scenario generator, a five-year projection of the SAM balance sheet (ORSA style), and IFRS 17 reporting.

## Economic scenario generator

A dynamic Nelson-Siegel model (Diebold and Li, 2006) for the nominal and real zero curves, calibrated to National Treasury auctions.

- **Monthly curves.** At each month-end from January 2011 to September 2026, for each kind, the latest point of each bond auctioned in the 91 days up to and including that day (v2's window and screen). Months whose window holds fewer than four bonds of a kind are skipped for that kind.
- **Fit.** Nelson-Siegel zero curve with the decay τ fixed for each kind, the three factors (β0, β1, β2) by v2's least squares on yield errors. τ is chosen once per kind from 0.5 to 10 years in steps of 0.5, as the value with the smallest total squared yield error over all its month-ends.
- **Dynamics.** Each of the six factors (three a kind) follows its own AR(1) at a monthly step, β(m+1) = μ + φ (β(m) − μ) + ε, estimated by least squares on consecutive month-ends. If φ comes out above 0.995 it is set to 0.995 and μ re-estimated. The six innovations are jointly normal, with the covariance of the residuals in the months where all six have one.
- **Jump-off.** The same fixed-τ fit on v3's curve days (fixed-rate on 22 September 2026, inflation-linked on 25 September 2026).
- **Scenarios.** 1,000 paths of 60 months, seed 20261027. In each, the zero curve at a year-end is the valuation curve (v3's LI bootstrap) plus the change in the Nelson-Siegel curve since the jump-off: z_t(T) = z_0(T) + NS(β_t)(T) − NS(β_0)(T), at every maturity T, turned into yearly forwards as in v2. So the curve keeps today's shape when the factors do not move.
- **The central path.** The factors' expected path, all innovations nil. Used for the named stresses and the IFRS 17 tables.
- **Inflation.** Realised inflation in each year is the one-year breakeven on the curves at its start: (1 + nominal 1-year spot) / (1 + real 1-year spot) − 1. Inflation-linked incomes and bond cash flows rise by it once a year, at each year-end, and so do the R600 and R180 expenses a policy. The expense inflation assumption in each valuation stays v3's: the 30-year breakeven on that year-end's curves.

## The five-year projection

Year-ends t = 0 (25 September 2026) to 5 (25 September 2031). Closed book: no new business, no dividends, no new capital, no tax.

- **The book ages as expected.** Deaths and lapses follow the best-estimate basis exactly (no random experience), except in the named stresses. At year-end t each annuity and funeral cell is weighted by its expected survivors in force, a year older and a year longer in force for each year. Annuitant mortality moves along the calendar years of v1's projection, so a cell's rates at t are its rates from today's projection t years on.
- **Cash.** Every cash flow in a year (bond coupons and redemptions, annuity payments, premiums, claims and expenses, at v3's timing within the month) and the bill earn the nominal curve at the start of the year to the year-end, as if held in Treasury bills maturing then. Bonds are revalued on the year-end curve.
- **Management action.** At each year-end the annuities are rematched on key rates (v3's amendment method) on that year's curve, among the bonds in issue with at least a year to run, and the rest goes into the 182-day bill. Rebalancing costs nothing. No new bonds are issued in the projection.
- **Each year-end.** BEL, risk margin and SCR recalculated in full on v3's standard formula, on that year-end's curves and aged book; assets carried forward; own funds = assets − BEL − risk margin; cover = own funds / SCR. Operational risk's premium term counts the funeral premiums only from t = 1, since no annuities are sold.

## IFRS 17

- **Groups and model.** One group per portfolio, annuities and funeral, both under the general measurement model. Transition on 25 September 2026 by the fair value approach (C20 to C24), which allows annual cohorts to be grouped together (C23).
- **Fulfilment cash flows.** The BEL on v3's basis, at current rates. Risk adjustment: cost of capital at 6% on the reference SCR for life and operational risk, run off as in v3, so it equals SAM's risk margin. It is split between the portfolios in v3's proportion w. Its confidence level is disclosed approximately, as Φ(2.576 × RA / SCR_RU(0)), treating the 1-in-200 SCR as a normal quantile.
- **Fair value** of each group: its BEL plus a cost of capital of 10% a year on the same reference SCR, the return a buyer would want. So the CSM at transition is (10/6 − 1) times the risk adjustment, by portfolio. The 10% is an assumption; 8% and 12% are reported.
- **Roll-forward each year.** CSM_close = CSM_open × (1 + i_k) + future-service changes − release. i_k is the year's one-year forward on the transition nominal curve (locked in, C23). Coverage units: annuities, the expected income payable in the year (undiscounted, inflation-linked in real terms); funeral, the expected sum assured in force averaged over the year's months. Release = the CSM before release × this year's units / this and all later years' units.
- **Future-service changes.** Changes in fulfilment cash flows from non-financial assumptions or from experience that changes what is in force, measured on the locked-in curve (the transition curve rolled forward), adjust the CSM. If they exceed it, the excess is a loss in profit and the CSM is nil; later reversals are not tracked. Changes from interest rates and inflation go to profit as insurance finance expense, with no OCI option.
- **Profit** = change in IFRS equity (assets − BEL − RA − CSM). It is shown as the insurance service result (CSM release + RA released + experience variance − losses), and the net financial result, which is the remainder: investment return less insurance finance expense.

## Named stresses (ORSA)

Each on the central path, applied at t = 0 unless stated, and projected for five years with the same management action:

| | Stress |
| --- | --- |
| S1 Rates fall | Both curves 1.5 points lower at every term at t = 0 (β0 of each kind −0.015), then mean-reverting along the model from there |
| S2 Longevity | Annuitant mortality 20% lower, permanently (annuitant adjustment 0.56 instead of 0.7), recognised at t = 0 |
| S3 Pandemic year | In year 1, mortality of both lines times the ratio of 2021 to 2019 crude death rates (Stats SA registered deaths over WPP population, ages 18 to 89, by sex); best estimate again from t = 1 |
| S4 Lapse wave | 30% of funeral policies lapse at once at t = 0, with no surrender value |
| S5 All at once | S1, S3 and S4 together |

S2 and S4 change future service at t = 0 and S3 at t = 1, through the CSM as above; S1 goes through finance.

## Reported

- The scenarios: the fitted τ, AR(1) parameters and correlations; fan charts of the 10-year nominal and real zero rates.
- Cover at each year-end: percentiles 5, 25, 50, 75 and 95 over the scenarios, and the share of scenarios below 1.0 at some year-end.
- The central path: balance sheet, SCR and cover by year; the IFRS 17 CSM roll-forward and profit by year, by portfolio.
- Profit by year across the scenarios (percentiles).
- The named stresses: cover at each year-end, the CSM used, any loss, and the capital that would restore cover to 1.0 at the worst year-end.
- Sensitivities: fair-value cost of capital 8% and 12% (IFRS 17 only); the scenarios recalibrated without March to May 2020; no rematching (the t = 0 key-rate portfolio held to the end, coupons and redemptions to the bill).

## Checks

- **R1, the roll-forward is right.** With the year-1 curve set to the valuation curve rolled forward one year and inflation held at its t = 0 values, each line's BEL at t = 1 plus its year-1 cash flows accumulated to t = 1 equals its BEL at t = 0 accumulated a year, to 1e-8 relative. Each part is accumulated on its own curve (real for inflation-linked).
- **R2, the books tie.** SAM own funds minus IFRS equity equals the CSM, at every year-end of every scenario and stress, to 1e-6 relative. It must, since the risk adjustment equals the risk margin; it checks that the two ledgers use the same numbers.
- **E1, the scenarios move like history.** The standard deviation across scenarios of the first year's change in the 10-year zero rate is between 0.75 and 1.33 times the standard deviation of 12-month changes at month-ends in the calibration sample, for each kind.
- **E2, context.** The scenarios' 0.5% quantile of that first-year change in the 10-year rate, beside SAM's down shock at 10 years. Not a test.
- **A1, risk appetite in the scenarios.** Cover at least 1.0 at every year-end in at least 95% of scenarios.
- **A2, risk appetite under stress.** Cover at least 1.0 at every year-end under each named stress, each reported.

The appetite (A1, A2) is the board's, set here before the run. Every result is reported, pass or fail, and failing does not change the method.

## Simplifications

- A real-world scenario generator for interest rates and inflation only, with Gaussian factors. No equity, credit or mortality scenarios; the book ages exactly as expected.
- Realised inflation is the market's one-year breakeven, and indexation is annual while v3's valuation treats inflation-linked flows as continuous real flows.
- The curve keeps today's LI shape, moving only by the Nelson-Siegel change; no issuance of new bonds.
- IFRS 17: one group per portfolio, the fair value approach with a cost-of-capital fair value, the risk adjustment equal to SAM's risk margin, no OCI, loss-component reversals not tracked, no tax, no acquisition cash flows.
- Everything v3 lists.

## Changes after freezing

None yet.
