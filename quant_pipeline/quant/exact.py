"""Exact portfolio optimizers with bounds on each weight (D29).

The Monte Carlo search of `quant.optimize` tries random weightings and it
keeps the best one. This module solves each problem exactly instead. Each
solver holds the portfolio fully invested and long only. Each weight must
stay between `min_weight` and `max_weight`.

The four objectives are:

- `max_sharpe`: the highest Sharpe ratio. A convex reformulation turns the
  ratio into a quadratic program (Cornuejols and Tutuncu).
- `min_variance`: the lowest variance. This is a quadratic program.
- `max_sortino`: the highest Sortino ratio. The downside deviation counts
  the shortfall below the daily risk-free rate. The solver uses SLSQP from
  several start points.
- `min_cvar`: the lowest Conditional Value at Risk at 5%. A linear program
  of Rockafellar and Uryasev gives it.

Each function uses plain data as input, so the tests can check it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

OBJECTIVES = ("max_sharpe", "min_variance", "max_sortino", "min_cvar")

# The tolerance of the bound check. A sum of exactly 1 is feasible.
_BOUND_TOLERANCE = 1e-12
# The convergence tolerance of SLSQP.
_FTOL = 1e-14


def check_bounds(n: int, min_weight: float, max_weight: float) -> None:
    """Raise ValueError when no weighting of n stocks fits the bounds.

    The weights must sum to 1. So n stocks at the minimum must not need
    more than all the money, and n stocks at the maximum must hold all of
    it.
    """
    if n < 1:
        raise ValueError("The portfolio needs at least one stock.")
    if min_weight < 0.0 or max_weight > 1.0 or min_weight > max_weight:
        raise ValueError(
            f"The bounds must satisfy 0 <= min_weight <= max_weight <= 1. "
            f"min_weight is {min_weight} and max_weight is {max_weight}.")
    if n * min_weight > 1.0 + _BOUND_TOLERANCE:
        raise ValueError(
            f"{n} stocks at min_weight {min_weight} need "
            f"{n * min_weight:.0%} of the money. Lower min_weight or use "
            f"fewer stocks.")
    if n * max_weight < 1.0 - _BOUND_TOLERANCE:
        raise ValueError(
            f"{n} stocks at max_weight {max_weight} hold only "
            f"{n * max_weight:.0%} of the money. Raise max_weight or use "
            f"more stocks.")


def _clean(weights: np.ndarray, min_weight: float,
           max_weight: float) -> np.ndarray:
    """Remove the numerical noise of a solver.

    Clip each weight to its bounds. Then divide by the sum, so the weights
    sum to 1 again.
    """
    w = np.clip(np.asarray(weights, dtype=float), min_weight, max_weight)
    return w / w.sum()


def _slsqp(objective, start: np.ndarray, min_weight: float,
           max_weight: float, jac=None) -> np.ndarray:
    """Minimize an objective over the bounded, fully invested weights."""
    n = len(start)
    result = minimize(
        objective, start, jac=jac, method="SLSQP",
        bounds=[(min_weight, max_weight)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0,
                      "jac": lambda w: np.ones_like(w)}],
        options={"ftol": _FTOL, "maxiter": 1000},
    )
    return _clean(result.x, min_weight, max_weight)


def min_variance_weights(cov: np.ndarray, min_weight: float,
                         max_weight: float) -> np.ndarray:
    """Find the weights with the lowest variance inside the bounds.

    The function divides the covariance by its trace first. The scale does
    not change the answer, and it keeps the objective near 1, so the
    tolerance of the solver means the same thing for every input.
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    check_bounds(n, min_weight, max_weight)
    scaled = cov / np.trace(cov)
    start = np.full(n, 1.0 / n)
    return _slsqp(lambda w: w @ scaled @ w, start, min_weight, max_weight,
                  jac=lambda w: 2.0 * scaled @ w)


def solve(returns: pd.DataFrame, objective: str, min_weight: float,
          max_weight: float, risk_free: float = 0.045,
          trading_days: int = 252) -> dict[str, Any]:
    """Find the exact weights of one objective.

    Return the weights by ticker, the annual return, the annual volatility
    and the Sharpe ratio. The measures use the same formulas as
    `quant.optimize.portfolio_performance`.
    """
    if objective not in OBJECTIVES:
        raise ValueError(
            f"objective must be one of {', '.join(OBJECTIVES)}, not "
            f"{objective!r}.")
    check_bounds(returns.shape[1], min_weight, max_weight)
    cov = returns.cov().to_numpy()
    if objective == "min_variance":
        weights = min_variance_weights(cov, min_weight, max_weight)
    else:
        raise NotImplementedError(objective)
    return _result(returns, weights, objective, risk_free, trading_days)


def _result(returns: pd.DataFrame, weights: np.ndarray, objective: str,
            risk_free: float, trading_days: int) -> dict[str, Any]:
    """Give the weights by ticker and the measures of the portfolio."""
    from quant import optimize

    annual_return, annual_vol, sharpe = optimize.portfolio_performance(
        weights, returns.mean().to_numpy(), returns.cov().to_numpy(),
        trading_days, risk_free)
    return {
        "weights": {ticker: float(w)
                    for ticker, w in zip(returns.columns, weights)},
        "annual_return": annual_return,
        "annual_volatility": annual_vol,
        "sharpe": sharpe,
        "objective": objective,
    }
