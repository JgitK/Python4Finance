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

- **A liquidity floor for the Nasdaq universe.** D14 selected the volume
  rule and left this option open. The rule keeps a stock with a market cap
  of at least $1B in a monthly snapshot, so a micro-cap that pumps above
  $1B for one month gets a one-month stint. A floor on the dollar volume,
  or a persistence rule of four snapshots in a row, would remove such a
  stock before the screen sees it. The screen already has a volume gate of
  100,000 shares, so the effect on the results may be small. Measure it
  before you decide.
- **The volume rule cannot see a spin-off.** D14 leaves such a move to a
  person, because a spin-off gaps at the open with a normal volume, like a
  split, and holds its price, like real news. HON is the one example in the
  data. A new spin-off in a future download will raise a warning, and a
  person must read it. A source of the corporate actions, for example a
  split and dividend feed, would remove the need for the rule.
- **7 of the 532 large moves hold a hand review, not a rule.** The rows of
  BAND, IBRX, NUTX, RADX, RGTI, SBET and SHAZ in the seed carry the note
  "Hand review (D14)". A later change to the limits of the rule does not
  change these rows. Read them again if you move a limit.
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

- **The Nasdaq large moves are not reviewed.** Solved by D14 and D15. The
  volume rule names 515 of the 532 large moves, a person read 7, and D15
  dropped 10 tickers whose price history is not one security.
  `assert_large_moves_are_reviewed` passes with 0 rows.

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
