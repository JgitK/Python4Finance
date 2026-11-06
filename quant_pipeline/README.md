# Markowitz Portfolio Pipeline

This project picks a stock portfolio. It uses real market data. It screens
the stocks, selects a diversified set, and finds the best weights. It then
tests the method against the S&P 500.

The project has two layers:

- **The data plane** uses **dbt** and **DuckDB**. It does all the SQL work.
  It cleans the prices and builds the indicators with window functions.
- **The stats layer** uses **Python**. It does the math that SQL does not fit:
  the Markowitz optimization and the walk-forward backtest.

This split is on purpose. SQL is strong for set-based work on many rows.
Python is strong for linear algebra and simulation. Each layer does the job
it is best at.

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
   together. It takes at most three stocks from one sector.
6. **Optimize.** Python runs a Monte Carlo search. It tries 10,000 random
   weightings and keeps the one with the highest Sharpe ratio.
7. **Allocate.** Python turns the weights into whole shares for a fixed budget.
8. **Backtest.** Python runs a walk-forward test. It picks a portfolio with
   past data only. It then holds the portfolio for six months and compares
   the result to SPY. This test has no look-ahead, so it is fair.

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
│   ├── backtest.py     Walk-forward backtest with no look-ahead.
│   └── pipeline.py     Join the select and optimize steps.
├── dbt/                The dbt-duckdb project.
│   ├── seeds/          The raw price and sector CSV files.
│   ├── models/
│   │   ├── staging/        Clean the prices and the sectors.
│   │   ├── intermediate/   Returns, Bollinger, Ichimoku, risk metrics.
│   │   └── marts/          Screen candidates, sector leaders, returns.
│   └── tests/          A singular uniqueness test.
├── tests/              The pytest suite for the Python layer.
└── run_pipeline.py     Run the whole pipeline end to end.
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

The dbt layer has 3 unit tests for the return, score, and screen logic.
It also has schema tests for not-null, unique, and relationship rules.
The Python layer has unit tests for every stats function. The backtest
tests check that the method never uses future data.

## Notes

- The data runs from late 2022 to late 2026. The nasdaq API serves this range.
- The Monte Carlo Sharpe ratio is an in-sample fit, so it looks high. The
  walk-forward backtest is the honest measure of the method.
- This project is for learning. It is not investment advice.
