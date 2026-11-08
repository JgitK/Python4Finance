# Context for a new chat

This file holds the context of the project and nothing else. It has no
next steps and no plan. Read `handoff.md` beside it for the work that
comes next.

Last update: 2026-11-07. The docs describe commit `6acf4fa` on the branch
`dbt-duckdb-markowitz-pipeline`.

## Paste this into the new chat

> Read `quant_pipeline/docs/context.md` in the repository
> JgitK/Python4Finance, branch `dbt-duckdb-markowitz-pipeline`. Then read
> `docs/decisions.md` and the last rows of `docs/results_log.md`.

## What the project is

`quant_pipeline/` picks a stock portfolio and it tests the method against
SPY. dbt and DuckDB do the data work: they clean the prices, they
calculate the indicators, and they apply the screen. Python does the
statistics: it ranks the candidates, it selects a low-correlation set, it
finds the Max Sharpe weights, it changes the weights to whole shares, and
it runs a walk-forward backtest.

The universe is point-in-time. A stock can pass a screen only on the
dates when it is in the index. `run_pipeline.py --universe` selects the
S&P 500 (`sp500`), a Nasdaq universe (`nasdaq`), or the two together
(`both`). The default is `sp500`.

## The result, stated honestly

**The method beats SPY on the return. It does not beat SPY on a
risk-adjusted measure.** The goal of the project is the Max Sharpe
portfolio, so the second sentence is the headline.

At the default settings, on 85 walk-forward windows with a step of 5
trading days and a hold of 180 trading days:

| Measure | The method | SPY |
|---|---|---|
| Share of windows that beat SPY on the return | 63.5% | - |
| Share of windows that beat SPY on the Sharpe ratio | 50.6% | - |
| Median excess return | +7.05% | - |
| Mean Sharpe ratio | 0.78 | 0.80 |

The screen has no Ichimoku gate since D27. The live run gives 110
candidates, 10 stocks over 4 sectors (Energy 3, Health Care 3,
Information Technology 3, Materials 1) and an in-sample Sharpe ratio of
4.26. A $10,000 plan of whole shares drops DELL and VLO, because one share
costs more than the target weight. `--fractional-shares` holds every
weight.

**The in-sample Sharpe ratio is not a result.** The optimizer tries
10,000 random weightings and it keeps the best, so a high number on the
window that it fits is certain. The live figure is 4.51 and the realized
figure is 0.68. The in-sample number also ranks the settings wrongly: the
`both` universe gives the highest in-sample Sharpe ratio of the small
settings (6.01) and the lowest realized one (0.60).

## How to start

```bash
cd quant_pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd dbt && dbt build --profiles-dir . && cd ..
python -m pytest
python verify_indicators.py
python run_pipeline.py --universe sp500 --investment 10000
```

The price file `data/raw_prices.parquet` is in git, so no download is
necessary. `python -m quant.ingest` downloads the prices again. It takes
approximately one hour, and it continues after a stop because of the
cache in `data/cache/`.

## The settings

| Setting | Default | Where | What it does |
|---|---|---|---|
| `universe` | sp500 | `dbt_project.yml`, `--universe` | The index membership on each date. |
| `top_n_per_sector` | 10 | `dbt_project.yml`, `--top-n-per-sector` | The candidates that each sector keeps in the screen. |
| `target_size` | 10 | `PortfolioParams`, `--target-size` | The count of stocks in the portfolio. |
| `max_per_sector` | 3 | `PortfolioParams`, `--max-per-sector` | The portfolio stocks that one sector can hold. |
| `rank_metric` | cum_return | `dbt_project.yml` and `PortfolioParams`, `--rank-metric` | The measure that ranks the candidates inside each sector. |
| `--null-draws` | 0 | `run_pipeline.py` | The draws of the random-order null benchmark. It needs `--many-windows`. |
| `--fractional-shares` | off | `run_pipeline.py` | Buy a part of a share where necessary. The plan then holds every weight and gives no warning (D26). |

Two settings live in two layers that must agree. `rank_metric` drives the
`rank_column` macro for the screen in dbt, and it drives
`rank_candidates` for the selection in Python. `--rank-metric` sets both.
Neither layer has a silent default: an unknown value stops the dbt build
and it raises ValueError in Python.

`PortfolioParams` in `quant/pipeline.py` is the one place that holds
`target_size` and `max_per_sector`. `greedy_low_correlation` requires the
two values and it has no default of its own.

## What the measurements established

- **The screen cap holds no exposure (D20).** The selection reads the
  candidates in rank order and it takes at most `max_per_sector` names of
  one sector, so it can never look deeper than the top `max_per_sector`
  names of a sector. While `top_n_per_sector` is at or above
  `max_per_sector`, a larger candidate pool gives the same portfolio to
  every decimal. A pool of 110 and a pool of 755 give the same result.
- **The portfolio size moves the measure (D20).** Under the Sharpe
  ranking, 40 stocks with at most 10 of a sector gave 64.7% on the
  return, 61.2% on the Sharpe ratio, a median of +3.68%, and a mean
  Sharpe ratio of 0.82 against 0.80 for SPY. The measure rose to 40
  stocks and it fell at 60. **That sweep ran before the ranking changed,
  and nobody repeated it.**
- **The money limits the portfolio size (D20, D21).** The backtest holds
  exact weights and a plan of whole shares cannot. With $10,000: a
  10-stock plan drops nothing, a 24-stock plan drops 3 stocks, a 40-stock
  plan drops 11, and a 60-stock plan drops 19. The smallest amount that
  holds every weight is $4,286 for 10 stocks, $39,675 for 24, $916,335
  for 40, and $1,638,602 for 60.
- **The small sizes cannot be separated (D21).** 10/2, 10/3, 10/4, 10/5,
  12/2 and 12/3 all sit between 47.1% and 50.6% of the windows, and the
  grid of the dates alone moves that share by approximately 5 points
  (D16). The user selected 10 stocks.
- **The cumulative-return ranking is the strongest result (D22).** The
  share of the windows rose from 47.1% to 57.6% and the median excess
  return from -1.40% to +4.84%. The median is positive on the date steps
  3, 5, 10 and 21, where the Sharpe ranking is negative on all four. That
  stable sign is what D16 asks for.
- **And it buys return with volatility (D22).** The mean Sharpe ratio
  moved only from 0.66 to 0.68, the win share on the Sharpe ratio is
  50.6%, and the live volatility rose from 13.3% to 16.1%.
- **The rank order earns the return and not a risk-adjusted result
  (D23).** A null benchmark repeats the whole walk-forward test with the
  same candidates in a random order. Against 200 draws the method beats
  **all 200** on the mean and the median excess return, and the best draw
  reached a median of +4.15% against +4.84%. On the mean Sharpe ratio the
  method sits at the **72nd percentile**: 56 of the 200 random orders did
  better, and 9 of them beat SPY at 0.80, which the method does not. A
  random order of the same candidates gives a median excess return of
  +0.22%, which is SPY.
- **The Ichimoku gate lowers the result (D24).** The screen keeps a
  stock with an Ichimoku score of 2 or more. With the gate off, the share
  of the windows that beat SPY on the return rose from 57.6% to 63.5%,
  the median excess return from +4.84% to +7.05%, and the mean Sharpe
  ratio from 0.68 to 0.78 against 0.80 for SPY. A stricter gate gives a
  lower result. D27 removed the gate from the code. The Ichimoku lines
  and the score stay as information for a chart: the user decides on the
  timing.
- **The three universes after D27.** `both` beats SPY on the return in
  68.2% of the windows with a median of +8.74%, `nasdaq` in 63.5% with
  +6.15%, and `sp500` in 63.5% with +7.05%. The mean Sharpe ratio is 0.68
  for `both`, 0.61 for `nasdaq` and 0.78 for `sp500`, against 0.80 for
  SPY. The mean realized beta is 1.64, 1.60 and 1.49. `both` and `nasdaq`
  carry 5 to 6 times more members with no prices than `sp500`. D28: the product uses `sp500` only.
- **A large part of the excess return is beta (D25).** The realized
  beta of the portfolio is 1.41 on average over the 85 windows, so the
  portfolio takes more market risk than SPY. After the beta, the median
  alpha is +6.17% a year and it is positive in 60.0% of the windows. The
  regression has only the market factor, so the alpha can still be a
  momentum premium.
- **Two independent benchmarks agree.** SPY and the random order both say
  the same thing: the selection rule adds return, not risk-adjusted
  return.

## What the safeguards are

`docs/README.md` holds the full table. The short list:

- `verify_indicators.py` rebuilds the indicators, the risk metrics, the
  screen history and the price adjustment with pandas, and it compares
  each result to dbt. One check puts absurd returns on every day after a
  selection date and it proves that the weights do not change.
- The dbt project holds 91 nodes. A build of `sp500` gives PASS=89 and 2
  warnings.
- Three warning tests watch the price data: a ticker that names a
  different security, a large one-day move that no person reviewed, and a
  price history that spans a factor of 1000.
- `mart_universe_coverage` counts the index members that have no prices
  or no sector, so the survivorship bias that remains stays visible.
- `run_pipeline.py` adds one row to `docs/results_log.md` with the commit
  hash, the caps and the rank metric.
- The results log holds 50 rows. The Caps column and the Rank column say
  which settings made each row.

## What is not solved

These are facts about the state, not a plan.

- **The survivorship bias.** The price source serves the symbols that
  trade now, so a company that left the market has no history at all. The
  source does not have 332 of the 2,123 symbols of the download list,
  which is 15.6%. For the `both` universe the share of the members with
  no prices rises from 0.8% on the last day to 8.8% in February 2025. The
  missing companies are the corporate-action exits, which is not a random
  group. Only a second price source can repair this, and the nasdaq API
  cannot do it.
- **The sectors are not point-in-time.** `read_sector_map` runs one query
  with no date, so every stock carries its newest GICS sector on every
  past date. `max_per_sector` therefore uses future information. The
  tamper test does not catch this, because it changes the returns matrix
  and not `dim_ticker`. Nobody measured the effect.
- **Some current members have no prices.**
  `assert_current_members_have_prices` lists them: 4 rows for `sp500`
  (BF.B, KVUE, PSKY, WBD) and 12 for `both`. These gaps are repairable,
  and the companies that left the market are not. BF.B needs another
  spelling of the ticker, because the API does not use a full stop. KVUE,
  PSKY and WBD are in the middle of an acquisition, so the index seed
  still holds them and the quote API does not.
- **The Monte Carlo search is not exact.** It finds a Sharpe ratio a
  little below the true maximum. A 10 times larger search raised the
  in-sample figure from 4.64 to 4.99 and it moved the realized measure by
  almost nothing.
- **The momentum premium is not separated from the skill.** A ranking on
  the trailing compound return is the classic momentum signal, so the
  gain of D22 can be a known factor premium. `quant_pipeline` has no
  factor regression.
- **The overlapping windows.** The 85 windows share most of their days,
  and the valid dates cover approximately two independent holding
  periods. A percentile or a share is a measure, not a test of
  significance.
- **`fct_prices`, `int_bollinger` and `mart_sector_leaders` have no
  reader.** Every build makes them and nothing selects from them.
- **The whole-share rounding is not in the backtest.** The backtest holds
  exact weights, so it measures a portfolio that the money cannot always
  buy, and the error grows with the portfolio size. With
  `--fractional-shares`, the live plan holds the exact weights, and the
  live plan and the backtest agree (D26).

## The rules of work

The user set these rules. Keep them.

1. **Test-driven development.** Write the test first. Show that it fails
   for the right reason. Then write the code.
2. **Mutation checks.** After a test passes, put a small bug in the code
   and show that the test fails. Then remove the bug. Two mutation checks
   in the last session found weak tests that passed a wrong
   implementation.
3. **Verify as you go.** Run `dbt build`, `pytest` and
   `verify_indicators.py`. After a push, clone the branch into a
   temporary folder and run the build and the tests there.
4. **ASD-STE100.** Write all comments, docstrings, descriptions and
   documents in Simplified Technical English: short sentences, active
   voice, one instruction in each sentence, no phrasal verbs.
5. **Document in `docs/`.** Add a decision entry for each choice between
   options. Write a note in each new results row. Update the open
   questions.
6. **Commit and push often** to `dbt-duckdb-markowitz-pipeline`. Do not
   open a pull request unless the user asks. Do not merge to `main`.
7. **Do not delete the other files** in the repository (decision D3).
8. **Explain with analogies.** The user learns by doing and likes
   analogies.
9. **Do not agree with a wrong statement.** The user asked for this
   directly. Say which part is wrong and show the evidence.

## How the user works

The user asks about the method, not only about the settings. Recent
questions: why the SPY comparison matters when the goal is the Max Sharpe
portfolio; whether the backtest is flawed because a stock that shows a
high return now did not have that return on a past date; and a request
for a benchmark that is "a different portfolio, put together the same
way". Answer such a question with a measurement, and name the part of the
question that is wrong when a part is wrong.

## Things that are easy to get wrong

- The root `.gitignore` ignores every `data/` folder. The file
  `quant_pipeline/.gitignore` keeps `quant_pipeline/data/`. Check that a
  new data file is in a commit with `git ls-files`.
- `stg_prices` must stay a table. A view keeps the relative path of the
  Parquet file.
- The two screen unit tests of `mart_screen_history` each override
  `rank_metric`. Keep those overrides, or a build with
  `--rank-metric sharpe` fails a test that states the other ranking.
- A build with `--top-n-per-sector` excludes
  `assert_screen_history_matches_candidates`, because that test compares
  the two screens and the screens read the cap of the project file. Such
  a build reports PASS=88 for `sp500`, not PASS=89.
- `--skip-dbt` reuses the warehouse of the last build, and the Caps cell
  of the new results row then reads the cap of `dbt_project.yml`. Build
  when you change a cap.
- `verify_indicators.py` must follow the settings of
  `dbt_project.yml`. It held a fixed Sharpe ranking after D22 changed the
  setting, so it compared dbt against a rule that nobody uses and it
  reported a failure for it. Keep the script in step with a new setting.
- `Nasdaq.csv` in the repository root is from early 2015. Do not use it.
- The network allows `api.nasdaq.com` and `github.com`. `archive.org`
  and `nasdaqtrader.com` are blocked.
- The API answers HTTP 200 for an error and it puts the error in the
  body. `nasdaq.rows_from_payload` reads the body.
- A refusal of the API does not go in the cache. A symbol with no trades
  does. Do not cache a refusal, or the gap of D19 becomes invisible.
- `git worktree add` and `git clone` of this repository fail with
  `mmap failed` on this machine. Use `--no-checkout`, then
  `git sparse-checkout init --cone`, then
  `git sparse-checkout set quant_pipeline`, then `git checkout -f`.
- `timeout` is not a command on this machine.
- The Monte Carlo search uses the seed 42, so a run reproduces exactly.

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D28) |
| How the results changed | `docs/results_log.md` (one row for each run) |
| Problems that are not solved | `docs/open_questions.md` |
| The work that comes next | `docs/handoff.md` |
| Universe rules and sources | `quant/reference.py` |
| Screen rules | `dbt/macros/screen.sql`, `dbt/macros/membership.sql` |
| The rank metric, in two layers | `dbt/macros/screen.sql` (`rank_column`), `quant/pipeline.py` (`rank_candidates`) |
| The portfolio selection | `quant/select_portfolio.py`, `quant/optimize.py` |
| Beta, alpha and the capital allocation line | `quant/capm.py`, `pipeline.live_capm` |
| The share plan, whole or fractional | `quant/allocate.py`, `run_pipeline.share_plan` |
| The random-order null benchmark | `quant/null_benchmark.py` |
| The rule for a large price move | `quant/large_moves.py`, `classify_large_moves.py` |
| Manual data fixes, with reasons | `dbt/seeds/corporate_actions.csv` (532 rows), `dbt/seeds/price_data_exclusions.csv` (11 tickers) |
| The symbols that the source lacks | `data/missing_symbols.csv` |
| Independent checks with pandas | `verify_indicators.py` |

## The state of the checks

218 Python tests pass. `dbt build` for `sp500` gives PASS=89 and 2
warnings, for `cum_return` and for `sharpe`. `verify_indicators.py`
passes every check. A fresh sparse clone of the branch reproduces the
build, the tests and the live run exactly.

The `nasdaq` and `both` universes add a third warning, for a member with
an implausible volume. They were built and measured again at `6acf4fa`.
