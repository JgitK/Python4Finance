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

from quant import (allocate, backtest, pipeline, results_log, universe,
                   warehouse)

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


def dbt_command(universe: str) -> list[str]:
    """Return the dbt command that builds the models for a universe."""
    return ["dbt", "build", "--profiles-dir", ".",
            "--vars", json.dumps({"universe": universe})]


def build_dbt(universe: str) -> None:
    """Build the dbt models with DuckDB."""
    print(f"Step 1: build the dbt models for the {universe} universe ...")
    subprocess.run(dbt_command(universe), cwd=DBT_DIR, check=True)


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


def main() -> None:
    """Run the pipeline and write the results."""
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
    args = parser.parse_args()

    if not args.skip_dbt:
        build_dbt(args.universe)

    OUTPUT_DIR.mkdir(exist_ok=True)
    params = pipeline.PortfolioParams(n_portfolios=args.n_portfolios)

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
    print(f"Step 3: selected {len(selected)} stocks. "
          f"Sharpe {result['sharpe']:.2f}, "
          f"return {result['annual_return']:.1%}, "
          f"volatility {result['annual_volatility']:.1%}.")

    # Step 4: change the weights to whole shares.
    selected_prices = {ticker: prices[ticker] for ticker in selected}
    plan = allocate.allocation_summary(weights, selected_prices, args.investment)

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

    # Step 6: write the results.
    weights_df = pd.DataFrame(
        {"ticker": list(weights), "weight": list(weights.values())}
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
