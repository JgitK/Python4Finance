"""Tests for the pipeline composition.

The pipeline ranks stocks, selects a diversified set, and optimizes the
weights. These tests use small synthetic returns, so they do not need a warehouse.
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
    # All three stocks sit in one sector, but the selector can choose only one.
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


# --- point-in-time screen ---------------------------------------------------
# The backtest must select from the stocks that passed the screen on the
# selection date. A screen from a later date is future data.

def _screen_history() -> pd.DataFrame:
    """Build a screen history. Each row is one stock that passed on one date."""
    return pd.DataFrame(
        {
            "as_of_date": pd.to_datetime(
                ["2023-06-01", "2023-06-01", "2024-01-02", "2024-01-02"]
            ),
            "ticker": ["BBB", "CCC", "AAA", "BBB"],
        }
    )


def test_candidates_as_of_uses_the_latest_screen_on_or_before_the_date():
    history = _screen_history()
    # On 2023-09-01, the latest screen is the screen of 2023-06-01.
    assert pipeline.candidates_as_of(history, "2023-09-01") == ["BBB", "CCC"]
    # On the screen date itself, that screen applies.
    assert pipeline.candidates_as_of(history, "2024-01-02") == ["AAA", "BBB"]


def test_candidates_as_of_is_empty_before_the_first_screen():
    history = _screen_history()
    assert pipeline.candidates_as_of(history, "2023-01-01") == []


def test_make_builder_selects_only_stocks_that_passed_the_screen_then():
    returns = _three_stocks()  # 2023-01-02 to late 2026.
    train = returns[returns.index <= "2023-09-01"]
    sector_of = {"AAA": "Tech", "BBB": "Health", "CCC": "Energy"}
    build = pipeline.make_builder(
        sector_of, pipeline.PortfolioParams(n_portfolios=500, seed=1),
        benchmark="SPY", screen_history=_screen_history(),
    )
    weights = build(train)
    # AAA has the best Sharpe ratio, but it passed the screen only in 2024.
    # On 2023-09-01, the builder must not know that AAA passes later.
    assert "AAA" not in weights
    assert set(weights) <= {"BBB", "CCC"}


def test_make_builder_returns_no_weights_when_no_stock_passed():
    returns = _three_stocks()
    train = returns[returns.index <= "2023-03-01"]
    build = pipeline.make_builder(
        {"AAA": "Tech", "BBB": "Health", "CCC": "Energy"},
        pipeline.PortfolioParams(n_portfolios=500, seed=1),
        benchmark="SPY", screen_history=_screen_history(),
    )
    assert build(train) == {}


# --- lookback window --------------------------------------------------------
# The live run and the backtest must select and weight the stocks from the
# same window: the last lookback_days rows up to the selection date.

def test_lookback_window_keeps_only_the_last_rows():
    returns = _three_stocks()
    params = pipeline.PortfolioParams(lookback_days=252)
    window = pipeline.lookback_window(returns, params)
    assert len(window) == 252
    assert window.index[-1] == returns.index[-1]


def test_lookback_window_drops_a_stock_with_a_gap_inside_the_window():
    returns = _three_stocks()
    returns.iloc[-10, returns.columns.get_loc("BBB")] = np.nan
    window = pipeline.lookback_window(returns, pipeline.PortfolioParams())
    assert "BBB" not in window.columns


def test_lookback_window_keeps_a_stock_with_a_gap_before_the_window():
    returns = _three_stocks()
    # A gap long before the window does not affect the window.
    returns.iloc[5, returns.columns.get_loc("BBB")] = np.nan
    window = pipeline.lookback_window(returns, pipeline.PortfolioParams())
    assert "BBB" in window.columns


def test_make_builder_uses_only_the_lookback_window(monkeypatch):
    returns = _three_stocks()
    seen = {}
    real_build = pipeline.build_max_sharpe_portfolio

    def spy(frame, *args, **kwargs):
        # Record the rows that the build step gets. This test is about the
        # window, so the spy passes every other argument through.
        seen["rows"], seen["last"] = len(frame), frame.index[-1]
        return real_build(frame, *args, **kwargs)

    monkeypatch.setattr(pipeline, "build_max_sharpe_portfolio", spy)
    params = pipeline.PortfolioParams(n_portfolios=200, seed=1, lookback_days=100)
    build = pipeline.make_builder(
        {"AAA": "Tech", "BBB": "Health", "CCC": "Energy"}, params, "SPY")
    build(returns)
    assert seen["rows"] == 100
    assert seen["last"] == returns.index[-1]


def test_lookback_equals_the_dbt_analysis_window():
    # The screen in dbt and the build step in Python must use the same year.
    import pathlib

    import yaml

    project = pathlib.Path(__file__).resolve().parents[1] / "dbt" / "dbt_project.yml"
    dbt_vars = yaml.safe_load(project.read_text())["vars"]
    assert pipeline.PortfolioParams().lookback_days == dbt_vars["analysis_window"]


# --- universe coverage --------------------------------------------------------
# The pipeline reports how many index members it drops for missing data.

def _coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "as_of_date": pd.to_datetime(
                ["2025-01-02"] * 3 + ["2025-06-02"] * 3),
            "ticker": ["AAA", "BBB", "CCC", "AAA", "BBB", "DDD"],
            "has_prices": [True, False, True, True, True, True],
            "has_sector": [True, True, False, True, True, True],
        }
    )


def test_coverage_summary_counts_the_dropped_members():
    summary = pipeline.coverage_summary(_coverage(), ["2025-01-02", "2025-06-02"])
    first = summary.iloc[0]
    assert first["members"] == 3
    assert first["usable"] == 1
    assert first["dropped"] == 2
    # BBB has no prices. CCC has no sector.
    assert first["dropped_tickers"] == "BBB CCC"
    assert summary.iloc[1]["dropped"] == 0


def test_coverage_summary_uses_the_latest_date_on_or_before_each_date():
    # 2025-03-03 is not a trading day in this data. Use 2025-01-02.
    summary = pipeline.coverage_summary(_coverage(), ["2025-03-03"])
    assert summary.iloc[0]["coverage_date"] == pd.Timestamp("2025-01-02")
    assert summary.iloc[0]["dropped"] == 2


def test_the_default_universe_is_the_sp500():
    import pathlib

    import yaml

    project = pathlib.Path(__file__).resolve().parents[1] / "dbt" / "dbt_project.yml"
    assert yaml.safe_load(project.read_text())["vars"]["universe"] == "sp500"


# ---------------------------------------------------------------------------
# The sector mix of a portfolio (D20).
#
# `top_n_per_sector` caps the candidates of each sector, so the cap also
# balances the sectors. A measurement of a larger cap must show the mix
# before and after the change.


def test_sector_mix_counts_the_stocks_of_each_sector():
    sector_of = {"AAA": "Energy", "BBB": "Energy", "CCC": "Utilities"}
    mix = pipeline.sector_mix(["AAA", "BBB", "CCC"], sector_of)
    assert mix == {"Energy": 2, "Utilities": 1}


def test_sector_mix_sorts_the_largest_sector_first():
    sector_of = {"AAA": "Utilities", "BBB": "Energy", "CCC": "Energy"}
    mix = pipeline.sector_mix(["AAA", "BBB", "CCC"], sector_of)
    assert list(mix) == ["Energy", "Utilities"]


def test_sector_mix_names_a_stock_with_no_sector_unknown():
    mix = pipeline.sector_mix(["AAA"], {})
    assert mix == {"Unknown": 1}


def test_sector_mix_of_an_empty_portfolio_is_empty():
    assert pipeline.sector_mix([], {"AAA": "Energy"}) == {}


# ---------------------------------------------------------------------------
# The default portfolio size (D21).


def test_the_default_portfolio_holds_ten_stocks():
    # The user selected 10 stocks. D20 measured 12, 24, 40 and 60, and D21
    # measured 10. A change of this number moves every new results row, so
    # this test states the value.
    default = pipeline.PortfolioParams()
    assert default.target_size == 10
    assert default.max_per_sector == 3


# ---------------------------------------------------------------------------
# The rank metric (D22).
#
# The screen and the selection rank the stocks inside each sector. The
# measure of that rank is the cumulative return of the lookback window, not
# the Sharpe ratio. dbt holds the same choice in the rank_metric variable,
# so the two layers must agree.


def _disagreeing_returns() -> pd.DataFrame:
    """Return a frame where the Sharpe order and the return order disagree.

    STEADY compounds less and it is calm, so it has the better Sharpe
    ratio. JUMPY compounds more and it is wild, so it has the better
    cumulative return.

    STEADY needs a small movement. A series of one value has a volatility
    of 0, and then the Sharpe ratio of a one-stock portfolio is not a
    number.
    """
    days = 60
    steady = [0.0025 if i % 2 else 0.0015 for i in range(days)]
    jumpy = [0.05 if i % 2 else -0.02 for i in range(days)]
    index = pd.bdate_range("2025-01-01", periods=days)
    return pd.DataFrame({"STEADY": steady, "JUMPY": jumpy}, index=index)


def test_the_two_rankings_disagree_on_this_frame():
    # A guard for the tests below. Without this property they prove nothing.
    returns = _disagreeing_returns()
    assert pipeline.rank_by_sharpe(returns)[0] == "STEADY"
    assert pipeline.rank_by_cumulative_return(returns)[0] == "JUMPY"


def test_rank_by_cumulative_return_compounds_the_window():
    returns = _disagreeing_returns()
    ranked = pipeline.rank_by_cumulative_return(returns)
    compound = (1.0 + returns).prod() - 1.0
    assert ranked == list(compound.sort_values(ascending=False).index)


def test_the_cumulative_return_is_not_the_average_return():
    # The volatility drag. DRAG has the higher average daily return and it
    # compounds to a loss, because a fall of 40% needs a rise of 67% to
    # recover. CREEP has the lower average and it compounds to a gain.
    # An average return would rank DRAG first. A compound return must not.
    days = 60
    drag = [0.50 if i % 2 else -0.40 for i in range(days)]
    creep = [0.004] * days
    index = pd.bdate_range("2025-01-01", periods=days)
    returns = pd.DataFrame({"DRAG": drag, "CREEP": creep}, index=index)

    assert returns["DRAG"].mean() > returns["CREEP"].mean()
    compound = (1.0 + returns).prod() - 1.0
    assert compound["DRAG"] < 0.0 < compound["CREEP"]
    assert pipeline.rank_by_cumulative_return(returns) == ["CREEP", "DRAG"]


def test_rank_candidates_follows_the_rank_metric():
    returns = _disagreeing_returns()
    by_return = pipeline.PortfolioParams(rank_metric="cum_return")
    by_sharpe = pipeline.PortfolioParams(rank_metric="sharpe")
    assert pipeline.rank_candidates(returns, by_return)[0] == "JUMPY"
    assert pipeline.rank_candidates(returns, by_sharpe)[0] == "STEADY"


def test_rank_candidates_refuses_an_unknown_metric():
    # A silent default would give a portfolio that nobody asked for.
    returns = _disagreeing_returns()
    params = pipeline.PortfolioParams(rank_metric="magic")
    with pytest.raises(ValueError, match="magic"):
        pipeline.rank_candidates(returns, params)


def test_the_default_rank_metric_is_the_cumulative_return():
    assert pipeline.PortfolioParams().rank_metric == "cum_return"


def test_the_build_selects_on_the_rank_metric():
    # One place of each sector, so the rank decides which stock gets it.
    returns = _disagreeing_returns()
    sector_of = {"STEADY": "Tech", "JUMPY": "Tech"}
    by_return = pipeline.PortfolioParams(
        rank_metric="cum_return", target_size=1, max_per_sector=1,
        n_portfolios=50, seed=3)
    by_sharpe = pipeline.PortfolioParams(
        rank_metric="sharpe", target_size=1, max_per_sector=1,
        n_portfolios=50, seed=3)
    assert pipeline.build_max_sharpe_portfolio(
        returns, sector_of, by_return)["selected"] == ["JUMPY"]
    assert pipeline.build_max_sharpe_portfolio(
        returns, sector_of, by_sharpe)["selected"] == ["STEADY"]
