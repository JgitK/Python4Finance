"""Tests for the momentum factor and the two-factor regression (D30).

The screen ranks the stocks on the trailing compound return. That is the
classic momentum signal. These tests check the tools that separate the
momentum premium from the rest of the alpha.

The regression tests build a portfolio with known loadings. The factor
tests use a tiny price panel. A person can check its long leg and its
short leg by hand.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant import capm, factors

DAYS = 252
RF = 0.045


def _two_factors(days: int = 600, seed: int = 1) -> tuple[pd.Series, pd.Series]:
    """Give a market series and a momentum series with no relation."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=days)
    market = pd.Series(rng.normal(0.0005, 0.01, days), index=dates)
    umd = pd.Series(rng.normal(0.0003, 0.008, days), index=dates)
    return market, umd


def _portfolio(market: pd.Series, umd: pd.Series, beta: float, loading: float,
               alpha_daily: float, noise_sd: float = 0.0,
               seed: int = 2) -> pd.Series:
    """Build a portfolio: excess = alpha + beta * market excess + loading * UMD."""
    rf_daily = RF / DAYS
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, noise_sd, len(market)) if noise_sd else 0.0
    excess = alpha_daily + beta * (market - rf_daily) + loading * umd + noise
    return excess + rf_daily


# --- regress_two_factor ---------------------------------------------------

def test_regress_two_factor_finds_known_loadings_without_noise():
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=0.3, loading=0.8, alpha_daily=0.0001)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(0.3, abs=1e-10)
    assert result["umd_loading"] == pytest.approx(0.8, abs=1e-10)
    # The annual alpha is the daily intercept times the trading days.
    assert result["alpha"] == pytest.approx(0.0001 * DAYS, abs=1e-10)
    assert result["r_squared"] == pytest.approx(1.0, abs=1e-10)
    assert result["n_days"] == len(market)


def test_regress_two_factor_finds_known_loadings_with_noise():
    market, umd = _two_factors(days=2000)
    port = _portfolio(market, umd, beta=0.3, loading=0.8,
                      alpha_daily=0.0004, noise_sd=0.002)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(0.3, abs=0.03)
    assert result["umd_loading"] == pytest.approx(0.8, abs=0.04)
    # The noise is large against the alpha, so the tolerance is wide. The
    # sign and the size must still be correct.
    assert result["alpha"] == pytest.approx(0.0004 * DAYS, abs=0.05)
    # The t statistic of a loading of 0.8 on 2000 days is very large.
    assert result["umd_t"] > 20
    assert result["r_squared"] < 1.0


def test_regress_two_factor_t_statistic_matches_the_textbook_formula():
    # Compute the standard error with the OLS formula, independently.
    market, umd = _two_factors(days=300, seed=5)
    port = _portfolio(market, umd, beta=1.2, loading=0.2,
                      alpha_daily=0.0, noise_sd=0.01, seed=6)
    rf_daily = RF / DAYS
    y = (port - rf_daily).to_numpy()
    x = np.column_stack([np.ones(len(y)), (market - rf_daily).to_numpy(),
                         umd.to_numpy()])
    coef = np.linalg.solve(x.T @ x, x.T @ y)
    resid = y - x @ coef
    sigma2 = resid @ resid / (len(y) - 3)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(x.T @ x)))
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["umd_t"] == pytest.approx(coef[2] / se[2], rel=1e-9)
    assert result["alpha_t"] == pytest.approx(coef[0] / se[0], rel=1e-9)
    assert result["beta_t"] == pytest.approx(coef[1] / se[1], rel=1e-9)


def test_regress_two_factor_does_not_subtract_the_risk_free_rate_from_umd():
    # UMD is a long-short return. It costs nothing, so it has no risk-free
    # part. A regression that subtracts the rate from UMD moves the alpha
    # by loading * rate.
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=1.0, loading=1.0, alpha_daily=0.0)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["alpha"] == pytest.approx(0.0, abs=1e-10)


def test_regress_two_factor_with_no_momentum_equals_the_capm_alpha():
    # A portfolio with no momentum loading and no noise has the same beta
    # and the same alpha in the two regressions.
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=1.3, loading=0.0,
                      alpha_daily=0.0002)
    two = factors.regress_two_factor(port, market, umd, RF, DAYS)
    one = capm.regress_on_market(port, market, RF, DAYS)
    assert two["beta"] == pytest.approx(one["beta"], abs=1e-10)
    assert two["alpha"] == pytest.approx(one["alpha"], abs=1e-10)


def test_regress_two_factor_uses_only_the_common_dates():
    market, umd = _two_factors(days=400)
    port = _portfolio(market, umd, beta=0.5, loading=0.5, alpha_daily=0.0)
    result = factors.regress_two_factor(port, market, umd.iloc[100:], RF,
                                        DAYS)
    assert result["n_days"] == 300
    assert result["umd_loading"] == pytest.approx(0.5, abs=1e-10)


def test_regress_two_factor_gives_nan_for_too_few_days():
    market, umd = _two_factors(days=3)
    result = factors.regress_two_factor(market, market, umd, RF, DAYS)
    assert np.isnan(result["umd_loading"])
    assert np.isnan(result["alpha"])
    assert result["n_days"] == 3


def test_spy_on_itself_gives_beta_one_and_no_momentum_or_alpha():
    # The sanity check of D30. The market factor is SPY minus the
    # risk-free rate. A regression of SPY on that factor and on UMD must
    # give a beta of 1, a UMD loading of 0, and an alpha of 0.
    market, umd = _two_factors()
    result = factors.regress_two_factor(market, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(1.0, abs=1e-10)
    assert result["umd_loading"] == pytest.approx(0.0, abs=1e-10)
    assert result["alpha"] == pytest.approx(0.0, abs=1e-10)
