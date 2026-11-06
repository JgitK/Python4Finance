"""Integration tests for the warehouse reader.

These tests read the real DuckDB warehouse. Run the dbt build before
these tests. The tests skip when the warehouse file is not there.
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
    # The matrix must hold a few years of trading days.
    assert len(matrix) > 500


def test_latest_prices_are_positive(con):
    prices = warehouse.read_latest_prices(con)
    assert len(prices) > 0
    assert all(price > 0 for price in prices.values())


def test_screen_history_on_the_latest_date_equals_the_candidates(con):
    history = warehouse.read_screen_history(con)
    latest = history[history["as_of_date"] == history["as_of_date"].max()]
    candidates = warehouse.read_candidates(con)
    assert set(latest["ticker"]) == set(candidates["ticker"])


def test_screen_history_covers_many_past_dates(con):
    history = warehouse.read_screen_history(con)
    # The backtest needs a screen on each past selection date.
    assert history["as_of_date"].nunique() > 250
    assert list(history.columns) == ["as_of_date", "ticker"]


# --- large moves -------------------------------------------------------------
# A real large move stays in the data. A corporate action is back-adjusted,
# so it does not drop the stock out of the lookback window.

def _return_on(con, ticker: str, date: str):
    row = con.execute(
        "select daily_return from main.int_daily_returns "
        "where ticker = ? and price_date = ?", [ticker, date]).fetchone()
    return None if row is None else row[0]


def test_a_real_crash_stays_in_the_returns(con):
    # GL fell 53% on 2024-04-11 on heavy volume. That loss is real.
    assert _return_on(con, "GL", "2024-04-11") == pytest.approx(-0.531, abs=1e-3)


def test_a_corporate_action_day_has_its_real_return(con):
    # HON gapped down 48% at the open on 2026-06-29 because of a separation.
    # After the back-adjustment, the day shows only the move during the day.
    value = _return_on(con, "HON", "2026-06-29")
    assert value is not None
    assert -0.10 < value < 0.0


def test_a_corporate_action_does_not_drop_the_stock_from_the_window(con):
    from quant import pipeline

    window = pipeline.lookback_window(warehouse.read_returns_matrix(con),
                                      pipeline.PortfolioParams())
    assert "HON" in window.columns


def test_the_warehouse_reports_its_universe(con):
    assert warehouse.read_universe(con) in {"sp500", "nasdaq", "both"}
