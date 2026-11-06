"""Tests for the share allocation.

The allocator changes portfolio weights to whole shares. It uses the latest
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


# ---------------------------------------------------------------------------
# The top-up pass.
#
# The floor pass gives each stock its share of the money and rounds the
# share count down. The money that stays is dead cash, and the rounding
# moves the portfolio away from the weights of the optimizer: an expensive
# stock loses more of its weight than a cheap one. The top-up pass spends
# that cash on the shares that move the weights back.


def test_top_up_buys_a_share_when_it_moves_the_weights_closer():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 10.0, "B": 10.0}
    # The floor pass buys 4 shares of each stock and leaves 15 dollars.
    floor = allocate.allocate_shares(weights, prices, 95.0)
    assert (floor["A"]["shares"], floor["B"]["shares"]) == (4, 4)

    plan = allocate.top_up_shares(floor, weights, prices, 95.0)
    # One more share of A costs 10 of the 15 dollars, and it moves A from
    # 42.1% to 52.6% of the money. B then has no cash for a fifth share.
    assert (plan["A"]["shares"], plan["B"]["shares"]) == (5, 4)
    assert sum(p["cost"] for p in plan.values()) == pytest.approx(90.0)


def test_top_up_does_not_buy_a_share_that_overshoots_the_target():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 30.0, "B": 10.0}
    # The floor pass buys 1 share of A and 5 of B, and leaves 20 dollars.
    floor = allocate.allocate_shares(weights, prices, 100.0)
    plan = allocate.top_up_shares(floor, weights, prices, 100.0)
    # A costs more than the cash. A sixth share of B would take B to 60%,
    # which is further from the target than the 20 dollars of cash.
    assert plan == floor


def test_top_up_never_spends_more_than_the_investment_amount():
    weights = {"A": 0.3, "B": 0.3, "C": 0.4}
    prices = {"A": 7.0, "B": 13.0, "C": 101.0}
    for amount in (500.0, 1000.0, 2500.0, 10000.0):
        floor = allocate.allocate_shares(weights, prices, amount)
        plan = allocate.top_up_shares(floor, weights, prices, amount)
        assert sum(p["cost"] for p in plan.values()) <= amount


def test_top_up_lowers_the_weight_error():
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}
    prices = {"A": 417.0, "B": 19.0, "C": 52.0}
    floor = allocate.allocate_shares(weights, prices, 10000.0)
    plan = allocate.top_up_shares(floor, weights, prices, 10000.0)
    before = allocate.weight_error(floor, weights, 10000.0)
    after = allocate.weight_error(plan, weights, 10000.0)
    assert after < before
    # The cash must fall too.
    assert (sum(p["cost"] for p in plan.values())
            > sum(p["cost"] for p in floor.values()))


def test_the_weight_error_counts_the_cash_that_the_plan_does_not_spend():
    # The actual weight uses the investment amount, not the money spent.
    # A plan that holds cash is therefore an error. Without this rule, a
    # plan that buys nothing has no error at all.
    weights = {"A": 1.0}
    prices = {"A": 10.0}
    nothing = {"A": {"shares": 0, "cost": 0.0}}
    everything = {"A": {"shares": 10, "cost": 100.0}}
    assert allocate.weight_error(nothing, weights, 100.0) == pytest.approx(1.0)
    assert allocate.weight_error(everything, weights, 100.0) == \
        pytest.approx(0.0)


def test_allocation_summary_tops_up_by_default():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 10.0, "B": 10.0}
    summary = allocate.allocation_summary(weights, prices, 95.0)
    assert summary["cost"].sum() == pytest.approx(90.0)
    # The floor pass alone leaves 15 dollars of the 95.
    floor_only = allocate.allocation_summary(weights, prices, 95.0,
                                             top_up=False)
    assert floor_only["cost"].sum() == pytest.approx(80.0)


def test_the_top_up_is_the_same_on_every_run():
    # Two stocks with the same price and the same weight are a tie. The
    # plan must not depend on the order of a dictionary, so each run gives
    # the same plan.
    weights = {"B": 0.5, "A": 0.5}
    prices = {"A": 10.0, "B": 10.0}
    first = allocate.allocation_summary(weights, prices, 95.0)
    second = allocate.allocation_summary(dict(reversed(weights.items())),
                                         prices, 95.0)
    shares = {r.ticker: r.shares for r in first.itertuples()}
    assert shares == {r.ticker: r.shares for r in second.itertuples()}
    assert shares == {"A": 5, "B": 4}
