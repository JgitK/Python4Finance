# Open questions

Each item is a problem or a question that is not solved. When you solve
one, move it to the "Solved" section with the commit hash.

## Open

### Results

- **The method does not beat SPY.** The backtest beats SPY in 1 of 3
  windows, and its Sharpe ratio is lower than the Sharpe ratio of SPY in
  all 3 windows. See `results_log.md`.
- **The backtest logs only 3 windows, and they overlap.** The windows start
  126 days apart but each one lasts 180 days. Three windows cannot show
  that a result is not luck. An experiment on 2026-11-06 ran 84 windows
  with a 5-day step (approximately 10 seconds), and gave a much better
  measure: sp500 beats SPY on the return in 53.6% of the windows and on the
  Sharpe ratio in 45.2%. `run_pipeline.py` must get an option for this, so
  each row of the results log holds the measure. Note that the valid dates
  cover only about two independent 180-day periods, so even 84 windows
  cannot prove a small difference.

### Universe and data

- **The Nasdaq large moves are not reviewed.** The price data holds 601
  one-day moves larger than 50% that no person classified. 104 of them are
  inside the `both` universe, and 34 of the affected tickers pass the
  screen. D11 requires a review of each large move, so
  `verify_indicators.py` fails its data quality check and the `nasdaq` and
  `both` rows in the results log are provisional. A hand review of 601
  moves is not practical. The next decision must select a rule. Three
  options: classify each move by its volume (a real move has a volume
  spike, a split does not); add a liquidity floor to the universe so the
  long tail never enters; or accept the warning and mark the results.
- **The Nasdaq universe admits a stock that pumps for one month.** The rule
  keeps a stock with a market cap of at least $1B in a monthly snapshot.
  A micro-cap that pumps above $1B for one month gets a one-month stint,
  for example SHAZ, NXTT, JDZG, and BDRX. These stocks hold most of the
  unreviewed large moves. A persistence rule, for example four snapshots
  in a row, would remove them.
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

- **A non-default universe build stopped with an error.** The unit test
  `test_membership_uses_the_sp500_by_default` read the universe from the
  project file, so a `--vars` flag made it fail and skip 24 models. Solved
  by `0e11033`.
- **The backtest selected a date that has no screen.** On 30 of 114 dates,
  the screen history was empty, so the backtest held nothing and reported a
  0% return as a loss. Solved by `23102b3`.
- **Which universe is the default.** Solved by D13 (`23102b3`): `sp500`.

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
