"""Tests for the walk-forward backtest.

The backtest must never use future data to pick a portfolio.
These tests check the date split, the window math, and that guarantee.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant import backtest


def _returns(days: int = 10) -> pd.DataFrame:
    """Build a small two-stock return frame with business-day dates."""
    dates = pd.bdate_range("2023-01-02", periods=days)
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {"AAA": rng.normal(0.001, 0.01, days),
         "BBB": rng.normal(0.001, 0.01, days)},
        index=dates,
    )


# --- split_by_date ---------------------------------------------------------

def test_split_by_date_puts_the_cut_day_in_the_past():
    returns = _returns(6)
    cut = returns.index[2]
    train, test = backtest.split_by_date(returns, cut)
    # The train set keeps the cut day. The test set starts after it.
    assert train.index.max() == cut
    assert test.index.min() > cut
    assert len(train) + len(test) == len(returns)


# --- portfolio_daily_returns ----------------------------------------------

def test_portfolio_daily_returns_is_the_weighted_sum():
    returns = pd.DataFrame({"AAA": [0.10, 0.20], "BBB": [0.30, 0.40]})
    series = backtest.portfolio_daily_returns(returns, {"AAA": 0.5, "BBB": 0.5})
    # Each day is the average of the two returns.
    assert list(series) == pytest.approx([0.20, 0.30])


# --- window_performance ----------------------------------------------------

def test_window_performance_total_return_compounds():
    daily = pd.Series([0.10, -0.10])
    perf = backtest.window_performance(daily, risk_free=0.0)
    # 1.10 * 0.90 - 1 = -0.01.
    assert perf["total_return"] == pytest.approx(-0.01)
    assert perf["n_days"] == 2


def test_window_performance_annualizes_return():
    # A total return of 100 percent over 252 days is 100 percent per year.
    daily = pd.Series([0.0] * 251 + [1.0])
    perf = backtest.window_performance(daily, risk_free=0.0, trading_days=252)
    # (1 + 1.0) ** (252 / 252) - 1 = 1.0.
    assert perf["annual_return"] == pytest.approx(1.0)


def test_window_performance_zero_volatility_for_constant_returns():
    daily = pd.Series([0.01, 0.01, 0.01, 0.01])
    perf = backtest.window_performance(daily, risk_free=0.0)
    assert perf["annual_volatility"] == pytest.approx(0.0)


# --- backtest_window: the no-look-ahead guarantee --------------------------

def test_backtest_window_shows_the_selector_only_past_data():
    returns = _returns(10)
    cut = returns.index[4]
    seen = {}

    def build_portfolio(train: pd.DataFrame) -> dict[str, float]:
        # Record the newest day that the selector can see.
        seen["max_train_date"] = train.index.max()
        return {"AAA": 1.0}

    backtest.backtest_window(
        returns, selection_date=cut, holding_period=3,
        build_portfolio=build_portfolio, benchmark="BBB",
    )
    # The selector must not see any day after the selection date.
    assert seen["max_train_date"] <= cut


def test_backtest_window_holds_for_the_requested_period():
    returns = _returns(12)
    cut = returns.index[4]

    result = backtest.backtest_window(
        returns, selection_date=cut, holding_period=3,
        build_portfolio=lambda train: {"AAA": 1.0}, benchmark="BBB",
    )
    # The holding window uses three days after the selection date.
    assert result["portfolio"]["n_days"] == 3
    assert result["benchmark"]["n_days"] == 3
    assert "sharpe_diff" in result


# ---------------------------------------------------------------------------
# The summary of many windows.


def _window(date: str, portfolio_return: float, portfolio_sharpe: float,
            benchmark_return: float, benchmark_sharpe: float,
            n_stocks: int = 12) -> dict:
    """Make one window result, in the shape that backtest_window returns."""
    weights = {f"S{i}": 1.0 / n_stocks for i in range(n_stocks)}
    return {
        "selection_date": pd.Timestamp(date),
        "weights": weights,
        "portfolio": {"total_return": portfolio_return,
                      "sharpe": portfolio_sharpe},
        "benchmark": {"total_return": benchmark_return,
                      "sharpe": benchmark_sharpe},
        "sharpe_diff": portfolio_sharpe - benchmark_sharpe,
    }


def test_summarize_windows_counts_the_wins_and_the_excess_return():
    windows = [
        _window("2025-01-02", 0.20, 1.50, 0.10, 1.00),   # win, win
        _window("2025-01-09", 0.05, 0.40, 0.10, 1.00),   # loss, loss
        _window("2025-01-16", 0.15, 0.80, 0.10, 1.00),   # win, loss
        _window("2025-01-23", -0.10, -0.50, 0.10, 1.00),  # loss, loss
    ]
    summary = backtest.summarize_windows(windows)
    assert summary["n_windows"] == 4
    assert summary["n_scored"] == 4
    assert summary["win_return"] == pytest.approx(0.5)
    assert summary["win_sharpe"] == pytest.approx(0.25)
    # The excess returns are +10%, -5%, +5% and -20%.
    assert summary["mean_excess"] == pytest.approx(-0.025)
    assert summary["median_excess"] == pytest.approx(0.0)
    assert summary["mean_sharpe"] == pytest.approx(0.55)
    assert summary["mean_benchmark_sharpe"] == pytest.approx(1.0)


def test_summarize_windows_does_not_score_a_window_with_no_stocks():
    # A selection date before the start of the screen history selects no
    # stock. The portfolio then holds nothing and reports a return of 0%.
    # A count of that window as a loss gives a wrong win rate. This is a
    # real bug of an earlier experiment, so the test holds the behaviour.
    empty = _window("2024-01-02", 0.0, float("nan"), 0.10, 1.00, n_stocks=0)
    windows = [empty, _window("2025-01-02", 0.20, 1.50, 0.10, 1.00)]
    summary = backtest.summarize_windows(windows)
    assert summary["n_windows"] == 2
    assert summary["n_scored"] == 1
    # The one scored window is a win on both measures.
    assert summary["win_return"] == pytest.approx(1.0)
    assert summary["win_sharpe"] == pytest.approx(1.0)
    assert summary["mean_excess"] == pytest.approx(0.10)


def test_summarize_windows_counts_a_window_with_no_sharpe_ratio():
    # A window can have a return but no Sharpe ratio, because one day is
    # not enough for a volatility. Such a window counts for the return,
    # and it does not count for the Sharpe ratio.
    windows = [
        _window("2025-01-02", 0.20, float("nan"), 0.10, 1.00),
        _window("2025-01-09", 0.20, 2.00, 0.10, 1.00),
    ]
    summary = backtest.summarize_windows(windows)
    assert summary["n_scored"] == 2
    assert summary["win_return"] == pytest.approx(1.0)
    assert summary["n_sharpe"] == 1
    assert summary["win_sharpe"] == pytest.approx(1.0)


def test_summarize_windows_with_no_windows_is_empty():
    summary = backtest.summarize_windows([])
    assert summary["n_windows"] == 0
    assert summary["n_scored"] == 0
    assert math.isnan(summary["win_return"])


# ---------------------------------------------------------------------------
# The realized CAPM measures of each window (D25).


def test_backtest_window_reports_the_realized_beta_and_alpha():
    # AAA is exactly 2 times the benchmark in excess return, so the
    # realized beta over the holding window is 2 and the alpha is 0.
    dates = pd.bdate_range("2023-01-02", periods=30)
    rng = np.random.default_rng(4)
    bench = pd.Series(rng.normal(0.0005, 0.01, 30), index=dates)
    rf_daily = 0.045 / 252
    returns = pd.DataFrame({"AAA": rf_daily + 2.0 * (bench - rf_daily),
                            "BBB": bench})
    result = backtest.backtest_window(
        returns, selection_date=dates[9], holding_period=15,
        build_portfolio=lambda train: {"AAA": 1.0}, benchmark="BBB")
    assert result["capm"]["beta"] == pytest.approx(2.0, abs=1e-10)
    assert result["capm"]["alpha"] == pytest.approx(0.0, abs=1e-10)
    assert result["capm"]["n_days"] == 15


def test_backtest_window_with_no_stocks_has_no_beta():
    returns = _returns(12)
    result = backtest.backtest_window(
        returns, selection_date=returns.index[4], holding_period=5,
        build_portfolio=lambda train: {}, benchmark="BBB")
    assert math.isnan(result["capm"]["beta"])


def test_summarize_windows_reports_the_mean_beta_and_alpha():
    windows = [
        _window("2025-01-02", 0.20, 1.50, 0.10, 1.00),
        _window("2025-01-09", 0.05, 0.40, 0.10, 1.00),
        _window("2025-01-16", 0.15, 0.80, 0.10, 1.00),
    ]
    for w, beta, alpha in zip(windows, [1.2, 1.4, 0.7], [0.10, -0.02, 0.04]):
        w["capm"] = {"beta": beta, "alpha": alpha}
    summary = backtest.summarize_windows(windows)
    assert summary["mean_beta"] == pytest.approx(1.1)
    assert summary["mean_alpha"] == pytest.approx(0.04)
    assert summary["median_alpha"] == pytest.approx(0.04)
    # Two of the three windows have a positive alpha.
    assert summary["win_alpha"] == pytest.approx(2 / 3)


def test_summarize_windows_without_capm_gives_nan_for_beta():
    summary = backtest.summarize_windows(
        [_window("2025-01-02", 0.20, 1.50, 0.10, 1.00)])
    assert math.isnan(summary["mean_beta"])
    assert math.isnan(summary["mean_alpha"])
