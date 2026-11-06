# Handoff for a new chat

Give this file to a new chat. It holds the state of the project and the
rules of work. Update it at the end of each session.

Last update: 2026-11-06 (third session of that day). HEAD is `a2cdfc6`.

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
honest result so far: the method does not beat SPY. On 85 walk-forward
windows the `sp500` portfolio beats SPY on the return in 48.2% of them and
on the Sharpe ratio in 45.9%, and the median window is 0.27% below SPY.

## What the user wants now

The user wants **as much market exposure as possible**, and the user wants
the survivorship bias under control. Read "The two limits of the exposure"
below before you change anything. The universe is not the limit.

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
necessary. `python -m quant.ingest` downloads the prices again (about one
hour; it continues after a stop because of the cache in `data/cache/`).

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D19; D20 is next) |
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

## The two limits of the exposure

The Nasdaq universe is already in the pipeline. `--universe both` gives
1,418 members. The universe is not the limit. Two caps are:

| Universe | Members | Have prices | Pass all 4 gates | Candidates | Portfolio |
|---|---|---|---|---|---|
| sp500 | 503 | 499 | 359 | 110 | 12 |
| nasdaq | 1,074 | 1,056 | 499 | 103 | 12 |
| both | 1,418 | 1,398 | **755** | 110 | 12 |

1. `top_n_per_sector: 10` in `dbt/dbt_project.yml` keeps the top 10 names
   of each sector, so `mart_screen_candidates` holds 110 rows at most.
   This is why `both` reports the same 110 candidates as `sp500`: the cap
   binds in both. 645 of the 755 eligible stocks never reach the selection.
2. `greedy_low_correlation(target_size=12, max_per_sector=3)` in
   `quant/select_portfolio.py` keeps 12 of the 110.

To measure the eligible pool, build with the cap removed:
`dbt build --profiles-dir . --vars '{"universe": "both", "top_n_per_sector": 100000}' --exclude assert_screen_history_matches_candidates`.
That unit test compares the mart with the screen history, and it fails
when the cap changes, so exclude it for the measurement only.

**Before you raise the caps:** the cap also does the sector balance. The
eligible stocks of `both` are not balanced: Health Care 164, Financials
142, Information Technology 110, Consumer Discretionary 101, Industrials
69, Consumer Staples 41, Utilities 36, Energy 27, Real Estate 26,
Materials 20, Communication Services 19. A larger cap gives a pool of
biotechnology and banks. `nasdaq` alone holds only 3 eligible Materials
names, so `both` is the better of the two Nasdaq options.

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

The session started from the universe comparison (D13) and added six
decisions. Each one has a clean-clone check.

- **D14, D15 (`895fabe` is later; the pair is `81e83c3`):** the volume rule
  classifies every large one-day move, and 10 tickers with a broken price
  history leave the universe. 598 moves had no review, and now 0 have
  none. **The numbers did not change at all**: a run on the old price data
  with the same 85 dates gives the same measure to every decimal, because
  none of those tickers passed the screen.
- **D16 (`06862e6`, `31d2a09`):** the results log holds the measure of 85
  windows. The measure moves by approximately 5 points with the grid of
  the dates, and the mean excess return changes its sign between grids.
  D13 holds an update: its 84-window table cannot separate the universes.
- **D17 (`a20f26d`):** the allocator spends the cash of the share
  rounding. For $10,000 the cash falls from $1,680.44 to $63.06.
- **D18 (`d90c665`):** a run says when whole shares cannot hold the target
  weights. The cash figure alone hides this: the $2,500 plan holds $13.14
  in cash and drops 3 of the 12 stocks.
- **D19 (`895fabe`, `a2cdfc6`):** the download separates a refusal of the
  API from a quiet symbol, and `data/missing_symbols.csv` records each
  refusal. I deleted the 333 cached empty answers and asked the API again:
  0 came back with data, so the cache was not the cause.

143 tests pass. The live `sp500` run gives 110 candidates, an in-sample
Sharpe ratio of 4.66, and a $10,000 plan that spends $9,936.94.

## Next steps

1. **Raise the two caps, and measure what happens.** This is the request
   of the user: more exposure. Read "The two limits of the exposure"
   first. The work is a decision entry, a change of
   `top_n_per_sector` and of `target_size` and `max_per_sector`, and a
   results row for each setting. Measure the sector mix of the portfolio
   before and after, because the cap also does the sector balance.
2. **Measure a liquidity floor for the Nasdaq universe.** D14 left this
   option open. The screen already has a volume gate of 100,000 shares,
   so the effect can be small. Measure it before you decide.
3. **Find a second price source** for a delisted company. This is the only
   repair of the survivorship bias. The nasdaq API cannot do it.
4. **The web app.** The user asked for an interactive web app of this
   pipeline. Three plans are open, and the user has not selected one: a
   read-only batch site, a live parameter workbench, and a browser-only
   teaching tool with toggles that turn each removed bias back on. Note
   that `webapp/` in this repository is an early FastAPI scaffold that
   reads CSV exports from the R modules, not from `quant_pipeline`.
