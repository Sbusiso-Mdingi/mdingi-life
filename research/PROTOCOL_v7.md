# Protocol: v7 A choice of premium for funeral cover, and credit risk

**Written on 28 October 2026, after v6's results were seen and published.** The product, the lapses and the credit risk exposures below were settled with the user on 28 October 2026, who approved this plan the same day, with v6's results in view: in particular v6's lapse charge (R112.4 million, the largest life charge) and its nil credit risk charge. Done beforehand, and disclosed here: FSI 2.2 §8 (contract boundary), Guidance Note FSI GN 2.2 chapter 2, FSI 4.1 §4.7 to 4.8 and §9 (spread and default risk) and FSI 4.1 Attachment 4 were read, from the same copy of the standards as v3. Nothing in v7 has been run.

Frozen at commit: (filled in when this is committed)

The question: what do the company's funeral premiums, capital and cover look like when each funeral customer chooses between a premium that is level for life and one that follows their age, reviewed every five years, and when the credit risk the company carries in its day-to-day business is counted?

What changes and what does not:
- **The funeral product.** The benefit is fixed; v5's rising benefit is dropped. The choice is now how the premium is paid (below).
- **Lapses** differ by premium type (below).
- **Credit risk** enters the SCR through SAM's default risk, on two exposures the book did not hold before, and a sovereign stress is reported outside SAM.
- **Everything else stays as v6:** the annuities, the funeral mortality table, the pricing basis (9% interest, 5% expense inflation, a 20% margin, no lapses), the SAM stresses, own funds of R400 million, the whole-book key-rate match on the BEL, and v6's two rules for the book's size and mix, which are solved again on v7's book.

## The product

- **The book.** v5's funeral policies keep their seed, sex, entry age, years in force and sum assured (R10,000, R15,000, R20,000 or R30,000). v5's benefit draw (seed 20261028, one half each) is reused as the premium type: a policy drawn "level" pays a level premium, one drawn "rising" pays an age-rated premium. Reusing the draw keeps the split at one half without a new seed, and the two draws were independent of everything else in the book.
- **Level premium.** As v5's level-benefit policies: one premium for life, (1 − 0.2) P ä = A + E on the pricing basis. These premiums are v5's to the cent (check F2).
- **Age-rated premium.** A schedule set at sale: one premium for each policy year, priced on that year alone. For policy year j (age e + j for entry age e), (1 − 0.2) P_j ä_j = A_j + E_j, where ä_j is the expected value of the year's 12 monthly premiums, A_j that of the year's death claims and E_j that of the year's expenses (R180 a year inflating at 5%), all on the pricing basis, discounted to the start of year j and with survival within the year only. Priced as if the policy started on the valuation date, as in v5. The schedule is whatever the table gives; where improvement outpaces ageing, a premium can fall from one year to the next. This is disclosed, not smoothed. Cover is for life, as the level option.
- **Reviews.** On every fifth anniversary of the policy's start (the 5th, 10th, 15th and so on), the company may revise the age-rated schedule for the whole book of age-rated policies, with notice. It cannot re-underwrite anyone. Level premiums are not reviewable.

## The contract boundary

FSI 2.2 §8.2 sets the boundary at the date the insurer may amend premiums "in such a way that the premiums fully reflect the risks". GN 2.2, chapter 2, individual life risk policies (ii): "If the insurer can only re-price on a portfolio level, the unilateral right to change policy conditions to fully reflect risk inherent in the specific policy is limited and therefore a longer contract boundary should apply. In order for a shorter boundary to apply, the insurer should have the right to set premium rates for existing policies that are the same as that for new policyholders with the same risk profile and should also have the right to re-underwrite the policies." The reviews are at portfolio level without re-underwriting, so the boundary is the end of the policy, as for level premiums, and every future premium of the schedule is in the BEL. No cap on the reviews is needed for this, so none is set.

## Management actions

- **Main run: no review is assumed,** in the best estimate or under any stress, as v3 to v6 assume no management actions. Each age-rated policy pays its schedule for life.
- **Variant, reported only: a review after the mortality stress.** Under the +15% mortality stress, at each age-rated policy's next review date, its remaining schedule is repriced on the stressed mortality, the pricing basis otherwise unchanged. The extra review lapse below applies as usual. The mortality charge, the SCR and cover are reported with and without the action, to show what the right to review is worth. It is not used in the main result because FSI 4 allows management actions only on conditions this model does not test.

## Lapses

- **Level premium:** v3's rates by policy year, 20%, 12%, 8%, then 6% from the fourth year.
- **Age-rated premium:** the same rates plus 10 percentage points in each review year (the policy year starting at a review: policy years 6, 11, 16 and so on, with v3's first year as policy year 1), whether or not the schedule changes. Policyholders reconsider when the review notice arrives.
- **Stated, not fitted.** No South African funeral lapse data this project may use was found. The 10 points is a judgement. A sensitivity at 0 and 20 points is reported.
- **The SAM lapse stresses** apply to the whole rate, spike included: up and down 50% (§8.6, capped at 100%), and the 40% mass lapse (§8.4), as v3.
- **Years in force** stay as v5 drew them, from v3's lapse survivors for both types. Drawing them again under the new rates would change the book's shape as well as its product. This is disclosed.

## Credit risk

**What SAM charges.** Credit risk sits in market risk as spread and default risk (FSI 4.1 §9). Rand bonds and bills of the South African government carry no spread charge (Attachment 4 B.1), so every asset of v3 to v6 was outside it. v7 adds the two exposures below, both taken out of the 182-day bill so own funds stay at R400 million and the bond match is unchanged. Both are valued at par and earn nothing beyond the bill's yield, which is ignored.

- **Premiums held by collectors, type 2 (§9.7 a).** One month of the funeral book's premiums in force on the valuation date, collected by employers, brokers and funeral parlours and not yet paid over. None is past due. The charge is 15% of it (§9.26).
- **Cash at a bank, type 3 (§9.8).** Three months of the book's expected outgo in the first projection year (annuity payments, funeral claims and expenses), held at one South African bank. The charge is the §9.28 factor for the bank's credit quality step times the cash.
- **The bank's step.** The PA's mapping from external ratings to credit quality steps is not in the standards and could not be found. Step 12 (probability of default 1.39% a year, §9.18; factor 4.35%, §9.28) is used as a stated judgement for a South African bank, whose rating is generally held at or below the sovereign's, which is below investment grade. The charge is linear in the factor, so it is also reported at every step from 1 to 18.
- **Aggregation.** With no type 1 exposures, Mkt_def = Mkt_def,type2 + Mkt_def,type3 (§9.15). Spread risk is nil, so Mkt_sp+def = Mkt_def (§9.3). It combines with interest rate risk with correlation A of §4.8: 0 if the nominal charge comes from the level increase, 0.5 if from the decrease. Equity, property, currency, concentration and illiquidity remain nil.
- **Risk margin.** Unchanged in method: default risk on these exposures is avoidable, so it is not in the reference insurer's SCR (FSI 2.2 §14).
- **v4.** At each year-end, the receivable is one month of that year-end's funeral premiums in force and the bank cash is three months of the next year's expected outgo, each taken from the bill.

**The sovereign, outside SAM.** SAM's zero charge is a rule, not a measure of the risk. Reported, on the valuation date: the fall h in the price of every government bond and bill held, liabilities and the SCR held as they are, at which cover reaches 100%, and at which own funds reach 0. A real sovereign loss would also move rates and the SCR, so this is a reverse stress, not a forecast.

**Household credit and lapses.** Discussed, not modelled: funeral lapses are largely missed debit orders, which follow household credit stress, so the lapse stresses are in part a credit risk. No data is used.

## The book's size and mix

v6's two rules, unchanged, on v7's book: the funeral line scaled so that a uniform change in mortality leaves the total BEL unchanged (A · E_ann + F · E_fun = 0), then the whole book scaled so cover is 1.8 at R400 million, with the default risk charge in the SCR. The book is reported in policies against v6's.

## Checks

- **F1, the valuation.** One age-rated policy is valued by a plain loop over months, with its review-year lapses, and agrees with the main code to 1e-8 of the BEL, unstressed and under every stress.
- **F2, the level option is v5's.** Level premiums equal v5's level-benefit premiums to the cent.
- **F3, no spike, no difference in lapses.** With the review spike at 0, an age-rated policy's lapse rates equal a level policy's in every year.
- **F4, the age-rated price.** Every premium of every schedule satisfies its year's equation to 1e-10.
- **F5, default risk.** Mkt_def equals 0.15 × receivable + 0.0435 × cash to 1e-12; with both exposures set to 0, the SCR equals the same run without them.
- **F6, the annuities.** The annuities' BEL and longevity charge equal v3's times A to 1e-8.
- **v6's D1, D2 and D5,** on v7's book.

## Reruns and reporting

1. The book: the age-rated schedules (and F2 to F4).
2. v7's balance sheet: the mix, the size, the main run, the review variant, the lapse sensitivities, the default risk at every step, and the sovereign reverse stress.
3. v4 on v7's book at R400 million, and at the level at which cover starts at 1.0, as in v6.

The cost and time of each run are agreed before it starts. Runs too heavy for the laptop go to the GCP VM.

Reported: premiums by age for each type; the funeral BEL by type; the SCR by risk with default risk, beside v6's; the review variant; the lapse sensitivities; the default charge at every step; the reverse stress; the book's size and mix beside v6's; every check, passed or failed.

**Attribution.** As v6.
