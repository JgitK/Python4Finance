# Handoff for a new chat

Give this file to a new chat. It holds the state of the project and the
rules of work. Update it at the end of each session.

Last update: 2026-11-06 (fourth session of that day). HEAD is `edb563b`.

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
honest result so far, in one line: **the method beats SPY on the return
and it does not beat SPY on a risk-adjusted measure.**

The default holds **10 stocks** (D21, the choice of the user) and ranks
the candidates on the cumulative return of the lookback window (D22, also
the choice of the user). At that setting the `sp500` portfolio beats SPY
on the return in 57.6% of 85 walk-forward windows, and the median window
is 4.84% above SPY. The median is positive on every date grid that D16
tried, which no earlier setting managed. But the mean Sharpe ratio is
0.68 against 0.80 for SPY, and the share of the windows that beat SPY on
the Sharpe ratio is 50.6%, a coin flip. The ranking buys return with
volatility: the live portfolio moved from 13.3% to 16.1%.

**The goal of the project is the Max Sharpe portfolio, so read the Sharpe
numbers as the headline, not the return numbers.** By that measure the
method still loses to SPY. Two separate findings are open against it: a
larger portfolio closed the Sharpe gap under the old ranking (40 stocks
gave 0.82 against 0.80, D20), and nobody has measured a larger portfolio
with the new ranking.

## What the user wants now

The user wants **as much market exposure as possible**, and the user wants
the survivorship bias under control. D20 answered where the exposure is,
D21 set the default size, and D22 set the ranking. Read "The limit of the
exposure" below before you change anything. **Neither the universe nor the
screen cap is the limit. The portfolio size is**, and the user selected 10
stocks for it.

The user is now asking the right questions about the method itself, not
about the settings. In this session the user asked why the SPY comparison
matters when the goal is the Max Sharpe portfolio, and then asked for a
benchmark that is "a different portfolio, put together the same way".
That is the null benchmark of D23. Expect more questions of this kind, and
answer them with measurements, not with opinions. The user also said
plainly: **do not agree with a wrong statement.** Say which part is wrong
and show the evidence.

Open items that the user has not decided:
- `max_per_sector`, where 2 reaches 7 sectors with 10 names instead of 6
  and measures the same inside the noise (D21).
- A backtest with the same whole-share rounding as the plan. The choice of
  10 stocks rests on a measure that does not model the plan at all.
- Whether to keep a ranking that raises the return and not the Sharpe
  ratio, now that D22 has measured the trade.

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
them in the Caps column of the results log, in that order. The default is 10/10/3 with
`--rank-metric cum_return` (D21, D22). Two more flags matter:
`--rank-metric {cum_return,sharpe}` changes the measure that ranks the
candidates, in dbt and in Python together; `--null-draws N` runs the
random-order null benchmark of D23, which needs `--many-windows`. The
setting that measures best on the return is
`python run_pipeline.py --universe sp500 --target-size 40 --max-per-sector 10 --many-windows`,
and $10,000 of whole shares cannot hold it.

The price file `data/raw_prices.parquet` is in git, so no download is
necessary. `python -m quant.ingest` downloads the prices again (about one
hour; it continues after a stop because of the cache in `data/cache/`).

## Where things are

| What | Where |
|---|---|
| Why each decision was made | `docs/decisions.md` (D1 to D23; D24 is next) |
| How the results changed | `docs/results_log.md` (one row for each run) |
| Problems that are not solved | `docs/open_questions.md` |
| The groups of the decisions | the Safeguards section of `docs/README.md` |
| Universe rules and sources | `quant/reference.py` |
| Screen rules | `dbt/macros/screen.sql`, `dbt/macros/membership.sql` |
| The portfolio selection | `quant/select_portfolio.py`, `quant/optimize.py` |
| The rank metric, in dbt and in Python | `dbt/macros/screen.sql` (`rank_column`), `quant/pipeline.py` (`rank_candidates`) |
| The random-order null benchmark | `quant/null_benchmark.py` |
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

**Read every number of this section with one caveat: D20 ran before D22,
so the whole sweep used the Sharpe ranking.** The current default ranks on
the cumulative return. The conclusion about which cap binds does not
depend on the ranking, because it follows from the sector cap arithmetic.
The measured sizes do. Step 2 of "Next steps" repeats the sweep.

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
(PASS=89, measured after D22). The `nasdaq` and `both` universes add a
third warning for the sector coverage. **Those two universes were last
built before D22**, when `sp500` gave PASS=88 and they gave PASS=87, so
expect PASS=88 for them now. Confirm that before you rely on it. No
warning is a data quality failure:

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
  `assert_screen_history_matches_candidates`, so its build reports PASS=88
  for `sp500`, not PASS=89. That unit test compares the two screens, and
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
- The rank metric lives in **two** layers that must agree: the dbt
  variable `rank_metric` for the screen, and `PortfolioParams.rank_metric`
  for the selection. `--rank-metric` sets both. A change in one layer only
  gives a screen that keeps one set of stocks and a selection that
  prefers another. Neither layer has a silent default: an unknown value
  stops the dbt build and raises `ValueError` in Python.
- The two screen unit tests of `mart_screen_history` each override
  `rank_metric`. Keep those overrides. Without them a build with
  `--rank-metric sharpe` fails a test that states the `cum_return`
  ranking, and the test then measures the build and not the model.
- `--skip-dbt` reuses the warehouse of the last build, and `caps_label`
  then reads `top_n_per_sector` from `dbt_project.yml`. If the last build
  used a different `--top-n-per-sector`, the Caps cell of the new row is
  wrong. Build when you change a cap.
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
- **D22 (`4837eeb`, `d65aef4`, `edb563b`):** the user asked that the
  stocks which reach the Ichimoku gate be the top cumulative return
  securities. The rank metric is now a setting in two layers that must
  agree: the dbt variable `rank_metric` drives the `rank_column` macro for
  both screen marts, and `PortfolioParams.rank_metric` drives
  `rank_candidates` for the selection. `--rank-metric` reaches both. The
  default is `cum_return`.
  - **This is the strongest result of the project.** The share of the 85
    windows that beat SPY on the return rises from 47.1% to 57.6%, and the
    median excess return from -1.40% to +4.84%. The median is positive on
    the date steps 3, 5, 10 and 21, where the Sharpe ranking is negative
    on all four. D16 asked for exactly that stable sign.
  - **And it does not move the Sharpe ratio.** The mean goes from 0.66 to
    0.68 against 0.80 for SPY, the win share on the Sharpe ratio is 50.6%,
    and the live volatility rises from 13.3% to 16.1%. The ranking buys
    return with volatility.
  - `int_risk_metrics_daily` gained a point-in-time `cum_return_window`,
    and `assert_risk_metrics_daily_matches_latest` compares it with the
    latest version on the last day of each stock. The ranking uses no
    future data.
  - The screen history unit test is a matched pair, one for each branch of
    the macro, each with its own `rank_metric` override. `dbt build` gives
    PASS=89 for both settings.
- **D23 (`612afe2`):** a random-selection null benchmark. SPY says whether
  the method beats the market; it does not say whether the rank order adds
  anything. The null keeps the same screen of the same date, the same
  sector cap, the same correlation gate and the same Max Sharpe weight
  search, and it replaces the rank order with a random permutation of the
  same candidates. `--null-draws N` and `--null-seed` run it, and it needs
  `--many-windows`. Each draw is a whole walk-forward run, at
  approximately 8.5 seconds for 85 windows.
  - **The measurement is not finished.** A smoke test of 5 draws put the
    real method above every draw on the return measures, and 5 draws
    cannot give a percentile. A run of 200 draws was in flight at the end
    of the session. Run it again and write the result into D23 and here:
    `python run_pipeline.py --universe sp500 --skip-dbt --no-log --many-windows --null-draws 200`
  - Read the percentile of `median_excess` and of `mean_sharpe`. A
    percentile near 0.5 means that the rank order of D22 does nothing, and
    that the gain comes from the screen or from the sector cap instead.

186 tests pass, up from 143 at the start of the day. `dbt build` for
`sp500` gives PASS=89 and the same 2 warnings. `verify_indicators.py`
passed every check at the end of D21, **and it has not run since D22.**
Run it before you trust the D22 numbers further. The live `sp500` run at
the new default gives 110 candidates, an in-sample Sharpe ratio of 4.51,
10 stocks over 4 sectors (Energy 3, Health Care 3, Information Technology
3, Materials 1), and a $10,000 plan that spends $9,952.53 with no
warning.

## Next steps

1. **Finish the null benchmark of D23.** The code and the tests are in.
   Only the 200-draw run is missing, and it takes approximately 30
   minutes:
   `python run_pipeline.py --universe sp500 --skip-dbt --no-log --many-windows --null-draws 200`.
   Write the percentiles into D23 and into the session state above. This
   is the measurement that the user asked for, and it answers the question
   that SPY cannot: does the rank order of D22 do any work, or would any
   10 stocks of the screened pool have done as well? A percentile near 0.5
   is the honest answer that the method has no skill in the selection.
2. **Measure the portfolio size again, under the new ranking.** D20
   measured 10, 12, 24, 40 and 60 stocks with the Sharpe ranking, and 40
   stocks reached a mean Sharpe ratio of 0.82 against 0.80 for SPY. D22
   changed the ranking and nobody repeated that sweep. The Sharpe gap of
   the current default may close at a larger size. The run is one loop
   over `--target-size`, and the share-rounding limit of D21 still applies
   to the plan.
3. **Give the backtest the same whole-share rounding as the plan.** The
   backtest holds exact weights, so it measures a portfolio that the money
   cannot always buy, and the error grows with the portfolio size. The
   user selected 10 stocks because a 40-stock plan needs $916,335, so that
   trade rests on a measure that does not model the plan at all. After
   this change, the measure and the plan agree.
4. **Separate the momentum premium from the skill of the pipeline.** A
   ranking on the trailing compound return is the classic momentum signal,
   so the gain of D22 can be a known factor premium. The test is a factor
   regression of the portfolio returns, or a comparison with a plain
   momentum portfolio of the same universe. `07_factor_decomposition.R` in
   the repository root does this kind of work for the R modules, and
   `quant_pipeline` has no equivalent.
5. **Add an equal-weight benchmark of the eligible pool.** This is the
   third null, beside SPY and the random order of D23. It tests the four
   gates themselves: a portfolio of 10 random stocks of the whole index,
   with no screen. If the screen adds nothing over that, the gates are
   decoration.
6. **Fix the sector leak.** `read_sector_map` gives every stock its newest
   GICS sector on every past date, so `max_per_sector` uses future
   information. This is a real look-ahead leak, it is not covered by the
   tamper test or by the truncation check, and nobody has measured it. The
   repair needs a point-in-time sector table, which the current source
   does not have.
7. **Ask the user about `max_per_sector`.** D21 left it at 3. With 10
   stocks and the new ranking the live portfolio reaches only 4 sectors,
   so the question matters more than it did: a cap of 2 would force at
   least 5.
8. **Measure a liquidity floor for the Nasdaq universe.** D14 left this
   option open. The screen already has a volume gate of 100,000 shares, so
   the effect can be small. D20 makes it less urgent: `sp500` measured
   better than `both` at every portfolio size.
9. **Find a second price source** for a delisted company. This is the only
   repair of the survivorship bias. The nasdaq API cannot do it.
10. **The web app.** The user asked for an interactive web app of this
    pipeline. Three plans are open, and the user has not selected one: a
    read-only batch site, a live parameter workbench, and a browser-only
    teaching tool with toggles that turn each removed bias back on. Note
    that `webapp/` in this repository is an early FastAPI scaffold that
    reads CSV exports from the R modules, not from `quant_pipeline`. The
    caps of D20 and the rank metric of D22 are command line flags now,
    which is the shape that a parameter workbench needs.
