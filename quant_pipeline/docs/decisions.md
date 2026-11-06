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
