"""Tests for the equal-weight controls of option B (D33).

Two controls separate the work of the optimizer from the work of the pool:

- The objective `equal_weight` gives 1/n to each stock. In the pool mode
  no stock drops, so it holds the whole pool.
- The setting `kept_weighting="equal"` lets `max_sharpe` prune the pool
  as before, and then it gives 1/k to each of the k stocks that it kept.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import run_pipeline
from quant import exact, pipeline

SECTORS = ["Tech", "Health", "Energy", "Utilities", "Materials", "Finance"]


def _many_stocks(n: int = 18, days: int = 300, seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    means = np.linspace(0.0003, 0.0015, n)
    data = rng.normal(means, 0.015, size=(days, n))
    columns = [f"T{i:02d}" for i in range(n)]
    frame = pd.DataFrame(data, columns=columns,
                         index=pd.bdate_range("2023-01-02", periods=days))
    # Six stocks lose money, so max_sharpe drops them from a pool.
    frame.iloc[:, :6] -= 0.003
    return frame


def _sectors(returns: pd.DataFrame) -> dict[str, str]:
    return {t: SECTORS[i % len(SECTORS)] for i, t in enumerate(returns)}


def _pool_params(**changes) -> pipeline.PortfolioParams:
    settings = {"optimizer": "exact", "size_mode": "pool", "pool_size": 15,
                "max_per_sector": 3}
    settings.update(changes)
    return pipeline.PortfolioParams(**settings)


# --- the objective equal_weight ----------------------------------------------

def test_equal_weight_is_an_objective():
    assert "equal_weight" in exact.OBJECTIVES


def test_equal_weight_gives_one_over_n_and_the_true_measures():
    returns = _many_stocks(n=7)
    result = exact.solve(returns, "equal_weight", 0.02, 0.25)
    assert list(result["weights"]) == list(returns.columns)
    for weight in result["weights"].values():
        assert weight == pytest.approx(1 / 7, abs=1e-15)
    daily = returns.mean(axis=1)
    assert result["annual_return"] == pytest.approx(daily.mean() * 252)
    assert result["annual_volatility"] == pytest.approx(
        daily.std() * np.sqrt(252))


def test_equal_weight_in_the_pool_mode_holds_the_whole_pool():
    returns = _many_stocks()
    params = _pool_params(objective="equal_weight")
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    assert len(result["pool"]) == 15
    assert set(result["selected"]) == set(result["pool"])
    for weight in result["weights"].values():
        assert weight == pytest.approx(1 / 15, abs=1e-15)


# --- equal weights on the stocks that the optimizer kept ---------------------

def test_the_default_keeps_the_weights_of_the_objective():
    assert pipeline.PortfolioParams().kept_weighting == "objective"


def test_kept_weighting_equal_keeps_the_names_of_max_sharpe():
    returns = _many_stocks()
    sector_of = _sectors(returns)
    solved = pipeline.build_max_sharpe_portfolio(returns, sector_of,
                                                 _pool_params())
    equal = pipeline.build_max_sharpe_portfolio(
        returns, sector_of, _pool_params(kept_weighting="equal"))
    kept = list(solved["weights"])
    # The pruning must drop a stock, or the test cannot see the difference.
    assert len(kept) < len(solved["pool"])
    assert list(equal["weights"]) == kept
    assert equal["selected"] == solved["selected"]
    assert equal["pool"] == solved["pool"]
    for weight in equal["weights"].values():
        assert weight == pytest.approx(1 / len(kept), abs=1e-15)
    daily = returns[kept].mean(axis=1)
    assert equal["annual_return"] == pytest.approx(daily.mean() * 252)
    assert equal["sharpe"] != pytest.approx(solved["sharpe"])


def test_the_backtest_builder_uses_the_kept_weighting():
    returns = _many_stocks()
    sector_of = _sectors(returns)
    params = _pool_params(kept_weighting="equal")
    build = pipeline.make_builder(sector_of, params, benchmark="SPY")
    live = pipeline.build_max_sharpe_portfolio(
        pipeline.lookback_window(returns, params), sector_of, params)
    assert build(returns) == live["weights"]


def test_kept_weighting_needs_the_exact_pool_mode():
    returns = _many_stocks(n=10)
    with pytest.raises(ValueError, match="kept_weighting"):
        exact.optimize_weights(returns, pipeline.PortfolioParams(
            kept_weighting="equal"))
    with pytest.raises(ValueError, match="kept_weighting"):
        exact.optimize_weights(returns, pipeline.PortfolioParams(
            optimizer="exact", kept_weighting="equal"))
    with pytest.raises(ValueError, match="kept_weighting"):
        exact.optimize_weights(returns, _pool_params(kept_weighting="none"))


# --- the command line and the log --------------------------------------------

def test_the_parser_carries_the_equal_weight_settings():
    args = run_pipeline.make_parser().parse_args(
        ["--optimizer", "exact", "--size-mode", "pool", "--pool-size", "33",
         "--kept-weighting", "equal"])
    params = run_pipeline.params_from_args(args)
    assert params.kept_weighting == "equal"
    args = run_pipeline.make_parser().parse_args(
        ["--optimizer", "exact", "--objective", "equal_weight"])
    assert run_pipeline.params_from_args(args).objective == "equal_weight"


def test_the_log_label_names_the_equal_weight_controls():
    params = _pool_params(objective="equal_weight", pool_size=33)
    assert exact.optimizer_label(params) == \
        "exact equal_weight 2-25% pool33"
    params = _pool_params(kept_weighting="equal", pool_size=33)
    assert exact.optimizer_label(params) == \
        "exact max_sharpe 2-25% pool33 kept-equal"
