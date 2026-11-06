"""Tests for the Markowitz optimizer.

These tests use small inputs with answers that are known by hand.
They check the portfolio math and the Max Sharpe search.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant import optimize


# --- portfolio_performance -------------------------------------------------

def test_portfolio_performance_matches_hand_calculation():
    # Two assets. Each has a mean daily return of 0.001 and a daily variance
    # of 0.0004. The assets do not move together, so the off-diagonal is zero.
    weights = [0.5, 0.5]
    mean_daily = np.array([0.001, 0.001])
    cov_daily = np.array([[0.0004, 0.0], [0.0, 0.0004]])

    annual_return, annual_vol, sharpe = optimize.portfolio_performance(
        weights, mean_daily, cov_daily, trading_days=252, risk_free=0.0
    )

    # Annual return is the weighted daily return times 252.
    assert annual_return == pytest.approx(0.001 * 252)
    # Annual variance is w' cov w times 252. Here that is 0.0002 * 252.
    assert annual_vol == pytest.approx(math.sqrt(0.0002 * 252))
    assert sharpe == pytest.approx(annual_return / annual_vol)


def test_portfolio_performance_subtracts_risk_free_rate():
    weights = [1.0]
    mean_daily = np.array([0.001])
    cov_daily = np.array([[0.0004]])

    annual_return, annual_vol, sharpe = optimize.portfolio_performance(
        weights, mean_daily, cov_daily, trading_days=252, risk_free=0.05
    )
    assert sharpe == pytest.approx((annual_return - 0.05) / annual_vol)


# --- random_weights --------------------------------------------------------

def test_random_weights_sum_to_one_and_are_non_negative():
    rng = np.random.default_rng(0)
    weights = optimize.random_weights(5, rng)
    assert len(weights) == 5
    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()


# --- optimize_max_sharpe ---------------------------------------------------

def _make_returns(seed: int = 1, days: int = 300) -> pd.DataFrame:
    """Build a small return frame for two stocks."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-02", periods=days)
    return pd.DataFrame(
        {
            "AAA": rng.normal(0.001, 0.01, days),
            "BBB": rng.normal(0.0005, 0.02, days),
        },
        index=dates,
    )


def test_optimize_max_sharpe_weights_sum_to_one():
    returns = _make_returns()
    result = optimize.optimize_max_sharpe(returns, n_portfolios=2000, seed=7)
    weights = result["weights"]
    assert set(weights) == {"AAA", "BBB"}
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(0.0 <= w <= 1.0 for w in weights.values())


def test_optimize_max_sharpe_is_deterministic_with_seed():
    returns = _make_returns()
    first = optimize.optimize_max_sharpe(returns, n_portfolios=2000, seed=7)
    second = optimize.optimize_max_sharpe(returns, n_portfolios=2000, seed=7)
    assert first["sharpe"] == pytest.approx(second["sharpe"])
    assert first["weights"] == second["weights"]


def test_optimize_max_sharpe_single_asset_gives_full_weight():
    # With one asset every random weight is 1.0, so the answer is exact.
    rng = np.random.default_rng(3)
    returns = pd.DataFrame({"ONLY": rng.normal(0.001, 0.01, 300)})

    result = optimize.optimize_max_sharpe(returns, n_portfolios=50, seed=1,
                                          risk_free=0.045)
    assert result["weights"]["ONLY"] == pytest.approx(1.0)

    # The reported Sharpe must match a direct calculation on the asset.
    daily = returns["ONLY"]
    annual_return = daily.mean() * 252
    annual_vol = daily.std(ddof=1) * math.sqrt(252)
    expected_sharpe = (annual_return - 0.045) / annual_vol
    assert result["sharpe"] == pytest.approx(expected_sharpe, rel=1e-6)
