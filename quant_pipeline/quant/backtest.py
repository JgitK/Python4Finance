"""Walk-forward backtest.

Each step selects a portfolio from past returns only. Then it holds that
portfolio and measures the result on returns that the build step did not use.
This module does not select the list of stocks. The caller must supply a
list that does not use future data.
This module splits the data at a date, builds the portfolio from the past,
and scores it on the future window. It also scores the benchmark.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
import pandas as pd

# A build_portfolio function uses a train frame as input.
# It returns weights by ticker.
BuildPortfolio = Callable[[pd.DataFrame], dict[str, float]]


def split_by_date(returns: pd.DataFrame,
                  date: Any) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the returns at a date.

    The train set holds every day before the date, and the date too.
    The test set holds every day after the date.
    """
    cut = pd.Timestamp(date)
    train = returns[returns.index <= cut]
    test = returns[returns.index > cut]
    return train, test


def holding_window(test: pd.DataFrame, holding_period: int) -> pd.DataFrame:
    """Keep the first few days of the test set. This is the holding period."""
    return test.iloc[:holding_period]


def portfolio_daily_returns(returns: pd.DataFrame,
                            weights: dict[str, float]) -> pd.Series:
    """Blend the stock returns into one portfolio return per day."""
    tickers = list(weights)
    weight_vector = np.array([weights[ticker] for ticker in tickers])
    matrix = returns[tickers].to_numpy()
    return pd.Series(matrix @ weight_vector, index=returns.index)


def window_performance(daily: pd.Series, risk_free: float = 0.045,
                       trading_days: int = 252) -> dict[str, Any]:
    """Score one return series over a holding window.

    Return the total return, the annual return, the annual volatility,
    the Sharpe ratio, and the number of days.
    """
    daily = pd.Series(daily).dropna()
    n_days = int(len(daily))
    if n_days == 0:
        return {"total_return": float("nan"), "annual_return": float("nan"),
                "annual_volatility": float("nan"), "sharpe": float("nan"),
                "n_days": 0}

    total_return = float((1.0 + daily).prod() - 1.0)
    annual_return = float((1.0 + total_return) ** (trading_days / n_days) - 1.0)
    # One day is not enough to measure volatility.
    annual_volatility = (
        float(daily.std(ddof=1) * math.sqrt(trading_days)) if n_days > 1 else 0.0
    )
    sharpe = (
        (annual_return - risk_free) / annual_volatility
        if annual_volatility > 0 else float("nan")
    )
    return {"total_return": total_return, "annual_return": annual_return,
            "annual_volatility": annual_volatility, "sharpe": sharpe,
            "n_days": n_days}


def backtest_window(returns: pd.DataFrame, selection_date: Any,
                    holding_period: int, build_portfolio: BuildPortfolio,
                    benchmark: str, risk_free: float = 0.045,
                    trading_days: int = 252) -> dict[str, Any]:
    """Run one walk-forward step.

    Build the portfolio from past data. Hold it forward. Score it against
    the benchmark over the same window.
    """
    train, test = split_by_date(returns, selection_date)
    weights = build_portfolio(train)
    window = holding_window(test, holding_period)

    portfolio_daily = portfolio_daily_returns(window, weights)
    portfolio = window_performance(portfolio_daily, risk_free, trading_days)

    benchmark_perf = window_performance(
        window[benchmark], risk_free, trading_days
    )

    sharpe_diff = portfolio["sharpe"] - benchmark_perf["sharpe"]
    return {"selection_date": pd.Timestamp(selection_date),
            "weights": weights, "portfolio": portfolio,
            "benchmark": benchmark_perf, "sharpe_diff": sharpe_diff}


def run_walk_forward(returns: pd.DataFrame, selection_dates: list[Any],
                     holding_period: int, build_portfolio: BuildPortfolio,
                     benchmark: str, risk_free: float = 0.045,
                     trading_days: int = 252) -> list[dict[str, Any]]:
    """Run the backtest at several selection dates."""
    return [
        backtest_window(returns, date, holding_period, build_portfolio,
                        benchmark, risk_free, trading_days)
        for date in selection_dates
    ]
