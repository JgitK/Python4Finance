"""Tests for the random-selection null benchmark.

SPY says whether the pipeline beats the market. It does not say whether
the ranking adds anything. The null keeps every other step of the method
and removes only the rank order: it sends the same candidates to the same
greedy selector in a random order. If the real method does not stand out
from a few hundred such draws, the rank order is decoration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant import null_benchmark, pipeline, universe


def _returns() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    index = pd.bdate_range("2024-01-01", periods=300)
    columns = [f"S{i:02d}" for i in range(12)] + [universe.BENCHMARK]
    data = rng.normal(0.0005, 0.012, size=(len(index), len(columns)))
    return pd.DataFrame(data, index=index, columns=columns)


def _sector_of() -> dict[str, str]:
    names = [f"S{i:02d}" for i in range(12)]
    return {name: f"Sector{i % 4}" for i, name in enumerate(names)}


def _params() -> pipeline.PortfolioParams:
    return pipeline.PortfolioParams(target_size=4, max_per_sector=1,
                                    n_portfolios=40, seed=5)


# ---------------------------------------------------------------------------
# The shuffled build.


def test_a_random_order_selects_a_different_portfolio():
    returns, sector_of, params = _returns(), _sector_of(), _params()
    ranked = pipeline.build_max_sharpe_portfolio(
        returns.drop(columns=[universe.BENCHMARK]), sector_of, params)
    shuffled = pipeline.build_max_sharpe_portfolio(
        returns.drop(columns=[universe.BENCHMARK]), sector_of, params,
        rng=np.random.default_rng(1))
    assert ranked["selected"] != shuffled["selected"]


def test_a_random_order_keeps_the_sector_cap():
    returns, sector_of, params = _returns(), _sector_of(), _params()
    for seed in range(8):
        result = pipeline.build_max_sharpe_portfolio(
            returns.drop(columns=[universe.BENCHMARK]), sector_of, params,
            rng=np.random.default_rng(seed))
        counts = pipeline.sector_mix(result["selected"], sector_of)
        assert max(counts.values()) <= params.max_per_sector
        assert len(result["selected"]) <= params.target_size


def test_a_random_order_draws_from_the_same_pool():
    # The null must not reach a stock that the ranked build could not see.
    returns, sector_of, params = _returns(), _sector_of(), _params()
    pool = set(returns.columns) - {universe.BENCHMARK}
    result = pipeline.build_max_sharpe_portfolio(
        returns.drop(columns=[universe.BENCHMARK]), sector_of, params,
        rng=np.random.default_rng(2))
    assert set(result["selected"]) <= pool


def test_the_same_seed_gives_the_same_random_portfolio():
    returns, sector_of, params = _returns(), _sector_of(), _params()
    first = pipeline.build_max_sharpe_portfolio(
        returns.drop(columns=[universe.BENCHMARK]), sector_of, params,
        rng=np.random.default_rng(7))["selected"]
    second = pipeline.build_max_sharpe_portfolio(
        returns.drop(columns=[universe.BENCHMARK]), sector_of, params,
        rng=np.random.default_rng(7))["selected"]
    assert first == second


# ---------------------------------------------------------------------------
# The percentile of the real method inside the null distribution.


def test_percentile_of_reads_the_share_below_the_value():
    assert null_benchmark.percentile_of(5.0, [1.0, 2.0, 3.0, 4.0]) == 1.0
    assert null_benchmark.percentile_of(0.0, [1.0, 2.0, 3.0, 4.0]) == 0.0
    assert null_benchmark.percentile_of(2.5, [1.0, 2.0, 3.0, 4.0]) == 0.5


def test_percentile_of_ignores_a_value_that_is_not_a_number():
    assert null_benchmark.percentile_of(2.5, [1.0, float("nan"), 4.0]) == 0.5


def test_percentile_of_an_empty_distribution_is_not_a_number():
    # numpy gives "not a number" for the mean of an empty array, and it
    # raises a warning. The function must answer without that warning, or
    # it reads the answer out of a numpy accident.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert np.isnan(null_benchmark.percentile_of(1.0, []))
        assert np.isnan(null_benchmark.percentile_of(
            1.0, [float("nan"), float("nan")]))


# ---------------------------------------------------------------------------
# The run.


def _draws(n_draws: int, seed: int = 0) -> pd.DataFrame:
    returns = _returns()
    dates = [returns.index[150]]
    return null_benchmark.run_random_selection(
        returns, dates, holding_period=60, sector_of=_sector_of(),
        params=_params(), benchmark=universe.BENCHMARK,
        screen_history=None, n_draws=n_draws, seed=seed)


def test_the_run_gives_one_row_for_each_draw():
    draws = _draws(6)
    assert len(draws) == 6
    for column in ("win_return", "win_sharpe", "median_excess", "mean_sharpe"):
        assert column in draws.columns


def test_the_draws_are_not_all_the_same():
    # A run that gives one answer every time is not a distribution.
    draws = _draws(10)
    assert draws["median_excess"].nunique() > 1


def test_the_same_seed_gives_the_same_draws():
    first = _draws(5, seed=3)["median_excess"].tolist()
    second = _draws(5, seed=3)["median_excess"].tolist()
    assert first == second


def test_a_different_seed_gives_different_draws():
    first = _draws(5, seed=3)["median_excess"].tolist()
    other = _draws(5, seed=99)["median_excess"].tolist()
    assert first != other


# ---------------------------------------------------------------------------
# The pool mode (D29, D32). The null must also work when the exact
# optimizer picks the count of stocks from a pool.


def _pool_params() -> pipeline.PortfolioParams:
    # Four sectors at two names give a pool of 8 from 12 stocks. The pool
    # is smaller than the screened set, so a random order can change it.
    return pipeline.PortfolioParams(target_size=4, max_per_sector=2,
                                    optimizer="exact", size_mode="pool",
                                    pool_size=8)


def test_a_random_order_in_the_pool_mode_selects_a_different_pool():
    returns = _returns().drop(columns=[universe.BENCHMARK])
    sector_of, params = _sector_of(), _pool_params()
    ranked = pipeline.build_max_sharpe_portfolio(returns, sector_of, params)
    pools = [pipeline.build_max_sharpe_portfolio(
        returns, sector_of, params, rng=np.random.default_rng(seed))["pool"]
        for seed in range(6)]
    assert any(set(pool) != set(ranked["pool"]) for pool in pools)


def test_a_random_pool_has_the_pool_size_and_not_the_target_size():
    returns = _returns().drop(columns=[universe.BENCHMARK])
    sector_of, params = _sector_of(), _pool_params()
    for seed in range(4):
        result = pipeline.build_max_sharpe_portfolio(
            returns, sector_of, params, rng=np.random.default_rng(seed))
        assert len(result["pool"]) == params.pool_size
        assert set(result["selected"]) <= set(result["pool"])
        counts = pipeline.sector_mix(result["pool"], sector_of)
        assert max(counts.values()) <= params.max_per_sector


def test_the_null_run_keeps_the_pool_mode():
    # The draws of the pool mode must differ from the draws of the fixed
    # mode with the same seed. If the run drops the pool settings, the two
    # sets of draws are the same.
    returns = _returns()
    dates = [returns.index[150], returns.index[200]]
    pool = null_benchmark.run_random_selection(
        returns, dates, holding_period=60, sector_of=_sector_of(),
        params=_pool_params(), benchmark=universe.BENCHMARK,
        n_draws=4, seed=0)
    fixed_params = pipeline.PortfolioParams(target_size=4, max_per_sector=2,
                                            n_portfolios=40, seed=5)
    fixed = null_benchmark.run_random_selection(
        returns, dates, holding_period=60, sector_of=_sector_of(),
        params=fixed_params, benchmark=universe.BENCHMARK,
        n_draws=4, seed=0)
    assert pool["mean_excess"].tolist() != fixed["mean_excess"].tolist()
