# Mdingi Life

A fictional South African life insurer, modelled end to end: its policies, its assets, its regulatory balance sheet and its solvency cover, recalculated from market data every day. The company is invented. The mortality, the yield curve and the methods are real, and every simplification of SAM and IFRS 17 is listed where it is made.

Built in releases. Each one stands on its own and feeds the next.

| Release | Question | Status |
| --- | --- | --- |
| v1 Liabilities | How much does uncertainty about South African mortality move the price of a life annuity? | Run on UN WPP 2024 and on Stats SA registered deaths ([results](research/RESULTS.md)) |
| v2 Assets | What does the SA government bond curve look like on each auction day, and how well do the assets match the liabilities? | Run on National Treasury auction results, 2010 to 2026 ([results](research/RESULTS_v2.md)) |
| v3 Balance sheet | What is Mdingi Life's SAM solvency capital requirement, and its cover ratio today? | Run on the standard formula for an invented book of 5,000 annuities and 50,000 funeral policies ([results](research/RESULTS_v3.md)) |
| v4 Scenarios and reporting | Over the next five years, how likely is Mdingi Life to stay covered, what does it report under IFRS 17, and which shocks would break it? | Protocol written ([plan](research/PROTOCOL_v4.md)) |

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
mdingilife/   data, models (B0, LC, CBD, RH), Kannisto tail, annuity factors, scores, bootstrap;
              curves.py: bond cash flows, LI, NS, NSS and the bootstrapped zero curve;
              sam.py: SAM shocked curves, the monthly projection and the correlation aggregation
research/     fetch, coverage, backtest, annuities, export; PROTOCOL.md and RESULTS.md
              treasury, curves, annuities_v2; PROTOCOL_v2.md and RESULTS_v2.md
              book_v3, balance_v3, keyrate_v3; PROTOCOL_v3.md and RESULTS_v3.md
tests/        every model and formula on simulated data with known answers
service/      FastAPI app serving the results
dashboard/    Vite front end: the company's site (overview, quotes, customers, investments, capital, how it's built)
data/book/    v3's invented policies
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

The published results run on Stats SA registered deaths. The DataFirst unit records (catalogues 830 and 1074) are not redistributed here; with their CSVs in `data/raw/statssa/mcd/`:

```
.venv/bin/python -m research.mcd           # deaths by year, sex and age
.venv/bin/python -m research.exposure      # WPP population, checked against Stats SA P0302
.venv/bin/python -m research.completeness  # registered vs WPP deaths, and the scaled deaths
.venv/bin/python -m research.backtest --source statssa \
  --deaths data/raw/statssa/mcd_deaths.csv --population data/raw/statssa/wpp_population.csv
```

`research.annuities` and `research.export` take the same three flags.

v2 runs on National Treasury's auction results. Curves exist per auction day, not per calendar day: Treasury auctions each kind of bond about weekly.

```
.venv/bin/python -m research.treasury                        # workbooks and schedules into auctions.csv and bonds.csv
.venv/bin/python -m research.curves --period design          # chooses the curve for each kind
.venv/bin/python -m research.curves --period validation      # once, after design
.venv/bin/python -m research.annuities_v2 \
  --deaths data/raw/statssa/mcd_deaths.csv --population data/raw/statssa/wpp_population.csv
```

v3 values an invented book on the SAM standard formula, on v2's curves and v1's annuitant mortality.

```
.venv/bin/python -m research.book_v3 \
  --deaths data/raw/statssa/mcd_deaths.csv --population data/raw/statssa/wpp_population.csv
.venv/bin/python -m research.balance_v3 \
  --deaths data/raw/statssa/mcd_deaths.csv --population data/raw/statssa/wpp_population.csv
.venv/bin/python -m research.keyrate_v3 \
  --deaths data/raw/statssa/mcd_deaths.csv --population data/raw/statssa/wpp_population.csv   # the amendment
```

Without `--source` the v1 scripts run on UN WPP 2024, the comparison run.

The service and dashboard read `data/research.json`, which `research.export` writes.

```
.venv/bin/pip install -r service/requirements.txt
cd service && ../.venv/bin/pytest && ../.venv/bin/uvicorn app.main:app --port 8000
cd dashboard && bun install && bun run dev     # http://localhost:5173, /api proxied to :8000
cd dashboard && bun run build                  # the service then serves dist/ on :8000
docker build -t mdingi-life .                  # deploy/azure.sh builds in ACR and rolls out
```

`GET /api/price?sex=male&age=65&rate=0.04&adj=0.7` answers from the precomputed grid (ages 55, 65, 75; rates 0.02, 0.04, 0.06; factors 0.6, 0.7, 0.8) and returns 400 for anything off it. Add `?embed` to the dashboard URL to drop the page chrome inside an iframe, and `&theme=dark` to match a dark host.

## Data sources and terms

- Statistics South Africa, P0309.3 and P0302. Downloaded manually and attributed in the dashboard.
- National Treasury, Republic of South Africa, investor.treasury.gov.za: weekly bond auction results and the Schedule of Domestic Debt. Used for non-commercial purposes with acknowledgement. The workbooks and PDFs are not redistributed; the tidy extracts `auctions.csv` and `bonds.csv` are.
- United Nations, Department of Economic and Social Affairs, Population Division (2024). *World Population Prospects 2024*. CC BY 3.0 IGO.
