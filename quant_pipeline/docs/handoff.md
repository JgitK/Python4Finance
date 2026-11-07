# Handoff for a new chat

Give this file to a new chat. It holds the state of the project and the
rules of work. Update it at the end of each session.

Last update: 2026-11-06 (fourth session of that day). HEAD is `PLACEHOLDER`.

## Paste this into the new chat

> Read `quant_pipeline/docs/handoff.md` in the repository JgitK/Python4Finance,
> branch `dbt-duckdb-markowitz-pipeline`. Then read `docs/README.md`,
> `docs/open_questions.md`, and the last rows of `docs/results_log.md`.
> Continue from "Next steps" in the handoff.

## The project in one paragraph

`quant_pipeline/` picks a stock portfolio and tests the method against SPY.
dbt and DuckDB do the data work (prices, indicators, screens). Python does
the statistics (low-correlation selection, Max Sharpe weights, a
walk-forward backtest). The universe is point-in-time: the S&P 500 on each
date, a Nasdaq universe, or both (`run_pipeline.py --universe`). The
honest result so far: the method beats SPY, but only with a much larger
portfolio than the default. The default holds **10 stocks** (D21, the
choice of the user). At that size the `sp500` portfolio beats SPY on the
return in 47.1% of 85 walk-forward windows and on the Sharpe ratio in
42.4%, and the median window is 1.40% below SPY. With 40 stocks and at
most 10 of a sector, the same universe beats SPY on the return in 64.7% of
the windows, on the Sharpe ratio in 61.2%, and the median window is 3.68%
above SPY (D20). The user accepted the smaller portfolio, because a
10-stock plan of whole shares works from $4,286 and a 40-stock plan needs
$916,335 to hold every weight.

## What the user wants now

The user wants **as much market exposure as possible**, and the user wants
the survivorship bias under control. D20 answered where the exposure is,
and D21 set the default. Read "The limit of the exposure" below before you
change anything. **Neither the universe nor the screen cap is the limit.
The portfolio size is**, and the user selected 10 stocks for it.

That choice gives up the measured gain of 40 stocks, and the user knows
it. Do not raise the default again without the user. Two things are still
open: `max_per_sector`, where 2 reaches 7 sectors with 10 names instead of
6 and measures the same inside the noise; and a backtest with the same
whole-share rounding as the plan, which is the only way to say whether 40
stocks still wins at the amount that the user really invests.

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

The three caps of the exposure come from the command line:
`--top-n-per-sector`, `--target-size` and `--max-per-sector`. A run states
them in the Caps column of the results log, in that order. The default is 10/10/3
(D21). The setting that measures best is
`python run_pipeline.py --universe sp500 --target-size 40 --max-per-sector 10 --many-windows`,
and $10,000 of whole shares cannot hold it.

The price file `data/raw_prices.parquet` is in git, so no download is
necessary. `python -m quant.ingest` downloads the prices again (about one
hour; it continues after a stop because of the cache in `data/cache/`).

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D21; D22 is next) |
| How the results changed | `docs/results_log.md` (one row for each run) |
| Problems that are not solved | `docs/open_questions.md` |
| The groups of the decisions | the Safeguards section of `docs/README.md` |
| Universe rules and sources | `quant/reference.py` |
| Screen rules | `dbt/macros/screen.sql`, `dbt/macros/membership.sql` |
| The portfolio selection | `quant/select_portfolio.py`, `quant/optimize.py` |
| The share plan | `quant/allocate.py` |
| The rule for a large price move | `quant/large_moves.py`, `classify_large_moves.py` |
| Manual data fixes, with reasons | `dbt/seeds/corporate_actions.csv`, `dbt/seeds/price_data_exclusions.csv` |
| The symbols that the source lacks | `data/missing_symbols.csv` |
| Independent checks with pandas | `verify_indicators.py` |

## Rules of work

The user set these rules. Keep them.

1. **Test-driven development.** Write the test first. Show that it fails
   for the right reason. Then write the code.
2. **Mutation checks.** After a test passes, put a small bug in the code
   and show that the test fails. Then remove the bug.
3. **Verify as you go.** Run `dbt build`, `pytest`, and
   `verify_indicators.py`. After a push, clone the branch into a temporary
   folder and run the build and the tests there.
4. **ASD-STE100.** Write all comments, docstrings, descriptions, and
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

## The limit of the exposure

D20 measured the three caps. The result is short: only the portfolio size
matters.

| Cap | Where | Does it hold the exposure? |
|---|---|---|
| `top_n_per_sector` (10) | `dbt/dbt_project.yml`, `--top-n-per-sector` | **No.** |
| `target_size` (10) | `quant/pipeline.py`, `--target-size` | **Yes.** |
| `max_per_sector` (3) | `quant/pipeline.py`, `--max-per-sector` | **Yes.** |

`PortfolioParams` in `quant/pipeline.py` is the one place that holds the
last two. `greedy_low_correlation` requires them and has no default of its
own, so a second default cannot drift away from the first (D21).

`top_n_per_sector` is slack. The selection reads the candidates in Sharpe
order, and it takes at most `max_per_sector` names of one sector, so it can
never look deeper than the top `max_per_sector` names of a sector. While
`top_n_per_sector >= max_per_sector`, a larger candidate pool gives the
same portfolio. The measurement shows it:

| Universe | Caps | Candidates | Beat SPY on return | Median excess |
|---|---|---|---|---|
| sp500 | 10/12/3 | 110 | 48.2% | -0.27% |
| sp500 | 100000/12/3 | 359 | 48.2% | -0.27% |
| both | 10/40/10 | 110 | 61.2% | +3.52% |
| both | 100000/40/10 | 755 | 61.2% | +3.52% |

The earlier handoff said that 645 of the 755 eligible stocks of `both`
never reach the selection. That is true, and it does not matter: those 645
rank below the third name of their sector, and a 12-stock portfolio holds
at most 3 names of a sector. **Do not spend time on the screen cap.**

The portfolio size does move the measure. `sp500`, 85 windows, step 5 days:

| Stocks (caps) | Beat SPY on return | On Sharpe | Median excess | Mean Sharpe |
|---|---|---|---|---|
| **10 (10/10/3), the default** | 47.1% | 42.4% | -1.40% | 0.66 |
| 12 (100000/12/3) | 48.2% | 45.9% | -0.27% | 0.68 |
| 24 (100000/24/6) | 62.4% | 56.5% | +2.46% | 0.82 |
| **40 (100000/40/10)** | **64.7%** | **61.2%** | **+3.68%** | **0.82** |
| 60 (100000/60/15) | 61.2% | 56.5% | +3.43% | 0.76 |

SPY has a mean Sharpe ratio of 0.80 over the same windows. The measure
rises to 40 stocks and then falls. The step from 10 to 12 stocks is inside
the noise of the date grid, and the step from 10 to 40 is not. D21 holds
the small sizes in one table. `sp500` at 40 stocks also measures
better than `both` at 40 stocks (+3.68% against +3.52%), and `both` carries
2 to 3 times more survivorship bias, so `sp500` stays the default universe
(D13 stands).

**The price of the exposure.** The backtest holds the exact weights. A plan
of whole shares cannot. `sp500`, $10,000:

| Stocks | Dropped by the rounding | Their target weight | Smallest amount that holds every weight |
|---|---|---|---|
| **10, the default** | 0 | 0.0% | **$4,286** |
| 12 | 0 | 0.0% | $8,553 |
| 24 | 3 | 6.6% | $39,675 |
| 40 | 11 | 9.5% | $916,335 |
| 60 | 19 | 16.6% | $1,638,602 |

So the 40-stock measure is the measure of the method, not of a plan that
$10,000 can place. This is the reason that D20 changed no default, and the
reason that the user then selected the smallest size of all.

**Two things that the measure does not prove.** First, a random weight
vector of 40 assets sits near equal weight, so the 40-stock portfolio is
near an equal-weight portfolio of the eligible pool. An equal-weight
portfolio of large companies can beat the capitalisation weight of SPY with
no skill in the screen. The test is an equal-weight benchmark of the
eligible pool, and nobody ran it. Second, the windows overlap and the date
grid moves the share by approximately 5 points (D16), so 48.2% against
64.7% is a real difference and 61.2% against 64.7% is not.

**The eligible pool of each universe**, for a reader who still wants it:

| Universe | Members | Have prices | Pass all 4 gates |
|---|---|---|---|
| sp500 | 503 | 499 | 359 |
| nasdaq | 1,074 | 1,056 | 499 |
| both | 1,418 | 1,398 | 755 |

The eligible stocks of `both` are not balanced: Health Care 164,
Financials 142, Information Technology 110, Consumer Discretionary 101,
Industrials 69, Consumer Staples 41, Utilities 36, Energy 27, Real Estate
26, Materials 20, Communication Services 19. `max_per_sector` holds the
sector balance of the portfolio, so the imbalance of the pool does not
reach the portfolio. No `sp500` setting reaches Communication Services or
Utilities, because no name of those two sectors passes the four gates on
the last day.

## The survivorship bias

The price source serves the symbols that trade now. A company that another
company bought, or a company that a new ticker replaced, has **no history
at all**. D19 measures the hole. It does not fill it.

- 345 of the 1,418 members of `both` have no prices. 333 of them are not
  members on the last day: ATVI, ABMD, ANSS, AZPN, AY and others. 12 are
  still members, and those 12 are repairable.
- The share of the members with no prices rises as a date goes back: 0.8%
  on the last day, 4.2% in February 2026, 6.5% in August 2025, 8.8% in
  February 2025. That pattern is the bias.
- The source does not have 332 of the 2,123 symbols of the download list,
  which is 15.6%. `data/missing_symbols.csv` holds them with the message
  of the API.
- The bias is 2 to 3 times larger for `both` than for `sp500`. A larger
  universe therefore gives more exposure **and** more bias.
- The missing companies are the corporate-action exits, which is not a
  random group. An acquisition closes at a premium, so the hole can make
  a past return too low, not too high. Nobody measured that direction yet.

The only repair is a second price source that serves a delisted company.
The nasdaq API cannot do it. See `docs/open_questions.md`.

## Read this before you run the checks

`python verify_indicators.py` passes every check. The script takes several
minutes, so give it time. `dbt build` gives **2 warnings for `sp500`**
(PASS=88) and **3 for `nasdaq` and `both`** (PASS=87). No warning is a
data quality failure:

- `relationships_..._stg_sectors_` (11,899 rows): a ticker in the prices
  with no sector.
- `assert_current_members_have_prices`: 4 rows for `sp500` (BF.B, KVUE,
  PSKY, WBD), 12 for `both`. These are the repairable gaps of D19.
- For the Nasdaq universes, the sector coverage (9 rows).

The state of the data fixes:

- The `corporate_actions` seed holds 532 rows. 508 are real moves, which
  keep their return, and 24 are corporate actions, which get a
  back-adjustment. The volume rule in `quant/large_moves.py` classified
  515 of them, and 7 rows carry the note "Hand review (D14)". Run
  `python classify_large_moves.py` after a new download. See D14.
- The `price_data_exclusions` seed holds 11 tickers. The close of each new
  ticker spans a factor of 1,000 or more, so its price history is not one
  security. See D15.
- `run_pipeline.py --many-windows` runs the walk-forward test on every
  valid date. Use it for each new result. The measure moves by
  approximately 5 points with the grid of the dates, so read the median
  excess return, not the mean. See D16.
- A run with `--top-n-per-sector` excludes
  `assert_screen_history_matches_candidates`, so its build reports PASS=87
  for `sp500`, not PASS=88. That unit test compares the two screens, and
  the screens read the cap of the project file. See D20.
- `allocate.py` runs a second pass that spends the cash of the share
  rounding. For $10,000 the cash is $63.06, and it was $1,680.44. See D17.
- Step 4 of a run prints a warning for each target weight that whole
  shares cannot hold. $10,000 gives no warning. $2,500 gives 9, and it
  reports $8,552.56 as the smallest amount for that portfolio. See D18.

## Things that are easy to get wrong

- The root `.gitignore` ignores every `data/` folder. The file
  `quant_pipeline/.gitignore` keeps `quant_pipeline/data/`. Check that a
  new data file is in a commit with `git ls-files`.
- `stg_prices` must stay a table. A view keeps the relative path of the
  Parquet file.
- `Nasdaq.csv` in the repository root is from early 2015. Do not use it.
- The network allows `api.nasdaq.com` and `github.com` (git clone).
  `archive.org` and `nasdaqtrader.com` are blocked.
- A ticker can name a different security after a company leaves (PARA).
  A warning test finds such a ticker by its low volume.
- The API answers HTTP 200 for an error, and it puts the error in the
  body. `nasdaq.rows_from_payload` reads the body. Do not read the rows
  without it, or an error looks the same as a symbol with no trades.
- A refusal of the API does not go in the cache. A symbol with no trades
  does. Do not cache a refusal, or the gap of D19 becomes invisible again.
- `git worktree add` and `git clone` of this repository fail with
  `mmap failed` on this machine. Use `--no-checkout`, then
  `git sparse-checkout init --cone`, then
  `git sparse-checkout set quant_pipeline`, then `git checkout -f`.
- `timeout` is not a command on this machine.
- The Monte Carlo search uses the seed 42, so a run reproduces exactly.

## State at the end of this session

The session answered "Raise the two caps, and measure what happens", which
was step 1 of the earlier handoff, and then the user selected the default.
It added two decisions.

- **D20 (`9ad5e17`, `f79e526`):** the three caps come from the command
  line, the results log holds a Caps column, and a run prints the sector
  mix of the portfolio. 14 results rows hold the measurement.
  - `top_n_per_sector` holds nothing. A 3.3 times larger candidate pool
    gives the same portfolio and the same measure to every decimal, in
    `sp500` and in `both`.
  - `target_size` and `max_per_sector` hold the exposure. 40 stocks with
    at most 10 of a sector beats SPY on the median window, on the share of
    the windows, and on the mean Sharpe ratio at the same time.
  - A 10 times larger Monte Carlo search does not remove the gain, so the
    gain is not an artifact of the weight search.
  - D20 changed no default, because $10,000 of whole shares drops 11 of
    the 40 stocks.
- **D21 (`845ce69`):** the user selected **10 stocks**, so
  `PortfolioParams.target_size` goes from 12 to 10 and `max_per_sector`
  stays 3. 6 results rows hold the measurement of the small sizes.
  - The small sizes cannot be separated. 10/2, 10/3, 10/4, 10/5, 12/2 and
    12/3 all sit between 47.1% and 50.6% of the windows, and the date grid
    alone moves that share by approximately 5 points.
  - The gain is in the plan, not in the measure: a 10-stock plan of whole
    shares works from $4,286, against $8,553 for 12 stocks and $916,335
    for 40.
  - `greedy_low_correlation` now requires the two caps, so
    `PortfolioParams` is the one place that holds them.

161 tests pass, up from 143. `dbt build` for `sp500` gives PASS=88 and 2
warnings, as before. `verify_indicators.py` passes every check. The live
`sp500` run at the new default gives 110 candidates, an in-sample Sharpe
ratio of 4.47, 10 stocks over 6 sectors, and a $10,000 plan that spends
$9,925.69 with no warning.

## Next steps

1. **Give the backtest the same whole-share rounding as the plan.** This
   is now the most valuable step. The backtest holds exact weights, so it
   measures a portfolio that the money cannot always buy, and the error
   grows with the portfolio size. The user selected 10 stocks because a
   40-stock plan needs $916,335, so the trade that the user made rests on
   a measure that does not model the plan at all. After this change, the
   measure and the plan agree, and the best portfolio size can be measured
   for the amount that the user really invests. That answer can be 10
   stocks, and then the choice of D21 has real evidence behind it.
2. **Ask the user about `max_per_sector`.** D21 left it at 3, because the
   user named the count of stocks only. With 10 stocks, a cap of 3 puts 6
   of the 10 names in two sectors and reaches 6 sectors. A cap of 2
   reaches 7 sectors, and it measures the same inside the noise. This is a
   one-line change with a decision entry and a results row.
3. **Add an equal-weight benchmark of the eligible pool.** A 40-stock
   portfolio sits near equal weight, so the gain of D20 can be the
   equal-weight premium and not the work of the screen. SPY alone cannot
   separate the two. This is the one test that says whether the screen
   adds value, and it matters more now: if the gain of 40 stocks is only
   the equal-weight premium, the choice of 10 stocks costs nothing.
4. **Measure a liquidity floor for the Nasdaq universe.** D14 left this
   option open. The screen already has a volume gate of 100,000 shares, so
   the effect can be small. Measure it before you decide. Note that D20
   makes this less urgent: `sp500` measures better than `both` at every
   portfolio size, so the Nasdaq universe is not the road to more
   exposure.
5. **Find a second price source** for a delisted company. This is the only
   repair of the survivorship bias. The nasdaq API cannot do it.
6. **The web app.** The user asked for an interactive web app of this
   pipeline. Three plans are open, and the user has not selected one: a
   read-only batch site, a live parameter workbench, and a browser-only
   teaching tool with toggles that turn each removed bias back on. Note
   that `webapp/` in this repository is an early FastAPI scaffold that
   reads CSV exports from the R modules, not from `quant_pipeline`. The
   three caps of D20 are now command line flags, which is the shape that a
   parameter workbench needs.
