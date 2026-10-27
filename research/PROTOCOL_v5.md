# Protocol: v5 The funeral mortality table, and a rising-benefit option

**A judged basis, not a tested one. Written on 27 October 2026, before any part of v5 was run in this repository.** Done beforehand, and disclosed here: the whole mortality method below was built outside the repository between 25 and 27 October 2026, on the same Stats SA and WPP data, while looking at its results, 2022 and 2024 included. Every choice in it was made with those results in view. So nothing below scores the table against data it has not seen, and no pass mark decides whether it is used: it is used because the user chose it, for the reasons given with each choice. Nothing in the book, v3 or v4 has been valued with it. Also done beforehand: FSI 4.1's interest rate volatility sections were read for the rising benefit. No inflation volatility was estimated and no option was valued.

Frozen at commit: `5039d84c999a` (27 October 2026)

The question: what do funeral policies cost, and what capital does the company need, when funeral mortality starts from 2024 and keeps improving, and half of the policies' benefits rise with inflation?

What changes and what does not:
- **Funeral mortality** is replaced: v3's 2017 to 2019 table, with no improvement, gives way to the table below.
- **Annuities** stay on v1, as v1.3 and v1.4 decided. v1.4's "pricing stays on v1" was about annuitant mortality; funeral was never priced on v1, but on v3's own table, which is what this replaces.
- **The book** keeps its seed and its policies. The one addition is a benefit type for each funeral policy. Premiums are repriced.
- **The dashboard** shows no mortality table, as before. Only its text on the funeral basis, the product and the data years is corrected.

## The mortality table

**Data.** Stats SA registered deaths from the DataFirst unit records: the 2010 to 2020 deceased and causes tables, and the 2021 to 2023 file, which holds deaths up to 2024. Deaths are counted by year of death, sex, single age 0 to 99 and underlying cause (ICD-10, first three characters). Stillbirths are dropped. Unknown sex and age are spread pro rata (`data.statssa`). The exposure is the WPP 2024 1 July population; 2024 comes from the medium variant's first projection year, the same source as the earlier years. 2023 is left out because its registered deaths are essentially missing. Any cause data is read from the zips in place, wherever they are; none of it is extracted into or committed to the repository.

**No completeness adjustment.** Rates are registered deaths over WPP population, as v3's table was. v1.4's 2024 check gave men's completeness as 0.787, below its 0.85 mark, and put women outside its stability band. If registration is incomplete, these rates are too low and the premiums too cheap. The death distribution methods (GGB, SEG) were tried and gave no level correction that held across periods and age ranges. This is a limitation, not a finding.

**1. The level: a graduated 2024 table.**
- Ages 0 and 1: the crude rates.
- Ages 2 to 80: Whittaker-Henderson on log m, weighted by deaths, with second differences. There are two smoothing levels, one for differences centred up to age 14 and one for 15 to 80, chosen together by UBRE: Σ D (y − z)² / φ + 2 · trace. Here φ is the overdispersion of deaths from year to year: Poisson straight lines in time at each age from 1 to 80, fitted over five-year windows centred on 2010 to 2017, with the Pearson χ² pooled over the degrees of freedom. There is one φ for each sex.
- Above 80: a Kannisto tail, m = c e^(dx) / (1 + c e^(dx)). It meets the table at 80.5 in value and slope. The slope is a straight-line fit to the graduated log m at 61 to 80, and d = slope / (1 − m(80.5)). Crude rates above 80 are not used, because registered deaths there drifted against WPP's population.

**2. The change from 2024: Lee-Carter by cause group.** Each group gets its own Poisson Lee-Carter, ln m_g(x, t) = a_g(x) + b_g(x) k_g(t) + c(t − x). It is fitted on 2012 to 2024 without 2020 and 2021 (Covid), at ages 0 to 85, by Newton steps (Brouhns, Denuit and Vermunt 2002). b sums to 1 and k sums to 0.
- **Groups.**
  - **HIV-related:** the codes of Groenewald et al. (*Identifying deaths from AIDS in South Africa*, AIDS 2005; 19:193–201, Tables 1 and 2), plus D84, E86 and J09.
    - D84 is there because HIV coding moved between D84 and B20–B24 after the paper's data.
    - E86 rose in the AIDS age pattern; the paper left it out only because its numbers were small.
    - J09 was created after the paper.
    - Every death in these codes counts, at every age. The paper counts only each condition's excess over 1996, but these data start in 1997 and have no pre-epidemic baseline.
  - **External:** V01–Y98.
  - **Other:** everything else.
  - **Ill-defined deaths** (R00–R99) are shared out pro rata over the other causes in their year, sex and age.
- **Smoothing.** a and b are penalised on their squared second differences from age 2 (Delwarde, Denuit and Eilers 2007), with one level for a and one for b in each group. Both are chosen on a grid by UBRE, with φ the Pearson overdispersion of the unsmoothed fit.
- **Cohort term.** One c by year of birth, shared by the three groups, at ages 50 to 85. It covers cohorts seen at least 3 times (born 1929 to 1969), sums to 0 and has no linear trend in year of birth.
  - It takes out a data artefact, not mortality. Its pattern is nearly the same in every group, injuries included. It spikes on round birth years (1940, 1950). And it sits high for cohorts born about 1938 to 1955.
  - It cancels in the change used in step 3.
  - It is fitted in turn with the groups (c by Newton steps on all groups' deaths, each group with c as an offset). The smoothing levels are chosen once, given the c of the unsmoothed joint fit.
- **Projection.** Each k is a random walk with drift, (k(2024) − k(2012)) / 12, starting from the fitted 2024. Two departures from the fitted trends:
  - external k has no drift: over 1997 to 2024 men's external rates both fell and rose;
  - other-cause b is floored at 0 from age 75, so these rates do not rise.
- **Only the central path is used.** The table is deterministic; no range is carried.

**3. The table from 2024 to 2050.**
- For x ≤ 80: m(x, t) = graduated 2024 m(x) × m_lc(x, t) / m_lc(x, 2024), with m_lc the sum of the three groups. So 2024 is the graduated table itself.
- For 81 to 120: a Kannisto tail, tied at 80.5 to that year's m at 80, with the 2024 slope from step 1 held for every year. If the slope were refitted each year, it would steepen as 61 to 74 improve while other-cause rates from 75 are held. That would raise every rate above 80.

**4. After 2050: improvement continues at each age's 2050 pace.**

    ln m(x, 2050 + n) = ln m(x, 2050) + n [ln m(x, 2050) − ln m(x, 2049)]

This runs for as long as any policy can, and nobody survives past 120.
- **Why.** Medicine, technology and research keep improving survival. A long-term price that stops improvement at a fixed year would be dearer than the market's. The 2050 pace is the model's own trend carried on, so no new number is set.
- **What it gives.** At working ages, from about 0.1% a year (men at 25) and 0.9% (women at 20) up to about 2.5% at 50 to 60. It falls to about 0.2% a year at 80 and above, where the 2012 to 2024 data show little improvement. The exception is men around 20, whose 2050 pace is a worsening of about 0.5% a year, so their rates keep rising. That is kept like the rest of the fitted pace. Each policy passes through those ages only once, if at all.
- **The direction of the risk.** More improvement makes funeral cover cheaper, and so less prudent. The SAM mortality stress, not this basis, carries the risk of being wrong.

**Features kept, and disclosed.** None of these is smoothed out. The premium is level for life, so it averages the risk over the whole term, and no customer sees a rate that moves with age.
- **Rates that fall with age.** In 2040 and 2050, m falls with age at men's 32 to 43 and women's 19 to 28. In 2024 and 2030 it does not. This comes from the cause split: the 2024 HIV hump at 30 to 45 falls by about 6% a year, while external causes, which dominate young men's deaths, are held.
- **Men's late teens and early 20s.** Their rates rise: at 20 the 2050 rate is about 12% above 2024. That is the fitted trend, kept.
- **Men's 72 to 75 in 2050.** m rises by 17% to 20% per year of age, because improvement fades between 70 and 78.
- **Full allocation to HIV-related.** Counting every death in the paper's codes, and not just the excess, gives the HIV-related group more deaths at 25 to 49 than the paper would. Those deaths then improve at the HIV pace, so improvement there is larger, and premiums cheaper, than with the excess only.

## Funeral on the table

- **Best estimate.** Ages and calendar years are whole years on the valuation date (25 September 2026), as in v3. A cell aged x then has the force μ(x + k, 2026 + k) in projection year k. The funeral adjustment is 1.0; the 0.8 and 1.2 sensitivities multiply the whole table.
- **Pricing basis.** Each premium is priced as if the policy started on the valuation date at its entry age, with rates along the cohort from 2026. v3 priced on a table with no dates, and the invented book has no history, so there is no earlier year to price from. Everything else is unchanged: 9% interest, 5% expense inflation, a 20% margin, no lapses, (1 − 0.2) P ä = A + E.
- **Stresses.**
  - Mortality +15%, permanent, on the new rates.
  - Catastrophe as in v3.
  - Longevity is still not applied to funeral, since it helps that line.
  - v4's S3 pandemic ratio is unchanged: crude 2021 over 2019 rates at 18 to 89.
- **v4.** Funeral mortality now moves along calendar years, as annuitant mortality already does: a cell's rates at year-end t are its rates from today's diagonal, t years on.

## The rising-benefit option

- **The book.**
  - Each funeral policy is level or rising, with probability one half each.
  - The draw uses its own generator (seed 20261028), after the book is generated, so every other field of the committed book stays the same.
  - `sum_assured` is the benefit on the valuation date. It is also the starting benefit the premium is priced on, since every policy is priced as if it started then.
  - The premium is level for life.
- **The increase.**
  - Once a year, on each anniversary of the valuation date, the benefit of a rising policy grows by that year's inflation. The increase is floored at 0%, so the benefit never falls, and capped at 6%.
  - This follows v3's whole-year steps, as the inflation-linked annuities do.
  - The 6% is the top of SARB's 3% to 6% target range, which applied over almost all of the book's issue years (2011 to 2026). Whether the target has since changed was checked and could not be confirmed; the cap does not depend on it.
- **Pricing.** The benefit grows at 5% a year, the pricing basis's inflation, which is below the cap.
- **The cap and floor are options, and they are valued as options.** Each year's increase is min(max(i, 0%), 6%), with i that year's inflation.
  - The cap is an option the policyholder gives the company: when inflation is volatile, the company's expected payments fall.
  - The floor is an option the company gives the policyholder: when inflation is volatile, the company's expected payments rise.
  - So a deterministic growth rate would be wrong both ways, and it would hide the interest rate volatility risk of FSI 4.1 §5.14 to 5.19. v3's statement that this risk is nil, because there are no options, no longer holds for the funeral line.
- **Inflation model, for the valuation.**
  - One-year inflation is i(t) = f + x(t), with f v3's 30-year breakeven held flat (6.87% on the valuation date), as v3 does for expense inflation.
  - x is a mean-reverting Gaussian process, x(t + 1/12) = φ x(t) + ε, starting at x(0) = 0. So the expected inflation in every year is f, and the valuation is centred on the market's breakeven.
  - φ and the volatility of ε are estimated by least squares on the one-year breakeven, (1 + nominal 1-year spot) / (1 + real 1-year spot) − 1, read from v4's two-factor curve fits at each month-end from January 2011 to September 2026. This follows §5.15's use of long-term realised data, since there are no swaption quotes this project can use. The 1-year point lies below every bond in the windows, so it is the fits' extrapolation, the same series v4 uses for realised inflation.
  - 10,000 paths, seed 20261029, monthly steps, out to the last year any policy can run.
- **The expected benefit.** G(n) is the expected growth factor of a rising benefit after n anniversaries: the mean over paths of Π (1 + min(max(i_k, 0%), 6%)), with i_k the inflation over the year before the k-th anniversary.
  - The book's deaths and lapses do not depend on inflation, so a rising policy's expected claim in year n is its level claim times G(n).
  - Claims are discounted on the nominal curve, as in v3. The correlation between inflation and nominal rates is left out and disclosed.
- **Pricing.** The benefit grows at 5% a year, the pricing basis's inflation, which is below the cap. The pricing basis is deterministic, as in v3.
- **The interest rate stresses.** Under each nominal and real curve stress, f is that stress's 30-year breakeven and the same process is used. The expense stress raises expense inflation only, not benefit growth.
- **Interest rate volatility risk (FSI 4.1 §5.16 to 5.18).**
  - Mkt_int_vol = max(0, the fall in own funds when the volatility of each year's inflation is increased).
  - The increase follows §5.18, with step (b)'s rise taken as the full 10 points. At term t, the standard deviation of i(t) rises by 0.10 f / √t: §5.17's 0.1 / √t on a lognormal volatility, turned into the normal process's terms at the forward f. It is applied by scaling each path's x(t) at term t, so the correlation between years is kept.
  - It is combined with the curve charge: Mkt_int = √(curve² + 2 · 0.5 · curve · vol + vol²) (§5.3).
  - It applies to the funeral line only, since the annuities hold no options.
- **Mitigation.**
  - **The cap is the mitigation, built into the product.** It makes the company long volatility, against the short floor, and it ends the company's exposure to inflation above 6%. Since the cap is near the money and the floor is far from it, the company is expected to gain when volatility rises, so the charge is expected to be nil. This is reported as calculated, whichever way it comes out.
  - **The inflation itself is hedged with bonds, as for the annuities.** The rising policies' expected claims are matched like an annuity's income, by v3's key-rate method: holdings in every nominal and inflation-linked bond in issue with at least a year to run. The holdings match the claims' best-estimate value and minimise the squared differences between the claims' and the portfolio's key-rate DV01s at 5, 10, 20 and 30 years on both curves (eight rows), on the unshocked curves. There is no shorting. The holdings are solved by non-negative least squares with the value as a heavily weighted row, then scaled to match the value exactly.
    - The claims' DV01s on each curve are found by moving that curve's key rate with the other curve held. G(n) is re-centred on the moved breakeven, so the inflation-linked bonds carry the claims' exposure to inflation up to the cap, and the nominal bonds carry what lies above the cap and the discounting.
    - The bonds are paid for from the 182-day bill. The premiums and expenses of every funeral policy, and the claims of level policies, stay in the bill, as in v3.
    - In v4, these holdings are rematched at each year-end with the annuities' (v4's management action), so they follow inflation as it moves.
  - **What bonds cannot hedge.** Bonds are linear in inflation, and the cap and floor are not. Bonds hedge the level of inflation, that is the curve risk, but not its volatility. No inflation option is in the universe of National Treasury bonds and bills. v4's yearly rematching is a rough dynamic hedge, nothing more.
  - **Reported both ways.** The SCR is also reported with the rising claims left in the bill (no hedge), so the effect of the hedge is visible.
  - **If the charge comes out positive,** so that the floor dominates, the same figures are also reported for a variant with the floor removed (increases capped at 6% with no floor at 0%). That shows what the floor costs in capital. The main result keeps the floor; whether to change the product is a separate decision.
  - Also reported, with the value of each option on the valuation date: G(n) with the cap and floor, with neither (fully inflation-linked), and with the cap only.
- **v4.**
  - Inflation in each of the five years is v4's realised one-year breakeven, and each rising benefit grows by it, path by path, between 0% and 6%.
  - At each year-end, the remaining increases are valued as above, by the inflation model centred on that year-end's 30-year breakeven.
- **Risk margin.** The driver S(t), the expected sum assured in force, includes the expected increases G(t).

## Checks

- **C1, the 2024 level.** The table's 2024 equals the graduated 2024 table to 1e-12.
- **C2, the port.** The repository's chain reproduces the table built outside it (`lcc_{sex}_table.csv`, 27 October 2026, 08:58), to a relative 1e-6 at every age and year. If it does not, nothing else is run until the difference is explained.
- **C3, the premium's shape.** Premiums rise with entry age from 18 to 64, for each sex and each benefit type. This is reported; failing it does not change the method.
- **C4, the valuation.** v3's K1 is extended: one rising policy is valued by a plain loop over months, and agrees with the main code to within 1e-8 of the BEL, unstressed and under every stress.
- **C5, a rising benefit with no growth is a level benefit.** With the cap at 0%, rising policies' premiums and BEL equal the level ones' exactly.
- **C6, only funeral moved.** The annuities' BEL and SCR equal v3's to 1e-8.
- **C7, the options vanish without volatility.** With ε set to 0, G(n) equals (1 + min(max(f, 0%), 6%))^n to 1e-12.
- **C8, enough paths.** The simulation's standard error of G(n) is reported. It is below 0.2% of G(n) at every n up to 50 years, or the number of paths is doubled until it is. Doubling changes nothing else.

## Reruns and reporting

As v1.3 planned for after mortality is final, everything downstream is run once, in this order:
1. the table chain;
2. the book (premiums and benefit types);
3. v3;
4. v4;
5. the capital levels of R400 million, R500 million and R627 million.

v2's annuity prices do not depend on funeral, so they are not rerun. The cost and time of each run are agreed before it starts. Runs too heavy for the laptop go to the GCP VM.

Reported:
- monthly premiums per R10,000 at entry ages 20, 30, 40, 50 and 60, by sex and benefit type, beside v3's;
- the funeral BEL, the SCR by risk, the risk margin and cover at R400 million, beside v3's;
- the inflation model's φ and volatility, G(n) with and without the cap and floor, the options' values, Mkt_int_vol and its effect on Mkt_int (and the variant with no floor, if the charge is positive);
- v4's share of scenarios covered, and the funeral line's IFRS 17 figures;
- the 0.8 and 1.2 sensitivities;
- every check, passed or failed.

**Attribution.** Statistics South Africa, *Mortality and Causes of Death*, unit records, produced by Stats SA and distributed by DataFirst, University of Cape Town (CC BY). UN *World Population Prospects 2024* (CC BY 3.0 IGO). Groenewald et al. 2005, for the HIV-related causes. National Treasury bond auction results, for the inflation model, as in v2 and v4 (non-commercial use, with acknowledgement). Prudential Authority, FSI 4.1 (version 1, 1 July 2018), §5.3 and §5.14 to 5.19, read from the Internet Archive's copy of the PA's standards zip (20 April 2022), as in v3.
