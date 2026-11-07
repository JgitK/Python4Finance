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
honest result so far: the method beats SPY, but only with a larger
portfolio than the default. With the default 12 stocks, the `sp500`
portfolio beats SPY on the return in 48.2% of 85 walk-forward windows and
on the Sharpe ratio in 45.9%, and the median window is 0.27% below SPY.
With 40 stocks and at most 10 of a sector, the same universe beats SPY on
the return in 64.7% of the windows, on the Sharpe ratio in 61.2%, and the
median window is 3.68% above SPY. See D20.

## What the user wants now

The user wants **as much market exposure as possible**, and the user wants
the survivorship bias under control. D20 answered where the exposure is.
Read "The limit of the exposure" below before you change anything.
**Neither the universe nor the screen cap is the limit. The portfolio size
is.** The open question for the user is whether the default changes from 12
stocks to 24 or 40, because whole shares of $10,000 cannot hold 40 target
weights.

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
them in the Caps column of the results log, in that order. The best setting
of the project is
`python run_pipeline.py --universe sp500 --target-size 40 --max-per-sector 10 --many-windows`.

The price file `data/raw_prices.parquet` is in git, so no download is
necessary. `python -m quant.ingest` downloads the prices again (about one
hour; it continues after a stop because of the cache in `data/cache/`).

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D20; D21 is next) |
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
| `target_size` (12) | `quant/pipeline.py`, `--target-size` | **Yes.** |
| `max_per_sector` (3) | `quant/pipeline.py`, `--max-per-sector` | **Yes.** |

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
| 12 (100000/12/3) | 48.2% | 45.9% | -0.27% | 0.68 |
| 24 (100000/24/6) | 62.4% | 56.5% | +2.46% | 0.82 |
| **40 (100000/40/10)** | **64.7%** | **61.2%** | **+3.68%** | **0.82** |
| 60 (100000/60/15) | 61.2% | 56.5% | +3.43% | 0.76 |

SPY has a mean Sharpe ratio of 0.80 over the same windows. The measure
rises to 40 stocks and then falls. `sp500` at 40 stocks also measures
better than `both` at 40 stocks (+3.68% against +3.52%), and `both` carries
2 to 3 times more survivorship bias, so `sp500` stays the default universe
(D13 stands).

**The price of the exposure.** The backtest holds the exact weights. A plan
of whole shares cannot. `sp500`, $10,000:

| Stocks | Dropped by the rounding | Their target weight | Smallest amount that holds every weight |
|---|---|---|---|
| 12 | 0 | 0.0% | $10,000 is enough |
| 24 | 3 | 6.6% | $39,675 |
| 40 | 11 | 9.5% | $916,335 |
| 60 | 19 | 16.6% | $1,638,602 |

So the 40-stock measure is the measure of the method, not of a plan that
$10,000 can place. This is the reason that D20 changed no default.

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
was step 1 of the earlier handoff. It added one decision.

- **D20 (`9ad5e17`):** the three caps come from the command line, the
  results log holds a Caps column, and a run prints the sector mix of the
  portfolio. 14 new results rows hold the measurement.
  - `top_n_per_sector` holds nothing. A 3.3 times larger candidate pool
    gives the same portfolio and the same measure to every decimal, in
    `sp500` and in `both`.
  - `target_size` and `max_per_sector` hold the exposure. 40 stocks with
    at most 10 of a sector is the first setting of the project that beats
    SPY on the median window, on the share of the windows, and on the mean
    Sharpe ratio at the same time.
  - A 10 times larger Monte Carlo search does not remove the gain, so the
    gain is not an artifact of the weight search.
  - **No default changed.** $10,000 of whole shares drops 11 of the 40
    stocks, which is 9.5% of the target weight, and a plan that holds
    every weight needs $916,335. The user must choose the default.

159 tests pass, up from 143. `dbt build` for `sp500` gives PASS=88 and 2
warnings, as before. `verify_indicators.py` passes every check. The live
`sp500` run at the default caps gives 110 candidates, an in-sample Sharpe
ratio of 4.66, and a $10,000 plan that spends $9,936.94. None of those
numbers moved.

## Next steps

1. **Ask the user for the default portfolio size.** This is the open
   decision of D20, and it is the only thing that gives the user the
   exposure that the user asked for. Three answers are open:
   - Keep 12 stocks. The $10,000 plan is exact, and the method loses to
     SPY on the median window.
   - Move to 24 stocks and at most 6 of a sector. The median window goes
     to +2.46%, and the $10,000 plan drops 3 of the 24 stocks (6.6% of the
     target weight).
   - Move to 40 stocks and at most 10 of a sector. The median window goes
     to +3.68%, and the $10,000 plan drops 11 of the 40 stocks (9.5%).
   A change of the default is a change of `PortfolioParams` in
   `quant/pipeline.py`, a decision entry, and a results row.
2. **Give the backtest the same whole-share rounding as the plan.** This
   is the honest repair of the problem in step 1. The backtest holds exact
   weights, so it measures a portfolio that the money cannot buy, and the
   error grows with the portfolio size. After this change, the measure and
   the plan agree, and the best portfolio size can be measured for the
   amount that the user really invests.
3. **Add an equal-weight benchmark of the eligible pool.** A 40-stock
   portfolio sits near equal weight, so the gain of D20 can be the
   equal-weight premium and not the work of the screen. SPY alone cannot
   separate the two. This is the one test that says whether the screen
   adds value.
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
