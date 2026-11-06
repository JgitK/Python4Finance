"""Compose the selection and the optimization into one portfolio build.

This module joins the small parts into one step. It ranks the stocks by
Sharpe ratio, picks a diversified set, and finds the Max Sharpe weights.
Both the live run and the backtest use the same build step. But the live
run starts from the dbt screen candidates, and the backtest does not apply
the screen gates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from quant import optimize, select_portfolio


@dataclass
class PortfolioParams:
    """The settings for one portfolio build."""

    target_size: int = 12
    max_per_sector: int = 3
    max_avg_correlation: float = 0.6
    risk_free: float = 0.045
    trading_days: int = 252
    n_portfolios: int = 10000
    seed: int = 42


def rank_by_sharpe(returns: pd.DataFrame, risk_free: float = 0.045,
                   trading_days: int = 252) -> list[str]:
    """Order the stocks from the highest Sharpe ratio to the lowest."""
    annual_return = returns.mean() * trading_days
    annual_vol = returns.std(ddof=1) * math.sqrt(trading_days)
    sharpe = (annual_return - risk_free) / annual_vol
    return list(sharpe.sort_values(ascending=False).index)


def build_max_sharpe_portfolio(returns: pd.DataFrame,
                               sector_of: dict[str, str],
                               params: PortfolioParams | None = None
                               ) -> dict[str, Any]:
    """Build one Max Sharpe portfolio from a return matrix.

    Rank the stocks, pick a diversified set, then optimize the weights.
    Return an empty result when no stock passes the selection.
    """
    params = params or PortfolioParams()

    ranked = rank_by_sharpe(returns, params.risk_free, params.trading_days)
    candidates = [
        {"ticker": ticker, "sector": sector_of.get(ticker, "Unknown")}
        for ticker in ranked
    ]
    corr = returns.corr()
    selected = select_portfolio.greedy_low_correlation(
        candidates, corr, params.target_size, params.max_per_sector,
        params.max_avg_correlation,
    )
    if not selected:
        return {"weights": {}, "selected": []}

    result = optimize.optimize_max_sharpe(
        returns[selected], params.n_portfolios, params.risk_free,
        params.trading_days, params.seed,
    )
    result["selected"] = selected
    return result


def make_builder(sector_of: dict[str, str], params: PortfolioParams,
                 benchmark: str) -> Callable[[pd.DataFrame], dict[str, float]]:
    """Make a build_portfolio function for the backtest.

    The function that this returns uses a train frame as input. It returns weights by ticker.
    It drops the benchmark first, so the benchmark never enters the portfolio.
    """
    def build(train: pd.DataFrame) -> dict[str, float]:
        tradeable = train.drop(columns=[benchmark], errors="ignore").dropna(axis=1)
        result = build_max_sharpe_portfolio(tradeable, sector_of, params)
        return result.get("weights", {})

    return build
