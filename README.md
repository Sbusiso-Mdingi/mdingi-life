# Mdingi Life

A fictional South African life insurer, modelled end to end: its policies, its assets, its regulatory balance sheet and its solvency cover, recalculated from market data every day. The company is invented. The mortality, the yield curve and the methods are real, and every simplification of SAM and IFRS 17 is listed where it is made.

Built in releases. Each one stands on its own and feeds the next.

| Release | Question | Status |
| --- | --- | --- |
| v1 Liabilities | How much does uncertainty about South African mortality move the price of a life annuity? | Building |
| v2 Assets | What does the SA government bond curve look like each day, and how well do the assets match the liabilities? | Planned |
| v3 Balance sheet | What is Mdingi Life's SAM solvency capital requirement, and its cover ratio today? | Planned |
| v4 Scenarios and reporting | Economic scenario generator, IFRS 17 CSM roll-forward, ORSA-style stress tests | Planned |

## The book

- **Annuities.** Level and inflation-linked life annuities bought at retirement. Longevity is the risk.
- **Funeral cover.** Monthly-premium whole-life funeral policies, the most common life product in South Africa. Mortality and lapses are the risk.

## v1 scope

1. **Data.** Registered deaths by single age and sex (Stats SA, *Mortality and causes of death*, P0309.3) over mid-year population estimates (P0302) as exposure, 1997 onwards. UN World Population Prospects 2024 single-age life tables as a cross-check. Under-registration at old ages and the closing age group are handled explicitly, not hidden.
2. **Models.** Lee-Carter as the baseline, with Cairns-Blake-Dowd and Renshaw-Haberman as challengers. South African mortality rose with HIV until about 2006, fell with antiretroviral treatment, then spiked with Covid-19. A single-trend model was not built for that, and the backtest is designed to show how badly it copes.
3. **Backtest.** Models fitted on data up to a jump-off year and scored on the years after it, against a no-improvement baseline. Rules and pass marks go in `research/PROTOCOL.md` before the first fit.
4. **Annuity prices.** Expected present value of a life annuity at 55, 65 and 75 by sex, with a 95% interval from parameter and process uncertainty. In v1 the discount rate is flat; v2 replaces it with the fitted bond curve.
5. **Annuitant basis.** People who buy annuities live longer than the population. v1 applies a stated level adjustment to population rates and shows how sensitive the price is to it.

## Layout

```
mdingilife/   data, models (B0, LC, CBD, RH), Kannisto tail, annuity factors, scores, bootstrap
research/     fetch, coverage, backtest, annuities, export; PROTOCOL.md and RESULTS.md
tests/        every model and formula on simulated data with known answers
service/      FastAPI app serving the results
dashboard/    Vite front end, embedded at mdingi.co.za
data/raw/     source files as downloaded
```

```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest
.venv/bin/python -m research.fetch        # UN WPP 2024, South Africa only
.venv/bin/python -m research.coverage     # years, ages and holes; no rates
.venv/bin/python -m research.backtest     # these three refuse to run until
.venv/bin/python -m research.annuities    # PROTOCOL.md is frozen at a commit
.venv/bin/python -m research.export
```

Add `--source statssa --deaths <csv> --population <csv>` to run on Stats SA data instead.

## Data sources and terms

- Statistics South Africa, P0309.3 and P0302. Downloaded manually and attributed in the dashboard.
- United Nations, Department of Economic and Social Affairs, Population Division (2024). *World Population Prospects 2024*. CC BY 3.0 IGO.
