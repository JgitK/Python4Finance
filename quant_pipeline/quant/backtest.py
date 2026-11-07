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

from quant import capm

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
    # The realized beta and alpha over the holding window (D25). They say
    # how much of the excess return the market risk explains.
    if weights:
        realized = capm.regress_on_market(portfolio_daily, window[benchmark],
                                          risk_free, trading_days)
    else:
        realized = capm.regress_on_market(pd.Series(dtype=float),
                                          window[benchmark],
                                          risk_free, trading_days)
    return {"selection_date": pd.Timestamp(selection_date),
            "weights": weights, "portfolio": portfolio,
            "benchmark": benchmark_perf, "sharpe_diff": sharpe_diff,
            "capm": realized}


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


def window_is_scored(window: dict[str, Any]) -> bool:
    """Say if one window holds a result.

    A window with no stock is not a result. The portfolio then holds
    nothing, and it reports a return of 0%. A count of that window as a
    loss gives a wrong win rate. A window also needs a total return for
    the portfolio and for the benchmark.
    """
    if not window["weights"]:
        return False
    return bool(np.isfinite(window["portfolio"]["total_return"])
                and np.isfinite(window["benchmark"]["total_return"]))


def summarize_windows(windows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize many walk-forward windows against the benchmark.

    Three overlapping windows cannot show that a result is not luck. This
    function reads many windows and gives the share that beats the
    benchmark, and the excess return.

    The summary reports `n_windows` and `n_scored`. A window that this
    function cannot score stays in `n_windows`, so a reader sees that it
    is there. See `window_is_scored`.

    The Sharpe ratio needs more than one day, so a window can have a
    return and no Sharpe ratio. `n_sharpe` gives the count of windows with
    a Sharpe ratio for the portfolio and for the benchmark.
    """
    nothing = float("nan")
    summary: dict[str, Any] = {
        "n_windows": len(windows), "n_scored": 0, "n_sharpe": 0,
        "win_return": nothing, "win_sharpe": nothing,
        "mean_excess": nothing, "median_excess": nothing,
        "mean_sharpe": nothing, "mean_benchmark_sharpe": nothing,
        "mean_beta": nothing, "mean_alpha": nothing,
        "median_alpha": nothing, "win_alpha": nothing,
    }
    scored = [w for w in windows if window_is_scored(w)]
    summary["n_scored"] = len(scored)
    if not scored:
        return summary

    excess = np.array([w["portfolio"]["total_return"]
                       - w["benchmark"]["total_return"] for w in scored])
    summary["win_return"] = float((excess > 0).mean())
    summary["mean_excess"] = float(excess.mean())
    summary["median_excess"] = float(np.median(excess))

    sharpe = np.array([w["portfolio"]["sharpe"] for w in scored])
    benchmark = np.array([w["benchmark"]["sharpe"] for w in scored])
    both = np.isfinite(sharpe) & np.isfinite(benchmark)
    summary["n_sharpe"] = int(both.sum())
    if both.any():
        summary["win_sharpe"] = float(
            (sharpe[both] > benchmark[both]).mean())
    if np.isfinite(sharpe).any():
        summary["mean_sharpe"] = float(np.nanmean(sharpe))
    if np.isfinite(benchmark).any():
        summary["mean_benchmark_sharpe"] = float(np.nanmean(benchmark))

    # The realized CAPM measures (D25). A window without them is not an
    # error: an older caller does not supply them.
    nan = float("nan")
    beta = np.array([w.get("capm", {}).get("beta", nan) for w in scored])
    alpha = np.array([w.get("capm", {}).get("alpha", nan) for w in scored])
    if np.isfinite(beta).any():
        summary["mean_beta"] = float(np.nanmean(beta))
    finite_alpha = alpha[np.isfinite(alpha)]
    if finite_alpha.size:
        summary["mean_alpha"] = float(finite_alpha.mean())
        summary["median_alpha"] = float(np.median(finite_alpha))
        summary["win_alpha"] = float((finite_alpha > 0).mean())
    return summary
