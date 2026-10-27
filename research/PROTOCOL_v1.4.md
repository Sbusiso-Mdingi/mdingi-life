# Protocol: v1.4 Liabilities, a chain of graduated base tables with mortality jumps (exploratory)

**Exploratory. Written on 26 October 2026 and frozen on 27 October 2026, before any v1.4 model fit to real data.** v1.3's plan called itself the last mortality iteration. This version reopens that at the user's request, as an exploratory study. **Pricing stays on v1 for both sexes unless v1.4 passes every mark set below.** v1 to v1.3 stand as reported.

Amended twice on 26 October 2026, both times before the freeze and at the user's request:
- **First amendment:**
  - the central price is trend-only;
  - HIV handling is judged on outcomes;
  - Covid separation is a measured rule;
  - the Covid link is judged against the same model with no jump term;
  - v1.4 cannot price without the 2024 link;
  - the 2024 exposure caveat is added;
  - the tests are stated in full.
- **Second amendment:**
  - the primary model is Liu and Li's Model J1 (one-year jumps with their own age pattern), and the decaying jump is reported beside it and can never price;
  - the separation rule is restated for one-year jumps;
  - both papers have been read, and the references are settled;
  - the whole plan was reread, and leftover contradictions from the earlier edits were removed (listed at the end, under "Pre-freeze record").

Changed once more on 27 October 2026, before the freeze, at the user's request and **after seeing the simulated test results** (see "Pre-freeze change, 27 October 2026"):
- the flag cutoff, the absorbed share's definition and threshold, and the trend test's band were calibrated on simulated data;
- a 2024 pricing condition against a permanent-shift model was added.

Nothing in v1.4 had been fitted to real data before any of these changes.

Frozen at commit: 442508e4fb728513ca2eddd3401f627e78c6f3dd (27 October 2026)

## The question

Can a projection that starts from a graduated base table, with a trend fitted on the whole record from 1997 and pandemics modelled as jumps, forecast South African deaths at ages 50 to 89 better than v1? And can it be trusted to price pensions from 2022 onward, refitted each time a new base table is made?

## Seen beforehand, and disclosed

- Everything in `RESULTS.md` and `RESULTS_v1.1.md` to `RESULTS_v1.3.md`. That includes one close relative of this design. Lee-Carter fitted on 2006 to 2016 had its starting level reset to the 2014 to 2016 average, smoothed over five ages; v1.1 called it "anchored LC". It scored as follows on 2017 to 2019:
  - men: deviance 5,396 against B0's 6,450, coverage 80.8%, annuity error 2.56%;
  - women: deviance 4,512 against 5,822, coverage 93.3%, annuity error 0.79%.

  At the 2014 to 2016 check, men's coverage was 87.5% and women's 95.0%. Those runs used completeness-scaled deaths.
- **Registered deaths at all ages, by year of death,** in `mcd_deaths.csv`. Seen in this session:

  | Year | Deaths |
  | --- | --- |
  | 2019 | 468,247 |
  | 2020 | 516,546 |
  | 2021 | 621,790 |
  | 2022 | 487,542 |
  | 2023 | 6,693 |
  | 2024 | 474,366 |

  No age-by-age 2024 rate has been computed or looked at.
- Registration completeness against WPP, from `completeness.csv`: rising to about 93% to 99% in 2003 to 2009, then falling to about 89% to 90% by 2019.
- The size of the Covid excess, about +33% in 2021 against 2019 at all ages. The jump-size prior below is set without reference to it.
- **The two papers** (see "References"), read before the freeze. Neither uses South African data.
- **The layout of Stats SA's mid-year estimates workbook** (`p0302_country_projection_2002-2025.xlsx`, already on disk): its sheet, columns and age groups. None of its 2024 numbers has been looked at.

**Hold-out reuse.**
- **2017 to 2019 has guided four earlier versions.** v1's model and window, and the choice to keep v1, were all settled with 2017 to 2019 in view. A score there therefore favours v1, so the L3 comparison is not a fair contest. It is kept because the user asked for it, and it is read with that bias in mind.
- **2020 to 2022 has been seen in total.**
- **2024 is the only period no model has been scored on.** It is the one clean test. **If L5 cannot be scored, v1.4 does not price** (see "2024").

## Data

- **Deaths:** Stats SA registered deaths (DataFirst unit records), by single age, sex and year of death. They are unscaled, as in v1's pricing run. Completeness-scaled deaths are a sensitivity.
- **Exposure:** WPP 2024's 1 July population, for 1997 to 2022.
- **Ages:** 50 to 89 for every fit and score. Graduation also uses 45 to 49 (see "Graduation"). Above 89, rates follow v1's Kannisto extension, fitted on ages 80 to 89, up to 120.
- **2023 is never used.** For 2024, see below.

## The model

For each sex, with t the calendar year:

  log m(x,t) = a(x) + b(x)·K(t) + bᴶ(x)·N(t)

- **a(x)** is the link's graduated base table. It is fixed, not re-estimated (see "Graduation").
- **b(x)K(t)** is the trend.
  - b(x) sums to 1, and a(x) is not centred, so K = 0 at the base level.
  - K(t) is a random walk with drift μ and volatility σ, and contains no jumps.
- **N(t)** is the jump effect, and **bᴶ(x)** is the jump's own age pattern.
  - bᴶ(x) is normalised to a **mean of 1 over ages 50 to 89**, so N(t) reads as the average rise in log death rates. Where no age pattern has been estimated, bᴶ(x) = b(x) / mean(b).
  - I(t) is 1 in a jump year. It is Bernoulli with probability p, fixed from outside, with at most one jump a year.
  - Y(t), the jump size, is Normal(μ_Y, σ_Y²).

### The primary model: one-year jumps (Liu and Li's Model J1)

N(t) = I(t)·Y(t). A jump raises rates in its own year only.

- This is Model J1 of Liu and Li (2015). With bᴶ = b / mean(b), it is their Model J0, which is Chen and Cox's (2009) transitory jump model.
- **J1 is the only v1.4 model that can price.**

### The decaying variant: reported beside J1 at every link

N(t) = ρ·N(t−1) + I(t)·Y(t), with 0 ≤ ρ < 1. A jump's effect falls by a factor ρ each year after it.

- **No paper read for this plan defines it.** It is described in words only (see "References").
- **It is reported beside J1 at every link, on every score. It cannot replace J1 for pricing, even if it scores better.** Decided now, before any fit.

### References

- **Chen, H. and Cox, S. H. (2009).** Modeling mortality with jumps: applications to mortality securitization. *Journal of Risk and Insurance* 76(3), 727–751. doi:10.1111/j.1539-6975.2009.01313.x.
  - Read on 26 October 2026, from the user's copy.
  - Their transitory model is k(t) = k̃(t) + N(t)Y(t). k̃ is a random walk with drift, N is Bernoulli(p) with at most one jump a year, and Y is Normal(m, s²). The jump enters k(t), so it takes the trend's b(x).
  - They also fit a permanent-jump model, after Cox, Lin and Wang (2006), and prefer the transitory one.
  - Their estimation: Lee-Carter in two stages (SVD, then k(t) refitted to total deaths each year), then conditional maximum likelihood on the year-to-year changes in k, with p estimated.
- **Liu, Y. and Li, J. S.-H. (2015).** The age pattern of transitory mortality jumps and its impact on the pricing of catastrophic mortality bonds. *Insurance: Mathematics and Economics* 64, 135–150. doi:10.1016/j.insmatheco.2015.05.005.
  - Read on 26 October 2026, from the accepted manuscript (the user's copy).
  - Model J0 is Chen and Cox's model. Model J1 gives the jump its own age pattern β⁽ᴶ⁾(x), with Σβ⁽ᴶ⁾ = 1. Model J2 makes the age pattern random; it is not used here.
  - All their jumps are transitory.
  - Their estimation: "Route II" (Haberman and Renshaw, 2012). That is conditional maximum likelihood on year-to-year changes in log rates, with Normal errors, every parameter in one step, and p estimated. α(x) is never estimated, and projections start from the last observed rates.

**How v1.4 compares with them:**
- **The jump structure matches.** J1 here is their Model J1, and J1 with bᴶ = b / mean(b) is their J0. The mean-1 normalisation, against their sum-1, only rescales Y: ours is theirs divided by 40.
- **The estimation differs:**
  - deaths are Poisson with dispersion, not Normal on log rates;
  - a(x) is a graduated base, held fixed;
  - the fit is staged (steps 1 to 3 below);
  - the jump likelihood is exact, not conditional;
  - p is fixed from outside;
  - bᴶ is estimated only from flagged Covid years.
- **The decaying jump** is in neither paper. Chen and Cox's alternative is a permanent jump, which is a different thing.

**Naming on public pages.**
- The site and Methods describe what was fitted, in words and with the equation above.
- Liu and Li (2015) are cited for the jump structure: "one-year jumps with their own age pattern, as in Liu and Li's (2015) Model J1, estimated differently". The differences are listed.
- Chen and Cox (2009) are named only as the source of the transitory jump that Liu and Li extend.
- The decaying variant is described as "a variant in which a jump's effect falls by a fixed fraction each year", and no paper is named for it.
- **The Covid separation rule is described on the Methods page as a sanity check that does not tell the correct model from the wrong one.** In simulation it passed 83.5% of series where Covid was one-year jumps and 94% where Covid was a permanent shift. It is never described as evidence that Covid was a jump. That question rests on 2024 (pricing condition 6).
- If the user finds a paper that defines it, the paper goes into this section as a dated addition, and the model is not changed.

## Estimation, at every link, in a fixed order

1. **The period index.** Poisson maximum likelihood of log m = a(x) + b(x)κ(t) on every year from 1997 to the link's last year, with a(x) held at the link's base and Σb = 1. Each κ(t) is free, so it carries trend, HIV and pandemic effects together.
2. **The jump time series,** on the changes Δκ(t) from step 1. Until step 3, the jump's age pattern is b / mean(b), so a jump of size Y adds Y / mean(b) to κ. The first year of the window is taken to be jump-free.
   - **J1:** Δκ(t) = μ + σZ(t) + (I(t)Y(t) − I(t−1)Y(t−1)) / mean(b). The likelihood is computed **exactly**, summed over every pattern of jump years.
     - Every jump-free year splits the series into independent blocks, so the sum is computed by a forward-backward pass over those blocks, with no cap on the number of jumps.
     - This is the same likelihood Chen and Cox maximise conditionally.
   - **Decaying variant:** given the jump years, Δκ is Gaussian. The likelihood is summed over every set of at most **4 jump years**, and the share of posterior probability left out is reported.
     - That share is estimated as the posterior mass on sets of 5 jumps, out of all sets of at most 5.
     - If it exceeds 1%, the fit is redone with a cap of 6, and the share is re-estimated on sets of 7.
   - **Fitting:** by maximum likelihood (L-BFGS-B), from two starting jump sizes when jump sizes are estimated: the prior's, and the largest change in κ over c. The better fit is kept.
     - σ̂ and σ̂_Y are bounded below at 10⁻⁴, and ρ̂ lies between 0 and 0.99.
     - With one pandemic in the window, σ_Y is barely identified. An estimate at the bound is reported as such.
   - **Output:** μ̂ and σ̂ (and μ̂_Y, σ̂_Y and ρ̂ where they are estimated); each year's posterior jump probability; and K̂(t) = κ(t) minus the posterior mean of the jump in κ.
3. **The jump age pattern (J1, and the variant alike).**
   - **A year is "flagged" if its posterior jump probability is above 0.95.** This cutoff is used everywhere in this plan. It was 0.5 until the pre-freeze change, and was set on simulated data (see "Pre-freeze change").
   - Let F be the flagged years in 2020 to 2022. For t in F, bᴶ(x) and N(t) are fitted by Poisson maximum likelihood, with log m = a(x) + b(x)K̂(t) + bᴶ(x)N(t), K̂ held from step 2, and mean(bᴶ) = 1.
   - Step 1 is then refitted once, with bᴶ(x)N̂(t) as a fixed offset in the F years. b(x) and κ*(t) are taken from this refit.
     - K̂(t) = κ*(t) for t in F.
     - For other years, K̂(t) = κ*(t) minus c times the step 2 posterior mean jump, with c = 1 / mean(b), and N̂(t) is that posterior mean.
     - **There is no further iteration.** μ̂, σ̂, μ̂_Y, σ̂_Y, ρ̂ and the posteriors all stay at their step 2 values.
   - **For the decaying variant**, N(t) is fitted freely in every year from the first flagged year in 2020 to 2022 through 2022, because a decaying jump carries into the following years.
   - If F is empty, there is no bᴶ step, and bᴶ = b / mean(b).
   - Flagged years outside 2020 to 2022, including HIV-era years, are reported. They get no age pattern of their own and count neither for nor against the model; HIV is judged on outcomes (see "The comparison with v1").
4. **Dispersion.** φ is the Pearson χ² of the step 1 fit over its residual degrees of freedom, floored at 1, as in v1.1.
5. **Uncertainty: 500 refits, 5,000 paths,** with v1.1's bootstrap.
   - Deaths are redrawn with dispersion φ from the fitted rates, for the base years and the whole window.
   - a(x) is re-graduated with λ held at the link's own value, and steps 1 to 3 are refitted.
   - Each refit then simulates K forward, and jumps where the projection includes them.

### Which jump parameters are estimated at each link

| Link | Fit window | p | μ_Y, σ_Y | ρ (decaying variant only) | bᴶ(x) |
| --- | --- | --- | --- | --- | --- |
| L1 to L4 (no pandemic in the window) | 1997 to 1999, 2006, 2012, 2019 | fixed, 1 in 30 | fixed at the prior | fixed at the prior | b(x) / mean(b) |
| L5 and the pricing fit (Covid inside) | 1997 to 2022 | fixed, 1 in 30 | estimated | estimated | estimated from F |

For J1, ρ = 0 always. **Sensitivities:** p = 1 in 15 and 1 in 60 at every link, with everything else unchanged.

### The jump prior (L1 to L4)

- **Central value:** μ_Y = 0.10 (about +10% on death rates in a jump year) and σ_Y = 0.05. For the decaying variant, ρ = 0.5.
- **Basis:** the 1957 and 1968 influenza pandemics, whose excess mortality was in the order of +5% to +10% of a normal year's deaths in the countries with records.
  - **This is a stated judgement, not a cited figure.** No source was checked for it before the freeze, and it is described that way on any public page.
- **Not set from Covid.** Covid's size has been seen, so it is not used.
- **Sensitivities:** μ_Y = 0.05 and 0.30. The upper value is a 1918-type pandemic.

## Graduation

Whittaker-Henderson on a Poisson likelihood:

- **Inputs:** deaths and exposures pooled over the three base years, by single age **45 to 89**. Ages 45 to 49 only steady the lower end, and are dropped after graduation.
- **Method:** log m minimises the Poisson deviance plus λ·Σ(Δ²log m)², where Δ² is the second difference over age. With heavy smoothing, the curve tends to a Gompertz line.
- **Choosing λ:** by BIC = deviance + log(n)·ED, over the grid 10⁰, 10^0.25, …, 10⁸. ED is the trace of the hat matrix, and n = 45.
- **λ is chosen once per base and sex,** then held fixed in that link's refits.
- **Reported for each base:** λ, ED and the standard graduation tests, as checks, not pass marks:
  - χ² against the crude rates;
  - the signs test;
  - the runs test;
  - the largest absolute standardised deviation;
  - cumulative deviations over 50 to 69 and 70 to 89.
- **b(x) and bᴶ(x) are not smoothed.** That would be a second change. Their roughness (the sum of squared second differences) is reported.

## The chain

Each link fits every year from 1997 to the end of its newest base, and projects to the next base.

| Link | Base, graduated | Fit window | Projects to and scored on | Counts? |
| --- | --- | --- | --- | --- |
| L1 | 1997 to 1999 | 1997 to 1999 | 2004 to 2006 | No: starting anchor, reported only |
| L2 | 2004 to 2006 | 1997 to 2006 | 2010 to 2012 | No: reported only |
| **L3** | **2010 to 2012** | **1997 to 2012** | **2017 to 2019** | **Yes** |
| **L4** | **2017 to 2019** | **1997 to 2019** | **2020 to 2022 (Covid)** | **Yes**, on Q2ᴿ only |
| **L5** | **2017 to 2019** | **1997 to 2022** | **2024** | **Yes**, and required (see "2024") |
| Pricing | 2017 to 2019 | 1997 to 2022 | 2026 on | Gate only |

**The backtest projections (L1 to L5) include jumps** at the link's p, μ_Y and σ_Y, because they are judged on whether their ranges hold what happened. **The central pricing projection does not** (see below).

**The base for the 2022 projection is 2017 to 2019,** graduated from years without Covid.
- Covid goes in the jump term, not the base. The trend and jump parameters are fitted on 1997 to 2022, and steps 2 and 3 separate Covid by estimation.
- A 2020 to 2022 base is ruled out: it would put the jump into a(x) and count Covid twice.
- The pricing fit is L5's fit. It is refitted whenever a new base table is made.

### The Covid separation rule, decided now

For each sex, on L5's J1 fit. **Amended before the freeze on 27 October 2026** (see "Pre-freeze change"). The original rule is kept below for the record.

- **The absorbed share uses step 2's posterior mean jump effect, with no flags.**
  - On step 1's index κ, the jump-free trend is K⁰(t) = κ(t) − c·E[N(t)], with c = 1 / mean(b).
  - **The trend line** is a(x) + b(x)·[K⁰(2019) + μ̂·(t − 2019)], for t = 2020 to 2022.
  - **The excess** is observed deaths minus the trend line's deaths, summed over ages 50 to 89 and 2020 to 2022.
  - **The deaths the jump term adds** are the deaths at a(x) + b(x)κ(t), minus those at a(x) + b(x)K⁰(t).
  - **The absorbed share** is the deaths the jump term adds, over the excess. A trend that moves up with Covid lowers the share.
- **The trend test** uses the final K̂ (after step 3): K̂(2022) against K̂(2019) + 3μ̂.

**The separation passes if both of these hold:**
1. **the trend does not move with Covid,** the main criterion: K̂(2022) lies within **2.31·σ̂·√3** of the trend line's 2022 value;
2. **the absorbed share is at least 45%.**

If either fails, the separation has failed: this is reported, and v1.4 does not price.

**How the numbers were set.** The 2.31 and the 45% were calibrated on simulated data, on seeds apart from the unit tests' (`research/v14_calibration.py`):
- 2.31 is the narrowest band that passes 90% of correct-model series. The band a three-year random walk would give, 2, passed 72%.
- 45% is the highest threshold, on a grid of 30% to 95% in steps of 5, at which the whole rule passes at least 80% of correct-model series.
- The correct model has one-year jumps of 0.10, 0.30 and 0.08 in 2020 to 2022. **That shape was chosen knowing what Covid looked like,** so the calibration is not an out-of-sample result.

**What the rule cannot do.** Data that end in 2022 cannot tell a permanent Covid shift in the trend from one-year jumps in 2021 and 2022: the fall that would follow a one-year jump is never observed. In the calibration, the wrong model (the same rise kept permanently in the trend) passed the whole rule in 94% of series, against 83.5% for the correct model. So **passing the separation rule does not show that Covid was a jump.** That question is left to 2024 (pricing condition 6).

*The original rule, replaced before the freeze:* the absorbed share (with the jump term's deaths from the step 3 fit, and 0 in unflagged years) had to be at least 75%, at least one of 2020 to 2022 had to be flagged at the 0.5 cutoff, and K̂(2022) had to lie within 2·σ̂·√3 of the trend line.

**A forecast returning to trend is automatic for J1.** One-year jumps leave no effect after their year, so the earlier "under 1% by 2030" check is met by construction and is dropped. For the decaying variant, the median remaining effect N(2030) is reported.

**2022 is the case to watch.** Its excess was smaller than 2021's, so the posterior may not flag it. If it is not flagged, only its posterior mean jump is taken out of K̂(2022), and most of its excess can stay in the starting level of the projection. The trend test is there to catch this. In the calibration, with a true 2022 jump of 0.08, it was rarely flagged. Whether or not either test fails, each of 2020 to 2022 is reported separately: its posterior, N̂(t), its absorbed share, and K̂(t) against the trend line.

### The pricing projection

- **The central price is trend-only.** It starts in 2022 from K̂(2022), and **no future jumps are simulated.** With J1, Covid's effect ends with 2022.
- **Why.** A jump raises death rates, which shortens pensions. Simulating future jumps would therefore lower the pension liability, and so the price. An insurer pricing annuities should not take credit for future pandemics, so they are left out of the central price.
- **The price with future jumps** (p = 1 in 30, and 1 in 15 and 1 in 60) is reported as a sensitivity. It is expected to be lower than the central price.
- The gate and the pricing rule use the central price only.

## How the chain is judged

At each counted link, for each sex, the model is scored against **crude deaths** in the target years, ages 50 to 89. Graduated tables are for display only.

- **Q1, beats no improvement.** Poisson deviance is below B0's. B0 is **the link's base period's crude rates, held flat.**
- **Q2, coverage.** Between **90% and 98%** of cells lie inside the 95% interval. Observation noise is added at dispersion φ, as in v1.3.
  - That is 108 to 117 of 120 cells for a three-year target, and 36 to 39 of 40 for 2024.
  - The interval's mean width (upper rate over lower) is reported beside each figure.
- **Q3, annuity error.** The mean absolute error of the period annuity factor at 65 (4%) is under **2%**.

**L3 and L5 are judged on Q1, Q2 and Q3.**

**The Covid link (L4) is judged differently, decided now.**
- **Its mark is relative, Q2ᴿ.** The jump model's 95% intervals must cover at least as many 2020 to 2022 cells as the same model with no jump term. That comparison model has p = 0, with the same a(x), b(x), K and φ, and the same bootstrap. Both coverages and both widths are reported.
- **Absolute coverage (90% to 98%), Q1 and Q3 are reported, not counted.**
  - No forecast median contains a pandemic, and Covid raised death rates by 10% to 35%. So the median-based Q1 and Q3 fail for any trend model, and flat rates (B0) sit closer to a pandemic than any improving forecast.
  - **A miss on absolute coverage is expected.** At L4 the jump size is fixed at the prior of about +10%, with p = 1 in 30, so only about 3 in 100 simulated years hold a jump. With that prior the ranges cannot reach 2021, and they are not tuned to.
- **A miss on Q2ᴿ blocks pricing.** If adding the jump term makes the ranges cover fewer Covid cells than leaving it out, the jump term adds nothing, and v1.4 does not price. A miss on absolute coverage at L4 does not block pricing.

**The plausibility gate, on the central pricing projection.**
- Women's price at 65 (median, 4%, annuitant factor 0.7) must be above men's.
- The median e65 must rise by at least 0.25 years from **2026 to 2036** for each sex. The window starts in 2026, not 2022, so the end of the Covid effect does not count as improvement.

## The comparison with v1, and what counts as a pass

v1 is Renshaw-Haberman post-peak: fitted from 2006, with the Covid years left out, on unscaled deaths.

- **Its links:**
  - L3: fit 2006 to 2012, scored on 2017 to 2019;
  - L4: fit 2006 to 2019, scored on 2020 to 2022;
  - L5: the same fit, scored on 2024.
  - v1 has no L1 or L2, because it cannot be fitted before 2006.
- **Same scores:** Q1 to Q3 and Q2ᴿ's absolute coverage, with observation noise at v1's own φ, so the comparison is about the model, not the scoring. That differs from v1's original P3, which used process noise only, and the difference is stated.
- **Its B0:** the same as the chain's.

**Decided now: the 1997 origin handles the HIV years if, for both sexes, at L3, the chain passes Q1, Q2 and Q3, and its deviance is below v1's.** This is judged on outcomes only.
- If the chain passes Q1 to Q3 but its deviance is above v1's, it is reported as **"no better than v1"**.
- If it fails any of Q1 to Q3, it is reported as **"does not handle the HIV years"**.
- **The flagged years from 1997 to 2012** are reported at every link, with their posteriors, but they do not enter the judgement.
- As stated under "Hold-out reuse", L3 is scored on 2017 to 2019, which favours v1.

**v1.4 (J1) prices a sex from 2022 only if all of the following hold:**

1. **L5 is scored** (see "2024"), and the sex passes it on Q1 to Q3;
2. it passes L3 on Q1 to Q3, and L4 on Q2ᴿ;
3. its deviance, summed over L3 and L5, is below v1's (L4 is left out, for the reason given above);
4. the Covid separation rule passes for that sex;
5. the gate passes on the central pricing projection, for both sexes together. If only one sex passes 1 to 4 and 6, the mixed set (that sex on v1.4, the other on v1) is gate-checked as a set, as in v1.3;
6. **Covid was a jump, not a permanent shift, as judged on 2024** (added before the freeze on 27 October 2026). On 2024's crude deaths at ages 50 to 89, J1's median forecast has a lower Poisson deviance than the permanent-shift model's.
   - Both are fitted on 1997 to 2022, without 2024, with the same a(x), b(x) and μ̂.
   - J1's median 2024 index is K̂(2022) + 2μ̂: Covid ends with 2022.
   - The permanent-shift model's is κ(2022) + 2μ̂, where κ is step 1's free period index: the whole 2022 level, Covid included, is carried into the trend. Chen and Cox (2009) fit a permanent-jump model of this kind. This one is simpler, and their paper is not cited for it.
   - **"Beats" is defined now.** Let the gap G be the shift model's 2024 deviance minus J1's, so a positive G favours J1.
     - Its sampling uncertainty comes from 1,000 simulated 2024 data sets under each model. Each one takes a path from that model's L5 bootstrap (parameter and process uncertainty) and draws deaths from it at dispersion φ. G is computed on each data set, against the same two medians as the observed G.
     - **J1 beats the shift model only if the observed G is above the 95th percentile of G simulated under the shift model.** That is a one-sided 5% test of "Covid was a permanent shift".
     - Otherwise the gap is within its sampling uncertainty, and **v1.4 does not price**.
     - Reported: the observed G, and the 2.5th, 50th and 97.5th percentiles of G under each model. When both models give similar ranges of G, 2024 cannot tell them apart, and that is said.
   - **Sensitivity to completeness.** G and its test are also computed with 2024's deaths scaled, for each sex, to the 2022 ratio of registered to WPP deaths. **If J1's pass or fail flips under that scaling, the outcome is "does not price".** The reason: in 2024 the two models differ by roughly the size of the Covid excess left in the 2022 level. A change of a few points in registration completeness moves 2024 deaths by about as much, so it could decide the test on its own.
   - **Power, reported before 2024 is scored.** Once the L5 fits exist, and before any 2024 death is scored, the share of J1-simulated data sets whose G exceeds the 95th percentile of G under the shift model is reported, for each sex. **If it is under 50%, 2024 cannot tell the two models apart, and v1.4 does not price.** The power is reported in either case.
   - If 2024 cannot be scored, v1.4 does not price (see "2024").

**Otherwise v1 stays,** with ranges marked as lower bounds. The decaying variant's results never enter this rule.

If v1.4 prices either sex, the downstream chain (v2 prices, v3 balance sheet and SCR, v4 projection and capital levels) is rerun once. Its cost, time and the VM start are agreed with the user beforehand.

## 2024

- **Population:** WPP 2024's medium-variant projection for 2024, by single age and sex, from the UN Population Division. It is the same release as the estimates already used. It is a projection, and that is stated.
  - It is downloaded after the freeze, by the same route as the existing WPP files (`research/fetch.py`).
  - Only South Africa's rows are kept.
- **Completeness check, before L5 is scored:** registered deaths at ages 50 to 89 in 2024, divided by WPP's projected 2024 deaths at those ages.
  - **85% or more for each sex** (2019 was about 89% to 90%): L5 is scored.
  - **Below 85%:** 2024 is taken as not yet fully registered. L5 is reported but cannot be scored, and **v1.4 does not price.** L3 and L4 alone are not enough, because L3's period favours v1 and L4 is judged only relatively.
  - **It must also be stable** (added before the freeze on 27 October 2026, with the band set before any 2024 ratio was looked at). For each sex, the 2024 ratio is compared with the same ratio for 2019 and for 2022 (registered deaths at ages 50 to 89 over WPP's deaths at those ages, from WPP's estimates for 2019 and 2022). **2024 is scored only if its ratio is within 2 percentage points of both.** Otherwise L5 is reported but cannot be scored, and v1.4 does not price.
  - All three ratios are reported for each sex.
- **The exposure caveat.** The 2024 population is a projection, not an estimate.
  - WPP 2024's estimates end in 2023, and 2024 is projected from them. If its view of Covid deaths at older ages, or of migration, is wrong, the population at ages 50 to 89 is wrong.
  - An error in exposure passes one-for-one into the 2024 death rates: a population 3% too high makes rates look 3% too low.
  - The completeness check uses the same WPP release, so it cannot catch this. The caveat is printed beside every L5 result.
- **Sensitivity: Stats SA's mid-year population estimates for 2024**, from `p0302_country_projection_2002-2025.xlsx`, already on disk.
  - It comes in five-year groups by population group, summed here over population groups. The group 80+ is open.
  - Each group is split to single ages in WPP 2024's 2024 proportions within the group. For 80+, the split is over WPP's ages 80 and up, and 80 to 89 are kept.
  - L5 is rescored on it and reported beside the main result. It is not counted.
  - **The pass or fail uses WPP,** decided now, so that the population cannot be chosen after seeing the scores. If the two populations give the same pass or fail, that is said. If they disagree, that is said prominently, and the result is labelled fragile.
- **2024 is never fitted.** It is only scored.

## Reporting

For every link and both sexes, for J1 and the decaying variant, and for the three values of p:

- the graduated base, with its λ, ED and graduation tests;
- b(x) and bᴶ(x), with their roughness;
- κ(t), K̂(t) and N̂(t);
- μ, σ, μ_Y, σ_Y and ρ, and which were fixed and which estimated;
- each year's posterior jump probability, and the flagged years;
- for the decaying variant, the share of posterior probability outside the jump cap;
- Q1 to Q3 against B0 and v1, with interval widths; at L4, also Q2ᴿ, and the no-jump model's coverage and width;
- the Covid separation rule's measures, overall and for each of 2020 to 2022; for the decaying variant, also N(2030);
- at L5, the 2024 deviance of J1 and of the permanent-shift model;
- for the central pricing projection: prices at 55, 65 and 75 (2%, 4% and 6%; annuitant factor 0.6, 0.7 and 0.8), and e65 in 2026, 2036 and 2056.

**Sensitivities** (each reported, none counted):
- completeness-scaled deaths;
- the jump prior at μ_Y = 0.05 and 0.30;
- the price with future jumps;
- L5 on Stats SA's 2024 population.

**Running it:**
- **Code:** `research/v14.py`, with `mdingilife/graduation.py` and `mdingilife/jumps.py`.
- **Output:** `research/results/v14.json`.
- **Seed:** 20261031. **Runs on:** the Mac.
- **Guard:** `PROTOCOL_V1_4` in `mdingilife/protocol.py`. No model fits until this file is frozen.

### Unit tests, written and run before the freeze, on simulated data only (`tests/test_v14.py`)

- **Whittaker-Henderson:**
  - it recovers a known Gompertz-plus-hump curve from Poisson deaths at WPP-sized exposures pooled over three years, to within 0.05 in log rate at every age from 50 to 89;
  - a very large λ gives a Gompertz line (second differences below 10⁻⁴);
  - λ = 0 returns the crude rates.
- **The jump likelihood:**
  - J1's block computation matches brute-force enumeration of every jump pattern on a 10-year series, to 10⁻⁸;
  - the decaying variant's capped sum matches brute force when the cap is the series length;
  - both posteriors match brute force.
- **The simulated data,** for the remaining tests:
  - Poisson deaths at ages 45 to 89 for 1997 to 2022, with WPP-sized exposures for men (about 330,000 at 45, falling to about 5,000 at 89);
  - a Gompertz-plus-hump a(x) at the 2017 to 2019 base, and a b(x) that falls with age;
  - K(t), a random walk with drift −0.01 and σ = 0.02 in average log rate;
  - each test uses 200 series, from seed 20261031.

  The full pipeline (graduation, then steps 1 to 3 as for L5) runs on each series.
- **Recovery, J1:** one jump in 2021 of size 0.3, with a true bᴶ(x) that rises with age. **It passes if:**
  - 2021 is flagged in at least 90% of series;
  - the median N̂(2021) is within 0.05 of 0.3;
  - the median correlation of b̂ᴶ with the true bᴶ is at least 0.9;
  - the separation rule passes in at least 80% of series.
- **Recovery, decaying variant:** the same jump with ρ = 0.5. It passes if the median ρ̂ is within 0.15 of 0.5. On the J1 data (ρ = 0), the median ρ̂ must be below 0.15.
- **No false jumps, on data without any:**
  - **(a) plain:** the trend above, with no jump;
  - **(b) HIV-like hump:** a smooth rise and fall added to the trend, shaped like a raised cosine. It is +0.35 in average log rate at its peak in 2006, and zero in 1997 and from 2016. It is spread over ages as the trend is.

  **Each passes if at most 10% of series have any flagged year.** The number of flagged years per series is reported. If (b) fails, that is a finding (the jump term would absorb an HIV-like hump). The model is not changed for it, and the result is written below before the freeze.
- **The same no-jump data with the jump prior fixed** (as at L1 to L4), reported only. This was added while the tests were being written, after a trial run on 3 to 5 series showed false flags in the L5 setting. It does not replace (a) or (b).
- **Covid-shaped data:** jumps of 0.10 in 2020, 0.30 in 2021 and 0.08 in 2022 (J1). Reported: how often each year is flagged. Reported only until the pre-freeze change; since then, **the separation rule must pass in at least 80% of series**.
- **Permanent shift, reported only:** the same rise kept permanently in the trend (+0.10 in 2020, +0.30 from 2021). How often the separation rule passes is reported; there is no pass mark (see "What the rule cannot do").

The results are recorded below, under "Pre-freeze record".

## Pre-freeze record

### Fixes from the full reread (26 October 2026)

The whole plan was read top to bottom after the first amendment. These leftovers were fixed:

1. The primary model was given as the decaying jump. It is now J1, and the decaying variant can never price.
2. A "not yet confirmed" block about the references was out of date. Both papers have now been read, and the block is replaced by "References".
3. Two paragraphs about naming the papers repeated each other, and one called the description of Chen and Cox "second-hand". They are now one section, written from the paper itself.
4. Step 2 converted the jump into κ units with c = mean(b). It should be c = 1 / mean(b). The cap on the number of jumps now applies only to the decaying variant; J1's likelihood is exact.
5. Step 3 used "flagged" before defining it, and said "rerun step 2 with bᴶ", which was undefined. Both are replaced by the defined procedure.
6. The parameter table gave ρ = 0.5 for every model. ρ is now 0 for J1 and applies only to the decaying variant.
7. The 1957 and 1968 jump prior read like a cited figure. It is now labelled a judgement, with no source checked.
8. The separation rule's "N(2030) under 1%" condition is automatic for one-year jumps. It is dropped as a pass condition, reported for the decaying variant, and 2022 is named as the case to watch.
9. The pricing projection said Covid "decays at the estimated ρ". For J1, Covid ends with 2022.
10. The absorbed share could be read as counting a rise in the trend as absorption. It is now defined on jump-added deaths only.
11. The reporting list said "primary and transitory model". It now says J1 and the decaying variant.
12. The tests were restated for J1 as the primary model, adding exact checks of the likelihoods and a Covid-shaped run.
13. The 2024 section now names Stats SA's workbook, which is on disk, and notes that its 80+ group is open.

Details settled while writing the code, before any test was run in full, are in steps 2 and 3:
- the two starting values;
- the bounds on σ, σ_Y and ρ;
- how the share left out of the cap is estimated;
- K̂ outside F;
- the decaying variant's free N from the first flagged Covid year.

### Pre-freeze change, 27 October 2026

**Made after seeing the simulated test results, at the user's request, and before any v1.4 fit to real data.** The first full run (26 to 27 October) passed 12 of 13 tests. Two problems showed:
- **(a) failed:** 28.5% of plain series had a flagged year at the 0.5 cutoff, against a mark of 10%.
- **The original separation rule passed only 29.5% of series from the correct model** (Covid-shaped jumps). Small jumps in 2020 and 2022 were often not flagged, so their excess counted against the absorbed share.

What was recorded about the first run at the time: (a) was to be kept as an expected failure, and the rule was not to be changed. **Both of those decisions were reversed by this change.** The first run's raw results are kept in `research/results/v14_tests_original.json`.

**What changed, and nothing else:**
1. **The flag cutoff** went from 0.5 to **0.95**.
2. **The absorbed share** is now measured from step 2's posterior mean jump effect, not from hard flags, and its threshold went from 75% to **45%**.
3. **The trend test's band** went from 2·σ̂·√3 to **2.31·σ̂·√3**. The trend test stays the main criterion.
4. **Pricing condition 6 was added:** on 2024, J1 must beat a permanent-shift model.
5. **Two safeguards were added to condition 6:** the completeness band with its scaling sensitivity, and the power requirement.
6. **Test changes:**
   - (a) is a normal test again;
   - the Covid-shaped run has a pass mark of 80%;
   - a permanent-shift run is reported.

The original rule's requirement that at least one of 2020 to 2022 be flagged was dropped along with the hard-flag share. **This is part of change 2, not a separate change:** the amended share uses no flags.

**Decided in advance by the user, before the calibration results were seen:**
- if the wrong model could not be made to fail, that target is dropped and both pass rates are reported (this happened);
- if the trend test capped the correct model below 80%, its band is the narrowest that passes 90% of correct-model series, and no wider (this happened: 2 passed 72%);
- no other change to the rule;
- if any test failed after the calibration, stop and report before freezing (none failed).

**How the numbers were set** (`research/v14_calibration.py`, seeds [20261031, 1, i], 200 series per case, apart from the tests' [20261031, i]; raw results in `research/results/v14_calibration.json`):

1. **The cutoff:** the lowest on the grid that flags at most 10% of plain series and the 0.30 jump of the J1 recovery case in at least 90%.

   | Cutoff | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | **0.95** | 0.975 | 0.99 |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Plain series with any flag | 28% | 23.5% | 20.5% | 16.5% | 11.5% | **9%** | 5.5% | 3% |
   | Recovery: 2021 flagged | 100% | 100% | 100% | 100% | 100% | **100%** | 100% | 100% |

2. **The band, at the 0.95 cutoff:**
   - At 2·σ̂·√3, the trend test passed 72% of correct-model series (and 86.5% of wrong-model series). That is under 80%.
   - The band became the 90th percentile of |K̂(2022) − trend| / (σ̂·√3) over correct-model series, rounded up to 0.01, which gives **2.31**. At 2.31, the trend test passes 90% of the correct model and 94% of the wrong model.
3. **The threshold, at that cutoff and band:** the highest on the grid of 30% to 95% at which the whole rule passes at least 80% of correct-model series.

   | Threshold | 30% | 35% | 40% | **45%** | 50% | 55% | 60% | 65% | 70% | 75% |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Correct model: rule passes | 90% | 90% | 89.5% | **83.5%** | 74.5% | 63% | 56% | 52% | 43.5% | 32% |
   | Wrong model: rule passes | 94% | 94% | 94% | **94%** | 94% | 93% | 89.5% | 77.5% | 64% | 57% |

   The median absorbed share is 0.68 for the correct model and 0.97 for the wrong one. **The wrong model absorbs more, not less,** because a permanent shift looks like two large jumps in 2021 and 2022. No threshold makes the wrong model fail in most series while the correct one passes, so that target was dropped.

**Original and amended results, side by side** (test seed 20261031, 200 series each):

| Test | Mark | First run (cutoff 0.5, original rule) | Rerun (cutoff 0.95, amended rule) |
| --- | --- | --- | --- |
| Graduation, both λ checks, both likelihood checks | as above | pass | pass (unchanged) |
| J1 recovery: 2021 flagged, N̂(2021), b̂ᴶ correlation | 90%, ±0.05, 0.9 | 100%, 0.300, 0.96 | 100%, 0.300, 0.96 |
| J1 recovery: separation passes | at least 80% | 92% (share 92.5%, trend 98%) | 99% (share 100%, trend 99%) |
| Decaying variant: ρ̂ on ρ = 0.5 data, and on J1 data | as above | 0.500, 0.004 | 0.500, 0.004 (unchanged; the cutoff does not enter) |
| (a) Plain data: any flag | at most 10% | **28.5% (fail)** | **7% (pass)** |
| (b) HIV-like hump: any flag | at most 10% | 0% | 0% |
| Reported: plain and HIV, prior fixed | none | 2.5%, 0% | 0.5%, 0% |
| Covid-shaped: flagged 2020, 2021, 2022 | none | 48.5%, 100%, 5.5% | 40.5%, 100%, 5% |
| Covid-shaped: separation passes | none in the first run; at least 80% now | **29.5%** (share 30.5%, trend 77%) | **88.5% (pass)** (share 91%, trend 94.5%) |
| Permanent shift: separation passes | reported only | not run | 95.5% (share 99.5%, trend 95.5%) |
| Tests passing | | 12 of 13 | 14 of 14 |

**What this means for the plan.** The amended rule is a sanity check. It catches a trend that runs away with Covid, but it passes a permanent shift as readily as it passes jumps (95.5% against 88.5% on the test seed; 94% against 83.5% in the calibration). Whether Covid was a jump is decided only by pricing condition 6 on 2024. If 2024 cannot be scored or cannot discriminate, v1.4 does not price.

### How a failure on the test seed is handled (27 October 2026)

The unit tests run on seed 20261031. The calibration used separate seeds. **If any test fails on the test seed after the calibration, nothing is recalibrated, and the tests are not rerun on that seed.** The failure is reported to the user with the size of the miss, before the freeze, and the user decides what follows.

### Unit test results (rerun on 27 October 2026 after the pre-freeze change, `tests/test_v14.py`, seed 20261031, 200 series each)

Run time: 43 minutes on the Mac (8 processes). Raw summaries: `research/results/v14_tests.json`. **All 14 tests pass.** The first run, under the original rule and cutoff, is kept in `research/results/v14_tests_original.json` and set beside this one under "Pre-freeze change, 27 October 2026".

| Test | Mark | Result | |
| --- | --- | --- | --- |
| Graduation recovers the known curve (ages 50 to 89) | error under 0.05 | largest error 0.009 (λ = 10^4.5, ED 9.0) | Pass |
| Very large λ gives a Gompertz line | second differences under 10⁻⁴ | yes | Pass |
| λ = 0 returns the crude rates | to 10⁻⁸ | yes | Pass |
| J1's block likelihood against brute force (10 years) | to 10⁻⁸ | likelihood, posteriors and E[N] agree | Pass |
| Decaying variant, cap at series length, against brute force (ρ = 0 and 0.5) | to 10⁻⁸ | agree | Pass |
| J1 recovery: 2021 flagged | at least 90% | 100% | Pass |
| J1 recovery: median N̂(2021) | within 0.05 of 0.3 | 0.300 | Pass |
| J1 recovery: median correlation of b̂ᴶ with the truth | at least 0.9 | 0.96 | Pass |
| J1 recovery: separation rule passes | at least 80% | 99% (absorbed share 100%, trend 99%) | Pass |
| Decaying variant recovers ρ = 0.5 | median within 0.15 | 0.500 (no fit needed the cap of 6; largest share left out 0.009%) | Pass |
| Decaying variant on J1 data | median ρ̂ under 0.15 | 0.004 (largest share left out 1.0%) | Pass |
| (a) No false jumps, plain data, L5 setting | at most 10% of series | 7% (14 of 200: 9 with one flagged year, 3 with two, 2 with three), spread over the years | Pass |
| (b) No false jumps, HIV-like hump, L5 setting | at most 10% | 0% | Pass |
| Reported only: plain data, prior fixed (L1 to L4 setting) | none | 0.5% (1 of 200) | |
| Reported only: HIV-like hump, prior fixed | none | 0% | |
| Covid-shaped jumps (0.10, 0.30, 0.08): separation rule passes | at least 80% | **88.5%** (absorbed share at least 0.45: 91%; trend: 94.5%). Flagged: 2020 40.5%, 2021 100%, 2022 5%. Median absorbed share 0.67. Median N̂: 0.016, 0.227, 0.000 | Pass |
| Reported only: permanent shift (+0.10 in 2020, +0.30 from 2021) | none | separation passes in **95.5%** (absorbed share 99.5%; trend 95.5%). Flagged: 2020 52%, 2021 100%, 2022 99.5%. Median absorbed share 0.97. Median N̂: 0.088, 0.260, 0.253 | |

**What the results show, recorded before the freeze:**

- **The false-flag rate is now within the mark** (7% on the test seed, 9% on the calibration seeds), at the cost of flagging small jumps less often. 2020's jump of 0.10 is flagged in 40.5% of Covid-shaped series, and 2022's 0.08 in 5%.
- **The HIV-like hump is not absorbed** in either setting (0%).
- **The amended rule passes the correct model in 88.5% of series, and the wrong model in 95.5%.** As said under "What the rule cannot do", it is a sanity check and does not discriminate. The two are told apart only by pricing condition 6, on 2024.
- **The permanent shift is fitted as jumps in 2021 and 2022** (both flagged in almost every series, each about 0.25 to 0.26). This is what the data to 2022 allow. A real-data fit with 2021 and 2022 both flagged at about the same size is therefore what both models predict, and is not evidence for J1.

## Not changed

- The annuity product, the annuitant factor of 0.7, the Kannisto tail and the funeral table.
- Everything on the site. Until v1.4 is run and reported, the site keeps v1 for both sexes.
- This is not redeployed until the user says so.

## Post-freeze record

### Running v1.4, 27 October 2026 (written after the freeze, before any v1.4 fit to real data)

Nothing above is changed. This records how the frozen plan is carried out, and one failure to run.

**Where it runs.** Not on the Mac, as "Running it" says, but on two Google Cloud VMs in africa-south1-b (t2d-standard-8 and t2d-standard-4, AMD EPYC Milan, 12 cores in all, no external IP), at the user's request, for time. Python 3.12, numpy 2.5.4, scipy 1.18.1. The 500 refits of each fit are cut into chunks and split between the two machines; each refit has its own seed, `SeedSequence(20261031, (job, refit))`, so the results do not depend on the split. One thread per process.

**A failure to run, and its fix (made after seeing the failure).** The guard refused to run: this plan's line "Frozen at commit: 442508e… (27 October 2026)" did not match the pattern in `mdingilife/protocol.py`, which expected the hash to end the line. With the user's approval, the pattern now also accepts a bracketed note after the hash. The plan's text was not touched, and every earlier plan's guard still returns its hash. No result had been seen.

**The runner, `research/v14.py`**, written after the freeze and tested on simulated data only (4 refits per fit) before the real run. It runs in three steps:
1. `boot`: the main fits and the bootstrap refits;
2. `stage1`: everything except 2024's deaths, including condition 6's power, written to `research/results/v14_stage1.json`;
3. `stage2`: the only step that reads 2024's deaths: the completeness check, L5's scores, G, and the decision, written to `research/results/v14.json`.

**Choices the plan left open, settled now:**
- **Data:** registered deaths from `mcd_deaths.csv` (unknown ages and sexes spread as before), over WPP exposure for 1997 to 2022. The completeness-scaled run uses `mcd_deaths_scaled.csv`; at L5, its 2024 deaths are divided by 2024's own ratio of registered to WPP deaths. The 2024 exposure is WPP 2024's projected 1 July population.
- **φ:** from the first step 1 fit (b and κ before step 3), with (ages − 1) + years parameters.
- **The bootstrap redraw:** deaths at ages 50 to 89 in every fitted year are drawn at φ from the fitted rates a + bK̂ + (age pattern)·N̂, which equal the final step 1 fit. In the base years, ages 45 to 49 are drawn from the graduated a(x). a(x) is re-graduated with λ held, and steps 1 to 3 are refitted with the link's settings.
- **The projection:** each refit's K starts from its K̂ at the last fitted year, a random walk with its own μ̂ and σ̂. Jumps are I ~ Bernoulli(p), Y ~ Normal(μ̂_Y, σ̂_Y²), at its bᴶ. The decaying variant carries its N̂ at the last year forward at ρ̂. Each refit gives 10 paths, so 5,000 in all.
- **L4's no-jump model:** the same refits and the same random walk, with N = 0 (no future jumps, and nothing carried); observation noise on the same seed as the jump model's.
- **Scores:** as in v1.3: deviance of the median path, coverage of the 95% interval with observation noise at φ, the mean width exp(upper − lower), and the annuity error of the median. B0 is the mean of the base years' crude rates, held flat.
- **Sensitivities:** the three values of p, for J1 and the decaying variant, at every link; μ_Y = 0.05 and 0.30 for J1 at L1 to L4 (σ_Y stays 0.05); completeness-scaled deaths for J1 at every link, with v1 refitted on scaled deaths beside it.
- **v1:** Renshaw-Haberman on ages 50 to 89 from 2006, with v1.1's bootstrap (500 refits, 5,000 paths, deaths at v1's φ), unanchored, scored with noise at v1's φ. L3 fits 2006 to 2012. L4 and L5 share one fit on 2006 to 2019. **For the mixed-set gate**, v1's price at 65 is its published production figure (13.53 men, 16.05 women). Its e65 in 2026 and 2036 come from rerunning v1's production bootstrap here (Poisson redraws, 2006 to 2022 with Covid out, 500 refits), because the published figures give e65 only for 2020 and 2030.
- **Condition 6:** the medians are J1's a + b(K̂(2022) + 2μ̂) and the shift model's a + b₀(κ(2022) + 2μ̂), with b₀ and κ from step 1. The simulated data sets take 2 paths from each of the 500 refits (1,000 sets). The shift model's paths use the same random walk and jump draws as J1's; they differ only in the starting level and b. Deaths are drawn at φ on the 2024 exposure. G and the power are computed for every J1 fit at L5 (each p, and scaled deaths); the counted one is the central fit on registered deaths.
- **The scaling sensitivity** multiplies 2024's deaths by the 2022 ratio over the 2024 ratio. **On Stats SA's population**, the simulated G and its 95th percentile are recomputed on that exposure.
- **Pricing:** every fit at L5 is projected from 2022, trend-only (no future jumps; the decaying variant carries N̂(2022) at ρ̂), and with future jumps at that fit's own p. Prices are per path, with Kannisto above 89, and e65 is in 2026, 2036 and 2056.
- **A refit that fails** is recorded, and nothing is scored until it is reported.

### A failed refit, 27 October 2026 (written after seeing the failure, before any v1.4 score was seen)

**The failure.** After the bootstrap, the collector stopped as planned. Of the 48,000 refits, none was missing and one had failed:
- **Cell:** women, L5, J1, p = 1/60, central prior (`chain|Female|L5|J1|1/60|central`, job 74). This is a jump-frequency sensitivity, not a primary cell.
- **Refit:** index 80 of 500 (0 to 499), seed `SeedSequence(20261031, (74, 80))`.
- **Error:** `LinAlgError: Matrix is not positive definite`.

**The fix, made after seeing the failure, with the user's approval.** It is one change to the runner: the collector now records failed refits and leaves them out, instead of stopping. A missing refit still stops the run. Each cell that loses refits is labelled with the number used ("499 of 500 refits") and lists its failures. Nothing else changes: no cutoff, threshold, seed or other refit. The failure was not investigated.

**A rule added now, after seeing this failure and before any further result.** The 1% threshold was set after seeing this failure.
- A cell with more than 1% of its refits failed (more than 5 of 500) is reported as not scored.
- If that happens to a primary L5 cell (J1, p = 1/30, central prior, either sex), v1.4 does not price.

**Which cells the decision uses.** Condition 6, its power and the completeness-scaled sensitivity use only cells with no failed refits: the women's and men's L5 J1 cells at p = 1/30, on central and on scaled deaths. The p = 1/60 cell is scored on its 499 good refits, and that is reported wherever it appears.

### An overflow in the bootstrap noise, 27 October 2026 (written after seeing the crash, before any v1.4 score was seen)

**The crash.** Stage 1 stopped with `ValueError: lam value too large`. It happened while observation noise was being added to the L3 paths of `chain|Male|L3|J1|1/30|central`. One path's expected deaths went past the largest Poisson mean numpy can draw from (about 9.22e18). Reading the stored paths showed that nine cells have such paths: 1 in Male L3 central, otherwise all at L1 and L2 (up to 34 of 5,000). No L4 cell has one.

**What this plan was missing.** Neither this plan nor any earlier one had an overflow rule. This fills the gap, with the user's approval.

**The fix.** It is a change to the shared bootstrap code (`mdingilife/bootstrap.py`), applied the same way to every cell and every use. When noise is added, the expected deaths, and the gamma-mixed mean, are capped at 9.2e18. Below the cap nothing changes, neither the values nor the random stream. No seed, cutoff, threshold or refit changes.

**What is reported.**
- Every score gives its number of paths, its capped paths and its paths with a death rate above 1 somewhere. Condition 6's simulated sets give the same counts.
- Stage 1 is rescored from the stored paths. It is checked against a run of the code before the cap in which only the crash was caught, and every cell without a capped path must give identical numbers.

**Primary cells with capped paths (L3 and L4, J1, p = 1/30, central prior).** Each such cell is scored with the cap and again with its capped paths dropped (the other paths keep the same noise). If a pass or fail flips, the mark is recorded as not robust and counts as a fail. The same applies to condition 3's deviance. This rule was set after seeing the crash.

**A limitation.** Bootstrap projections from very short fitted windows (L1 and L2, a few years after a three-year base) are unstable: many paths reach death rates above 1. They are reported as they stand, with nothing tuned.
