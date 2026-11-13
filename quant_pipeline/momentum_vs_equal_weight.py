"""Measure how much of the gain over equal weight is momentum (D36).

The script runs four arms of the pool mode on the same walk-forward
dates: equal weight, max_sharpe, and the robust objective with and
without the standard-error rho. It makes one overlapping daily series for
each arm (`quant.overlap`). It then regresses each arm, and each arm minus
equal weight, on the market and on UMD.

Run this file from the quant_pipeline folder after a dbt build:

    . .venv/bin/activate
    python momentum_vs_equal_weight.py --window-step 5

The script writes output/momentum_vs_equal_weight.csv.
"""

from __future__ import annotations

import argparse

import pandas as pd

import run_pipeline
from quant import backtest, factors, overlap, pipeline, universe, warehouse

ARMS = {
    "ew": {"objective": "equal_weight"},
    "max_sharpe": {"objective": "max_sharpe"},
    "rob_none": {"objective": "robust", "rho_rule": "none", "varrho": 0.0},
    "rob_stderr": {"objective": "robust", "rho_rule": "stderr",
                   "varrho": 0.02},
}
BASELINE = "ew"


def make_parser() -> argparse.ArgumentParser:
    """Return the command line parser of the script."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window-step", type=int,
                        default=run_pipeline.DEFAULT_WINDOW_STEP,
                        help="The days between two selection dates.")
    parser.add_argument("--pool-size", type=int, default=33,
                        help="The count of stocks in the pool.")
    parser.add_argument("--lags", type=int, default=20,
                        help="The lags of the Newey-West errors.")
    return parser


def main() -> None:
    args = make_parser().parse_args()
    con = warehouse.connect()
    sector_of = warehouse.read_sector_map(con)
    returns, history = run_pipeline.load_backtest_inputs(con)
    members = warehouse.read_universe_coverage(con)
    con.close()
    dates = run_pipeline.choose_many_selection_dates(
        returns.index, args.window_step,
        first_screen_date=pd.Timestamp(history["as_of_date"].min()))

    series = {}
    for name, settings in ARMS.items():
        params = pipeline.PortfolioParams(optimizer="exact",
                                          size_mode="pool",
                                          pool_size=args.pool_size,
                                          **settings)
        build = pipeline.make_builder(sector_of, params, universe.BENCHMARK,
                                      screen_history=history)
        windows = backtest.run_walk_forward(
            returns, dates, run_pipeline.HOLDING_PERIOD, build,
            universe.BENCHMARK, params.risk_free, params.trading_days)
        frame = overlap.overlapping_returns(returns, windows,
                                            run_pipeline.HOLDING_PERIOD)
        series[name] = frame["return"]
        print(f"{name}: {len(frame)} days, mean depth "
              f"{frame['depth'].mean():.1f} windows")

    momentum = factors.momentum_sources(returns, members, universe.BENCHMARK)
    table = overlap.difference_table(
        series, BASELINE, returns[universe.BENCHMARK],
        {"french": momentum["french"], "in_house": momentum["in_house"]},
        lags=args.lags)
    path = run_pipeline.OUTPUT_DIR / "momentum_vs_equal_weight.csv"
    run_pipeline.OUTPUT_DIR.mkdir(exist_ok=True)
    table.to_csv(path, index=False)
    with pd.option_context("display.width", 140,
                           "display.float_format", "{:+.4f}".format):
        print(table.to_string(index=False))
    print(f"Wrote {path}.")


if __name__ == "__main__":
    main()
