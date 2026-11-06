# Markowitz Portfolio Pipeline

This project picks a stock portfolio. It uses real market data. It screens
the stocks, selects a diversified set, and finds the best weights. It then
tests the method against the S&P 500.

The project has two layers:

- **The data plane** uses **dbt** and **DuckDB**. It does all the SQL work.
  It cleans the prices and builds the indicators with window functions.
- **The stats layer** uses **Python**. It does the math that SQL does not fit:
  the Markowitz optimization and the walk-forward backtest.

The project uses this split for a reason. SQL is good at set-based work on
many rows. Python is good at linear algebra and simulation. Each layer does
the work that it does best.

## What the pipeline decides

The pipeline runs these steps in order:

1. **Ingest.** Download daily prices from the nasdaq API for the SPY
   benchmark and for each stock that was in the S&P 500 at some time in
   the date range.
2. **Clean and index.** dbt builds the daily return, the cumulative return,
   the Bollinger Bands, and the five Ichimoku Cloud lines for every stock.
3. **Measure risk.** dbt measures each stock over the last 252 trading days:
   the Sharpe ratio, the Sortino ratio, the CVaR, and the volatility.
4. **Screen.** dbt keeps the stocks that pass four gates: enough history,
   enough volume, calm enough daily moves, and a bullish Ichimoku score.
   On each date, only the stocks in the S&P 500 on that date can pass.
5. **Select.** Python picks a diversified set. It avoids stocks that move
   together. It selects a maximum of three stocks from one sector.
6. **Optimize.** Python runs a Monte Carlo search. It tries 10,000 random
   weightings and keeps the one with the highest Sharpe ratio.
7. **Allocate.** Python changes the weights to whole shares for a fixed budget.
8. **Backtest.** Python runs a walk-forward test. At each past date, it
   selects a portfolio from past returns only. It holds the portfolio for
   180 trading days, approximately 8.5 months. Then it compares the result
   to SPY. On each past date, the backtest applies the screen of that date.
   The screen of a date uses only the data up to that date.

## Project layout

```
quant_pipeline/
├── quant/              The Python package.
│   ├── nasdaq.py       Download and clean the price data.
│   ├── reference.py    Build the S&P 500 membership and sector seeds.
│   ├── ingest.py       Download the prices to a Parquet file.
│   ├── universe.py     The benchmark ticker.
│   ├── warehouse.py    Read the dbt marts from DuckDB.
│   ├── select_portfolio.py  Low-correlation stock selection.
│   ├── optimize.py     Markowitz Max Sharpe optimization.
│   ├── allocate.py     Weights to whole shares.
│   ├── backtest.py     Walk-forward backtest.
│   └── pipeline.py     Join the select and optimize steps.
├── data/               The raw prices as a Parquet file. dbt reads it.
├── dbt/                The dbt-duckdb project.
│   ├── seeds/          The S&P 500 membership and the sectors.
│   ├── models/
│   │   ├── staging/        Clean the prices and the sectors.
│   │   ├── intermediate/   Returns, Bollinger, Ichimoku, risk metrics.
│   │   └── marts/          Screens, universe coverage, returns.
│   ├── macros/         The screen and membership rules.
│   └── tests/          Singular tests for uniqueness and consistency.
├── tests/              The pytest suite for the Python layer.
├── run_pipeline.py     Run the whole pipeline end to end.
└── verify_indicators.py  Check the numbers against an independent calculation.
```

## How to run

Set up the Python environment once:

```bash
cd quant_pipeline
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Refresh the data (optional). First, refresh the reference seeds. Clone the
two source repositories, then build the seeds from them:

```bash
git clone https://github.com/fja05680/sp500.git ../sp500
git clone https://github.com/datasets/s-and-p-500-companies.git ../spc
python -m quant.reference --sp500 ../sp500 --companies ../spc
```

Then download the prices. This step needs network access to the nasdaq
API. It downloads approximately 580 symbols. With the default settings, this
step takes approximately 30 to 60 minutes. If the download stops, run it again.
The cache in `data/cache/` keeps the symbols that are complete.

```bash
python -m quant.ingest
```

Build the data plane and run the tests:

```bash
cd dbt
dbt build --profiles-dir .
```

Run the whole pipeline:

```bash
cd quant_pipeline
python run_pipeline.py            # build dbt, then run the stats
python run_pipeline.py --skip-dbt # reuse the warehouse from the last run
```

The pipeline writes the results to the `output/` folder: the weights, the
share allocation, the efficient frontier, the backtest results, and the
universe coverage.

## Tests

The project uses test-driven development. Both layers have tests.

```bash
# The Python stats layer.
python -m pytest

# The dbt data plane. This runs the data tests and the unit tests.
cd dbt && dbt build --profiles-dir .
```

The dbt layer has 9 unit tests for the return, score, screen, membership,
coverage, and exclusion logic.
Three of these tests put a large future value in the input. They make sure
that an earlier row does not change.
It also has schema tests for not-null, unique, and relationship rules.
The Python layer has unit tests for every stats function. The backtest
tests make sure that the build step does not use future returns.

### Independent verification

The tests check each part against a fixed expected value. The verify script
checks the whole warehouse a second way. It rebuilds the indicators and the
risk metrics with pandas, then compares them to dbt. It also calculates the
Sharpe ratio of the optimizer again. Then it makes sure that future returns
cannot change the weights of a past portfolio.

```bash
cd quant_pipeline
. .venv/bin/activate
python verify_indicators.py      # exits 0 when every check passes
```

Run it after a dbt build. It needs the warehouse file.

## Notes

- The data runs from late 2022 to late 2026. The nasdaq API serves this range.
- The nasdaq close is split-adjusted but not spinoff-adjusted. A spinoff causes
  a large one-day decrease that is not a real loss. The data layer nulls any
  one-day move beyond 50 percent, so a corporate action does not distort the
  risk metrics. The `max_abs_daily_return` variable sets this limit.
- The Monte Carlo Sharpe ratio is an in-sample fit. Because of this, the value is too
  high. Use the backtest to measure the method, but read the next note first.
- The backtest has no look-ahead in the screen. On each selection date, it
  uses `mart_screen_history` for that date. The verify script calculates
  that screen again from prices that stop on that date. The two must agree.
- The universe is the S&P 500 on each date. The membership data comes from
  fja05680/sp500 (MIT license). The sectors come from
  datasets/s-and-p-500-companies (ODC-PDDL). This rule removes most of the
  survivorship bias of a list of stocks that are large today.
- Some survivorship bias remains. The nasdaq API has no prices for a stock
  that does not trade now, for example after a takeover or a bankruptcy.
  The screen cannot select such a stock. The pipeline counts these stocks
  on each selection date. See `output/universe_coverage.csv`.
- A ticker can name a different security after a company leaves. The
  nasdaq API then returns the history of the wrong security. The
  `price_data_exclusions` seed lists such tickers with the reason, and the
  staging model drops them. A warning test finds an index member with a
  median volume under 1,000 shares. At this time, the seed lists PARA.
- The nasdaq API has no data for BF.B. The coverage report counts it.
- A renamed stock is a removal and an addition in the membership data. On
  the dates before the rename, the old ticker has no prices, so the
  coverage report counts it as dropped.
- The sectors are the newest GICS sectors, not the sectors on each date.
  For example, GICS moved Visa and Mastercard to Financials in 2023.
- The live run and the backtest use the same build step and the same
  window: the last 252 trading days up to the selection date. A test makes
  sure that, on the last date, the backtest gives the same weights as the
  live run.
- This project is for education. It is not investment advice.
