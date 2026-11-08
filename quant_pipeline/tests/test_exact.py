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
