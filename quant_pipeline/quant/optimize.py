"""Markowitz portfolio optimization.

Modern Portfolio Theory finds the best mix of stocks.
The best mix gives the most return for each unit of risk.
This module searches for the mix with the highest Sharpe ratio.
It uses a Monte Carlo search. It tries many random weightings and keeps
the best one. Every function uses plain data as input, so the tests can check them.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def portfolio_performance(weights: Any, mean_daily: np.ndarray,
                          cov_daily: np.ndarray, trading_days: int = 252,
                          risk_free: float = 0.0) -> tuple[float, float, float]:
    """Measure one portfolio.

    Return the annual return, the annual volatility, and the Sharpe ratio.
    The weights say how much of the portfolio sits in each stock.
    """
    w = np.asarray(weights, dtype=float)
    annual_return = float(np.dot(w, mean_daily) * trading_days)
    annual_variance = float(w @ cov_daily @ w) * trading_days
    annual_volatility = math.sqrt(annual_variance)
    if annual_volatility == 0.0:
        return annual_return, annual_volatility, float("nan")
    sharpe = (annual_return - risk_free) / annual_volatility
    return annual_return, annual_volatility, sharpe


def random_weights(n: int, rng: np.random.Generator) -> np.ndarray:
    """Make n random weights that sum to 1."""
    weights = rng.random(n)
    return weights / weights.sum()


def monte_carlo_frontier(returns: pd.DataFrame, n_portfolios: int = 10000,
                         risk_free: float = 0.045, trading_days: int = 252,
                         seed: int = 42) -> pd.DataFrame:
    """Try many random portfolios.

    Return one row per portfolio. Each row has the return, the volatility,
    the Sharpe ratio, and the weights. The rows draw the efficient frontier.
    """
    mean_daily = returns.mean().to_numpy()
    cov_daily = returns.cov().to_numpy()
    n_assets = returns.shape[1]
    rng = np.random.default_rng(seed)

    rows = []
    for _ in range(n_portfolios):
        weights = random_weights(n_assets, rng)
        annual_return, annual_vol, sharpe = portfolio_performance(
            weights, mean_daily, cov_daily, trading_days, risk_free
        )
        rows.append(
            {
                "annual_return": annual_return,
                "annual_volatility": annual_vol,
                "sharpe": sharpe,
                "weights": weights,
            }
        )
    return pd.DataFrame(rows)


def optimize_max_sharpe(returns: pd.DataFrame, n_portfolios: int = 10000,
                        risk_free: float = 0.045, trading_days: int = 252,
                        seed: int = 42) -> dict[str, Any]:
    """Find the portfolio with the highest Sharpe ratio.

    Return the best weights by ticker, the return, the volatility, the
    Sharpe ratio, and the full frontier for a plot.
    """
    frontier = monte_carlo_frontier(
        returns, n_portfolios, risk_free, trading_days, seed
    )
    best = frontier.loc[frontier["sharpe"].idxmax()]
    weights = {
        ticker: float(weight)
        for ticker, weight in zip(returns.columns, best["weights"])
    }
    return {
        "weights": weights,
        "annual_return": float(best["annual_return"]),
        "annual_volatility": float(best["annual_volatility"]),
        "sharpe": float(best["sharpe"]),
        "frontier": frontier,
    }
