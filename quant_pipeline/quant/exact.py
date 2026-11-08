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
from scipy.optimize import linprog, minimize

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


def sortino_ratio(daily: np.ndarray, risk_free: float = 0.045,
                  trading_days: int = 252) -> float:
    """Give the Sortino ratio of a daily return series.

    The numerator is the annual return minus the risk-free rate, as in the
    Sharpe ratio. The downside deviation counts each daily shortfall below
    the daily risk-free rate, and a day above that rate counts as zero. The
    mean runs over all days, so a calm day lowers the deviation.

    The dbt model int_risk_metrics measures the shortfall below 0, not
    below the risk-free rate. D29 explains the difference.
    """
    daily = np.asarray(daily, dtype=float)
    target = risk_free / trading_days
    shortfall = np.minimum(daily - target, 0.0)
    downside = math.sqrt(float((shortfall ** 2).mean()) * trading_days)
    if downside == 0.0:
        return math.inf
    return (float(daily.mean()) * trading_days - risk_free) / downside


def max_sortino_weights(scenarios: np.ndarray, min_weight: float,
                        max_weight: float, risk_free: float = 0.045,
                        trading_days: int = 252,
                        starts: list[np.ndarray] | None = None
                        ) -> np.ndarray:
    """Find the weights with the highest Sortino ratio inside the bounds.

    `scenarios` holds one row of daily returns for each day. The weights
    sum to 1, so the shortfall of the portfolio below the daily target is
    (scenarios - target) times the weights. The squared shortfall has a
    smooth gradient, so SLSQP can use it. The function starts SLSQP from
    equal weights and from each extra start, and it keeps the best result.
    """
    scenarios = np.asarray(scenarios, dtype=float)
    n_days, n = scenarios.shape
    check_bounds(n, min_weight, max_weight)
    excess = scenarios - risk_free / trading_days
    mean_excess = excess.mean(axis=0) * trading_days

    def negative_sortino(w: np.ndarray) -> tuple[float, np.ndarray]:
        shortfall = np.minimum(excess @ w, 0.0)
        downside = math.sqrt(max(float(shortfall @ shortfall) / n_days
                                 * trading_days, 1e-300))
        numerator = float(mean_excess @ w)
        d_downside = (excess.T @ shortfall) / n_days * trading_days / downside
        gradient = (mean_excess * downside - numerator * d_downside) \
            / downside ** 2
        return -numerator / downside, -gradient

    candidates = [np.full(n, 1.0 / n)] + list(starts or [])
    results = [_slsqp(negative_sortino, start, min_weight, max_weight,
                      jac=True) for start in candidates]
    return max(results + candidates,
               key=lambda w: sortino_ratio(scenarios @ w, risk_free,
                                           trading_days))


def tail_count(n_days: int, level: float = 0.05) -> int:
    """Give the count of days that the 5% CVaR of dbt averages.

    int_risk_metrics takes the linear quantile, which sits at position
    level * (n_days - 1) in the sorted returns. It then averages every day
    at or below that quantile. With no ties, that is the worst
    floor(level * (n_days - 1)) + 1 days.
    """
    return int(math.floor(level * (n_days - 1) + 1e-9)) + 1


def cvar_5(daily: np.ndarray) -> float:
    """Give the 5% CVaR of a daily return series, as dbt calculates it.

    The value is a return, so a loss is negative. It is the mean of the
    returns at or below the linear 5% quantile.
    """
    daily = np.asarray(daily, dtype=float)
    var_5 = float(np.quantile(daily, 0.05))
    return float(daily[daily <= var_5].mean())


def min_cvar_weights(scenarios: np.ndarray, min_weight: float,
                     max_weight: float, level: float = 0.05) -> np.ndarray:
    """Find the weights with the lowest 5% CVaR inside the bounds.

    The linear program of Rockafellar and Uryasev has the variables w, a
    and u. It minimizes a + sum(u) / k, subject to u_t >= loss_t - a and
    u_t >= 0. The loss of day t is minus the return of the portfolio. At
    the optimum, a is the Value at Risk and the objective is the mean loss
    of the k worst days.

    k comes from `tail_count`, so the program minimizes the cvar_5 of dbt
    exactly. HiGHS solves the program.
    """
    scenarios = np.asarray(scenarios, dtype=float)
    n_days, n = scenarios.shape
    check_bounds(n, min_weight, max_weight)
    k = tail_count(n_days, level)
    cost = np.concatenate([np.zeros(n), [1.0], np.full(n_days, 1.0 / k)])
    # -r_t . w - a - u_t <= 0 for each day t.
    upper = np.hstack([-scenarios, -np.ones((n_days, 1)), -np.eye(n_days)])
    equal = np.concatenate([np.ones(n), [0.0], np.zeros(n_days)])[None, :]
    bounds = ([(min_weight, max_weight)] * n + [(None, None)]
              + [(0.0, None)] * n_days)
    result = linprog(cost, A_ub=upper, b_ub=np.zeros(n_days), A_eq=equal,
                     b_eq=[1.0], bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"The CVaR program failed: {result.message}")
    return _clean(result.x[:n], min_weight, max_weight)


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
    elif objective == "max_sortino":
        excess, annual_cov = _annual_inputs(returns, risk_free, trading_days)
        starts = [max_sharpe_weights(excess, annual_cov, min_weight,
                                     max_weight),
                  min_variance_weights(cov, min_weight, max_weight)]
        weights = max_sortino_weights(returns.to_numpy(), min_weight,
                                      max_weight, risk_free, trading_days,
                                      starts)
    else:
        weights = min_cvar_weights(returns.to_numpy(), min_weight,
                                   max_weight)
    result = _result(returns, weights, objective, risk_free, trading_days)
    daily = returns.to_numpy() @ weights
    result["sortino"] = sortino_ratio(daily, risk_free, trading_days)
    result["cvar_5"] = cvar_5(daily)
    return result


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


def prune_pool(returns: pd.DataFrame, solver, min_weight: float,
               max_weight: float) -> dict[str, Any]:
    """Let the optimizer pick the count of stocks from a larger pool.

    This is option B of D29. `solver(frame, low, high)` gives a result with
    weights by ticker. The steps are:

    1. Solve on the pool with a floor of 0 and the cap `max_weight`.
    2. Drop each stock with a weight below `min_weight`.
    3. When too few stocks remain for the cap, add back the dropped stocks
       with the largest weights. Four stocks at a cap of 25% must remain.
    4. Solve again on the stocks that remain. Stop when no stock drops.
    5. Solve one last time with the full bounds.

    Return the result of the last solve, the pool and the count of rounds.
    """
    pool = list(returns.columns)
    check_bounds(len(pool), 0.0, max_weight)
    need = math.ceil(1.0 / max_weight - _BOUND_TOLERANCE)
    kept = pool
    rounds = 0
    while True:
        rounds += 1
        weights = solver(returns[kept], 0.0, max_weight)["weights"]
        survivors = [t for t in kept if weights[t] >= min_weight]
        if len(survivors) < need:
            dropped = sorted((t for t in kept if t not in survivors),
                             key=lambda t: -weights[t])
            back = set(dropped[:need - len(survivors)])
            survivors = [t for t in kept if t in survivors or t in back]
        if survivors == kept:
            break
        kept = survivors
    result = solver(returns[kept], min_weight, max_weight)
    result["pool"] = pool
    result["rounds"] = rounds
    return result
