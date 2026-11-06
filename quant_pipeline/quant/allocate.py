"""Change portfolio weights to whole shares.

The optimizer gives a weight for each stock. The weight is a fraction of
the money. This module buys whole shares with that money. A person cannot
buy part of a share, so the first pass rounds each share count down.

The first pass alone leaves cash, and it moves the portfolio away from the
weights of the optimizer. An expensive share loses more of its weight than
a cheap one, because the money that it cannot use is larger. A second pass
spends that cash: it buys one more share at a time, and each step takes
the share that moves the weights nearest to the target. See decision D17.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


def allocate_shares(weights: dict[str, float], prices: dict[str, float],
                    investment_amount: float) -> dict[str, dict[str, float]]:
    """Buy whole shares for each stock.

    Give each stock its share of the money. Divide by the price. Round down.
    Return the share count and the cash cost for each stock.
    """
    plan: dict[str, dict[str, float]] = {}
    for ticker, weight in weights.items():
        budget = investment_amount * weight
        shares = int(math.floor(budget / prices[ticker]))
        plan[ticker] = {"shares": shares, "cost": shares * prices[ticker]}
    return plan


def weight_error(plan: dict[str, dict[str, float]],
                 weights: dict[str, float],
                 investment_amount: float) -> float:
    """Measure the distance between the plan and the target weights.

    The actual weight of a stock is its cost over the investment amount,
    not over the money spent. The cash that the plan does not spend is
    therefore an error. Without that rule, a plan that buys nothing has no
    error, and the top-up pass has no reason to buy a share.

    The measure is the sum of the squared differences.
    """
    return float(sum(
        (plan[ticker]["cost"] / investment_amount - weight) ** 2
        for ticker, weight in weights.items()))


def top_up_shares(plan: dict[str, dict[str, float]],
                  weights: dict[str, float], prices: dict[str, float],
                  investment_amount: float
                  ) -> dict[str, dict[str, float]]:
    """Spend the cash that the first pass leaves.

    Buy one more share at a time. Each step takes the share that lowers
    the weight error by the largest amount. Stop when no share is
    affordable, and stop when no share lowers the error. A share that
    takes a stock further from its target than the cash does is not a
    better plan, so the pass does not buy it.

    The ticker order is alphabetic, so a tie gives the same plan on every
    run.
    """
    plan = {ticker: dict(position) for ticker, position in plan.items()}
    while True:
        spent = sum(position["cost"] for position in plan.values())
        cash = investment_amount - spent
        best_ticker = None
        best_error = weight_error(plan, weights, investment_amount)
        for ticker in sorted(weights):
            if prices[ticker] > cash:
                continue
            shares = plan[ticker]["shares"] + 1
            trial = dict(plan)
            trial[ticker] = {"shares": shares,
                             "cost": shares * prices[ticker]}
            error = weight_error(trial, weights, investment_amount)
            # The margin keeps a rounding difference from a purchase.
            if error < best_error - 1e-15:
                best_ticker, best_error = ticker, error
        if best_ticker is None:
            return plan
        plan[best_ticker]["shares"] += 1
        plan[best_ticker]["cost"] = (plan[best_ticker]["shares"]
                                     * prices[best_ticker])


def minimum_investment(weights: dict[str, float],
                       prices: dict[str, float]) -> float:
    """Return the smallest amount of money that can hold every weight.

    One share of a stock is a step. The step is the price of the share
    over the investment amount. When the step is larger than the target
    weight of the stock, no plan of whole shares can hold that weight: the
    plan must hold 0 shares, or more than the target.

    The smallest amount that keeps each step inside its target weight is
    therefore the largest price divided by its weight.
    """
    return max(prices[ticker] / weight
               for ticker, weight in weights.items() if weight > 0)


def plan_warnings(shares: dict[str, int], weights: dict[str, float],
                  prices: dict[str, float],
                  investment_amount: float) -> list[str]:
    """List the weights that the plan cannot hold.

    A plan of whole shares cannot always hold the weights of the
    optimizer. The investment amount can be too small for the price of a
    share. The plan then drops a stock, or it holds more of a stock than
    the target. The top-up pass cannot repair this, because a part of a
    share does not exist.

    Return one sentence for each stock with such a problem, then one
    sentence with the smallest amount that has no such problem. Return an
    empty list when the plan holds every weight. The order is alphabetic,
    so the list is the same on every run.
    """
    dropped, above = [], []
    for ticker in sorted(weights):
        weight = weights[ticker]
        if weight <= 0:
            continue
        step = prices[ticker] / investment_amount
        if shares.get(ticker, 0) == 0:
            dropped.append(
                f"The plan drops {ticker}. Its target weight is "
                f"{weight:.1%}, and one share costs "
                f"{prices[ticker]:,.2f}, which is {step:.1%} of the money.")
        elif step > weight:
            held = shares[ticker] * step
            above.append(
                f"{ticker} holds {held:.1%} of the money against a target "
                f"of {weight:.1%}. One share is {step:.1%}, so the plan "
                f"cannot hold less.")
    if not dropped and not above:
        return []
    smallest = minimum_investment(weights, prices)
    return dropped + above + [
        f"Invest at least {smallest:,.2f} to hold every stock at its "
        f"target weight. A smaller amount needs fewer stocks."]


def allocation_summary(weights: dict[str, float], prices: dict[str, float],
                       investment_amount: float,
                       top_up: bool = True) -> pd.DataFrame:
    """Build a table of the final plan.

    The table has the weight, the price, the shares, the cost, and the
    actual weight. The actual weight is the real share of the money spent.

    The plan runs the top-up pass. Use `top_up=False` for the first pass
    alone.
    """
    plan = allocate_shares(weights, prices, investment_amount)
    if top_up:
        plan = top_up_shares(plan, weights, prices, investment_amount)
    rows = [
        {
            "ticker": ticker,
            "target_weight": weights[ticker],
            "price": prices[ticker],
            "shares": plan[ticker]["shares"],
            "cost": plan[ticker]["cost"],
        }
        for ticker in weights
    ]
    summary = pd.DataFrame(rows)

    total_cost = summary["cost"].sum()
    # Prevent a division by zero when the plan buys no shares.
    summary["actual_weight"] = (
        summary["cost"] / total_cost if total_cost > 0 else 0.0
    )
    return summary
