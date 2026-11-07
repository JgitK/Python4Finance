"""Tests for the low-correlation portfolio selection.

The selector picks a diversified set of stocks. It avoids stocks that move
together. It also limits how many stocks come from one sector.
"""

from __future__ import annotations

import pandas as pd

from quant import select_portfolio


def _corr(frame: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Build a correlation matrix from a nested dict."""
    return pd.DataFrame(frame)


def test_average_correlation_is_zero_for_empty_selection():
    corr = _corr({"A": {"A": 1.0}})
    assert select_portfolio.average_correlation("A", [], corr) == 0.0


def test_selector_skips_a_highly_correlated_stock():
    # A and B move together. The selector must keep A and skip B.
    candidates = [
        {"ticker": "A", "sector": "Tech"},
        {"ticker": "B", "sector": "Health"},
        {"ticker": "C", "sector": "Energy"},
    ]
    corr = _corr({
        "A": {"A": 1.0, "B": 0.95, "C": 0.10},
        "B": {"A": 0.95, "B": 1.0, "C": 0.10},
        "C": {"A": 0.10, "B": 0.10, "C": 1.0},
    })
    selected = select_portfolio.greedy_low_correlation(
        candidates, corr, target_size=12, max_per_sector=3,
        max_avg_correlation=0.6,
    )
    assert selected == ["A", "C"]


def test_selector_limits_stocks_per_sector():
    # Three Tech stocks, all uncorrelated, but only two can come from Tech.
    candidates = [
        {"ticker": "T1", "sector": "Tech"},
        {"ticker": "T2", "sector": "Tech"},
        {"ticker": "T3", "sector": "Tech"},
        {"ticker": "E1", "sector": "Energy"},
    ]
    corr = _corr({t: {u: (1.0 if t == u else 0.0) for u in
                      ["T1", "T2", "T3", "E1"]}
                  for t in ["T1", "T2", "T3", "E1"]})
    selected = select_portfolio.greedy_low_correlation(
        candidates, corr, target_size=12, max_per_sector=2,
        max_avg_correlation=0.6,
    )
    # The selector drops T3 because Tech already has two names.
    assert selected == ["T1", "T2", "E1"]


def test_selector_stops_at_target_size():
    candidates = [{"ticker": f"S{i}", "sector": f"Sec{i}"} for i in range(10)]
    corr = _corr({a["ticker"]: {b["ticker"]: (1.0 if a is b else 0.0)
                                for b in candidates} for a in candidates})
    selected = select_portfolio.greedy_low_correlation(
        candidates, corr, target_size=4, max_per_sector=3,
        max_avg_correlation=0.6,
    )
    assert len(selected) == 4


# ---------------------------------------------------------------------------
# One place holds the default (D21).


def test_the_selector_has_no_cap_default_of_its_own():
    # The caps lived in two places: PortfolioParams and the signature of
    # this function. Two defaults can drift, and then the live run and a
    # direct caller select different portfolios. PortfolioParams is the one
    # place, so each cap of this function must be a required parameter.
    import inspect

    signature = inspect.signature(select_portfolio.greedy_low_correlation)
    for name in ("target_size", "max_per_sector"):
        assert signature.parameters[name].default is inspect.Parameter.empty
