# Project documentation

This folder is the lab notebook of the project. Git records what changed.
This folder records why it changed and what the results showed.

| File | What it holds | Who writes it |
|---|---|---|
| [decisions.md](decisions.md) | One entry for each important decision. | You, after each decision. |
| [results_log.md](results_log.md) | One row for each pipeline run. | `run_pipeline.py` adds the row. You write the note. |
| [open_questions.md](open_questions.md) | The problems and questions that are not solved. | You, when you find or solve one. |
| [handoff.md](handoff.md) | The state of the project and the rules of work, for a new chat. | You, at the end of each session. |

## How to use it

1. **Before a change**, read `open_questions.md`. Select one question.
2. **Make the change** in small commits. Write the reason in the body of each
   commit message.
3. **Run the pipeline.** `python run_pipeline.py` adds a row to
   `results_log.md`. Write a short note in the last cell of the new row.
   Use `--no-log` for an experiment that you do not want to record.
4. **After the change**, add an entry to `decisions.md` if you selected one
   option from two or more options. Put the commit hash in the entry.
5. **Update `open_questions.md`.** Move a solved question to the "Solved"
   section with the commit hash.
6. **Commit the documents** with the code, or in the next commit.

## Safeguards and correctness fixes

The core loop is the chain that makes a portfolio: screen, select,
optimize, allocate, and backtest. Each decision in
[decisions.md](decisions.md) carries a `Role` line. The role puts the
decision in one of two groups. A decision that only selects a default,
and changes no number, says so in its Role line.

### Protective measures, outside the core loop

These parts do not change the numbers. They measure how much you can trust
the numbers. Remove one, and the results stay the same. You then have less
proof that the results are correct.

| Decision | The safeguard |
|---|---|
| D2 | `verify_indicators.py` calculates the indicators, the risk metrics, the screen history, and the price adjustment again with pandas. It compares each result to dbt. One check proves that future data does not change a past selection. |
| D8 | `mart_universe_coverage` counts the index members that have no prices or no sector. Each run reports the count, so the survivorship bias that remains stays visible. |
| D12 | `docs/` holds the reasons and the results. `run_pipeline.py` adds one row to the results log with the commit hash, so each result points to the code that made it. |
| D10, D11 | Two warning tests watch the price data: `assert_members_have_plausible_volume` finds a ticker that names a different security, and `assert_large_moves_are_reviewed` finds a large one-day move that no person reviewed. A warning does not stop a build. |
| D15 | A third warning test, `assert_a_price_history_is_one_security`, finds a ticker whose close spans a factor of 1000. Such a file mixes the prices before and after a split. |
| D19 | The download separates an error of the price source from a quiet symbol. `data/missing_symbols.csv` holds each symbol that the source does not have, and the run reports the share. `assert_current_members_have_prices` finds a current member with no prices, which is the repairable case. |
| D18 | The pipeline prints a warning for each target weight that whole shares cannot hold, and it gives the smallest investment amount that has no such problem. |
| D20 | A run states the three caps of the exposure in the results log, so two settings of one commit are two rows. It also prints the sector mix of the portfolio, because the caps balance the sectors. |
| D21 | `PortfolioParams` is the one place that holds the two portfolio caps. `greedy_low_correlation` requires them, so a second default cannot drift away from the first. |
| D1 | The 48 data tests and the 15 unit tests in the dbt project check each model on every build. |

### Correctness fixes, in the core loop

These decisions changed the method. The numbers moved. The results before
each fix are not valid.

| Decision | The fix | The effect |
|---|---|---|
| D5 | The backtest applies the screen of each past date, not the screen of today. | The newest window fell from +13.9% to +5.8%. |
| D6 | The live run and the backtest use the same 252-day lookback window. | The windows changed to +6.3%, +8.2%, and +9.8%. |
| D7 | The universe is the S&P 500 on each date, not a list of 43 stocks that are large today. | The candidate count went from 32 to 110. |
| D10 | `stg_prices` drops PARA, because its price history is a different security. | The screens changed. |
| D11 | A real large move stays in the returns. Only a confirmed corporate action gets a back-adjustment. | The screens changed. MRNA now fails the volatility gate. |
| D14 | The volume rule classifies each large one-day move. The seed grew from 10 rows to 532 rows, and 24 of them get a back-adjustment. | The `nasdaq` prices changed. The `sp500` prices did not: HON is the only S&P 500 member with a corporate action. |
| D17 | The allocator spends the cash that the share rounding leaves. It buys the shares that move the weights back to the target. | For $10,000 the cash fell from $1,680.44 to $63.06, and the largest weight difference fell from 3.65 points to 1.70. |
| D21 | The default portfolio holds 10 stocks, not 12. | The live portfolio drops CSX and ADI. The in-sample Sharpe ratio falls from 4.66 to 4.47, and the median window from -0.27% to -1.40%, which is inside the noise of the date grid. |
| D15 | `stg_prices` drops 10 more tickers. The close of each one spans a factor of 1000 or more, so the file mixes two price regimes. | The Nasdaq universe lost 10 of approximately 1,000 members. None of them passed the screen. |

D9 supports both groups. It moved the prices to a Parquet file, so the
repository can hold the full S&P 500 history that D7 needs.

## The commit column in the results log

The commit column shows the code that made the row.

- `4cfa116` means that the code was the same as that commit.
- `4cfa116-dirty` means that the code had changes that were not committed.
  Commit the changes, then run the pipeline again to get a clean row.

A run with the same clean commit and the same results does not add a row.
