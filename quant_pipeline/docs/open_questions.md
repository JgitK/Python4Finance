# Open questions

Each item is a problem or a question that is not solved. When you solve
one, move it to the "Solved" section with the commit hash.

## Open

### Results

- **The default settings do not beat SPY, and a larger portfolio does.**
  With the default caps (10/12/3) the `sp500` portfolio beats SPY on the
  return in 48.2% of 85 windows, and the median window is 0.27% below SPY.
  D20 found that 40 stocks with at most 10 of a sector beats SPY on the
  median window (+3.68%), on the share of the windows (64.7%) and on the
  mean Sharpe ratio (0.82 against 0.80). The default is still 12 stocks,
  because the share rounding cannot hold 40 weights with $10,000. The open
  part is the choice of the default. See "The money cannot hold a large
  portfolio" below.

- **Is the gain of a large portfolio only the equal-weight premium?** A
  random weight vector of 40 assets sits near equal weight, so a 40-stock
  portfolio of the screen is near an equal-weight portfolio of the
  eligible pool. An equal-weight portfolio of large companies can beat the
  capitalisation weight of SPY without any skill in the screen. D20
  evidence 4 shows that a 10 times better search does not remove the gain,
  which supports this reading instead of ruling it out. The test is a third
  benchmark beside SPY: the equal weight of every stock that passes the
  four gates on each selection date. Until that test runs, the +3.68% is
  not proof that the screen adds value.
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
- **The survivorship bias that remains.** The price source serves the
  symbols that trade now, so a company that left the market has no history
  at all. D19 measures the hole and does not fill it: the source does not
  have 332 of the 2,123 symbols of the download list, and the share of the
  members with no prices rises from 0.8% on the last day to 8.8% in
  February 2025 for the `both` universe. A repair needs a second price
  source that serves a delisted company. Until then, every backtest window
  holds the companies that survived to today, and the further back the
  window, the larger the hole. See `data/missing_symbols.csv` and
  `output/universe_coverage.csv`.
- **12 current members have no prices.** `assert_current_members_have_prices`
  lists them. These are repairable, and the 333 companies that left the
  market are not. BF.B needs another spelling of the ticker, because the
  API does not use a full stop. KVUE, PSKY and WBD are in the middle of an
  acquisition, so the index seed still holds them and the quote API does
  not.
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

- **A small investment amount cannot hold the weights.** D18 reports the
  problem, and it does not solve it. For $2,500 the plan of 12 stocks
  drops 3 of them, because one share of each costs more than its target
  weight. Two options are open: select fewer stocks when the amount is
  small, which changes the core loop and needs a measurement; or allow a
  part of a share, which depends on the broker of the user.

- **The money cannot hold a large portfolio.** This is the same problem
  from the other side, and D20 made it the limit of the exposure. With
  $10,000, a 24-stock plan drops 3 stocks (6.6% of the target weight), a
  40-stock plan drops 11 (9.5%), and a 60-stock plan drops 19 (16.6%).
  The smallest amount that holds every weight is $39,675 for 24 stocks and
  $916,335 for 40. The backtest holds the exact weights, so it measures a
  portfolio that $10,000 cannot buy. Three options are open: raise the
  default and accept the drift; allow a part of a share; or give the
  backtest the same whole-share rounding as the plan, so the measure and
  the plan agree. The third option is the one that makes the measure
  honest, and nobody measured its cost yet.

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

- **Which cap holds the market exposure down?** Solved by D20 (`9ad5e17`).
  `top_n_per_sector` holds nothing: while it is at or above
  `max_per_sector`, the selection can never look deeper than the top
  `max_per_sector` names of a sector, so a 3.3 times larger candidate pool
  gives the same portfolio to every decimal. `target_size` and
  `max_per_sector` hold the exposure. The 645 "unreachable" stocks of the
  earlier handoff were never reachable, and raising the screen cap does not
  reach them.

- **The backtest logs only 3 windows, and they overlap.** Solved by D16.
  `run_pipeline.py --many-windows` runs the test on every valid date with
  a step of 5 trading days, and the results log holds the measure. The
  windows still overlap, so read the share as a measure, not as proof.

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
