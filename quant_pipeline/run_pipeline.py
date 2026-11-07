"""Run the whole pipeline end to end.

The steps are:
  1. Build the dbt models. This cleans the data and makes the marts.
  2. Read the screened candidates and the returns from the warehouse.
  3. Select a diversified set of stocks and find the Max Sharpe weights.
  4. Change the weights to whole shares for a fixed budget.
  5. Backtest the method with a walk-forward test against SPY. On each
     past date, the backtest uses only the screen of that date. Use
     --many-windows for a test on every valid date, not only three.
  6. Write the results to the output folder.
  7. Add one row to docs/results_log.md. Use --no-log to skip this step.

Run this file from the quant_pipeline folder. Use --skip-dbt to reuse the
warehouse from an earlier run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import pandas as pd
import yaml

from quant import (allocate, backtest, null_benchmark, pipeline,
                   results_log, universe, warehouse)

HERE = Path(__file__).resolve().parent
DBT_DIR = HERE / "dbt"
OUTPUT_DIR = HERE / "output"

# The backtest holds each portfolio for 180 trading days, approximately 8.5 months.
HOLDING_PERIOD = 180
# The warm-up of the risk metrics and the Ichimoku lines, in trading days.
# No stock passes the screen before this day.
WARM_UP = 261
# The step between the selection dates of a many-window run, in trading days.
DEFAULT_WINDOW_STEP = 5


def dbt_command(universe: str, top_n_per_sector: int | None = None,
                rank_metric: str | None = None) -> list[str]:
    """Return the dbt command that builds the models for a universe.

    A value for `top_n_per_sector` or for `rank_metric` goes into the dbt
    vars. Without a value, dbt reads that setting from dbt_project.yml.
    """
    variables: dict[str, object] = {"universe": universe}
    if top_n_per_sector is not None:
        variables["top_n_per_sector"] = top_n_per_sector
    if rank_metric is not None:
        variables["rank_metric"] = rank_metric
    return ["dbt", "build", "--profiles-dir", ".",
            "--vars", json.dumps(variables)]


def build_dbt(universe: str, top_n_per_sector: int | None = None,
              rank_metric: str | None = None) -> None:
    """Build the dbt models with DuckDB."""
    print(f"Step 1: build the dbt models for the {universe} universe ...")
    command = dbt_command(universe, top_n_per_sector, rank_metric)
    if top_n_per_sector is not None:
        # The unit test compares the two screens, and it fails when the
        # cap of the command is not the cap of the project file.
        command += ["--exclude", "assert_screen_history_matches_candidates"]
    subprocess.run(command, cwd=DBT_DIR, check=True)


def project_default_top_n() -> int:
    """Return the sector cap of dbt_project.yml.

    A run without `--top-n-per-sector` uses this value. The results log
    states it, so a reader can repeat the run.
    """
    text = (DBT_DIR / "dbt_project.yml").read_text()
    return int(yaml.safe_load(text)["vars"]["top_n_per_sector"])


def choose_selection_dates(index: pd.DatetimeIndex,
                           first_screen_date: pd.Timestamp | None = None
                           ) -> list[pd.Timestamp]:
    """Select three past dates. Each date must have a full holding window after it.

    A date must also have a screen. The screen history starts after the
    warm-up of the risk metrics and the Ichimoku lines. On an earlier date,
    no stock passes the screen, so the backtest holds nothing and reports a
    0% return. Such a window is not a result, so this function drops it.
    """
    last = len(index) - 1
    offsets = [HOLDING_PERIOD + 1, HOLDING_PERIOD + 127, HOLDING_PERIOD + 253]
    positions = [last - offset for offset in offsets]
    dates = [index[pos] for pos in positions if pos >= WARM_UP]
    if first_screen_date is not None:
        dates = [d for d in dates if d >= first_screen_date]
    return dates


def choose_many_selection_dates(index: pd.DatetimeIndex,
                                step: int = DEFAULT_WINDOW_STEP,
                                first_screen_date: pd.Timestamp | None = None
                                ) -> list[pd.Timestamp]:
    """Select every past date that has a full holding window after it.

    Three overlapping windows cannot show that a result is not luck. A run
    with many windows gives a much better measure. The step between the
    dates controls the count of the windows.

    The dates start after the warm-up of the risk metrics and the Ichimoku
    lines, and they stop one holding period before the end of the data. A
    date must also have a screen, for the reason in
    `choose_selection_dates`.

    The windows overlap, so they are not independent. The valid dates of
    the current data cover approximately two independent holding periods.
    Read the share of the windows that beat the benchmark as a measure of
    the method, not as proof.
    """
    last_usable = len(index) - 1 - HOLDING_PERIOD
    dates = [index[position]
             for position in range(WARM_UP, last_usable + 1, step)]
    if first_screen_date is not None:
        dates = [date for date in dates if date >= first_screen_date]
    return dates


def load_backtest_inputs(con) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the inputs of the backtest.

    Return the returns of every stock and the benchmark, and the screen
    history. Do not start from the stocks that pass the screen today.
    Today's screen uses data from the holding periods of the backtest.
    On each selection date, the backtest uses the screen of that date.
    """
    returns = warehouse.read_returns_matrix(con)
    history = warehouse.read_screen_history(con)
    return returns, history


def coverage_report(con, dates: list[pd.Timestamp]) -> pd.DataFrame:
    """Count the index members that the pipeline drops on each date.

    A member is dropped when the price source has no data for it, or when
    it has no sector. Such a stock cannot pass the screen. The backtest
    cannot hold it, so this count shows the survivorship bias that remains.
    """
    coverage = warehouse.read_universe_coverage(con)
    return pipeline.coverage_summary(coverage, dates)


def build_live_portfolio(con, params: pipeline.PortfolioParams
                         ) -> dict:
    """Build the portfolio for today from the stocks that pass the screen."""
    candidates = warehouse.read_candidates(con)
    returns = warehouse.read_returns_matrix(con, candidates["ticker"].tolist())
    window = pipeline.lookback_window(returns, params)
    return pipeline.build_max_sharpe_portfolio(
        window, warehouse.read_sector_map(con), params)


def make_parser() -> argparse.ArgumentParser:
    """Return the command line parser of the pipeline."""
    default = pipeline.PortfolioParams()
    parser = argparse.ArgumentParser(description="Run the quant pipeline.")
    parser.add_argument("--investment", type=float, default=10000.0,
                        help="The amount of money to invest.")
    parser.add_argument("--n-portfolios", type=int, default=10000,
                        help="The number of random portfolios to try.")
    parser.add_argument("--skip-dbt", action="store_true",
                        help="Do not build dbt. Use the warehouse from the last run.")
    parser.add_argument("--universe", default="sp500",
                        choices=["sp500", "nasdaq", "both"],
                        help="The universe of stocks. The default is sp500.")
    parser.add_argument("--no-log", action="store_true",
                        help="Do not add a row to docs/results_log.md.")
    parser.add_argument("--many-windows", action="store_true",
                        help="Also run the backtest on every valid date. "
                             "The row then holds the share of the windows "
                             "that beat the benchmark.")
    parser.add_argument("--window-step", type=int, default=DEFAULT_WINDOW_STEP,
                        help="The step between the dates of a many-window "
                             "run, in trading days. The default is 5.")
    # The three caps of the exposure. See decision D20.
    parser.add_argument("--top-n-per-sector", type=int, default=None,
                        help="The count of candidates that each sector "
                             "keeps in the screen. Without this flag, dbt "
                             "reads the value of dbt_project.yml.")
    parser.add_argument("--target-size", type=int, default=default.target_size,
                        help="The count of stocks in the portfolio. "
                             f"The default is {default.target_size}.")
    parser.add_argument("--max-per-sector", type=int,
                        default=default.max_per_sector,
                        help="The count of portfolio stocks that one sector "
                             f"can hold. The default is "
                             f"{default.max_per_sector}.")
    # The measure that ranks the candidates inside each sector. The flag
    # reaches dbt and Python, so the screen and the selection agree.
    parser.add_argument("--rank-metric", default=default.rank_metric,
                        choices=["cum_return", "sharpe"],
                        help="The measure that ranks the candidates inside "
                             "each sector. The default is "
                             f"{default.rank_metric}.")
    # The null benchmark. See decision D23.
    parser.add_argument("--null-draws", type=int, default=0,
                        help="Run the random-selection null benchmark with "
                             "this many draws. Each draw repeats the whole "
                             "walk-forward test with the same candidates in "
                             "a random order. 0 skips it.")
    parser.add_argument("--null-seed", type=int, default=0,
                        help="The seed of the null benchmark draws.")
    return parser


def params_from_args(args: argparse.Namespace) -> pipeline.PortfolioParams:
    """Return the portfolio settings of a command line."""
    return pipeline.PortfolioParams(n_portfolios=args.n_portfolios,
                                    target_size=args.target_size,
                                    max_per_sector=args.max_per_sector,
                                    rank_metric=args.rank_metric)


def caps_label(args: argparse.Namespace) -> str:
    """Return the three caps of the exposure as one cell of the log.

    The order is top_n_per_sector/target_size/max_per_sector.
    """
    top_n = (args.top_n_per_sector if args.top_n_per_sector is not None
             else project_default_top_n())
    return f"{top_n}/{args.target_size}/{args.max_per_sector}"


def main() -> None:
    """Run the pipeline and write the results."""
    args = make_parser().parse_args()

    if not args.skip_dbt:
        build_dbt(args.universe, args.top_n_per_sector, args.rank_metric)

    OUTPUT_DIR.mkdir(exist_ok=True)
    params = params_from_args(args)
    print(f"Caps: {caps_label(args)} "
          "(candidates per sector / portfolio size / portfolio per sector). "
          f"Rank: {args.rank_metric}.")

    con = warehouse.connect()
    candidates = warehouse.read_candidates(con)
    sector_of = warehouse.read_sector_map(con)
    prices = warehouse.read_latest_prices(con)
    universe_name = warehouse.read_universe(con)
    backtest_returns, screen_history = load_backtest_inputs(con)
    print(f"Step 2: read {len(candidates)} candidates and "
          f"{len(backtest_returns)} days of returns.")

    # Step 3: build the portfolio from the most recent year.
    result = build_live_portfolio(con, params)
    selection_dates = choose_selection_dates(
        backtest_returns.index,
        first_screen_date=pd.Timestamp(screen_history["as_of_date"].min()))
    coverage = coverage_report(
        con, selection_dates + [backtest_returns.index[-1]])
    con.close()
    weights = result["weights"]
    selected = result["selected"]
    mix = pipeline.sector_mix(selected, sector_of)
    print(f"Step 3: selected {len(selected)} stocks. "
          f"Sharpe {result['sharpe']:.2f}, "
          f"return {result['annual_return']:.1%}, "
          f"volatility {result['annual_volatility']:.1%}.")
    print("        sector mix: "
          + ", ".join(f"{sector} {count}" for sector, count in mix.items()))

    # Step 4: change the weights to whole shares. The top-up pass spends
    # the cash that the rounding leaves.
    selected_prices = {ticker: prices[ticker] for ticker in selected}
    plan = allocate.allocation_summary(weights, selected_prices,
                                       args.investment)
    spent = float(plan["cost"].sum())
    drift = float((plan["cost"] / args.investment
                   - plan["target_weight"]).abs().max())
    print(f"Step 4: spent {spent:,.2f} of {args.investment:,.2f}, "
          f"so the cash is {args.investment - spent:,.2f}. "
          f"The largest weight difference is {drift:.2%}.")
    # A plan of whole shares cannot always hold the weights. Say so.
    warnings = allocate.plan_warnings(
        dict(zip(plan["ticker"], plan["shares"])), weights, selected_prices,
        args.investment)
    for warning in warnings:
        print(f"        WARNING: {warning}")

    # Step 5: backtest the method. On each selection date, the builder uses
    # only the stocks that passed the screen on that date.
    build = pipeline.make_builder(sector_of, params, universe.BENCHMARK,
                                  screen_history=screen_history)
    windows = backtest.run_walk_forward(
        backtest_returns, selection_dates, HOLDING_PERIOD, build,
        universe.BENCHMARK, params.risk_free, params.trading_days,
    )
    backtest_rows = [
        {
            "selection_date": w["selection_date"].date(),
            "portfolio_return": w["portfolio"]["total_return"],
            "portfolio_sharpe": w["portfolio"]["sharpe"],
            "benchmark_return": w["benchmark"]["total_return"],
            "benchmark_sharpe": w["benchmark"]["sharpe"],
            "sharpe_diff": w["sharpe_diff"],
        }
        for w in windows
    ]
    backtest_df = pd.DataFrame(backtest_rows)
    print(f"Step 5: ran {len(backtest_df)} walk-forward windows against "
          f"{universe.BENCHMARK}.")

    # Step 5b: the same test on every valid date. Three windows overlap,
    # so they cannot show that a result is not luck.
    summary = None
    if args.many_windows:
        many_dates = choose_many_selection_dates(
            backtest_returns.index, args.window_step,
            first_screen_date=pd.Timestamp(screen_history["as_of_date"].min()))
        summary = backtest.summarize_windows(backtest.run_walk_forward(
            backtest_returns, many_dates, HOLDING_PERIOD, build,
            universe.BENCHMARK, params.risk_free, params.trading_days))
        print(f"Step 5b: ran {summary['n_windows']} windows with a step of "
              f"{args.window_step} days. "
              f"{summary['n_scored']} hold a result.")
        print(f"         beat {universe.BENCHMARK} on the return in "
              f"{summary['win_return']:.1%} of them, and on the Sharpe "
              f"ratio in {summary['win_sharpe']:.1%}.")
        print(f"         mean excess return {summary['mean_excess']:+.2%}, "
              f"median {summary['median_excess']:+.2%}. "
              f"Mean Sharpe {summary['mean_sharpe']:.2f} against "
              f"{summary['mean_benchmark_sharpe']:.2f}.")

    # Step 5c: the null benchmark. SPY says whether the method beats the
    # market. It does not say whether the rank order adds anything. The
    # null keeps every other step and randomizes only the order.
    null_draws = None
    if args.null_draws and summary is not None:
        print(f"Step 5c: run {args.null_draws} random-order draws of the "
              "same walk-forward test ...")
        null_draws = null_benchmark.run_random_selection(
            backtest_returns, many_dates, HOLDING_PERIOD, sector_of, params,
            universe.BENCHMARK, screen_history=screen_history,
            n_draws=args.null_draws, seed=args.null_seed)
        comparison = null_benchmark.compare_with_null(summary, null_draws)
        print("         the real method against the random order:")
        print(comparison.to_string(index=False))
        print("         A percentile near 0.5 means that the rank order "
              "does nothing.")
    elif args.null_draws:
        print("Step 5c: the null benchmark needs --many-windows. Skipped.")

    # Step 6: write the results.
    weights_df = pd.DataFrame(
        {"ticker": list(weights),
         "sector": [sector_of.get(t, "Unknown") for t in weights],
         "weight": list(weights.values())}
    ).sort_values("weight", ascending=False)
    frontier = result["frontier"][
        ["annual_return", "annual_volatility", "sharpe"]
    ]

    weights_df.to_csv(OUTPUT_DIR / "optimal_weights.csv", index=False)
    plan.to_csv(OUTPUT_DIR / "allocation.csv", index=False)
    frontier.to_csv(OUTPUT_DIR / "efficient_frontier.csv", index=False)
    backtest_df.to_csv(OUTPUT_DIR / "backtest_results.csv", index=False)
    candidates.to_csv(OUTPUT_DIR / "screen_candidates.csv", index=False)
    coverage.to_csv(OUTPUT_DIR / "universe_coverage.csv", index=False)
    if null_draws is not None:
        null_draws.to_csv(OUTPUT_DIR / "null_benchmark.csv", index=False)
        comparison.to_csv(OUTPUT_DIR / "null_comparison.csv", index=False)

    print(f"Step 6: wrote the results to {OUTPUT_DIR}.")
    print("\nPortfolio weights:")
    print(weights_df.to_string(index=False))
    print("\nWalk-forward backtest:")
    print(backtest_df.to_string(index=False))
    # Step 7: add one row to the results log.
    if not args.no_log:
        row = results_log.format_row(
            run_date=dt.date.today().isoformat(),
            revision=results_log.git_revision(HERE), universe=universe_name,
            caps=caps_label(args), rank_metric=args.rank_metric,
            n_candidates=len(candidates), live_sharpe=result["sharpe"],
            backtest=backtest_df, summary=summary)
        added = results_log.append_row(results_log.LOG_FILE, row)
        print("Step 7: " + ("added a row to" if added else
                            "no new results for") + " docs/results_log.md.")

    print(f"\nUniverse members dropped for missing data ({universe_name}, "
          "survivorship bias):")
    print(coverage[["date", "members", "usable", "dropped",
                    "dropped_tickers"]].to_string(index=False))


if __name__ == "__main__":
    main()
