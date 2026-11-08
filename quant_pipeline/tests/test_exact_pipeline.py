"""Tests for the exact optimizers inside the portfolio build (D29).

The build step selects the stocks and then weights them. These tests check
that the settings reach the optimizer, that the live run and the backtest
use the same optimizer, and that the command line carries the settings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import run_pipeline
from quant import exact, pipeline

SECTORS = ["Tech", "Health", "Energy", "Utilities", "Materials", "Finance"]


def _many_stocks(n: int = 18, days: int = 300, seed: int = 2) -> pd.DataFrame:
    """Make n stocks with low correlation, three in each sector."""
    rng = np.random.default_rng(seed)
    means = np.linspace(0.0003, 0.0015, n)
    data = rng.normal(means, 0.015, size=(days, n))
    columns = [f"T{i:02d}" for i in range(n)]
    return pd.DataFrame(data, columns=columns,
                        index=pd.bdate_range("2023-01-02", periods=days))


def _sectors(returns: pd.DataFrame) -> dict[str, str]:
    return {t: SECTORS[i % len(SECTORS)] for i, t in enumerate(returns)}


# --- the settings ------------------------------------------------------------

def test_the_defaults_keep_the_monte_carlo_search_and_ten_stocks():
    # D29 does not choose a new default. The user decides.
    default = pipeline.PortfolioParams()
    assert default.optimizer == "monte_carlo"
    assert default.objective == "max_sharpe"
    assert default.size_mode == "fixed"
    assert default.min_weight == 0.02
    assert default.max_weight == 0.25
    assert default.pool_size == 25


def test_the_monte_carlo_search_refuses_another_objective():
    params = pipeline.PortfolioParams(objective="min_cvar")
    with pytest.raises(ValueError, match="monte_carlo"):
        exact.optimize_weights(_many_stocks(n=4), params)


def test_the_monte_carlo_search_refuses_the_pool_mode():
    params = pipeline.PortfolioParams(size_mode="pool")
    with pytest.raises(ValueError, match="monte_carlo"):
        exact.optimize_weights(_many_stocks(n=4), params)


def test_an_unknown_optimizer_or_size_mode_raises():
    with pytest.raises(ValueError, match="optimizer"):
        exact.optimize_weights(_many_stocks(n=4), pipeline.PortfolioParams(
            optimizer="genetic"))
    with pytest.raises(ValueError, match="size_mode"):
        exact.optimize_weights(_many_stocks(n=4), pipeline.PortfolioParams(
            optimizer="exact", size_mode="auto"))


# --- the build step ----------------------------------------------------------

def test_the_default_build_still_uses_the_monte_carlo_search():
    returns = _many_stocks()
    params = pipeline.PortfolioParams(n_portfolios=300, seed=1)
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    direct = exact.optimize_weights(returns[result["selected"]], params)
    assert result["weights"] == direct["weights"]
    assert len(result["frontier"]) == 300


@pytest.mark.parametrize("objective", exact.OBJECTIVES)
def test_the_exact_build_holds_the_bounds_and_the_size(objective):
    returns = _many_stocks()
    params = pipeline.PortfolioParams(optimizer="exact", objective=objective)
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    weights = np.array(list(result["weights"].values()))
    assert len(weights) == params.target_size
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    assert weights.min() >= params.min_weight - 1e-12
    assert weights.max() <= params.max_weight + 1e-12
    assert result["objective"] == objective


def test_the_exact_build_solves_the_objective_on_the_selection():
    returns = _many_stocks()
    params = pipeline.PortfolioParams(optimizer="exact",
                                      objective="min_variance")
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    direct = exact.solve(returns[result["selected"]], "min_variance",
                         params.min_weight, params.max_weight)
    assert result["weights"] == direct["weights"]


def test_the_pool_mode_selects_a_pool_and_keeps_part_of_it():
    returns = _many_stocks()
    # Six stocks lose money, so a floor of 0 drops them.
    returns.iloc[:, :6] -= 0.003
    params = pipeline.PortfolioParams(optimizer="exact", size_mode="pool",
                                      pool_size=15, max_per_sector=3)
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    assert len(result["pool"]) == 15
    assert set(result["selected"]) == set(result["weights"])
    assert set(result["selected"]) < set(result["pool"])
    assert len(result["selected"]) != params.target_size
    weights = np.array(list(result["weights"].values()))
    assert weights.min() >= params.min_weight - 1e-12
    assert weights.max() <= params.max_weight + 1e-12


def test_the_pool_respects_the_sector_cap():
    returns = _many_stocks()
    params = pipeline.PortfolioParams(optimizer="exact", size_mode="pool",
                                      pool_size=18, max_per_sector=2)
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    # Six sectors at two stocks each give a pool of 12, not 18.
    assert len(result["pool"]) == 12
    counts = pipeline.sector_mix(result["selected"], _sectors(returns))
    assert max(counts.values()) <= 2


def test_the_backtest_builder_uses_the_same_optimizer_as_the_live_build():
    returns = _many_stocks()
    sector_of = _sectors(returns)
    params = pipeline.PortfolioParams(optimizer="exact",
                                      objective="max_sortino")
    build = pipeline.make_builder(sector_of, params, benchmark="SPY")
    live = pipeline.build_max_sharpe_portfolio(
        pipeline.lookback_window(returns, params), sector_of, params)
    assert build(returns) == live["weights"]


# --- the command line --------------------------------------------------------

def test_the_parser_defaults_match_the_portfolio_params():
    args = run_pipeline.make_parser().parse_args([])
    params = run_pipeline.params_from_args(args)
    assert params == pipeline.PortfolioParams()


def test_the_parser_carries_the_optimizer_settings():
    args = run_pipeline.make_parser().parse_args(
        ["--optimizer", "exact", "--objective", "min_cvar",
         "--min-weight", "0.01", "--max-weight", "0.3",
         "--size-mode", "pool", "--pool-size", "15"])
    params = run_pipeline.params_from_args(args)
    assert params.optimizer == "exact"
    assert params.objective == "min_cvar"
    assert params.min_weight == 0.01
    assert params.max_weight == 0.3
    assert params.size_mode == "pool"
    assert params.pool_size == 15


def test_the_parser_refuses_an_unknown_objective():
    with pytest.raises(SystemExit):
        run_pipeline.make_parser().parse_args(["--objective", "max_return"])


def test_the_log_label_is_empty_for_the_default():
    # The rank cell of an old row must keep its meaning.
    assert exact.optimizer_label(pipeline.PortfolioParams()) == ""


def test_the_log_label_names_the_exact_settings():
    params = pipeline.PortfolioParams(optimizer="exact", objective="min_cvar")
    assert exact.optimizer_label(params) == "exact min_cvar 2-25% fixed"
    params = pipeline.PortfolioParams(optimizer="exact", size_mode="pool",
                                      pool_size=15)
    assert exact.optimizer_label(params) == "exact max_sharpe 2-25% pool15"


def test_the_count_of_stocks_in_each_window():
    windows = [{"weights": {"A": .5, "B": .5}}, {"weights": {}},
               {"weights": {"A": .2, "B": .3, "C": .5}},
               {"weights": {"A": .5, "C": .5}}]
    assert exact.count_distribution(windows) == {2: 2, 3: 1}
