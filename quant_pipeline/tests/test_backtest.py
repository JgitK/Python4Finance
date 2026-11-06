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
        # Record the newest day the selector was allowed to see.
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
