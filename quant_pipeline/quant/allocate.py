"""Change portfolio weights to whole shares.

The optimizer gives a weight for each stock. The weight is a fraction of
the money. This module buys whole shares with that money. A person cannot
buy part of a share, so the plan always rounds the share count down.
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


def allocation_summary(weights: dict[str, float], prices: dict[str, float],
                       investment_amount: float) -> pd.DataFrame:
    """Build a table of the final plan.

    The table has the weight, the price, the shares, the cost, and the
    actual weight. The actual weight is the real share of the money spent.
    """
    plan = allocate_shares(weights, prices, investment_amount)
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
