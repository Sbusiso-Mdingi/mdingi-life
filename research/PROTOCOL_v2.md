# Protocol: v2 Assets

Written on 26 October 2026, before any curve in this repository was fitted. Done beforehand, and disclosed here: National Treasury's auction results and bond schedules were downloaded and reduced to two tables (`research/treasury.py`). To check the parse, clearing yields were compared with each auction's best and worst bids, which showed about 40 rows where a figure is mistyped (a clearing yield of 1.85 for 11.85, a best bid of 113.89) or zero, and the bond codes and terms were checked against the schedules. No yields were plotted, averaged or fitted.

Frozen at commit: `f79f922ff837`

The question: what does the South African government bond curve look like on each auction day, how well can it be read from a handful of auctions, and what does it do to the price and the interest-rate risk of v1's annuities?

## Data

- **Yields.** Clearing yields from National Treasury's weekly auctions of fixed-rate (nominal) and inflation-linked (real) government bonds, April 2010 to the latest results, from investor.treasury.gov.za (Historical Results). Used for non-commercial purposes with acknowledgement. A clearing yield is the yield at which Treasury sold the bond that day: a traded price, but one auction a week, each covering two to four bonds.
- **Bond terms.** Coupon, coupon dates and redemption dates from Treasury's *Schedule of domestic government bonds*, the March schedule of each year from 2011 and the latest. Bonds redeemed in instalments (R186, R2044, R2048, I2050) are given every redemption date listed for them, in equal shares. The bond code on an auction sheet is trusted over the coupon and year printed next to it, which are often copied from a neighbouring column.
- **Not used.** SARB's published yields and any JSE data, whose terms do not allow republishing.

## Cleaning

Fixed before any fit:

1. Rows whose bond is not in the schedules are dropped, as are clearing yields that are missing or not positive (an auction with no accepted bids).
2. Bonds with less than one year to their final redemption on the auction day are dropped.
3. After a curve is fitted, any bond whose fitted yield misses its clearing yield by more than 100 basis points is dropped, and the curve is refitted once. This removes typing errors without inspecting them one by one. The number dropped is reported.

## Curves

- **Curve dates.** Every auction day, separately for fixed-rate and inflation-linked bonds. Inflation-linked yields are real, so that curve is a real curve.
- **Window.** On each curve date, the latest clearing yield of every bond auctioned in the 28 days up to and including that day. Fixed at 28 days (four weekly auctions); 56 days is reported as a sensitivity and changes nothing else.
- **Pricing.** Each bond pays half its coupon on each coupon date and its redemption share on each redemption date. Time is in years, actual/365, from the settlement date. A clearing yield y gives the price Σ c(i) (1 + y/2)^(−2 t(i)). A curve gives the price Σ c(i) exp(−z(t(i)) t(i)), z being the continuously compounded zero rate. Ex-coupon periods, accrued-interest conventions and the inflation index ratio are ignored: they scale cash flows or shift them by days, and the errors are measured in yield.
- **Fit.** Each model minimises the sum over bonds of the squared price error divided by the bond's price duration, so each bond counts by its yield error. Errors are reported as the model's yield to maturity minus the clearing yield, in basis points.

| Model | Zero curve |
| --- | --- |
| B0, no curve | Each bond's own most recent clearing yield, if it was auctioned in the previous 91 days |
| LI, linear | Yield to maturity linear in maturity between the window's bonds, flat beyond them |
| NS, Nelson-Siegel | z(t) = β0 + β1 (1 − e^(−t/τ))/(t/τ) + β2 [(1 − e^(−t/τ))/(t/τ) − e^(−t/τ)] |
| NSS, Svensson | NS plus β3 [(1 − e^(−t/τ2))/(t/τ2) − e^(−t/τ2)], with τ1 < τ2 |

NS and NSS need β0 > 0 and β0 + β1 > 0, and are fitted from a grid of starting values of τ. On a date with fewer bonds in the window than a model has parameters, that model is not fitted and the date is not scored for it.

## Scores

Each auction is predicted from the curve of the window that ends the day before it: every model is fitted on the previous 28 days only, and its yield for each bond auctioned that day is compared with the clearing yield. The scores, by kind of bond, are the root mean squared error (RMSE) and the mean absolute error in basis points. Models are compared on the bonds every model in the comparison could price.

- **Design period.** Auctions from April 2010 to December 2017. Used to choose the model and to debug.
- **Validation period.** Auctions from January 2018 to the latest results. Run once, after the design choices are fixed. March to May 2020 (the Covid sell-off) stays in, and the scores without it are reported alongside.
- **Chosen curve.** For each kind of bond, the one of LI, NS and NSS with the lowest design RMSE. It is the curve tested below and used for the annuities.

## Tests (validation period)

- **C1, the curve adds information.** The chosen curve beats B0 on RMSE for both kinds. Expected to pass for fixed-rate bonds, where other bonds' auctions since a bond was last sold carry the market's moves. Uncertain for inflation-linked bonds, which move less and are auctioned with fewer bonds a week.
- **C2, the extra hump.** NSS beats NS on RMSE. Expected to pass for fixed-rate bonds (more bonds, a humped curve) and to fail for inflation-linked bonds, where six parameters on a handful of bonds overfit.
- **C3, accuracy.** The chosen curve's RMSE is under 25 basis points for both kinds.

Passing or failing does not change the method. Every result is reported.

## Annuity prices

- **Valuation date.** The latest inflation-linked auction day in the data, and the fixed-rate auction day closest before it. Curves on that date are fitted on the 28 days up to and including it.
- **Beyond the last bond.** Past the longest maturity in the window, the forward rate is held at its value at that maturity.
- **Products.** Both from the book in the README, for a single life aged 55, 65 and 75 by sex, paid monthly in advance:
  - an *inflation-linked* annuity, discounted on the real curve, which replaces v1's flat 4% real rate;
  - a *level* annuity, discounted on the nominal curve.
- **Mortality.** v1's production fit, chosen models and annuitant adjustments (0.6, 0.7, 0.8), unchanged, on the primary Stats SA run. The 95% intervals carry mortality uncertainty only; the curve is held fixed.
- **Reported.** The curve price against v1's flat 2%, 4% and 6% prices, and the flat rate that gives the curve price.

## Matching

On the valuation date, for the inflation-linked annuity at 65 (adjustment 0.7) and the real curve:

- **Duration.** Effective duration, from a parallel 1 basis point move in the zero curve.
- **Key rates.** The value change for a 1 basis point move in the zero rate at 5, 10, 20 and 30 years, each spread linearly to its neighbouring key rates.
- **A matching portfolio.** The two inflation-linked bonds in issue whose durations are nearest below and above the annuity's, held in the amounts that match its value and duration. Reported: the portfolio, and its key-rate mismatch against the annuity.

## Changes after freezing

### 26 October 2026: how the 100 basis point screen runs

Written before any curve was fitted, to settle two things the cleaning rule left open: which curve does the screening, and whether a screened point also leaves the scores.

- **The screen uses NS**, the simpler parametric curve, so that it does not depend on the model being tested. LI passes through every bond and B0 has no curve, so neither can flag a point.
- **In date order.** On each curve date, NS is fitted on that day's window (including the day), with points already flagged left out. A bond auctioned that day whose yield NS misses by more than 100 basis points is flagged, and NS is refitted once without it.
- **Everywhere.** A flagged point is dropped from the data: from every model's windows and from the scored auctions.
- **The coupon dates** of each bond are taken from its final redemption date, stepping back six months at a time, because a South African government bond pays its last coupon on its redemption date. The schedules' coupon dates are checked against this and disagreements reported, not used.

Reason: as frozen, a mistyped yield could stay in the LI and B0 windows and in the targets, where every model would be charged for it.

### 26 October 2026: a 91-day window, and no NSS for inflation-linked bonds

Written after the first design run and before any validation run. That run used the frozen 28-day window, and its design scores were seen: fixed-rate RMSE 44 (LI), 21 (NS) and 24 (NSS) basis points on the 476 auctions all three could price; inflation-linked, 13, 22 and 20 on 15 auctions. It chose NS for fixed-rate bonds and LI for inflation-linked ones. It is kept as `curves_design_28.json` and reported.

What it showed: Treasury auctions the same few bonds week after week, so 28 days holds a median of 5 fixed-rate bonds and 3 inflation-linked ones. NSS could be fitted on half the fixed-rate days and 1% of the inflation-linked days, and the inflation-linked choice rested on 15 auctions. The number of bonds per window was then counted, without fitting, for longer windows: at 91 days, 98% of fixed-rate days have six bonds or more, and 83% of inflation-linked days have four or more; inflation-linked windows reach six bonds on fewer than half the days even at a year.

- **Window.** 91 days instead of 28, everywhere the window is used: the screen, the backtest and the valuation-date curves. The sensitivity is 182 days instead of 56.
- **Inflation-linked curves.** NSS is not fitted. The choice is between LI and NS, on the auctions both can price. C2 is tested on fixed-rate bonds only.
- Nothing else changes: B0's 91 days, the periods, the screen, the tests and their pass marks.

Reason: the frozen window was too short for how Treasury auctions, which the design period exists to find out. The cost is staleness: a window can hold yields up to three months old, which the backtest charges for.
