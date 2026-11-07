"""The CAPM measures: beta, alpha, and the capital allocation line.

The CAPM splits the return of a stock into two parts.

- Beta is the part that follows the market. A beta of 1.5 means that the
  stock moves 1.5% when the market moves 1%, on average.
- Alpha is the return that the market does not explain. A positive alpha
  means that the stock earned more than its beta predicts.

The risk splits the same way. The systematic risk follows the market, and
diversification cannot remove it. The idiosyncratic risk belongs to the
stock alone, and more stocks with a low correlation remove more of it.

The capital allocation line mixes the Max Sharpe portfolio with cash at
the risk-free rate. Each mix has the same Sharpe ratio, so the line is the
correct way to take less risk than the Max Sharpe portfolio.

All the functions use simple daily returns, the same as the backtest.
Each regression uses the excess returns over the daily risk-free rate.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# A regression needs this count of days at minimum.
MIN_DAYS = 3
# A daily market variance at or below this value is a flat market. A real
# market has a daily variance of approximately 1e-4.
MIN_MARKET_VARIANCE = 1e-18


def _empty(n_days: int) -> dict[str, Any]:
    nothing = float("nan")
    return {"beta": nothing, "alpha": nothing, "r_squared": nothing,
            "systematic_variance": nothing, "idiosyncratic_variance": nothing,
            "systematic_share": nothing, "idiosyncratic_volatility": nothing,
            "n_days": n_days}


def regress_on_market(asset: pd.Series, market: pd.Series,
                      risk_free: float = 0.045,
                      trading_days: int = 252) -> dict[str, Any]:
    """Regress the excess return of one series on the market excess return.

    Return the beta, the annual alpha, the R squared, the annual systematic
    and idiosyncratic variance, the systematic share of the variance, the
    annual idiosyncratic volatility, and the count of days.

    The function uses only the dates that hold a value in both series. With
    fewer than `MIN_DAYS` days, or with a market that does not move, the
    function gives NaN for each measure.
    """
    both = pd.concat([pd.Series(asset), pd.Series(market)], axis=1,
                     join="inner").dropna()
    n_days = int(len(both))
    if n_days < MIN_DAYS:
        return _empty(n_days)

    rf_daily = risk_free / trading_days
    asset_excess = both.iloc[:, 0].to_numpy() - rf_daily
    market_excess = both.iloc[:, 1].to_numpy() - rf_daily

    market_var = float(np.var(market_excess, ddof=1))
    # A flat market gives a variance of approximately 1e-36 from the
    # rounding, not exactly 0. Such a market has no beta.
    if market_var <= MIN_MARKET_VARIANCE:
        return _empty(n_days)

    covariance = float(np.cov(asset_excess, market_excess, ddof=1)[0, 1])
    beta = covariance / market_var
    alpha_daily = float(asset_excess.mean() - beta * market_excess.mean())
    residual = asset_excess - alpha_daily - beta * market_excess

    total_var = float(np.var(asset_excess, ddof=1))
    systematic_var = beta ** 2 * market_var
    idiosyncratic_var = float(np.var(residual, ddof=1))
    share = systematic_var / total_var if total_var > 0 else float("nan")

    return {
        "beta": beta,
        "alpha": alpha_daily * trading_days,
        "r_squared": share,
        "systematic_variance": systematic_var * trading_days,
        "idiosyncratic_variance": idiosyncratic_var * trading_days,
        "systematic_share": share,
        "idiosyncratic_volatility": math.sqrt(idiosyncratic_var * trading_days),
        "n_days": n_days,
    }


def capm_table(returns: pd.DataFrame, tickers: list[str], market: str,
               risk_free: float = 0.045,
               trading_days: int = 252) -> pd.DataFrame:
    """Give one row of CAPM measures for each ticker, in the given order."""
    rows = []
    for ticker in tickers:
        row = regress_on_market(returns[ticker], returns[market],
                                risk_free, trading_days)
        rows.append({"ticker": ticker, **row})
    return pd.DataFrame(rows)


def portfolio_capm(returns: pd.DataFrame, weights: dict[str, float],
                   market: str, risk_free: float = 0.045,
                   trading_days: int = 252) -> dict[str, Any]:
    """Give the CAPM measures of a portfolio with fixed weights.

    The function blends the stock returns into one daily series, and it
    regresses that series on the market. The beta and the alpha of the
    portfolio are then the weighted sums of the stock betas and alphas.
    """
    tickers = list(weights)
    frame = returns[tickers + [market]].dropna()
    weight_vector = np.array([weights[t] for t in tickers])
    daily = pd.Series(frame[tickers].to_numpy() @ weight_vector,
                      index=frame.index)
    return regress_on_market(daily, frame[market], risk_free, trading_days)


def capital_allocation_line(tangency_return: float,
                            tangency_volatility: float, risk_free: float,
                            fractions: list[float]) -> pd.DataFrame:
    """Give the points of the line from cash to the Max Sharpe portfolio.

    A fraction is the share of the money in the portfolio. The rest is cash
    at the risk-free rate. A fraction above 1 borrows at the risk-free rate.
    """
    fractions = [float(f) for f in fractions]
    returns = [risk_free + f * (tangency_return - risk_free) for f in fractions]
    vols = [f * tangency_volatility for f in fractions]
    sharpe = [(r - risk_free) / v if v > 0 else float("nan")
              for r, v in zip(returns, vols)]
    return pd.DataFrame({"fraction": fractions, "annual_return": returns,
                         "annual_volatility": vols, "sharpe": sharpe})


def fraction_for_volatility(tangency_volatility: float,
                            target_volatility: float) -> float:
    """Give the share of the money in the portfolio for a target volatility."""
    if tangency_volatility <= 0:
        raise ValueError("The portfolio volatility must be above 0.")
    if target_volatility < 0:
        raise ValueError("The target volatility must not be below 0.")
    return target_volatility / tangency_volatility
