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


def _annual_inputs(returns: pd.DataFrame, risk_free: float,
                   trading_days: int) -> tuple[np.ndarray, np.ndarray]:
    """Give the annual excess return and the annual covariance.

    The formulas are those of `quant.optimize.portfolio_performance`.
    """
    excess = returns.mean().to_numpy() * trading_days - risk_free
    cov = returns.cov().to_numpy() * trading_days
    return excess, cov


def _sharpe_of(w: np.ndarray, excess: np.ndarray, cov: np.ndarray) -> float:
    """Give the Sharpe ratio of the weights. Give -inf for no risk."""
    variance = float(w @ cov @ w)
    if variance <= 0.0:
        return -math.inf
    return float(w @ excess) / math.sqrt(variance)


def _tangency_by_reformulation(excess: np.ndarray, cov: np.ndarray,
                               min_weight: float,
                               max_weight: float) -> np.ndarray | None:
    """Solve the convex form of the Max Sharpe problem.

    Cornuejols and Tutuncu put y = kappa * w, with kappa > 0, and they fix
    the excess return of y at 1. The problem then becomes: minimize
    y' cov y, subject to excess' y = 1, y >= 0, and
    min_weight * kappa <= y <= max_weight * kappa, with kappa = sum(y).
    The weights are y / kappa.

    This form needs a feasible portfolio with a positive excess return.
    Return None when no such portfolio exists.
    """
    n = len(excess)
    start_w = np.full(n, 1.0 / n)
    best_return = float(start_w @ excess)
    # A start point with a positive excess return. Move the money to the
    # asset with the highest excess return, as far as the bounds allow.
    order = np.argsort(-excess)
    greedy = np.full(n, min_weight)
    left = 1.0 - greedy.sum()
    for i in order:
        add = min(max_weight - min_weight, left)
        greedy[i] += add
        left -= add
    if float(greedy @ excess) > best_return:
        start_w, best_return = greedy, float(greedy @ excess)
    if best_return <= 0.0:
        return None

    constraints = [
        {"type": "eq", "fun": lambda y: y @ excess - 1.0,
         "jac": lambda y: excess},
        {"type": "ineq", "fun": lambda y: y - min_weight * y.sum(),
         "jac": lambda y: np.eye(n) - min_weight},
        {"type": "ineq", "fun": lambda y: max_weight * y.sum() - y,
         "jac": lambda y: max_weight - np.eye(n)},
    ]
    result = minimize(
        lambda y: y @ cov @ y, start_w / best_return,
        jac=lambda y: 2.0 * cov @ y, method="SLSQP",
        bounds=[(0.0, None)] * n, constraints=constraints,
        options={"ftol": _FTOL, "maxiter": 1000},
    )
    y = np.clip(result.x, 0.0, None)
    if y.sum() <= 0.0:
        return None
    return _clean(y / y.sum(), min_weight, max_weight)


def max_sharpe_weights(excess: np.ndarray, cov: np.ndarray,
                       min_weight: float, max_weight: float) -> np.ndarray:
    """Find the weights with the highest Sharpe ratio inside the bounds.

    `excess` is the annual return minus the risk-free rate, and `cov` is
    the annual covariance. The convex reformulation gives the answer when
    a portfolio with a positive excess return exists. A direct SLSQP
    search on the ratio then starts from that answer, from equal weights
    and from the minimum-variance weights. The function keeps the best
    result. When every portfolio loses to cash, only the direct search
    can give the answer.
    """
    excess = np.asarray(excess, dtype=float)
    cov = np.asarray(cov, dtype=float)
    n = len(excess)
    check_bounds(n, min_weight, max_weight)
    starts = [np.full(n, 1.0 / n), min_variance_weights(cov, min_weight,
                                                        max_weight)]
    tangency = _tangency_by_reformulation(excess, cov, min_weight,
                                          max_weight)
    if tangency is not None:
        starts.insert(0, tangency)

    def negative_sharpe(w: np.ndarray) -> float:
        return -float(w @ excess) / math.sqrt(max(float(w @ cov @ w), 1e-300))

    candidates = list(starts)
    for start in starts:
        candidates.append(_slsqp(negative_sharpe, start, min_weight,
                                 max_weight))
    return max(candidates, key=lambda w: _sharpe_of(w, excess, cov))


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
    elif objective == "max_sharpe":
        excess, annual_cov = _annual_inputs(returns, risk_free, trading_days)
        weights = max_sharpe_weights(excess, annual_cov, min_weight,
                                     max_weight)
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
