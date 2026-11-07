"""Tests for the CAPM measures.

The CAPM splits the return of a stock into two parts. One part follows
the market (beta). The other part does not follow the market (alpha and
the idiosyncratic risk). These tests build series with a known beta and a
known alpha, and they check that the functions find those values.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant import capm

DAYS = 252
RF = 0.045


def _market(days: int = 300, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=days)
    return pd.Series(rng.normal(0.0005, 0.01, days), index=dates)


def _asset_from(market: pd.Series, beta: float, alpha_daily: float,
                noise: pd.Series | None = None,
                risk_free: float = RF) -> pd.Series:
    """Build a stock whose excess return is alpha + beta * market excess."""
    rf_daily = risk_free / DAYS
    excess = alpha_daily + beta * (market - rf_daily)
    if noise is not None:
        excess = excess + noise
    return excess + rf_daily


# --- regress_on_market ----------------------------------------------------

def test_regress_on_market_finds_a_known_beta_and_alpha():
    market = _market()
    asset = _asset_from(market, beta=1.5, alpha_daily=0.0002)
    result = capm.regress_on_market(asset, market, RF, DAYS)
    assert result["beta"] == pytest.approx(1.5, abs=1e-10)
    # The annual alpha is the daily intercept times the trading days.
    assert result["alpha"] == pytest.approx(0.0002 * DAYS, abs=1e-10)
    # With no noise, the market explains all of the variance.
    assert result["r_squared"] == pytest.approx(1.0, abs=1e-10)
    assert result["idiosyncratic_volatility"] == pytest.approx(0.0, abs=1e-10)
    assert result["n_days"] == len(market)


def test_regress_on_market_uses_excess_returns():
    # A stock that holds cash at the risk-free rate on half of its money
    # and the market on the other half has beta 0.5 and alpha 0. A
    # regression on the raw returns gives a false positive alpha.
    market = _market()
    rf_daily = RF / DAYS
    asset = 0.5 * rf_daily + 0.5 * market
    result = capm.regress_on_market(asset, market, RF, DAYS)
    assert result["beta"] == pytest.approx(0.5, abs=1e-10)
    assert result["alpha"] == pytest.approx(0.0, abs=1e-10)


def test_regress_on_market_measures_the_idiosyncratic_risk():
    market = _market()
    rng = np.random.default_rng(1)
    noise = pd.Series(rng.normal(0.0, 0.02, len(market)), index=market.index)
    # Remove the part of the noise that follows the market, so the true
    # beta stays exactly 1.0.
    noise = noise - noise.mean()
    m = market - market.mean()
    noise = noise - (noise @ m) / (m @ m) * m
    asset = _asset_from(market, beta=1.0, alpha_daily=0.0, noise=noise)
    result = capm.regress_on_market(asset, market, RF, DAYS)
    assert result["beta"] == pytest.approx(1.0, abs=1e-10)
    expected_vol = noise.std(ddof=1) * math.sqrt(DAYS)
    assert result["idiosyncratic_volatility"] == pytest.approx(
        expected_vol, rel=1e-10)
    # R squared is the share of the variance that follows the market.
    market_var = (1.0 ** 2) * market.var(ddof=1)
    assert result["r_squared"] == pytest.approx(
        market_var / asset.var(ddof=1), rel=1e-10)


def test_regress_on_market_aligns_the_dates_and_drops_gaps():
    market = _market()
    asset = _asset_from(market, beta=2.0, alpha_daily=0.0)
    asset.iloc[:10] = np.nan
    asset = asset.iloc[:-5]
    result = capm.regress_on_market(asset, market, RF, DAYS)
    assert result["beta"] == pytest.approx(2.0, abs=1e-10)
    assert result["n_days"] == len(market) - 15


def test_regress_on_market_with_too_few_days_gives_nan():
    market = _market(days=2)
    result = capm.regress_on_market(market * 2.0, market, RF, DAYS)
    assert math.isnan(result["beta"])
    assert math.isnan(result["alpha"])
    assert result["n_days"] == 2


def test_regress_on_market_with_a_flat_market_gives_nan():
    dates = pd.bdate_range("2024-01-01", periods=10)
    market = pd.Series(0.001, index=dates)
    asset = pd.Series(np.linspace(-0.01, 0.01, 10), index=dates)
    result = capm.regress_on_market(asset, market, RF, DAYS)
    assert math.isnan(result["beta"])


# --- capm_table -----------------------------------------------------------

def test_capm_table_gives_one_row_for_each_stock():
    market = _market()
    returns = pd.DataFrame({
        "AAA": _asset_from(market, beta=0.8, alpha_daily=0.0001),
        "BBB": _asset_from(market, beta=1.3, alpha_daily=-0.0001),
        "SPY": market,
    })
    table = capm.capm_table(returns, ["AAA", "BBB"], "SPY", RF, DAYS)
    assert list(table["ticker"]) == ["AAA", "BBB"]
    assert table.set_index("ticker").loc["AAA", "beta"] == pytest.approx(0.8)
    assert table.set_index("ticker").loc["BBB", "alpha"] == pytest.approx(
        -0.0001 * DAYS)


# --- portfolio_capm -------------------------------------------------------

def test_portfolio_beta_is_the_weighted_sum_of_the_stock_betas():
    market = _market()
    rng = np.random.default_rng(2)
    returns = pd.DataFrame({
        "AAA": _asset_from(market, 0.6, 0.0001,
                           pd.Series(rng.normal(0, 0.01, len(market)),
                                     index=market.index)),
        "BBB": _asset_from(market, 1.4, 0.0,
                           pd.Series(rng.normal(0, 0.01, len(market)),
                                     index=market.index)),
        "SPY": market,
    })
    weights = {"AAA": 0.25, "BBB": 0.75}
    table = capm.capm_table(returns, list(weights), "SPY", RF, DAYS)
    betas = table.set_index("ticker")["beta"]
    alphas = table.set_index("ticker")["alpha"]
    result = capm.portfolio_capm(returns, weights, "SPY", RF, DAYS)
    assert result["beta"] == pytest.approx(
        0.25 * betas["AAA"] + 0.75 * betas["BBB"], rel=1e-10)
    assert result["alpha"] == pytest.approx(
        0.25 * alphas["AAA"] + 0.75 * alphas["BBB"], rel=1e-10)


def test_portfolio_capm_splits_the_variance_into_two_parts():
    market = _market()
    rng = np.random.default_rng(3)
    returns = pd.DataFrame({
        "AAA": _asset_from(market, 1.0, 0.0,
                           pd.Series(rng.normal(0, 0.015, len(market)),
                                     index=market.index)),
        "SPY": market,
    })
    result = capm.portfolio_capm(returns, {"AAA": 1.0}, "SPY", RF, DAYS)
    total = result["systematic_variance"] + result["idiosyncratic_variance"]
    assert total == pytest.approx(
        returns["AAA"].var(ddof=1) * DAYS, rel=1e-10)
    assert result["systematic_share"] == pytest.approx(
        result["r_squared"], rel=1e-10)


# --- capital_allocation_line ----------------------------------------------

def test_capital_allocation_line_mixes_the_portfolio_with_cash():
    line = capm.capital_allocation_line(
        tangency_return=0.20, tangency_volatility=0.16, risk_free=0.04,
        fractions=[0.0, 0.5, 1.0, 1.5])
    assert list(line["fraction"]) == [0.0, 0.5, 1.0, 1.5]
    assert list(line["annual_return"]) == pytest.approx(
        [0.04, 0.12, 0.20, 0.28])
    assert list(line["annual_volatility"]) == pytest.approx(
        [0.0, 0.08, 0.16, 0.24])
    # Every point that holds some of the portfolio has the same Sharpe ratio.
    assert list(line["sharpe"].iloc[1:]) == pytest.approx([1.0, 1.0, 1.0])


def test_fraction_for_volatility_reaches_the_target():
    assert capm.fraction_for_volatility(0.16, 0.08) == pytest.approx(0.5)
    assert capm.fraction_for_volatility(0.16, 0.16) == pytest.approx(1.0)


def test_fraction_for_volatility_refuses_a_bad_input():
    with pytest.raises(ValueError):
        capm.fraction_for_volatility(0.0, 0.08)
    with pytest.raises(ValueError):
        capm.fraction_for_volatility(0.16, -0.01)
