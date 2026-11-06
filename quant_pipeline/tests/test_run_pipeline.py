"""Tests for the backtest inputs in run_pipeline.

The backtest must not start from the stocks that pass the screen today.
Today's screen uses data from the holding periods of the backtest.
These tests read the real DuckDB warehouse. Run the dbt build before
these tests. The tests skip when the warehouse file is not there.
"""

from __future__ import annotations

import pytest

import run_pipeline
from quant import universe, warehouse

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
    assert set(returns.columns) == every_stock | {universe.BENCHMARK}


def test_backtest_inputs_include_stocks_that_fail_the_screen_today(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    today = set(warehouse.read_candidates(con)["ticker"])
    # Some stocks fail the screen today. They can still pass on a past date.
    assert set(returns.columns) - today - {universe.BENCHMARK}


def test_backtest_inputs_include_the_screen_history(con):
    _, history = run_pipeline.load_backtest_inputs(con)
    assert len(history) > 0
