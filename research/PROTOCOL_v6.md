# Protocol: v6 The book's size and mix, set by rule

**Written on 27 October 2026, after v5's v3 results were seen** (funeral BEL −R84.4 million, SCR R424.6 million, cover 0.942 at R400 million). Those results are why the two rules below were asked for: the book's 5,000 annuitants and 50,000 funeral policies were invented counts, with nothing behind them. The two rules, the whole-book matching (Q1 below) and the capital levels (Q2) were settled by the user on 27 October 2026. Nothing in v6 has been run on the real book. Seen before freezing: a test of the code with invented annuitant mortality (a Gompertz line, not v1's) and the real funeral book, market and inflation model. It gave a mix of about 20 funeral units per annuity unit, a size of about 0.12 of v5's annuities, and, at that size, a lapse charge and a nominal interest rate charge from the funeral line larger than the mortality and longevity charges. Q1 below comes from that test.

Frozen at commit: (filled in when this is committed)

The question: how big should each line be, if the funeral book is sized so its mortality risk offsets the annuities' longevity risk, and the whole book is sized so the company's cover equals the industry's?

What changes and what does not:
- **The size of each line** is set by the two rules below, instead of by the counts 5,000 and 50,000.
- **Everything within each line stays as in v5:** the policies' ages, sexes, incomes, sums assured, benefit types and premiums, their mortality, lapses and expenses, and the inflation model. Each line is scaled as a whole: every cell's count, income, sum assured and premium is multiplied by the line's scale. No policies are redrawn, so the shape of each line is v5's, and only its size moves.
- **Own funds stay at R400 million.**
- **The matching** is of the whole book together (Q1), in place of v5's matching of the annuities and separate hedge of the rising claims.

## Rule 1: the mix, mortality-neutral (user's choice)

The funeral line is sized so that a uniform change in mortality leaves the company's total BEL unchanged: what the annuities lose when people live longer, the funeral line gains, and the reverse.

- **The exposure of each line.** E = dBEL / ds, where every force of mortality of that line is multiplied by (1 + s). It is found by central difference at s = ±1%, on the best-estimate basis (LI curves, unstressed, with lapses), on v5's book. E_ann is negative (more deaths, lower annuity BEL) and E_fun positive.
- **The mix.** With the annuity line scaled by A and the funeral line by F, A · E_ann + F · E_fun = 0, so F / A = −E_ann / E_fun. Both lines' BELs are linear in their scale, so the ratio does not depend on the size.
- **Why a uniform change.** It is the plainest meaning of "the two lines' mortality risks offset": the same error in the level of mortality, on both books at once. It does not use the SAM stresses, which treat mortality and longevity as separate risks (correlation −0.25, FSI 4.2), so SAM recognises only part of the offset. How much it recognises is reported.
- **What it does not offset.** A uniform change is an error in the level. An error in the trend compounds with time, and the two lines' exposures are spread over time differently, so the level offset need not hold for the trend. This is disclosed, not used: each line's exposure to improvement 1 point a year faster, the force in projection year k multiplied by 0.99^k, is reported at the chosen mix.

## Rule 2: the size, cover 1.8 (user's choice)

With the mix held, the whole book is scaled so that cover, own funds over the SCR, is 1.8 at own funds of R400 million.

- **The 1.8** is the median SCR cover of South African life insurers in 2025, from SARB's *Financial Stability Review* (2026, Table B.2), as already cited in v3.
- **The scale** is solved by root-finding (Brent's method) on A, with F = A × (F / A), and every run of v5's balance sheet in between: matching, hedge, risk margin and SCR all recomputed at each scale. The SCR is not exactly proportional to the scale, since own funds are held fixed in the bill, so it is solved and not divided.
- **The book's size is then reported as policies:** 5,000 · A annuitants and 50,000 · F funeral policies, rounded.

## Everything else, as v5

- The funeral 0.8 and 1.2 sensitivities are run at the main run's scales, not re-solved, so they show the effect of the basis alone.
- The unmatched variant (everything in the 182-day bill) and v5's matching (annuities matched, rising claims hedged, the rest of the funeral line in the bill) are run at the main run's scales, so the effect of matching the whole book is shown.

## Settled questions

- **Q1, the funeral line's interest rate risk.** v5 matches the annuities' income and the rising claims with bonds. The rest of the funeral line (premiums, level claims and expenses) stays in the 182-day bill. At v5's size that mattered little. At the mortality-neutral mix the funeral line's future profits are about 20 times larger, and when nominal rates rise their value falls, unhedged. Two choices:
  - **(a) Keep v5's matching** and report the funeral line's rate charge as found.
  - **(b) Match the whole book together** (chosen by the user): v3's key-rate method on the net cash flows of both lines, by curve, with no shorting. The funeral line's future profits then offset part of the annuities' exposure, so fewer long bonds are held, rather than the profits being left exposed. This replaces v5's separate hedge of the rising claims, whose cash flows are included at G. Precisely: non-negative holdings in every bond of v3's book that equal the whole book's BEL and come nearest, by least squares, its DV01 at each of v3's four key rates on each curve (eight in all), each DV01 found by bumping that key rate with the other curve held, expense inflation and G re-centred on the moved breakeven as in v5's stresses. Where an exposure cannot be met without shorting (the test run found the funeral line's 30-year nominal one), it is left and its charge reported. At each year-end of v4 the match is redone on that year-end's book and curves.
- **Q2, the capital levels for v4** (left to judgement by the user, settled as): R400 million (cover 1.8, the main run) and the level at which cover starts at 1.0. Cover 1.0 is SAM's floor, so it shows how often a company that just meets its SCR falls below it; R400 million shows the industry's median company. Two levels keep the cost to two v4 runs. v5's R500 million and R627 million are dropped, since they were chosen on the old counts.

## Checks

- **D1, the mix is neutral.** At the chosen scales, the total BEL changes by less than 1e-9 of the annuities' exposure A · |E_ann| for a ±1% uniform change.
- **D2, the size.** Cover at the chosen scales is 1.8 to 1e-6.
- **D3, scaling is exact.** With A = F = 1, the run equals v5's main run (BEL, SCR, risk margin) to 1e-10.
- **D4, v5's checks.** C4 to C6 are rerun at the chosen scales (C6 against v3 times A).
- **D5, the match.** The holdings' value equals the whole book's BEL to 1e-8, and every holding is non-negative.

## Reruns and reporting

These replace v5's steps 4 and 5 (v4 and the capital levels), which have not been run. v5's v3 result stands as v5's record, on the old counts.
1. v6's balance sheet: the exposures, the mix, the size, and the runs above.
2. v4 on v6's book at R400 million (cover 1.8 at the start, by construction).
3. The capital level at which cover starts at 1.0 (own funds equal to the SCR), in place of v5's R500 million and R627 million, which were picked on the old counts. Unlike v4's capital levels, which put extra capital into every asset in the same proportion, the change in own funds is taken from the 182-day bill alone and the whole-book match stays on the BEL, at every year-end too. Scaling the bonds down with the capital would leave part of the BEL unmatched on purpose, and the result would mix the capital level with a rate mismatch (the test run: at k = 0.77 the SCR rose by 2%). Since the SCR moves a little with the bill, the level is solved by root-finding on own funds (Brent's method), to cover 1.0 within 1e-6, and then v4's scenarios and stresses are run on it.

The cost and time of each run are agreed before it starts. Runs too heavy for the laptop go to the GCP VM.

Reported:
- E_ann, E_fun, the mix F / A, the scales and the book in policies;
- the funeral and annuity BELs, the SCR by risk (with the mortality and longevity charges and the diversification between them, to show how much of the offset SAM recognises), the risk margin and cover, beside v5's;
- the exposures to improvement 1 point a year faster, for both lines and in total at the chosen mix;
- the BEL change at the chosen mix for uniform changes of ±15% (the residual from the exposure's curvature);
- the sensitivities and variants, and every check, passed or failed.

**Attribution.** As v5. SARB, *Financial Stability Review*, 2026, Table B.2, for the median cover.
