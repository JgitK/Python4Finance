"""Tests for the pipeline composition.

The pipeline ranks stocks, selects a diversified set, and optimizes the
weights. These tests use small synthetic returns, so no warehouse is needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant import pipeline


def _three_stocks() -> pd.DataFrame:
    # AAA has a clearly better risk and return than the others.
    # The gap is wide, so sampling noise does not flip the Sharpe order.
    rng = np.random.default_rng(5)
    days = 1000
    return pd.DataFrame(
        {
            "AAA": rng.normal(0.0030, 0.008, days),
            "BBB": rng.normal(0.0008, 0.016, days),
            "CCC": rng.normal(0.0001, 0.030, days),
        },
        index=pd.bdate_range("2023-01-02", periods=days),
    )


def test_rank_by_sharpe_puts_the_best_stock_first():
    returns = _three_stocks()
    ranked = pipeline.rank_by_sharpe(returns)
    assert ranked[0] == "AAA"


def test_build_portfolio_weights_sum_to_one():
    returns = _three_stocks()
    sector_of = {"AAA": "Tech", "BBB": "Health", "CCC": "Energy"}
    result = pipeline.build_max_sharpe_portfolio(
        returns, sector_of, pipeline.PortfolioParams(n_portfolios=1000, seed=1)
    )
    assert sum(result["weights"].values()) == pytest.approx(1.0)


def test_build_portfolio_respects_the_sector_cap():
    returns = _three_stocks()
    # All three stocks sit in one sector, but only one may be chosen.
    sector_of = {"AAA": "Tech", "BBB": "Tech", "CCC": "Tech"}
    params = pipeline.PortfolioParams(max_per_sector=1, n_portfolios=500, seed=1)
    result = pipeline.build_max_sharpe_portfolio(returns, sector_of, params)
    assert len(result["weights"]) == 1


def test_make_builder_drops_the_benchmark():
    returns = _three_stocks()
    returns["SPY"] = np.random.default_rng(9).normal(0.0005, 0.01, len(returns))
    sector_of = {"AAA": "Tech", "BBB": "Health", "CCC": "Energy"}
    build = pipeline.make_builder(sector_of, pipeline.PortfolioParams(
        n_portfolios=500, seed=1), benchmark="SPY")
    weights = build(returns)
    # The benchmark must never appear in the portfolio.
    assert "SPY" not in weights
