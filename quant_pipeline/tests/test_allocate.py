"""Tests for the share allocation.

The allocator turns portfolio weights into whole shares. It uses the latest
price of each stock and a fixed amount of money.
"""

from __future__ import annotations

import pytest

from quant import allocate


def test_allocate_shares_uses_floor_of_the_budget():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 100.0, "B": 50.0}
    plan = allocate.allocate_shares(weights, prices, investment_amount=1000.0)

    # A gets 500 dollars at 100 each, so 5 shares. B gets 500 at 50, so 10.
    assert plan["A"]["shares"] == 5
    assert plan["B"]["shares"] == 10
    assert plan["A"]["cost"] == pytest.approx(500.0)
    assert plan["B"]["cost"] == pytest.approx(500.0)


def test_allocate_shares_rounds_down_partial_shares():
    weights = {"A": 1.0}
    prices = {"A": 300.0}
    plan = allocate.allocate_shares(weights, prices, investment_amount=1000.0)
    # 1000 / 300 = 3.33, so the plan buys 3 whole shares.
    assert plan["A"]["shares"] == 3
    assert plan["A"]["cost"] == pytest.approx(900.0)


def test_allocation_summary_reports_actual_weights():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 100.0, "B": 50.0}
    summary = allocate.allocation_summary(weights, prices,
                                          investment_amount=1000.0)
    total_cost = summary["cost"].sum()
    assert total_cost == pytest.approx(1000.0)
    # The actual weight is the cost of a stock over the total cost.
    assert summary.loc[summary["ticker"] == "A", "actual_weight"].iloc[0] == \
        pytest.approx(0.5)
