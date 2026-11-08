"""A random-selection null benchmark for the portfolio method.

SPY says whether the pipeline beats the market. It does not say whether
the rank order of the candidates adds anything. This module answers that
question.

The null keeps every other step of the method. It applies the same screen
of the same date, it uses the same sector cap, the same correlation gate,
and the same Max Sharpe weight search. It removes one thing only: the
order of the candidates. The real method reads them best first. The null
reads them in a random order.

Each draw is one complete walk-forward run. A few hundred draws give a
distribution of outcomes for "any portfolio of this size from the same
screened pool". The percentile of the real result inside that
distribution says how much the rank order is worth. A result at the 50th
percentile means that the rank order does nothing.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from quant import backtest, pipeline

# The measures of one draw that the summary keeps.
MEASURES = ("win_return", "win_sharpe", "mean_excess", "median_excess",
            "mean_sharpe")


def percentile_of(value: float, distribution: Any) -> float:
    """Return the share of the distribution that is below the value.

    Drop a value of the distribution that is not a number. Return "not a
    number" for an empty distribution, because no percentile exists then.
    """
    values = np.array([v for v in np.asarray(distribution, dtype=float)
                       if math.isfinite(v)])
    if values.size == 0 or not math.isfinite(value):
        return float("nan")
    return float((values < value).mean())


def run_random_selection(returns: pd.DataFrame, selection_dates: list[Any],
                         holding_period: int, sector_of: dict[str, str],
                         params: pipeline.PortfolioParams, benchmark: str,
                         screen_history: pd.DataFrame | None = None,
                         n_draws: int = 100, seed: int = 0) -> pd.DataFrame:
    """Run the walk-forward test with a random candidate order, many times.

    Return one row for each draw. Each row holds the measures of a whole
    walk-forward run. The seed makes the set of draws reproducible.

    The draws use the optimizer and the size mode of `params`. In the
    pool mode, each draw gives a random pool of `pool_size` names to the
    exact optimizer (D32).
    """
    rows = []
    for draw in range(n_draws):
        rng = np.random.default_rng(seed + draw)
        build = pipeline.make_builder(sector_of, params, benchmark,
                                      screen_history=screen_history, rng=rng)
        summary = backtest.summarize_windows(backtest.run_walk_forward(
            returns, selection_dates, holding_period, build, benchmark,
            params.risk_free, params.trading_days))
        rows.append({"draw": draw, "n_scored": summary["n_scored"],
                     **{name: summary[name] for name in MEASURES}})
    return pd.DataFrame(rows)


def compare_with_null(real: dict[str, Any],
                      draws: pd.DataFrame) -> pd.DataFrame:
    """Place the real result inside the distribution of the draws.

    Return one row for each measure, with the real value, the median of
    the draws, the best draw, and the percentile of the real value.
    """
    rows = []
    for name in MEASURES:
        column = draws[name]
        rows.append({
            "measure": name,
            "real": real.get(name, float("nan")),
            "null_median": float(column.median()),
            "null_best": float(column.max()),
            "percentile": percentile_of(real.get(name, float("nan")), column),
        })
    return pd.DataFrame(rows)
