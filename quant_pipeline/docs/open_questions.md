# Open questions

Each item is a problem or a question that is not solved. When you solve
one, move it to the "Solved" section with the commit hash.

## Open

### Results

- **Is the alpha that remains after momentum skill (D30)?** D30 found a
  UMD loading near 0.4 to 0.5, significant in 88% of the windows. UMD
  explains 25% to 45% of the one-factor alpha. A two-factor alpha of +5%
  to +7% a year remains, but no window gives it a t of 1.96 or more. More
  years of prices or a longer history of the method can decide it. The
  Fama-French SMB and HML factors are in `data/french/` and nobody has
  used them.

- **The Ichimoku chart as a timing aid (D27).** D27 removed the gate.
  The user reads the chart and decides on the timing. Two questions
  remain: does an Ichimoku entry signal improve the entry date inside the
  holding period, and does the chart improve the result of a person who
  reads it? Neither is measured.

- **Which holding period does the user select (D31)?** The backtest
  measures each window at 90, 120, 150 and 180 days with
  `--hold-days`. The return result holds at every hold: 61% to 74% of the
  windows beat SPY on the return. The Sharpe result does not improve in a
  reliable way: on the same dates the 90-day hold gives 58.8% on the
  Sharpe ratio, and on all valid dates it gives 48.5%. 18 recent windows
  make that difference, and they cover approximately one period. The
  default stays 180 days. The user decides. A longer price history is the
  only way to give each hold more periods that share no day.

- **The method beats SPY on the return and not on the Sharpe ratio.**
  D22 changed the ranking to the cumulative return, and the `sp500`
  portfolio now beats SPY on the return in 57.6% of 85 windows with a
  median window 4.84% above SPY. The median is positive on every date grid
  that D16 tried, so this result is stable. The Sharpe ratio is not: the
  mean is 0.68 against 0.80 for SPY, and the share of the windows that
  beat SPY on the Sharpe ratio is 50.6%, a coin flip. **The stated goal of
  the project is the Max Sharpe portfolio, so the headline number is still
  a loss.** The ranking buys return with volatility (13.3% to 16.1% on the
  live portfolio). Two questions follow: is a risk-adjusted ranking that
  is not the Sharpe ratio better, for example the Sortino ratio or the
  return over the maximum drawdown; and does the Sharpe gap close at a
  larger portfolio size, where D20 measured 0.82 against 0.80 under the
  old ranking?

- **The old default did not beat SPY either.**
  With the Sharpe ranking (10/10/3) the `sp500` portfolio beat SPY on the
  return in 47.1% of 85 windows, and the median window was 1.40% below
  SPY.
  D20 found that 40 stocks with at most 10 of a sector beats SPY on the
  median window (+3.68%), on the share of the windows (64.7%) and on the
  mean Sharpe ratio (0.82 against 0.80). The user selected 10 stocks (D21),
  so the pipeline gives up that measured gain. The reason to accept it is
  the plan: a 10-stock plan of whole shares works from $4,286, and a
  40-stock plan needs $916,335 to hold every weight. The open part is
  whether a backtest with whole-share rounding still favours 40 stocks for
  the amount that the user really invests. See the next item.

- **The selection rule adds return and not a risk-adjusted result.**
  D23 ran 200 random-order draws of the same method: the same screen, the
  same sector cap, the same correlation gate, the same weight search, and
  only the rank order replaced by a random permutation of the same
  candidates. The method beats **all 200** draws on the mean and the
  median excess return. It sits at the 72nd percentile on the mean Sharpe
  ratio, where **56 of the 200 random orders did better** and 9 of them
  beat SPY at 0.80, which the method does not. Two independent benchmarks
  now say the same thing, so this is the central open question of the
  project: the goal is the Max Sharpe portfolio and the selection rule
  does not deliver one. A ranking that is risk-adjusted but not the Sharpe
  ratio (the Sortino ratio, the return over the maximum drawdown) is the
  obvious next thing to measure.

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
  $10,000, a 10-stock plan drops nothing, a 24-stock plan drops 3 stocks
  (6.6% of the target weight), a 40-stock plan drops 11 (9.5%), and a
  60-stock plan drops 19 (16.6%).
  The smallest amount that holds every weight is $39,675 for 24 stocks and
  $916,335 for 40. The backtest holds the exact weights, so it measures a
  portfolio that $10,000 cannot buy. Three options are open: raise the
  default and accept the drift; allow a part of a share; or give the
  backtest the same whole-share rounding as the plan, so the measure and
  the plan agree. The third option is the one that makes the measure
  honest, and nobody measured its cost yet.

- **The Sortino ratio uses two targets.** The downside deviation of dbt
  uses 0, but the numerator subtracts the risk-free rate. The
  `max_sortino` objective of D29 uses the daily risk-free rate for the
  downside, so the two Sortino numbers of the project are not the same.
- **Is the gain of option B the optimizer or the sector spread (D29)?**
  Mostly answered by D32 and D33: the wide pool gives the gain. The
  rank order and the optimizer do not. D32 runs the null of D23 in the
  pool mode (200 draws). The method sits at the 59th percentile of the
  mean Sharpe ratio with a pool of 33 (null median 0.87), and at the
  25th percentile with a pool of 20. 172 of 200 random pools of 33 beat
  SPY. D33 gives equal weight on all 33 names a mean Sharpe ratio of
  0.88 (step 5) and 0.90 (step 3), against 0.88 and 0.87 for option B.
  Equal weight on the names that option B keeps gives 0.96 and 0.92, so
  the `max_sharpe` weights lower the result on the same names. The low
  beta of option B (0.75) comes from its weights: the same names at equal
  weight have a beta of 0.92. One part stays open. The name choice of the
  pruning helps with a pool of 33 and not with a pool of 20 on step 3, so
  its sign is not stable. The windows overlap, so these gaps are inside
  the noise of the grid.
- **Which default for the optimizer and the size (D29)?** The user
  decides. D33 shows that an equal weight of the same pool matches
  option B on the mean Sharpe ratio and has a higher median excess
  return. Its beta and its volatility are higher (1.00 against 0.75, and
  19.6% against 18.6%). The windows overlap, so the gaps are inside the
  noise. The pool of 33 gives the best Sharpe result and gives up about
  half of the median excess return (+3.67% against +7.05%). The
  exact solver with 10 stocks does not beat the Monte Carlo search out of
  sample.
- **Can the pool be larger than 33?** The sector cap applies to the
  pool, so 11 sectors at 3 names give at most 33. A larger pool needs a
  larger `max_per_sector`, which changes a second setting at the same
  time.
- **`fct_prices` and `int_bollinger` have no reader.** No model or script
  uses them.

### Project

- **Merge to `main`?** Not decided. See decision D3.

## Solved

- **How much of the alpha is the momentum premium?** Measured by D30
  (`519b44e`). The portfolio has a significant UMD loading in most
  windows. UMD explains 32% of the median alpha and 45% of the mean alpha
  with the French factor, and 25% and 28% with the in-house factor. The
  alpha that remains is not significant in any window. This also answers
  "Is the momentum ranking of D22 only a factor tilt?": it is mostly a
  factor tilt plus market beta, and the residual is too noisy to call.

- **The Monte Carlo search is not exact.** Solved by D29. `quant/exact.py`
  solves the Max Sharpe problem exactly, with bounds. On the live
  selection with no bounds it gives 4.37 against 4.26 for the random
  search. Out of sample, the exact weights do worse (mean Sharpe ratio
  0.70 with no bounds, 0.76 with 2% to 25%, against 0.78). The default
  stays the Monte Carlo search.

- **Does the rank order of the candidates do any work?** Solved by D23
  (`612afe2`). Yes for the return, no for the Sharpe ratio. See the open
  item above for the part that is not solved. The two nulls that stay open
  are an equal weight of the same 10 picks, which tests the weight search,
  and 10 random stocks of the whole index, which tests the four gates.

- **Which default portfolio size?** Solved by D21 (`845ce69`): 10 stocks,
  which the user selected. `max_per_sector` stays 3. Note that D21 could
  not separate 10/2, 10/3 and 12/3 by measurement: every small setting
  sits between 47.1% and 50.6% of the windows, and the date grid moves
  that share by approximately 5 points. **The open part is
  `max_per_sector`:** 2 reaches 7 sectors with 10 names instead of 6, and
  it measures the same inside the noise. The user has not chosen it.

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
