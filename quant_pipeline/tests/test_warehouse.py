"""Integration tests for the warehouse reader.

These tests read the real DuckDB warehouse. They need the dbt build to have
run first. They skip themselves when the warehouse file is missing.
"""

from __future__ import annotations

import pytest

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


def test_candidates_have_rows_and_pass_the_min_score(con):
    candidates = warehouse.read_candidates(con)
    assert len(candidates) > 0
    # Every candidate must meet the minimum Ichimoku score of 2.
    assert candidates["ichimoku_score"].min() >= 2


def test_returns_matrix_includes_the_benchmark(con):
    matrix = warehouse.read_returns_matrix(con)
    assert universe.BENCHMARK in matrix.columns
    # The matrix should hold a few years of trading days.
    assert len(matrix) > 500


def test_latest_prices_are_positive(con):
    prices = warehouse.read_latest_prices(con)
    assert len(prices) > 0
    assert all(price > 0 for price in prices.values())
