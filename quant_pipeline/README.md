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

1. **Ingest.** Download daily prices for 43 large stocks and the SPY benchmark
   from the nasdaq API. The stocks cover all 11 GICS sectors.
2. **Clean and index.** dbt builds the daily return, the cumulative return,
   the Bollinger Bands, and the five Ichimoku Cloud lines for every stock.
3. **Measure risk.** dbt measures each stock over the last 252 trading days:
   the Sharpe ratio, the Sortino ratio, the CVaR, and the volatility.
4. **Screen.** dbt keeps the stocks that pass four gates: enough history,
   enough volume, calm enough daily moves, and a bullish Ichimoku score.
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
│   ├── ingest.py       Write the dbt seed files.
│   ├── universe.py     The list of stocks and sectors.
│   ├── warehouse.py    Read the dbt marts from DuckDB.
│   ├── select_portfolio.py  Low-correlation stock selection.
│   ├── optimize.py     Markowitz Max Sharpe optimization.
│   ├── allocate.py     Weights to whole shares.
│   ├── backtest.py     Walk-forward backtest.
│   └── pipeline.py     Join the select and optimize steps.
├── dbt/                The dbt-duckdb project.
│   ├── seeds/          The raw price and sector CSV files.
│   ├── models/
│   │   ├── staging/        Clean the prices and the sectors.
│   │   ├── intermediate/   Returns, Bollinger, Ichimoku, risk metrics.
│   │   └── marts/          Screen candidates, screen history, returns.
│   ├── macros/         The screen rules. Two marts use the same rules.
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

Refresh the data (optional, needs network access to the nasdaq API):

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
share allocation, the efficient frontier, and the backtest results.

## Tests

The project uses test-driven development. Both layers have tests.

```bash
# The Python stats layer.
python -m pytest

# The dbt data plane. This runs the data tests and the unit tests.
cd dbt && dbt build --profiles-dir .
```

The dbt layer has 6 unit tests for the return, score, and screen logic.
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
- The backtest still has a survivorship bias. The universe is a list of 43
  stocks that are large today. A stock that failed before today is not in
  the list. Because of this, the backtest result can be too high.
- The live run and the backtest use the same build step and the same
  window: the last 252 trading days up to the selection date. A test makes
  sure that, on the last date, the backtest gives the same weights as the
  live run.
- This project is for education. It is not investment advice.
