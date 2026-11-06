# Handoff for a new chat

Give this file to a new chat. It holds the state of the project and the
rules of work. Update it at the end of each session.

Last update: 2026-11-06 (second session of that day).

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
honest result so far: the method does not beat SPY (see the results log).

## How to start

```bash
cd quant_pipeline
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd dbt && dbt build --profiles-dir . && cd ..
python -m pytest
python verify_indicators.py
python run_pipeline.py --universe sp500
```

The price file `data/raw_prices.parquet` is in git, so no download is
necessary. `python -m quant.ingest` downloads the prices again (about one
hour; it continues after a stop because of the cache in `data/cache/`).

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D12; D13 is next) |
| How the results changed | `docs/results_log.md` (one row for each run) |
| Problems that are not solved | `docs/open_questions.md` |
| Universe rules and sources | `quant/reference.py` |
| Screen rules | `dbt/macros/screen.sql`, `dbt/macros/membership.sql` |
| Manual data fixes, with reasons | `dbt/seeds/corporate_actions.csv`, `dbt/seeds/price_data_exclusions.csv` |
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

## State at the end of this session

- **Done:** look-ahead fix (D5), same lookback (D6), S&P 500 universe (D7),
  survivorship report (D8), Parquet prices (D9), PARA exclusion (D10),
  real large moves (D11), docs system (D12), and the universe comparison
  (D13, `23102b3`).
- The Nasdaq prices are complete, in `data/raw_prices.parquet` (25 MB, in
  git). Two sessions downloaded the prices at the same time. The merge
  `b1a5be4` keeps the file of commit `a8a44b3`. The two files are not the
  same bytes, so a results row from before that merge can differ by a
  small amount.
- Two bugs are fixed. A unit test made every non-default universe build
  stop with an error (`0e11033`). The backtest selected dates that have no
  screen and counted them as 0% losses (`23102b3`).
- The docs separate a protective measure outside the core loop from a
  correctness fix in the core loop. See the Safeguards section of
  `docs/README.md`.

## Read this before you run the checks

`python verify_indicators.py` passes every check again. The script takes
several minutes, so give it time. `dbt build` gives 1 warning for `sp500`
and 2 for the other universes. The warnings are
`relationships_stg_prices_ticker__ticker__ref_stg_sectors_` (a ticker in
the prices with no sector) and, for the Nasdaq universes, the sector
coverage. No warning is a data quality failure now.

The `corporate_actions` seed grew from 10 rows to 532 rows. 508 rows are
real moves, which keep their return, and 24 rows are corporate actions,
which get a back-adjustment. `quant/large_moves.py` holds the rule that
classified 515 of them, and `classify_large_moves.py` runs it. 7 rows carry
the note "Hand review (D14)": the rule could not name those moves. See D14.

The `price_data_exclusions` seed grew from 1 ticker to 11. The close of
each new ticker spans a factor of 1000 or more over four years, so its
price history is not one security. See D15.

`data/missing_symbols.csv` holds the 332 symbols that the price source
does not have. The download writes the file again on each run, and it does
not cache a refusal, so the list stays current. See D19.

`allocate.py` runs a second pass that spends the cash of the share
rounding. For $10,000 the cash is $63.06, and it was $1,680.44. See D17.
Step 4 of a run also prints a warning for each target weight that whole
shares cannot hold. A run with $10,000 prints no warning. A run with
$2,500 prints 9. See D18.

`run_pipeline.py --many-windows` runs the walk-forward test on every valid
date, not only three. The row of the results log then holds the share of
the windows that beat SPY. Use it for each new result. See D16.

## Next steps

1. Measure a liquidity floor for the Nasdaq universe. D14 left this option
   open. See `docs/open_questions.md`.
2. The user asked for an interactive web app of this pipeline. Three plans
   are open, and the user has not selected one: a read-only batch site, a
   live parameter workbench, and a browser-only teaching tool with toggles
   that turn each removed bias back on. Note that `webapp/` in this
   repository is an early FastAPI scaffold that reads CSV exports from the
   R modules, not from `quant_pipeline`.
