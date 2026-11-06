"""Tests for the backtest inputs in run_pipeline.

The backtest must not start from the stocks that pass the screen today.
Today's screen uses data from the holding periods of the backtest.
These tests read the real DuckDB warehouse. Run the dbt build before
these tests. The tests skip when the warehouse file is not there.
"""

from __future__ import annotations

import pytest

import run_pipeline
from quant import pipeline, universe, warehouse

pytestmark = pytest.mark.skipif(
    not warehouse.DEFAULT_WAREHOUSE.exists(),
    reason="Run 'dbt build' first to create the warehouse.",
)


@pytest.fixture(scope="module")
def con():
    connection = warehouse.connect()
    yield connection
    connection.close()


def test_backtest_inputs_hold_every_stock_and_the_benchmark(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    every_stock = set(warehouse.read_sector_map(con))
    # A stock with prices but no sector can be in the frame too.
    assert every_stock | {universe.BENCHMARK} <= set(returns.columns)


def test_backtest_inputs_include_stocks_that_fail_the_screen_today(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    today = set(warehouse.read_candidates(con)["ticker"])
    # Some stocks fail the screen today. They can still pass on a past date.
    assert set(returns.columns) - today - {universe.BENCHMARK}


def test_backtest_inputs_include_the_screen_history(con):
    _, history = run_pipeline.load_backtest_inputs(con)
    assert len(history) > 0


def test_backtest_builder_on_the_last_date_equals_the_live_portfolio(con):
    # On the last date, the backtest and the live run have the same data.
    # Because of this, they must give the same weights. A different lookback
    # window or a different stock list makes the weights different.
    params = pipeline.PortfolioParams(n_portfolios=300, seed=7)
    live = run_pipeline.build_live_portfolio(con, params)

    returns, history = run_pipeline.load_backtest_inputs(con)
    build = pipeline.make_builder(warehouse.read_sector_map(con), params,
                                  universe.BENCHMARK, screen_history=history)
    assert build(returns) == pytest.approx(live["weights"])


def test_coverage_report_has_one_row_for_each_date(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    dates = run_pipeline.choose_selection_dates(returns.index) + [returns.index[-1]]
    report = run_pipeline.coverage_report(con, dates)
    assert len(report) == len(dates)
    assert (report["members"] >= report["usable"]).all()
    if warehouse.read_universe(con) == "sp500":
        # The S&P 500 has about 500 members on each date.
        assert report["members"].between(490, 510).all()


def test_dbt_command_passes_the_universe():
    command = run_pipeline.dbt_command("nasdaq")
    assert command[:2] == ["dbt", "build"]
    assert "--vars" in command
    assert command[command.index("--vars") + 1] == '{"universe": "nasdaq"}'


def test_the_default_universe_in_the_dbt_project_is_sp500():
    # A dbt unit test cannot prove this. A --vars flag on the command line
    # replaces the project value, so each unit test pins its own universe.
    # This test reads the project file, which no flag changes.
    import yaml

    project = yaml.safe_load((run_pipeline.DBT_DIR / "dbt_project.yml").read_text())
    assert project["vars"]["universe"] == "sp500"


def test_choose_selection_dates_skips_dates_before_the_screen_history(con):
    # The screen history starts after the warm-up of the risk metrics and
    # the Ichimoku lines. On a date before that, no stock passes the screen,
    # so the backtest holds nothing and reports a 0% return. Such a window
    # is not a result. The function must not return such a date.
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    every_date = run_pipeline.choose_selection_dates(index)
    assert len(every_date) == 3

    # A cut-off on the newest date must drop the two older dates.
    newest = max(every_date)
    kept = run_pipeline.choose_selection_dates(index, first_screen_date=newest)
    assert kept == [newest]

    # The real screen history must keep all three dates of the live run.
    _, history = run_pipeline.load_backtest_inputs(con)
    first = pd.Timestamp(history["as_of_date"].min())
    returns, _ = run_pipeline.load_backtest_inputs(con)
    real = run_pipeline.choose_selection_dates(returns.index,
                                               first_screen_date=first)
    assert len(real) == 3
    assert min(real) >= first
