# Context for a new chat

This file holds the context of the project and nothing else. It has no
next steps and no plan. Read `handoff.md` beside it for the work that
comes next.

Last update: 2026-11-09. The docs describe D32 and D33 and the change of
aim in D34, on the branch `dbt-duckdb-markowitz-pipeline`.

## The aim of the product (D34)

The project no longer tries to beat SPY. The tool builds a Markowitz
portfolio and shows how much the user can trust it: the error range of
each input, a cloud of bootstrap frontiers, warning lights for each
assumption, and an honest scorecard against equal weight, SPY and the
random-order null. `docs/product_spec.md` holds the spec. The sections
below describe the measurements that led to this aim.

Why Markowitz does not help here:

- Markowitz needs known expected returns and a known covariance. The
  tool estimates them from past prices, and the optimizer uses the
  estimates as facts.
- The expected return is the weak input. Its standard error is
  approximately the volatility divided by the square root of the years
  of data: ±104% for 1 month, ±30% for 1 year, ±13% for 5 years, for a
  stock with a volatility of 30%. The covariance becomes accurate much
  faster.
- The optimizer puts the most weight on the largest upward errors
  (error maximisation, Michaud 1989). The in-sample Sharpe ratio of 5.32
  against a realized 0.88 shows it. 1/N beats mean-variance out of
  sample (DeMiguel, Garlappi and Uppal, 2009), and D33 gives the same
  result. The windows overlap, so the gap of D33 is inside the noise.
  The safe result is that the optimizer is not better.
- The screen ranks on the past return, and the optimizer uses the same
  return as its forecast. That is a selection bias.
- In the CAPM the market portfolio is on the efficient frontier, so SPY
  is a hard benchmark for a small set of stocks.
- Markowitz is a risk tool. Minimum variance, Ledoit-Wolf shrinkage,
  Black-Litterman and risk parity trust the mean less, and they work
  better in practice.

The user wants a ranking window from 1 month to 5 years. The window does
not remove the error, and each window measures a different effect:
short-term reversal at 1 month, momentum at 3 to 12 months, long-term
reversal at 3 to 5 years. The spec keeps the choice and shows the error,
the effect, the rank stability and the walk-forward result of each
window.

## Paste this into the new chat

> Read `quant_pipeline/docs/context.md` in the repository
> JgitK/Python4Finance, branch `dbt-duckdb-markowitz-pipeline`. Then read
> `docs/product_spec.md`, `docs/decisions.md` and the last rows of
> `docs/results_log.md`.

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
| `--hold-days` | 180 | `run_pipeline.py` | The holding checkpoints of a many-window run, for example `90,120,150,180`. Each window is measured at each checkpoint, in two views (D31). |
| `optimizer` | monte_carlo | `PortfolioParams`, `--optimizer` | `monte_carlo` tries 10,000 random weightings. `exact` solves the objective with the weight bounds (D29). |
| `objective` | max_sharpe | `PortfolioParams`, `--objective` | `max_sharpe`, `min_variance`, `max_sortino` or `min_cvar`. Only `exact` accepts an objective other than `max_sharpe` (D29). |
| `min_weight`, `max_weight` | 0.02, 0.25 | `PortfolioParams`, `--min-weight`, `--max-weight` | The bounds on each weight. Only `exact` uses them. Bounds that cannot sum to 1 raise ValueError (D29). |
| `size_mode` | fixed | `PortfolioParams`, `--size-mode` | `fixed` holds `target_size` stocks. `pool` lets `exact` pick the count from `pool_size` stocks (D29). |
| `pool_size` | 25 | `PortfolioParams`, `--pool-size` | The count of stocks that the selection gives to the pool mode. The sector cap applies to the pool (D29). |

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
  alpha is +6.17% a year and it is positive in 60.0% of the windows.
- **A part of the alpha is the momentum premium (D30).** A regression on
  the market and on the French UMD factor gives a UMD loading with a
  median of +0.41, significant in 88.2% of the 85 windows. The median
  alpha falls from +9.77% to +6.65% and the mean from +9.84% to +5.41%
  on the same days. No window has a two-factor alpha with a t of 1.96 or
  more. An in-house UMD from the project prices gives the same picture
  (correlation 0.91). So the excess return is beta, then momentum, then a
  residual that the data cannot separate from luck.
- **A shorter hold does not change the conclusion (D31).** On the 85
  dates with a full 180-day window, the method beats SPY on the return
  in 68.2% of the windows at 90 days and in 63.5% at 180 days. On the
  Sharpe ratio it gives 58.8% at 90 days. But all 103 valid dates of a
  90-day hold give 48.5% on the Sharpe ratio and a mean Sharpe ratio of
  1.02 against 1.16 for SPY. The 18 extra recent windows give 0 Sharpe
  wins. The median annual excess is +7.5% to +14.8% at every hold, so no
  hold is clearly best. The mean beta stays 1.49 to 1.62.
- **The exact optimizers and option B (D29).** With 10 stocks, no exact
  objective beats SPY on the mean Sharpe ratio: `max_sharpe` 0.76,
  `min_variance` 0.73, `max_sortino` 0.79, `min_cvar` 0.74, against
  0.80. `max_sortino` beats SPY on the return in 71.8% of the windows.
  Option B, where the optimizer keeps part of a pool, gives 0.88 against
  0.80 with a pool of 33 (0.87 against 0.81 on the step of 3 days), 61.2%
  of the windows on the Sharpe ratio, and a beta of 0.75. The median
  excess return falls from +7.05% to +3.67%. The defaults did not change.
- **The rank order does not earn the Sharpe result of option B (D32).**
  The null of D23 in the pool mode, 200 draws: the real pool of 33 sits
  at the 59th percentile of the mean Sharpe ratio (null median 0.87),
  and 172 of 200 random pools beat SPY. With a pool of 20 it sits at the
  25th percentile. The median excess return sits at the 86th percentile.
- **The optimizer weights do not help (D33).** Equal weight on all 33
  names gives a mean Sharpe ratio of 0.88 (0.90 on the step of 3), the
  same as option B, and a higher median excess (+5.01% against +3.67%).
  Equal weight on the names that option B keeps gives 0.96 (0.92). The
  low beta of option B (0.75) comes from its weights: the same names at
  equal weight have a beta of 0.92. The realized volatility of option B
  is 18.6% against 16.7% for SPY. The in-sample 11.3% is not a result.
  So the wide pool across the sectors gives the gain. The windows
  overlap, so these gaps are inside the noise. The measurement shows
  that the optimizer is not better, not that equal weight is better.
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
- The results log holds 68 rows. The Caps column and the Rank column say
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
- **The default weights are not exact.** The default stays the Monte
  Carlo search. D29 added exact solvers (`--optimizer exact`). With 10
  stocks they do worse out of sample than the random search, which
  holds a more even mix.
- **The residual alpha is not decided (D30).** After the market and
  momentum, an alpha of +5% to +7% a year remains, but it is not
  significant in any window. The Fama-French SMB and HML factors are in
  `data/french/` and nobody has used them.
- **The overlapping windows.** The 85 windows share most of their days,
  and the valid dates cover approximately two independent holding
  periods. A percentile or a share is a measure, not a test of
  significance. D31 counts the windows that share no day: 3 at 180
  days, 5 or 6 at 90 days.
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
  and `nasdaqtrader.com` are blocked. The Ken French site
  (`mba.tuck.dartmouth.edu`) answered on 2026-11-07 (D30).
- The French files end one month or more before the price data. The
  two-factor regression uses only the common days, so a late window has
  fewer days. Compare a one-factor alpha and a two-factor alpha only on
  the same days.
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
| The product spec (D34) | `docs/product_spec.md` |
| Why each decision was made | `docs/decisions.md` (D1 to D34) |
| How the results changed | `docs/results_log.md` (one row for each run) |
| Problems that are not solved | `docs/open_questions.md` |
| The work that comes next | `docs/handoff.md` |
| Universe rules and sources | `quant/reference.py` |
| Screen rules | `dbt/macros/screen.sql`, `dbt/macros/membership.sql` |
| The rank metric, in two layers | `dbt/macros/screen.sql` (`rank_column`), `quant/pipeline.py` (`rank_candidates`) |
| The portfolio selection | `quant/select_portfolio.py`, `quant/optimize.py` |
| The exact optimizers and the pool mode | `quant/exact.py` (D29) |
| Beta, alpha and the capital allocation line | `quant/capm.py`, `pipeline.live_capm` |
| The momentum factor and the two-factor regression | `quant/factors.py`, `run_pipeline.momentum_lines` |
| The Ken French factor files (end 2026-09-30) | `data/french/` |
| The share plan, whole or fractional | `quant/allocate.py`, `run_pipeline.share_plan` |
| The random-order null benchmark | `quant/null_benchmark.py` |
| The holding checkpoints (90 to 180 days) | `quant/holding.py`, `run_pipeline.run_checkpoints` |
| The rule for a large price move | `quant/large_moves.py`, `classify_large_moves.py` |
| Manual data fixes, with reasons | `dbt/seeds/corporate_actions.csv` (532 rows), `dbt/seeds/price_data_exclusions.csv` (11 tickers) |
| The symbols that the source lacks | `data/missing_symbols.csv` |
| Independent checks with pandas | `verify_indicators.py` |

## The state of the checks

350 Python tests pass. `dbt build` for `sp500` gives PASS=89 and 2
warnings, for `cum_return` and for `sharpe`. `verify_indicators.py`
passes every check, with three momentum checks since D30. A fresh sparse clone of the branch reproduces the
build, the tests and the live run exactly.

The `nasdaq` and `both` universes add a third warning, for a member with
an implausible volume. They were built and measured again at `6acf4fa`.
