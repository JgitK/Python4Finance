# Decisions

Each entry records one decision: the question, the options, the choice, and
the evidence. The newest entry is at the top. Find the code with the commit
hash, for example `git show 4cfa116`.

Use this template for a new entry:

```markdown
## D<number>. <Short title>

- **Date:** YYYY-MM-DD
- **Role:** A protective measure outside the core loop, or a
  correctness fix in the core loop. See [README.md](README.md).
- **Question:** What did you have to decide?
- **Options:** The options that you examined.
- **Decision:** The option that you selected.
- **Evidence:** The data or the test that supports the decision.
- **Results:** How the numbers changed, if they changed.
- **Commits:** The commit hashes.
```

---

## D23. Measure the rank order against a random order

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It changes no
  number of a run. It measures how much of the result comes from the rank
  order, which no comparison with SPY can show.
- **Question:** The user asked why the SPY comparison matters when the
  goal is the Max Sharpe portfolio, and then asked for a benchmark that is
  "a different portfolio, put together the same way". SPY answers one
  question: does the pipeline beat the market? It cannot answer a second
  one: does the **rank order** of the candidates do any work, or would any
  10 stocks of the same screened pool have done as well?
- **Options:**
  1. Equal weight on the same 10 stocks that the method selected. This
     tests the Max Sharpe weight search only.
  2. 10 random stocks of the same screened pool, with the same sector cap.
     This tests the rank order and the correlation gate.
  3. 10 random stocks of the whole index, with no screen. This tests the
     four gates themselves.
- **Decision:** Option 2. The user selected it, and it is the sharpest of
  the three: option 1 tests the last step only, and option 3 tests a step
  that nobody has questioned yet. Options 1 and 3 stay open.
- **The design, and why it is a fair null:** The null keeps **every** other
  step of the method. It applies the screen of the same date, it uses the
  same sector cap, the same correlation gate, and the same Monte Carlo Max
  Sharpe weight search with the same seed. It removes one thing: the
  order. `build_max_sharpe_portfolio` takes an `rng`, and with one the
  candidate list becomes a random permutation of **the same list**. The
  null therefore cannot reach a stock that the ranked build could not see,
  and a test holds that property. Each draw is a whole walk-forward run of
  85 windows, at approximately 8.5 seconds.
- **Evidence:** `sp500`, 10 stocks, the `cum_return` ranking of D22, 85
  windows with a step of 5 days, against **200 random-order draws** (seed
  0), commit `612afe2`.

  | Measure | The method | Null median | Null best | Percentile |
  |---|---|---|---|---|
  | Beat SPY on return | 57.6% | 50.6% | 61.2% | 0.92 |
  | Beat SPY on Sharpe | 50.6% | 47.1% | 61.2% | 0.74 |
  | Mean excess return | +6.65% | +0.90% | +4.71% | **1.00** |
  | Median excess return | +4.84% | +0.22% | +4.15% | **1.00** |
  | Mean Sharpe ratio | 0.68 | 0.62 | 0.91 | 0.72 |

  SPY has a mean Sharpe ratio of 0.80 over the same windows.
- **What this says, in two parts.**

  1. **The rank order earns the return.** On the mean and the median
     excess return the method beats **all 200** draws. The best draw
     reached a median of +4.15% against +4.84% for the method, and 0 of
     200 draws reached the method's figure. A random order of the same
     candidates gives a median excess return of +0.22%, which is SPY. So
     the compound-return ranking of D22 is doing real work, and the gain
     is not a property of the screened pool alone.
  2. **The rank order does not earn a risk-adjusted result.** On the mean
     Sharpe ratio the method sits at the 72nd percentile: **56 of the 200
     random orders gave a better Sharpe ratio**, and 9 of them beat SPY at
     0.80, which the method does not. On the share of the windows that
     beat SPY on the Sharpe ratio the method sits at the 74th percentile.
     Above the middle, and inside the crowd.

  The two benchmarks now agree. D22 compared the method with SPY and found
  a return gain and no Sharpe gain. D23 compares it with its own random
  order and finds the same split. **The project optimizes for the Max
  Sharpe portfolio and the evidence says that its selection rule adds
  return, not risk-adjusted return.**
- **A note on the strongest-looking number:** A percentile of 1.00 on 200
  draws is not a p-value of 0.005. The 85 windows overlap, and the valid
  dates cover approximately two independent holding periods (D16). The
  200 draws are independent of each other, so the percentile is a fair
  statement about **this sample of windows**. It is not a test of
  significance over time.
- **The use of the best draw:** The null best column is the honest answer
  to "could I have done better by luck?". For the Sharpe ratio the answer
  is yes, and by a wide margin: 0.91 against 0.68. A reader who wants the
  Sharpe ratio should take that as a warning about the selection rule, not
  as a target.
- **Commits:** `612afe2`
- **A failure that this decision found:** `verify_indicators.py` ranked
  the pandas screen on the Sharpe ratio with a fixed rule, and it read
  every other gate from `dbt_project.yml`. After D22 the script therefore
  compared dbt against a rule that nobody uses, and the check failed with
  16 to 26 stocks different on each selection date. The pipeline was
  correct and the independent check was stale. `screen_rank_column` now
  reads `rank_metric` from the same place as the other gates, and it
  raises ValueError for an unknown value. Two new tests hold the script to
  the setting, and one of them compares the dbt variable with
  `PortfolioParams.rank_metric`, so a change to one layer alone now fails
  a test.

## D22. Rank the candidates on the cumulative return

- **Date:** 2026-11-06
- **Role:** Correctness fix and method choice, in the core loop. It
  changes which stocks pass the screen and which stocks the selection
  takes, so it changes every reported number. Each row before this
  decision ranked on the Sharpe ratio.
- **Question:** The user asked that the stocks which reach the Ichimoku
  gate be the top cumulative return securities. Both screen marts ranked
  the stocks inside each sector by `sharpe_ratio`, and `rank_by_sharpe`
  ordered the candidates for the greedy selection. What measure must do
  the ranking?
- **Options:**
  1. Keep the Sharpe ratio.
  2. Rank on the cumulative return of the lookback window.
  3. Make the measure a setting, and measure both.
- **Decision:** Option 3, with `cum_return` as the default, which is the
  request of the user. A setting is necessary here: the measure lives in
  two layers, and a change in one layer only gives a screen and a
  selection that disagree.
  - dbt: the variable `rank_metric` drives the `rank_column` macro, which
    `mart_screen_candidates` and `mart_screen_history` both use. The two
    screens therefore always rank on the same measure.
  - Python: `PortfolioParams.rank_metric` drives `rank_candidates`, which
    orders the candidates for `greedy_low_correlation`.
  - The flag `--rank-metric` reaches both. An unknown value stops the dbt
    build with a compiler error and raises `ValueError` in Python. A
    silent default would give a portfolio that nobody asked for.
- **A note on the two measures in one method:** The rank metric and the
  weight objective are now different measures. The rank selects the stocks
  on the compound return, and the optimizer then finds the **Max Sharpe**
  weights of the stocks that the rank selected. That is not a
  contradiction, and it is worth saying out loud: the method picks on
  momentum and weights on risk.
- **Evidence 1, the comparison:** `sp500`, 10 stocks, 85 windows, step 5
  days, commit `d65aef4`. The two rows differ in the rank metric only.

  | Rank | Beat SPY on return | On Sharpe | Mean excess | Median excess | Mean Sharpe | Live volatility |
  |---|---|---|---|---|---|---|
  | sharpe | 47.1% | 42.4% | +1.70% | -1.40% | 0.66 | 13.3% |
  | **cum_return** | **57.6%** | **50.6%** | **+6.65%** | **+4.84%** | 0.68 | 16.1% |

  SPY has a mean Sharpe ratio of 0.80 over the same windows. The control
  row is identical to the `845ce69` row, which proves that the
  `rank_metric` machinery changed nothing by itself.
- **Evidence 2, the date grid:** D16 found that the grid of the dates
  moves the share by approximately 5 points, so one grid cannot carry this
  result. Every grid agrees:

  | Step | Windows | sharpe: share / median | cum_return: share / median |
  |---|---|---|---|
  | 3 | 141 | 49.6% / -0.01% | 60.3% / +7.13% |
  | 5 | 85 | 47.1% / -1.40% | 57.6% / +4.84% |
  | 10 | 43 | 46.5% / -1.40% | 62.8% / +7.05% |
  | 21 | 20 | 45.0% / -0.67% | 65.0% / +6.87% |

  The cumulative-return ranking wins on all four grids, by 11 to 20
  points. The median excess return is **positive on all four grids** for
  `cum_return` and **negative on all four** for `sharpe`. That is the
  stable sign that D16 asks for, and it is the strongest result of the
  project so far.
- **The honest limit of this result:** The gain is in the return, and it
  is paid for with volatility. The mean Sharpe ratio moves from 0.66 to
  0.68 against 0.80 for SPY, and the share of the windows that beat SPY
  **on the Sharpe ratio** is 50.6%, which is a coin flip. Across the four
  grids that share is 54.6%, 50.6%, 48.8% and 60.0%, and the mean Sharpe
  ratio is below SPY on three of the four. So:

  **The method now beats SPY on the return. It still does not beat SPY on
  a risk-adjusted measure.** The stated goal of the project is the Max
  Sharpe portfolio, so this is the number that matters, and the ranking
  change does not move it. A reader who wants the return will take this
  change. A reader who wants the Sharpe ratio gains almost nothing.
- **The point-in-time column:** `int_risk_metrics_daily` had no cumulative
  return, so the change needed one. It uses the same trailing window as
  the other metrics, with `exp(sum(ln(1 + daily_return)) over w) - 1`.
  `assert_risk_metrics_daily_matches_latest` now compares that column with
  `int_risk_metrics` on the last day of each stock, to a tolerance of
  1e-12, so the point-in-time version is proved against the latest
  version. The ranking therefore uses no future data, and the tamper test
  of D5 still passes.
- **The discriminating test:** The screen history unit test gives AAA the
  better Sharpe ratio and BBB the better cumulative return on the second
  date, with one place in the Tech sector. The `cum_return` version
  expects BBB and the `sharpe` version expects AAA. Each test overrides
  `rank_metric`, so the pair proves that the macro selects the column and
  neither test depends on the build. `dbt build` gives PASS=89 for both
  settings.
- **Results:** The live portfolio changes from 6 sectors to 4 (Energy 3,
  Health Care 3, Information Technology 3, Materials 1), the annual return
  rises from 64.0% to 77.0%, and the volatility rises from 13.3% to 16.1%.
  The results log gains a Rank column, and every row before this decision
  used `sharpe`.
- **Commits:** `4837eeb`, `d65aef4`

## D21. Hold 10 stocks by default

- **Date:** 2026-11-06
- **Role:** Method choice, in the core loop. It changes the portfolio of
  every new run, so each row before this decision used 12 stocks.
- **Question:** D20 measured the portfolio size and changed no default. It
  left the choice to the user: 12 stocks, 24 stocks, or 40 stocks. The user
  selected **10 stocks**, which is below every setting of D20. What does a
  10-stock portfolio measure, and what does the change cost?
- **Options:** 10, 12, 24 or 40 stocks, with `max_per_sector` at a quarter
  to a third of that count.
- **Decision:** 10 stocks, with `max_per_sector` at 3.
  `PortfolioParams.target_size` goes from 12 to 10. The user named the
  count of stocks only, so `max_per_sector` does not change.
- **Evidence, the small sizes:** `sp500`, 85 windows, step 5 days. The
  screen cap is at its default of 10 in each row.

  | Caps | Stocks | Beat SPY on return | On Sharpe | Median excess | Mean Sharpe |
  |---|---|---|---|---|---|
  | 10/10/2 | 10 | 50.6% | 45.9% | +0.07% | 0.62 |
  | **10/10/3** | **10** | **47.1%** | **42.4%** | **-1.40%** | **0.66** |
  | 10/10/4 | 10 | 49.4% | 44.7% | -0.87% | 0.68 |
  | 10/10/5 | 10 | 49.4% | 44.7% | -0.87% | 0.69 |
  | 10/12/2 | 12 | 47.1% | 38.8% | -1.07% | 0.63 |
  | 10/12/3 | 12 | 48.2% | 45.9% | -0.27% | 0.68 |

  SPY has a mean Sharpe ratio of 0.80 over the same windows.
- **The honest reading of that table:** **No difference in it is real.**
  Every row sits between 47.1% and 50.6% on the return, and the date grid
  alone moves that share by approximately 5 points (D16). The medians sit
  between -1.40% and +0.07%, and they are all near zero. At 10 to 12
  stocks the method does not beat SPY and it does not clearly lose to it
  either. The choice between 10/2, 10/3 and 12/3 therefore cannot come
  from this data. It comes from the user.

  The comparison that **is** larger than the noise stays the comparison of
  D20: 10 stocks (47.1%, median -1.40%) against 40 stocks (64.7%, median
  +3.68%). The new default gives up that measured gain.
- **What the change buys:** The plan of whole shares gets much easier.
  The live `sp500` portfolio of commit `845ce69`, for $10,000:

  | Stocks | Warnings | Cash | Largest weight difference | Smallest amount that holds every weight |
  |---|---|---|---|---|
  | 10 | none | $74.31 | 1.80 points | **$4,285.96** |
  | 12 | none | $63.06 | 1.70 points | $8,552.56 |
  | 40 | 11 dropped, 7 above target | $301.74 | 1.14 points | $916,334.83 |

  A 10-stock plan works down to $4,286, which is half of the 12-stock
  figure and 1/214 of the 40-stock figure. The user can therefore place
  the plan that the backtest measures, which is not true of 40 stocks (see
  D20, "The price of the exposure"). This is the one measured gain of the
  change.
- **The sector mix:** 10 stocks with at most 3 of a sector reach 6
  sectors: Energy 3, Health Care 3, Financials 1, Industrials 1, Materials
  1, Real Estate 1. The 12-stock default reached 7. 6 of the 10 names sit
  in two sectors. `max_per_sector: 2` would reach 7 sectors with 10 names
  (Energy 2, Health Care 2, Industrials 2, Financials 1, Information
  Technology 1, Materials 1, Real Estate 1), and it measures the same
  inside the noise. That option stays open for the user.
- **One place holds the caps:** The two caps lived in
  `PortfolioParams` and in the signature of
  `select_portfolio.greedy_low_correlation`. Two defaults can drift, and
  then the live run and a direct caller select different portfolios.
  `greedy_low_correlation` now requires `target_size` and
  `max_per_sector`, so `PortfolioParams` is the one place. Every caller
  already passed the two values, so no behaviour changed. A test holds this
  property.
- **Results:** The live portfolio drops CSX and ADI from the 12-stock
  portfolio and keeps the other 10. The in-sample Sharpe ratio falls from
  4.66 to 4.47, which is the expected direction: a smaller search finds a
  worse fit. The walk-forward measure goes from 48.2% to 47.1% on the
  return and the median from -0.27% to -1.40%, both inside the noise of
  the date grid.
- **Commits:** `845ce69`

## D20. The portfolio size holds the exposure, not the screen cap

- **Date:** 2026-11-06
- **Role:** Measurement of the core loop. It changes no default, so no
  earlier row of the results log changes. It names the cap that holds the
  exposure down, and it shows what a larger portfolio does.
- **Question:** The user wants as much market exposure as possible. The
  handoff named two caps. `top_n_per_sector` (10) keeps the top 10 names of
  each sector in `mart_screen_candidates`, so that mart holds 110 rows at
  most. `greedy_low_correlation(target_size=12, max_per_sector=3)` then
  keeps 12 of the 110. With the `both` universe, 755 stocks pass the four
  gates and 645 of them never reach the selection. Which cap holds the
  exposure, and what happens to the results when it goes up?
- **Options:**
  1. Raise `top_n_per_sector` only. This gives the selection a deeper pool
     of each sector.
  2. Raise `target_size` and `max_per_sector` only. This gives a larger
     portfolio from the same pool.
  3. Raise the three together.
  4. Change no default, and measure each setting first.
- **Decision:** Option 4 for now. The measurement below shows that
  option 1 does nothing at all, and that option 2 moves the method from
  a loss against SPY to a gain. The defaults stay at 10/12/3 until the
  user accepts the cost that the share rounding adds (see "The price of
  the exposure"). The three caps now come from the command line, so each
  results row states the setting that made it.
- **The reason that the screen cap does nothing:** The selection reads the
  candidates in Sharpe order and it takes at most `max_per_sector` names
  from one sector. It can therefore never look deeper than the top
  `max_per_sector` names of a sector. While
  `top_n_per_sector >= max_per_sector`, the screen cap is slack. With the
  defaults, the selection needs the top 3 names of a sector and the screen
  offers the top 10. The 645 stocks of the handoff were never reachable:
  they rank below the third name of their sector, and the portfolio holds
  only three names of a sector. The cap binds a little at
  `max_per_sector: 10`, where the correlation gate can empty a sector of
  10 names, and the effect on the measure is inside the noise of the date
  grid.
- **Evidence 1, the screen cap:** `sp500`, 85 windows, step 5 days.

  | Caps | Candidates | Beat SPY on return | On Sharpe | Median excess |
  |---|---|---|---|---|
  | 10/12/3 | 110 | 48.2% | 45.9% | -0.27% |
  | 25/12/3 | 243 | 48.2% | 45.9% | -0.27% |
  | 100000/12/3 | 359 | 48.2% | 45.9% | -0.27% |
  | 10/24/6 | 110 | 62.4% | 56.5% | +2.46% |
  | 25/24/6 | 243 | 62.4% | 56.5% | +2.46% |
  | 100000/24/6 | 359 | 62.4% | 56.5% | +2.46% |

  A 3.3 times larger candidate pool gives the same portfolio, the same
  sector mix, the same three windows, and the same measure to every
  decimal. The `both` universe agrees: 110 candidates and 755 candidates
  both give the same 40 stocks and the same median of +3.52%.
- **Evidence 2, the portfolio size:** `sp500`, 85 windows, step 5 days.
  The screen cap is removed, so only the portfolio caps change.

  | Caps | Stocks | Beat SPY on return | On Sharpe | Median excess | Mean Sharpe |
  |---|---|---|---|---|---|
  | 100000/12/3 | 12 | 48.2% | 45.9% | -0.27% | 0.68 |
  | 100000/24/6 | 24 | 62.4% | 56.5% | +2.46% | 0.82 |
  | 100000/40/10 | 40 | **64.7%** | **61.2%** | **+3.68%** | 0.82 |
  | 100000/60/15 | 60 | 61.2% | 56.5% | +3.43% | 0.76 |

  SPY has a mean Sharpe ratio of 0.80 over the same windows. This is the
  first setting of the project that beats SPY on the median window, on
  the share of the windows, and on the mean Sharpe ratio at the same time.
  The measure rises to 40 stocks and then falls, so the gain is not
  "more is always better".
- **Evidence 3, the `both` universe:** 85 windows, step 5 days.

  | Caps | Candidates | Beat SPY on return | On Sharpe | Median excess |
  |---|---|---|---|---|
  | 10/12/3 | 110 | 45.9% | 37.6% | -0.72% |
  | 10/24/6 | 110 | 57.6% | 49.4% | +2.61% |
  | 10/40/10 | 110 | 61.2% | 54.1% | +3.52% |
  | 100000/40/10 | 755 | 61.2% | 55.3% | +3.52% |
  | 100000/60/15 | 755 | 63.5% | 56.5% | +3.65% |

  The portfolio size gives the same gain in the larger universe, and
  `sp500` at 40 stocks still measures better than `both` at 40 stocks
  (+3.68% against +3.52%). `both` also carries 2 to 3 times more
  survivorship bias (D19). The larger universe is therefore not the way
  to more exposure. D13 stands.
- **Evidence 4, the Monte Carlo search is not the cause:** A larger
  portfolio has more assets, and a random weight vector of 40 assets sits
  near equal weight, so a weak search could explain the gain. A run of
  `100000/40/10` with 100,000 random portfolios instead of 10,000 raises
  the in-sample Sharpe ratio from 4.64 to 4.99 and leaves the measure
  almost unmoved: 62.4% on return, 61.2% on Sharpe, median +3.57% against
  +3.68%. The gain comes from the count of the stocks, not from the
  weights of the optimizer.
- **The price of the exposure:** A plan of whole shares cannot hold 40
  target weights with $10,000. D18 reports this, and the report grows with
  the portfolio size. `sp500`, $10,000:

  | Caps | Stocks dropped by the rounding | Their target weight | Smallest amount that holds every weight |
  |---|---|---|---|
  | 100000/12/3 | 0 | 0.0% | $10,000 is enough |
  | 100000/24/6 | 3 of 24 | 6.6% | $39,675 |
  | 100000/40/10 | 11 of 40 | 9.5% | $916,335 |
  | 100000/60/15 | 19 of 60 | 16.6% | $1,638,602 |

  The backtest holds the exact weights. It therefore measures a portfolio
  that $10,000 cannot buy. The 40-stock measure of evidence 2 is the
  measure of the method, not of the plan that the user can place today.
  This is the reason that the default does not change in this decision.
- **The sector mix:** The screen cap balances the sectors, so a larger
  portfolio spreads over more of them. `sp500`, live run:

  | Caps | Sectors | The mix |
  |---|---|---|
  | 10/12/3 | 7 | Energy 3, Health Care 3, Industrials 2, Financials 1, Information Technology 1, Materials 1, Real Estate 1 |
  | 100000/24/6 | 9 | Energy 6, Health Care 6, Industrials 3, Information Technology 3, Consumer Staples 2, Consumer Discretionary 1, Financials 1, Materials 1, Real Estate 1 |
  | 100000/40/10 | 9 | Energy 10, Health Care 10, Industrials 6, Financials 4, Information Technology 4, Consumer Discretionary 2, Consumer Staples 2, Materials 1, Real Estate 1 |

  The count of sectors rises from 7 to 9. The largest sector stays at 25%
  of the names (3 of 12, and 10 of 40), because each setting raises
  `max_per_sector` and `target_size` by the same factor. A larger
  portfolio therefore adds sectors, and it does not concentrate the
  portfolio more. `max_per_sector` holds the largest sector, not
  `top_n_per_sector`. No setting reaches Communication Services or
  Utilities in `sp500`, because no name of those two sectors passes the
  four gates on the last day.
- **The change:** `run_pipeline.py` gets `--top-n-per-sector`,
  `--target-size` and `--max-per-sector`. The results log gets a Caps
  column with the three values, so two settings of one commit are two
  rows. A run prints the sector mix, and `output/optimal_weights.csv` holds
  the sector of each stock. A build with `--top-n-per-sector` excludes
  `assert_screen_history_matches_candidates`, because that unit test
  compares the two screens and the screens use the cap of the project file.
- **What this does not measure:**
  1. A portfolio of 40 stocks of the screen may beat SPY because it is
     near an equal-weight portfolio of the eligible pool, and an
     equal-weight portfolio of large companies beat the capitalisation
     weight of SPY over these windows. The test is an equal-weight
     benchmark of the eligible pool. It is not in this decision.
  2. The windows overlap. The valid dates cover approximately two
     independent holding periods, and the date grid moves the share by
     approximately 5 points (D16). A rise from 48.2% to 64.7% is larger
     than that noise. A rise from 61.2% to 64.7% is not.
  3. The survivorship bias of D19 is in every row above.
- **Commits:** `9ad5e17`

## D19. Make the survivorship gap visible at the download

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It changes no
  number of a run. It measures a hole in the data that the numbers hide.
- **Question:** The price source has no prices for 345 of the 1,418
  members of the `both` universe. The share of the members with no prices
  rises as a date goes back: 0.8% on the last day, 4.2% in February 2026,
  6.5% in August 2025, and 8.8% in February 2025. That pattern is
  survivorship bias: the source serves the symbols that trade now, so a
  company that another company bought, or a company that a new ticker
  replaced, has no history at all. 333 of the 345 are not members of the
  universe on the last day, for example ATVI (Microsoft bought
  Activision), ABMD (Johnson & Johnson bought Abiomed) and ANSS (Synopsys
  bought Ansys).

  The pipeline hid this. `fetch_historical` read the body of an answer and
  returned the rows. For a symbol that the API does not have, the answer
  is HTTP 200 with `rCode 400` and `"Symbol not exists."` in the body, and
  no rows. The function returned an empty list, so an error looked the
  same as a quiet symbol. `cached_download` then wrote the empty list to
  the cache, and no later run asked again. The log of the download said
  "No prices for 333 symbols", as if that were normal.
- **Options:**
  1. Fill the gap from a second price source that serves a delisted
     company. The nasdaq API cannot do it at any price.
  2. Make the gap visible: separate an error of the API from a quiet
     symbol, record each symbol that the source does not have, and report
     the share on each run.
  3. Keep the three selection dates near the last day, where the coverage
     is good, and say nothing about the earlier dates.
- **Decision:** Option 2. The user selected it. Option 1 is the only real
  repair, and it needs a new data source, so it stays open. Option 3 hides
  the problem instead of measuring it.
- **The change:**
  * `nasdaq.rows_from_payload` reads the status of the body. It raises
    `SymbolNotFound` for code 1001, and `NasdaqApiError` for another
    error. It returns an empty list only for a symbol that exists and has
    no trade in the date range.
  * `ingest.download_all` sorts the problems into two groups. A missing
    symbol is a known gap: the download records it and continues, and it
    does **not** go in the cache, so each run asks again and the gap stays
    visible. Another error is a failure: the download still writes no
    price file, because a later run can repair it.
  * `ingest.write_missing_report` writes `data/missing_symbols.csv` with
    the ticker, the date of the check, and the message of the API.
  * The end of a download reports the share of the symbols that the source
    does not have, and it says that the backtest therefore holds a
    survivor of the period only.
  * A new warning test, `assert_current_members_have_prices`, lists a
    member of the universe on the last day with no prices. Such a row is
    repairable, and the 333 companies that left the market are not.
- **Evidence:** I deleted the 333 cached empty answers and asked the API
  again for each symbol, on 2026-11-06:

  | Answer | Symbols |
  |---|---|
  | The API has prices after all | **0** |
  | The symbol exists, and it has no trade | 1 |
  | "Symbol not exists." | **332** |
  | Another error | 0 |

  No symbol came back with data, so the cache was not the cause. The
  source does not have 332 of the 2,123 symbols of the download list,
  which is 15.6%. `assert_current_members_have_prices` gives 4 rows for
  `sp500` (BF.B, KVUE, PSKY, WBD) and 12 for `both`.
- **What this does not repair:** The backtest still holds a survivor of
  the period only. The result of a past window is therefore the result of
  a portfolio of the companies that are still here. This decision makes
  the size of that hole a number in the output. It does not fill it.
- **Commits:** `895fabe`

## D18. Say when the money cannot hold the weights

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It changes no
  number of a plan. It reports a limit of the plan that the numbers alone
  do not show.
- **Question:** D17 spends the cash of the share rounding, but it cannot
  make a part of a share. One share of a stock is a step, and the step is
  the price over the investment amount. When the step is larger than the
  target weight, no plan of whole shares can hold that weight: the plan
  holds 0 shares, or more than the target. For $2,500 the plan drops 3 of
  the 12 stocks and gives MPC 17.8% against a target of 11.6%. The output
  showed none of this. A reader saw 9 positions and a cash figure of
  $13.14, which looks correct. How does the pipeline report the limit?
- **Options:**
  1. Report nothing. The share counts are in `output/allocation.csv`, and
     a reader can compare them with the target weights.
  2. Print a warning for each weight that the plan cannot hold, and give
     the smallest amount of money that has no such problem.
  3. Change the selection: pick fewer stocks when the amount is small, so
     the optimizer proposes only what the money can buy.
- **Decision:** Option 2. Option 3 changes the core loop and the reported
  numbers, so it needs its own decision and its own measurement. It stays
  open.
- **The rule, and why it needs no limit of its own:** A warning comes from
  an exact condition, not from a threshold that a person selected. A stock
  gets a warning when the plan holds 0 shares of it, or when one share is
  larger than its target weight. `minimum_investment` returns the largest
  price divided by its weight, which is the smallest amount for which no
  step is larger than its target.
- **Evidence:** The live portfolio of commit `b495496`, with three
  amounts:

  | Amount | Cash | Largest weight difference | Warnings |
  |---|---|---|---|
  | $2,500 | $13.14 | 6.78 points | 3 stocks dropped, 5 above target |
  | $10,000 | $63.06 | 1.70 points | none |
  | $50,000 | $168.35 | 0.31 points | none |

  The pipeline reports $8,552.56 as the smallest amount for this
  portfolio. The stock that sets it is NUE: one share costs $273.87, and
  its target weight is 3.2%.
- **A note on the cash figure:** The cash of the $2,500 plan is $13.14,
  which is lower than the cash of the $10,000 plan. A low cash figure is
  therefore not proof of a good plan. The $2,500 plan spends almost every
  dollar, and it still holds the wrong portfolio.
- **Commits:** `d90c665`

## D17. Spend the cash that the share rounding leaves

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changes the share counts
  of a plan. It does not change the weights, the screen, or the backtest,
  so no row of the results log changes.
- **Question:** `allocate.py` gave each stock its share of the money,
  divided by the price, and rounded down. For an investment of $10,000 in
  12 stocks, that plan spent $8,319.56 and left $1,680.44, which is 16.8%
  of the money, in cash. The rounding also moved the portfolio away from
  the weights of the optimizer, and not by the same amount for each stock:
  an expensive share loses more of its weight than a cheap one, because
  the money that it cannot use is larger. ADI at $417.11 held 8.3% of the
  money against a target of 12.0%. VTRS at $19.04 held 10.1% against
  10.3%. What does the plan do with the cash?
- **Options:**
  1. Keep the cash. The plan is simple, and it never holds more of a stock
     than the target.
  2. Buy one more share at a time. Each step takes the share that moves
     the actual weights nearest to the target weights. Stop when no share
     is affordable, and stop when no share makes the plan better.
  3. Allow a part of a share. Some brokers sell them.
- **Decision:** Option 2. The pass runs on each plan.
  `allocation_summary(..., top_up=False)` gives the first pass alone.
  Option 3 is not a code question: it depends on the broker of the user,
  and the data does not say which broker that is.
- **Evidence:** The live plan of commit `31d2a09`, for $10,000 in the same
  12 stocks:

  | | First pass | With the top-up |
  |---|---|---|
  | Money spent | $8,319.56 | $9,936.94 |
  | Cash | $1,680.44 (16.8%) | $63.06 (0.6%) |
  | Largest weight difference | 3.65 points (TRV) | 1.70 points (MPC) |
  | Sum of the squared differences | 0.004721 | 0.000706 |

  The cash falls to less than the price of one share of the cheapest stock
  that the plan could still use. The weight error falls by a factor of 6.7.
- **The measure:** `weight_error` divides the cost of a stock by the
  investment amount, not by the money spent. The cash is therefore an
  error. Without that rule, a plan that buys nothing has no error, and the
  pass has no reason to buy a share. A test holds this property.
- **A note on the direction:** The top-up can hold more of a stock than
  the target. MPC ends 1.70 points above its target, because the third
  share at $444.73 moves MPC from 2.75 points below to 1.70 points above.
  That plan is nearer to the target than the cash is.
- **Commits:** `a20f26d`

## D16. Measure the method on many windows, not three

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It does not change
  the portfolio or the numbers of a run. It measures how much you can
  trust them.
- **Question:** Each results row held three windows. The windows start 126
  trading days apart, and each one lasts 180 trading days, so they overlap
  and they share most of their days. Three overlapping windows cannot show
  that a result is not luck. How does a row report the method?
- **Options:**
  1. Keep the three windows.
  2. Use only windows that do not overlap. The data holds approximately
     two such windows after the warm-up, so this gives two results.
  3. Run the test on every valid date with a small step, and report the
     share of the windows that beats the benchmark.
- **Decision:** Option 3, with option 1 beside it. `run_pipeline.py` gets
  `--many-windows` and `--window-step` (the default step is 5 trading
  days). The three windows stay in their columns, so a new row stays
  comparable with every old row. A new column holds the measure of the
  many windows.
- **Evidence:**
  1. A run with 85 windows takes approximately 10 seconds. The cost is not
     a reason to use three windows.
  2. `backtest.summarize_windows` reports `n_windows` and `n_scored`. A
     window that holds no result stays in the count. This matters: an
     earlier experiment counted 30 windows that held no stock as 0%
     losses, and reported a mean excess return of -4.49%. A second
     attempt dropped those windows in silence and reported +0.22%. Both
     numbers were wrong for the same reason, in two directions.
     `window_is_scored` and its test hold the correct behaviour now.
  3. `choose_many_selection_dates` drops a date before the start of the
     screen history, for the reason in the backtest date guard. The run
     reports 85 windows and 85 results, so no window is empty.
- **How stable is the measure?** Not very. The same data with a different
  step gives a different share. On `sp500`:

  | Step | Windows | Beat SPY on return | On Sharpe | Mean excess | Median excess |
  |---|---|---|---|---|---|
  | 3 | 141 | 46.1% | 44.0% | +0.33% | -0.53% |
  | 5 | 85 | 48.2% | 45.9% | +1.09% | -0.27% |
  | 10 | 43 | 46.5% | 48.8% | +1.99% | -0.66% |
  | 21 | 20 | 45.0% | 40.0% | -1.37% | -0.34% |

  The mean excess return changes its sign. The median stays negative on
  every step. Read the median, not the mean: a few large wins make the
  mean. The earlier experiment of this day used a different grid of 84
  dates and gave 53.6% on return for `sp500`, against 48.2% here. The
  grid moves the share by approximately 5 points, so a difference of 5
  points between two universes is not a difference.
- **Limit of the measure:** The windows overlap. The valid dates cover
  approximately two independent 180-day periods, so a share of 54% against
  46% is not proof of a difference. The measure is better than three
  windows. It is not a test of significance.
- **Results:** No number of a run changes. Each new row holds the measure.
- **Commits:** `06862e6`

## D15. Drop a ticker whose price history is not one security

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It removes 10 tickers from
  the Nasdaq universe and changes the reported numbers of that universe.
- **Question:** The price file holds tickers whose close goes from 4.71 to
  5,323,475 (NXTT) or from 2.80 to 6,080,000 (BDRX). Such a file mixes the
  prices before a reverse split and the prices after it, with no
  adjustment. The daily returns of such a history are not returns. How
  does the pipeline find these tickers?
- **Options:**
  1. Review each large move of each such ticker by hand. NXTT alone has 16
     large moves, and SEZL has 15.
  2. Drop a ticker when the highest close divided by the lowest close
     reaches a limit over the history.
  3. Do nothing. The volume rule (D14) reads each move.
- **Decision:** Option 2, with a limit of 1000. A new test,
  `assert_a_price_history_is_one_security`, lists each ticker above the
  limit. The 10 tickers above the limit go in the `price_data_exclusions`
  seed, with the span in the reason.
- **Evidence:**
  1. No listed share rises or falls by a factor of 1000 in four years.
  2. PARA is already in the seed for the same reason (D10). Its span is
     359,306. The new rule finds PARA too, so it agrees with the one
     exclusion that a person made by hand.
  3. The 11 tickers at or above the limit are BDRX, NXTT, GDHG, PARA,
     JDZG, KALA, SEZL, AIXI, NCT, NAAS and RDHL. **None of them passes the
     screen on any date, and none of them is in the S&P 500 seed.** The
     limit of 1000 is therefore safe: a lower limit of 100 catches 43
     tickers, and one of those does pass the screen.
  4. Option 3 is not safe. Without this decision the volume rule calls
     these moves "real", because a 1000x gap comes with a high volume.
     That answer is worse than no answer.
- **Results:** The large move count falls from 608 to 532. The `sp500`
  results do not change, because no excluded ticker is in that universe.
- **Commits:** `81e83c3`

## D14. Classify a large move with the volume rule

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It back-adjusts the prices
  of 24 corporate actions, so it changes the returns of those days.
- **Question:** D11 requires a review of each one-day move larger than
  50%. 598 moves had no review, so `verify_indicators.py` failed that
  check, and the `nasdaq` and `both` results stayed provisional. A review
  of 598 moves by hand is not practical. What rule replaces it?
- **Options:**
  1. Classify each move with the volume of the day. A real move brings a
     volume spike. A split brings a gap and no trading.
  2. Add a liquidity floor to the universe, so the micro-caps that hold
     most of these moves never enter it.
  3. Accept the warning and mark every result that uses the Nasdaq
     universe.
- **Decision:** Option 1. The user selected it. Option 2 changes the
  definition of the universe, so it needs its own decision. It stays open.
- **The rule:** `quant/large_moves.py` reads three signals of each move:
  the volume of the day divided by the median volume of the 60 days on
  each side; the move from the open to the close; and the gap, which is
  the open divided by the close of the day before. The tests run in this
  order:
  1. A gap by a factor of 5 or more, with no volume spike, is a corporate
     action. A share does not change its price by a factor of 5 in one day.
  2. A volume below 2x with a day that moves no more than 5% after the
     open is a corporate action. The price gapped, and then nobody traded.
  3. A volume at or above 6x is a real move. Many people traded.
  4. A move larger than 20% from the open to the close is a real move. A
     corporate action gaps at the open. It does not trade.
  5. Every other move is "unclear". A person reads it.
- **Evidence:**
  1. The rule never contradicts the 10 moves that a person classified by
     hand (D11). A test holds this property:
     `test_the_rule_never_contradicts_a_hand_review`. The rule names 8 of
     the 10 and leaves 2 to the person.
  2. The two that the rule leaves are HON and STRL. HON is the one
     corporate action that a person found: a spin-off with 3.1x volume and
     a day that moved only -5% after the open. No volume limit separates it
     from a real move, so the rule must not try. This is the reason for
     the "unclear" answer, and a test holds it.
  3. On the 532 large moves of the clean price file, the rule names 515:
     493 real moves and 22 corporate actions. 7 moves stay unclear, one
     for each of 7 tickers. A person read those 7 and wrote the rows with
     the evidence: 6 real moves and 1 corporate action.
  4. 16 tests cover the rule. Each test fails when a small bug goes into
     the code, and passes again when the bug comes out.
- **Results:**
  - `assert_large_moves_are_reviewed` passes. 0 moves have no review, down
    from 598. `verify_indicators.py` passes all of its checks again.
  - The `sp500` results do not change. HON is the only S&P 500 member with
    a corporate action, and its row was already in the seed.
- **Commits:** `81e83c3`

## D13. Keep the S&P 500 as the default universe

- **Date:** 2026-11-06
- **Role:** Method choice, in the core loop. It keeps the current default,
  so the reported numbers do not change.
- **Question:** The pipeline can use the S&P 500 (`sp500`), the Nasdaq
  universe (`nasdaq`), or the two together (`both`). Which one must be the
  default?
- **Options:** The three universes.
- **Decision:** Keep `sp500`. Mark the `nasdaq` and `both` results as
  provisional until a person reviews the large moves in the Nasdaq prices.
- **Evidence:**
  1. The live, in-sample Sharpe ratio goes up with the size of the
     universe: 4.66 (sp500), 5.72 (nasdaq), 6.01 (both). The out-of-sample
     Sharpe ratio goes down: 0.58, 0.55, 0.51. A bigger search finds a
     better fit, not a better method.
  2. A walk-forward run with 84 windows, each one a 180-day hold:

     | Universe | Beat SPY on return | Beat SPY on Sharpe | Mean excess | Median excess |
     |---|---|---|---|---|
     | sp500 | 53.6% | 45.2% | +0.22% | +0.19% |
     | nasdaq | 48.8% | 44.0% | +3.87% | -0.53% |
     | both | 45.2% | 38.1% | +3.00% | -2.45% |

     The two Nasdaq universes have a positive mean and a negative median.
     A few large wins make the mean. The best window is +60.5%. The
     windows overlap, and the valid dates cover about two independent
     180-day periods, so this table cannot show a real difference.
     **Update (D16):** the table above comes from one grid of 84 dates. A
     grid of 85 dates gives 48.2% on return for `sp500` and 56.5% for
     `nasdaq`, which reverses the order of the first two columns. The
     grid moves the share by approximately 5 points. This evidence is
     therefore weaker than it looks, and it cannot separate the
     universes. Evidence 1, 3 and 4 carry the decision.
  3. The data quality of the Nasdaq prices is not good enough. The price
     data holds 598 one-day moves larger than 50% that no person reviewed.
     102 of them are inside the Nasdaq universe, and 31 to 34 of the
     affected tickers pass the screen. D11 requires a review of each large
     move. `verify_indicators.py` fails this check.
  4. The survivorship bias is larger. The Nasdaq universe drops 55 to 105
     of approximately 1,000 members on each selection date (5% to 11%).
     The S&P 500 drops 4 to 20 of 503 members (1% to 4%).
- **Results:** The default does not change. The `nasdaq` and `both` rows in
  the results log are provisional.
- **Update, later the same day:** D14 and D15 solved the data quality
  problem of evidence 3. The `nasdaq` and `both` rows after commit
  `81e83c3` are not provisional. The numbers did not change, because none
  of the affected tickers passed the screen. Evidence 1, 2 and 4 stand, so
  the decision stands.
- **Commits:** `0e11033`, `329a747`, `23102b3`

## D12. Record the decisions and the results in `docs/`

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It does not
  change the numbers. It measures how much you can trust them.
- **Question:** Git records what changed. Where do the reasons and the
  results go?
- **Decision:** A `docs/` folder with three files: `decisions.md`,
  `results_log.md`, and `open_questions.md`. `run_pipeline.py` adds one row
  to the results log after each run, with the commit hash.
- **Evidence:** Before this decision, the reasons and the results of each
  change were only in the work notes, not in the repository.
- **Commits:** `f0509e1`

## D11. Keep real large moves. Back-adjust a corporate action only.

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changed the
  reported numbers.
- **Question:** What must the data layer do with a one-day move larger
  than 50%?
- **Options:**
  1. Set the return to null (the old rule).
  2. Keep every move, and back-adjust only a confirmed corporate action.
- **Decision:** Option 2. The `corporate_actions` seed lists each reviewed
  move as a `corporate_action` or as a `real_move`, with the evidence.
  `stg_prices` multiplies each earlier price by the gap factor (the open on
  the event day divided by the close of the day before). A warning test
  lists each large move that is not in the seed.
- **Evidence:** The data had 7 moves larger than 50%. Six were real trading
  on high volume, for example GL -53% on 20 times its usual volume and MRNA
  +177% on 46 times its usual volume. The old rule erased these moves. Only
  the HON move on 2026-06-29 was a corporate action: a gap of -48% at the
  open on normal volume, on the day that HONA joined the S&P 500. The price
  source adjusts most spinoffs: GE, 3M, and Danaher show no gap.
- **Results:** The backtest did not change. The screens changed: MRNA now
  fails the volatility gate after its spike.
- **Commits:** `4cfa116`

## D10. Exclude a ticker whose price history is a different security

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changed the
  reported numbers.
- **Question:** What must the pipeline do with PARA? Its prices go up to
  1,139,000 and its median volume is 87 shares.
- **Options:** Delete the rows by hand; add a rule for high prices; list
  the ticker in a seed with the reason.
- **Decision:** The `price_data_exclusions` seed lists PARA with the
  reason. `stg_prices` drops it. A warning test finds an index member with
  a median volume under 1,000 shares.
- **Evidence:** Paramount left the S&P 500 on 2025-08-08 and trades as
  PSKY. The nasdaq API now uses PARA for a different security.
- **Commits:** `9c2addd`

## D9. Store the prices as a Parquet file, not as a dbt seed

- **Date:** 2026-11-06
- **Question:** The S&P 500 universe has approximately 536,000 price rows.
  Where must they go?
- **Options:** A CSV seed (as before); a Parquet file that dbt reads as a
  source.
- **Decision:** A Parquet file in `data/`, committed to git (8.8 MB).
  `stg_prices` is a table, so a reader in another folder does not need the
  path of the file.
- **Evidence:** dbt seeds are for small reference tables. The root
  `.gitignore` ignored every `data/` folder, so `quant_pipeline/.gitignore`
  now keeps this folder.
- **Commits:** `ad891f6`, `9c2addd`

## D8. Report the survivorship bias that remains. Do not buy data.

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It does not
  change the numbers. It measures how much you can trust them.
- **Question:** The nasdaq API has no prices for a stock that does not
  trade now. What must the pipeline do with these index members?
- **Options:** Buy one month of data from a vendor; model each exit by
  hand; count the dropped members and report them.
- **Decision:** Count and report them (the minimum option).
  `mart_universe_coverage` flags each member with no prices or no sector.
  `run_pipeline.py` prints the count on each selection date and writes
  `output/universe_coverage.csv`.
- **Evidence:** 41 of 583 symbols have no prices. On the selection dates,
  the pipeline drops 10 to 20 of approximately 503 members. The 2023 bank
  failures occurred before the first date that the screen can use.
- **Commits:** `ad891f6`

## D7. Use the S&P 500 on each date as the universe

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changed the
  reported numbers.
- **Question:** The universe was a list of 43 stocks that are large today.
  This list has a survivorship bias. Which universe must replace it?
- **Options:** All Nasdaq-listed stocks; the Nasdaq-100; the S&P 500.
- **Decision:** The S&P 500 on each date. A stock can pass a screen only on
  the dates when it is in the index. The membership comes from
  fja05680/sp500 (MIT license). The GICS sectors come from
  datasets/s-and-p-500-companies (ODC-PDDL).
- **Evidence:** Only the S&P 500 has free, point-in-time membership data.
  No free history of the Nasdaq-100 was found. A list of Nasdaq stocks has
  no dates for when a stock joined or left. See the open question about the
  Nasdaq universe.
- **Results:** 110 candidates instead of 32. Live Sharpe (in-sample) 4.66.
  The backtest beats SPY in 1 of 3 windows.
- **Commits:** `ad891f6`, `9c2addd`

## D6. Use the same lookback window in the live run and the backtest

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changed the
  reported numbers.
- **Question:** The live run selected the stocks from the last 252 days.
  The backtest used all of the history. Which window is correct?
- **Decision:** The last 252 trading days in both. The function
  `pipeline.lookback_window` holds the rule. A test makes sure that, on the
  last date, the backtest gives the same weights as the live run.
- **Evidence:** Before the fix, the two runs selected different stocks on
  the same date (JPM, MSFT, and XOM instead of COP, CVX, and LIN).
- **Results:** Backtest +6.3%, +8.2%, +9.8% (was +5.8%, +4.3%, +6.6%).
- **Commits:** `9bc2d8c`

## D5. Remove the look-ahead bias with a point-in-time screen

- **Date:** 2026-11-06
- **Role:** Correctness fix, in the core loop. It changed the
  reported numbers.
- **Question:** The backtest started from the stocks that pass the screen
  today. Today's screen uses data from the holding periods. How can the
  backtest use only past data?
- **Options:** Backtest all 43 stocks without the screen; apply the screen
  on each past date.
- **Decision:** Apply the screen on each past date. `mart_screen_history`
  holds the screen on each date with only the data up to that date. The
  screen rules are in macros, so the live screen and the history use the
  same rules.
- **Evidence:** On each selection date, 17 to 22 stocks were different
  from today's screen. The verify script makes the screen again with pandas
  from prices that stop on each date. The two screens agree.
- **Results:** The newest window changed from +13.9% to +5.8% (SPY +11.2%).
  The backtest no longer beats SPY.
- **Commits:** `6505a47`, `e379ad0`, `0208699`

## D4. Write the project text in ASD-STE100

- **Date:** 2026-11-06
- **Decision:** All comments, docstrings, dbt descriptions, and documents
  use ASD-STE100 Simplified Technical English: short sentences, active
  voice, one instruction in each sentence, and no phrasal verbs.
- **Commits:** `8d87df4`

## D3. Keep the other project files on this branch

- **Date:** 2026-11-06
- **Question:** The repository has many files that this pipeline does not
  use. Can this branch delete them?
- **Decision:** Keep them. The branch can merge into `main` later. A merge
  with deletions would remove these files from `main`. The root README
  points to `quant_pipeline/`.
- **Commits:** `24a0865`

## D2. Verify the numbers a second way

- **Date:** 2026-11-06
- **Role:** Protective measure, outside the core loop. It does not
  change the numbers. It measures how much you can trust them.
- **Decision:** `verify_indicators.py` calculates the indicators, the risk
  metrics, the screen history, and the price adjustment again with pandas,
  and compares the results to dbt.
- **Commits:** `c324453` and later commits

## D1. Use dbt and DuckDB for the data, and Python for the statistics

- **Date:** 2026-11-06
- **Decision:** dbt and DuckDB do the set-based work: data cleanup, indicators,
  and screens. Python does the work that SQL does not fit: the Markowitz
  optimization and the walk-forward backtest.
- **Commits:** `9aa4770`, `0dfccbe`
