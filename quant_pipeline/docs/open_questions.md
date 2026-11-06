# Open questions

Each item is a problem or a question that is not solved. When you solve
one, move it to the "Solved" section with the commit hash.

## Open

### Results

- **The method does not beat SPY.** The backtest beats SPY in 1 of 3
  windows, and its Sharpe ratio is lower than the Sharpe ratio of SPY in
  all 3 windows. See `results_log.md`.
- **The backtest has only 3 windows, and they overlap.** The windows start
  126 days apart but each one lasts 180 days. Three windows cannot show
  that a result is not luck. More windows, with a shorter step, would give
  a better measure.

### Universe and data

- **The Nasdaq universe.** You wanted Nasdaq stocks in the universe. No
  free point-in-time Nasdaq membership was found. One option: a switch
  between the S&P 500 and the 2021 Nasdaq list (`Nasdaq.csv`), so that you
  can compare the two results. A better backtest result with the Nasdaq list
  can come partly from survivorship bias.
- **The survivorship bias that remains.** The pipeline drops 10 to 20 index
  members on each selection date because the nasdaq API has no prices for
  them. See `output/universe_coverage.csv`.
- **Renamed tickers count as dropped.** The membership data records a rename
  as a removal and an addition (for example FI to FISV). On the dates before
  the rename, the old ticker has no prices.
- **BF.B has no data** in the nasdaq API.
- **The sectors are not point-in-time.** Each stock has its newest GICS
  sector on all dates. For example, GICS moved Visa and Mastercard to
  Financials in 2023.
- **SOLS has no sector.** A dbt test gives a warning for its 260 rows.
- **Small corporate actions.** The `corporate_actions` seed has only the
  moves larger than 50%. If the source does not adjust a smaller one, its
  gap stays in the returns.

### Method

- **The Monte Carlo search is not exact.** It finds a Sharpe ratio a little
  below the true maximum (2.90 against 3.00 on the old universe).
  `scipy.optimize` can find the true maximum.
- **The Sortino ratio uses two targets.** The downside deviation uses 0, but
  the numerator subtracts the risk-free rate.
- **`fct_prices` and `int_bollinger` have no reader.** No model or script
  uses them.

### Project

- **Merge to `main`?** Not decided. See decision D3.

## Solved

- **Look-ahead bias in the backtest.** Solved by D5 (`0208699`).
- **The live run and the backtest used different windows.** Solved by D6
  (`9bc2d8c`).
- **A list of 43 stocks that are large today (survivorship bias).** Mostly
  solved by D7 (`ad891f6`, `9c2addd`).
- **HON dropped from the lookback window after a corporate action.** Solved
  by D11 (`4cfa116`).
- **The 50% rule erased real crashes.** Solved by D11 (`4cfa116`).
- **The price data was a large dbt seed.** Solved by D9 (`ad891f6`).
- **The holding period was called "six months".** It is 180 trading days.
  Corrected in `8d87df4`.
