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


# ---------------------------------------------------------------------------
# The warnings of a plan.
#
# Whole shares cannot always hold the weights of the optimizer. One share
# of a stock is a step, and the step is the price over the investment
# amount. When the step is larger than the target weight of the stock, the
# plan must hold 0 shares or more than the target. No top-up pass can
# repair that. The plan must say so.


def test_a_plan_that_holds_every_weight_gives_no_warning():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 10.0, "B": 10.0}
    shares = {"A": 5, "B": 4}
    assert allocate.plan_warnings(shares, weights, prices, 95.0) == []


def test_a_warning_names_each_stock_that_the_plan_drops():
    weights = {"A": 0.9, "B": 0.1}
    prices = {"A": 10.0, "B": 200.0}
    shares = {"A": 9, "B": 0}
    warnings = allocate.plan_warnings(shares, weights, prices, 100.0)
    dropped = [w for w in warnings if w.startswith("The plan drops")]
    assert len(dropped) == 1
    assert "B" in dropped[0]
    # The warning must give the target weight and the cost of one share.
    assert "10.0%" in dropped[0] and "200.00" in dropped[0]


def test_a_warning_names_each_stock_above_its_target():
    # One share of A is 30% of the money, and the target is 10%. The plan
    # holds one share, so A is 20 points above its target. The plan cannot
    # hold less than one share, so this is not a mistake of the top-up.
    weights = {"A": 0.1, "B": 0.9}
    prices = {"A": 300.0, "B": 100.0}
    shares = {"A": 1, "B": 7}
    warnings = allocate.plan_warnings(shares, weights, prices, 1000.0)
    above = [w for w in warnings if w.startswith("A holds")]
    assert len(above) == 1
    assert "30.0%" in above[0] and "10.0%" in above[0]


def test_the_warnings_give_the_smallest_investment_amount():
    # One share of a stock must not be larger than the target weight of
    # that stock. The smallest amount that holds this rule for every stock
    # is the largest price divided by its weight: 200 / 0.1 = 2000.
    weights = {"A": 0.9, "B": 0.1}
    prices = {"A": 10.0, "B": 200.0}
    assert allocate.minimum_investment(weights, prices) == pytest.approx(2000.0)
    warnings = allocate.plan_warnings({"A": 9, "B": 0}, weights, prices, 100.0)
    assert any("2,000.00" in w for w in warnings)


def test_the_warnings_are_in_the_same_order_on_every_run():
    weights = {"C": 0.05, "A": 0.9, "B": 0.05}
    prices = {"A": 10.0, "B": 200.0, "C": 300.0}
    shares = {"A": 9, "B": 0, "C": 0}
    first = allocate.plan_warnings(shares, weights, prices, 100.0)
    second = allocate.plan_warnings(
        {t: shares[t] for t in reversed(list(shares))},
        {t: weights[t] for t in reversed(list(weights))}, prices, 100.0)
    assert first == second
    # The dropped stocks come in alphabetic order.
    assert "B" in first[0] and "C" in first[1]


def test_a_small_amount_gives_warnings_and_a_large_amount_does_not():
    # The same stocks and the same weights, with two amounts of money.
    weights = {"BIG": 0.12, "MID": 0.28, "SMALL": 0.60}
    prices = {"BIG": 445.0, "MID": 150.0, "SMALL": 19.0}
    for amount, expected in ((2500.0, True), (50000.0, False)):
        plan = allocate.allocation_summary(weights, prices, amount)
        shares = dict(zip(plan["ticker"], plan["shares"]))
        warnings = allocate.plan_warnings(shares, weights, prices, amount)
        assert bool(warnings) is expected
