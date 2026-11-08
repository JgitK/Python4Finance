"""Tests for the exact portfolio optimizers (D29).

These tests use small inputs. You can check each answer by hand or with a
brute-force search over a fine grid of weights.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest

from quant import exact, optimize


def _returns(seed: int = 1, days: int = 300, n: int = 4) -> pd.DataFrame:
    """Make a small return frame with different means and volatilities."""
    rng = np.random.default_rng(seed)
    means = np.linspace(0.0002, 0.0012, n)
    vols = np.linspace(0.008, 0.025, n)
    data = rng.normal(means, vols, size=(days, n))
    columns = [f"S{i}" for i in range(n)]
    return pd.DataFrame(data, columns=columns,
                        index=pd.bdate_range("2023-01-02", periods=days))


# --- the bounds ------------------------------------------------------------

def test_bounds_that_cannot_sum_to_one_from_below_raise():
    # 10 stocks at a minimum of 15% need 150% of the money.
    with pytest.raises(ValueError, match="min_weight"):
        exact.check_bounds(10, 0.15, 0.25)


def test_bounds_that_cannot_sum_to_one_from_above_raise():
    # 3 stocks at a maximum of 25% hold only 75% of the money.
    with pytest.raises(ValueError, match="max_weight"):
        exact.check_bounds(3, 0.0, 0.25)


def test_bounds_that_sum_to_exactly_one_are_feasible():
    exact.check_bounds(4, 0.0, 0.25)
    exact.check_bounds(50, 0.02, 0.25)


def test_a_minimum_above_the_maximum_raises():
    with pytest.raises(ValueError):
        exact.check_bounds(4, 0.3, 0.2)


def test_the_solvers_check_the_bounds():
    returns = _returns(n=3)
    for objective in exact.OBJECTIVES:
        with pytest.raises(ValueError, match="max_weight"):
            exact.solve(returns, objective, 0.0, 0.25)


def test_an_unknown_objective_raises():
    with pytest.raises(ValueError, match="objective"):
        exact.solve(_returns(), "max_return", 0.0, 1.0)


# --- min_variance ----------------------------------------------------------

def test_min_variance_of_two_assets_matches_the_formula():
    # For two assets, w1 = (s2^2 - s12) / (s1^2 + s2^2 - 2 s12).
    returns = _returns(seed=3, n=2)
    cov = returns.cov().to_numpy()
    s1, s2, s12 = cov[0, 0], cov[1, 1], cov[0, 1]
    expected = (s2 - s12) / (s1 + s2 - 2 * s12)

    result = exact.solve(returns, "min_variance", 0.0, 1.0)
    assert result["weights"]["S0"] == pytest.approx(expected, abs=1e-6)
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-9)


def test_min_variance_of_three_uncorrelated_assets_is_inverse_variance():
    # With no correlation, the weight is proportional to 1 / variance.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.0, 1.0)
    inverse = 1.0 / np.diag(cov)
    np.testing.assert_allclose(weights, inverse / inverse.sum(), atol=1e-6)


def test_min_variance_holds_a_binding_maximum():
    # The calm asset wants 36/49 of the money alone. A cap of 50% binds.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.0, 0.5)
    assert weights[0] == pytest.approx(0.5, abs=1e-6)
    # The other two split the rest in proportion to 1 / variance.
    assert weights[1] / weights[2] == pytest.approx(9.0 / 4.0, rel=1e-4)


def test_min_variance_holds_a_binding_minimum():
    # The wild asset wants 4/49 of the money. A floor of 20% binds.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.2, 1.0)
    assert weights[2] == pytest.approx(0.2, abs=1e-6)
    assert weights.min() >= 0.2 - 1e-9


# --- max_sharpe ------------------------------------------------------------

def _grid(n: int, step: float, low: float, high: float):
    """Give every weighting of n assets on a grid that sums to 1."""
    ticks = np.round(np.arange(low, high + 1e-9, step), 10)
    for head in itertools.product(ticks, repeat=n - 1):
        last = 1.0 - sum(head)
        if low - 1e-9 <= last <= high + 1e-9:
            yield np.array([*head, last])


def _sharpe(w, returns, risk_free=0.045):
    return optimize.portfolio_performance(
        w, returns.mean().to_numpy(), returns.cov().to_numpy(), 252,
        risk_free)[2]


def test_max_sharpe_of_two_assets_matches_the_tangency_formula():
    # With no bound that binds, the tangency weights are proportional to
    # inverse(cov) times the excess return.
    returns = _returns(seed=4, n=2)
    mu = returns.mean().to_numpy() * 252 - 0.045
    cov = returns.cov().to_numpy() * 252
    raw = np.linalg.solve(cov, mu)
    expected = raw / raw.sum()
    assert (expected > 0).all()

    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    got = np.array([result["weights"]["S0"], result["weights"]["S1"]])
    np.testing.assert_allclose(got, expected, atol=1e-5)


def test_max_sharpe_beats_a_fine_grid_with_binding_bounds():
    returns = _returns(seed=7, n=3)
    best = max(_sharpe(w, returns) for w in _grid(3, 0.01, 0.1, 0.5))
    result = exact.solve(returns, "max_sharpe", 0.1, 0.5)
    w = np.array(list(result["weights"].values()))
    assert w.min() >= 0.1 - 1e-9 and w.max() <= 0.5 + 1e-9
    assert result["sharpe"] >= best - 1e-9
    # The grid step is small, so the grid must come close to the optimum.
    assert result["sharpe"] - best < 0.01


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_max_sharpe_matches_or_beats_the_monte_carlo_search(seed):
    # The Monte Carlo search has no bounds, so give the exact solver none.
    returns = _returns(seed=seed, n=6)
    monte_carlo = optimize.optimize_max_sharpe(returns, n_portfolios=5000,
                                               seed=42)
    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    assert result["sharpe"] >= monte_carlo["sharpe"] - 1e-12


def test_max_sharpe_holds_the_default_bounds_on_ten_assets():
    returns = _returns(seed=11, n=10)
    result = exact.solve(returns, "max_sharpe", 0.02, 0.25)
    w = np.array(list(result["weights"].values()))
    assert w.sum() == pytest.approx(1.0, abs=1e-12)
    assert w.min() >= 0.02 - 1e-12
    assert w.max() <= 0.25 + 1e-12


def test_max_sharpe_works_when_every_asset_loses_to_cash():
    # Every excess return is negative, so the best Sharpe ratio is
    # negative too. The convex reformulation needs a positive one, so the
    # solver must still find the best weights another way.
    returns = _returns(seed=13, n=3) - 0.003
    best = max(_sharpe(w, returns) for w in _grid(3, 0.01, 0.0, 1.0))
    assert best < 0
    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    assert result["sharpe"] >= best - 1e-9


def test_the_reported_sharpe_matches_the_weights():
    returns = _returns(seed=17, n=5)
    result = exact.solve(returns, "max_sharpe", 0.05, 0.4)
    w = np.array([result["weights"][t] for t in returns.columns])
    assert result["sharpe"] == pytest.approx(_sharpe(w, returns), rel=1e-12)


def test_the_convex_reformulation_alone_beats_a_fine_grid():
    # Four assets with a cap of 40%. The cap binds on one asset, and the
    # other three weights are inside the bounds. The reformulation must
    # find the optimum without the help of the direct search.
    returns = _returns(seed=3, n=4)
    excess, cov = exact._annual_inputs(returns, 0.045, 252)
    weights = exact._tangency_by_reformulation(excess, cov, 0.05, 0.4)
    best = max(_sharpe(w, returns) for w in _grid(4, 0.01, 0.05, 0.4))
    assert weights.max() == pytest.approx(0.4, abs=1e-7)
    assert weights.min() >= 0.05 - 1e-12
    assert _sharpe(weights, returns) >= best - 1e-9
    assert _sharpe(weights, returns) - best < 0.01


def test_the_convex_reformulation_gives_none_when_every_asset_loses():
    returns = _returns(seed=13, n=3) - 0.003
    excess, cov = exact._annual_inputs(returns, 0.045, 252)
    assert exact._tangency_by_reformulation(excess, cov, 0.0, 1.0) is None
