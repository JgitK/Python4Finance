"""Run the whole pipeline end to end.

The steps are:
  1. Build the dbt models. This cleans the data and makes the marts.
  2. Read the screened candidates and the returns from the warehouse.
  3. Select a diversified set of stocks and find the Max Sharpe weights.
  4. Change the weights to whole shares for a fixed budget.
  5. Backtest the method with a walk-forward test against SPY. On each
     past date, the backtest uses only the screen of that date.
  6. Write the results to the output folder.

Run this file from the quant_pipeline folder. Use --skip-dbt to reuse the
warehouse from an earlier run.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pandas as pd

from quant import allocate, backtest, pipeline, universe, warehouse

HERE = Path(__file__).resolve().parent
DBT_DIR = HERE / "dbt"
OUTPUT_DIR = HERE / "output"

# The backtest holds each portfolio for 180 trading days, approximately 8.5 months.
HOLDING_PERIOD = 180


def build_dbt() -> None:
    """Build the dbt models with DuckDB."""
    print("Step 1: build the dbt models ...")
    subprocess.run(
        ["dbt", "build", "--profiles-dir", "."],
        cwd=DBT_DIR, check=True,
    )


def choose_selection_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Select three past dates. Each date must have a full holding window after it."""
    last = len(index) - 1
    offsets = [HOLDING_PERIOD + 1, HOLDING_PERIOD + 127, HOLDING_PERIOD + 253]
    positions = [last - offset for offset in offsets]
    return [index[pos] for pos in positions if pos > 260]


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


def main() -> None:
    """Run the pipeline and write the results."""
    parser = argparse.ArgumentParser(description="Run the quant pipeline.")
    parser.add_argument("--investment", type=float, default=10000.0,
                        help="The amount of money to invest.")
    parser.add_argument("--n-portfolios", type=int, default=10000,
                        help="The number of random portfolios to try.")
    parser.add_argument("--skip-dbt", action="store_true",
                        help="Do not build dbt. Use the warehouse from the last run.")
    args = parser.parse_args()

    if not args.skip_dbt:
        build_dbt()

    OUTPUT_DIR.mkdir(exist_ok=True)
    params = pipeline.PortfolioParams(n_portfolios=args.n_portfolios)

    con = warehouse.connect()
    candidates = warehouse.read_candidates(con)
    sector_of = warehouse.read_sector_map(con)
    prices = warehouse.read_latest_prices(con)
    candidate_tickers = candidates["ticker"].tolist()
    returns = warehouse.read_returns_matrix(
        con, candidate_tickers + [universe.BENCHMARK]
    )
    backtest_returns, screen_history = load_backtest_inputs(con)
    con.close()

    print(f"Step 2: read {len(candidate_tickers)} candidates and "
          f"{len(returns)} days of returns.")

    # Step 3: build the portfolio from the most recent year.
    tradeable = returns.drop(columns=[universe.BENCHMARK])
    recent = tradeable.tail(params.trading_days).dropna(axis=1)
    result = pipeline.build_max_sharpe_portfolio(recent, sector_of, params)
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
    selection_dates = choose_selection_dates(backtest_returns.index)
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

    print(f"Step 6: wrote the results to {OUTPUT_DIR}.")
    print("\nPortfolio weights:")
    print(weights_df.to_string(index=False))
    print("\nWalk-forward backtest:")
    print(backtest_df.to_string(index=False))


if __name__ == "__main__":
    main()
