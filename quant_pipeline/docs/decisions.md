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
