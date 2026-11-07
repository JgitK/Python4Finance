"""Low-correlation portfolio selection.

A good portfolio holds stocks that do not move together. When one stock
falls, another may hold or rise. This smooths the return.
This module picks stocks with a greedy rule. It examines the candidates in
sequence, from best to worst. It adds a stock only when the stock is
different enough from the stocks it already holds. It also limits how many
stocks come from one sector.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def average_correlation(ticker: str, selected: list[str],
                        corr: pd.DataFrame) -> float:
    """Find the mean correlation of a stock to the chosen stocks.

    Return 0.0 when no stock is chosen yet.
    """
    if not selected:
        return 0.0
    values = [corr.loc[ticker, other] for other in selected]
    return float(np.mean(values))


def greedy_low_correlation(candidates: list[dict[str, Any]], corr: pd.DataFrame,
                           target_size: int, max_per_sector: int,
                           max_avg_correlation: float = 0.6) -> list[str]:
    """Choose a diversified set of stocks.

    The candidates come sorted from best to worst. The rule adds a stock when
    two tests pass: its sector still has room, and its mean correlation to the
    chosen stocks is not too high. Stop at the target size.

    `target_size` and `max_per_sector` have no default here.
    `pipeline.PortfolioParams` is the one place that holds them. Two
    defaults can drift, and then the live run and a direct caller select
    different portfolios.
    """
    selected: list[str] = []
    sector_counts: dict[str, int] = {}

    for row in candidates:
        if len(selected) >= target_size:
            break
        ticker = row["ticker"]
        sector = row["sector"]

        # Skip the stock when its sector is already full.
        if sector_counts.get(sector, 0) >= max_per_sector:
            continue
        # Skip the stock when it moves too much like the chosen stocks.
        if average_correlation(ticker, selected, corr) > max_avg_correlation:
            continue

        selected.append(ticker)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    return selected
