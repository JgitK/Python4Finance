"""Measure each walk-forward window at several holding periods (D31).

The user holds a portfolio for 90 to 180 trading days, not for exactly
180. This module selects the portfolio once on each date. Then it scores
the same weights at each checkpoint: after 90 days, after 120 days, and
so on. Each checkpoint uses the scoring of `backtest.backtest_window`, so
the measures are the same as for the single hold.

Two views are possible:

- The same dates. Every checkpoint uses only the dates that have a full
  window for the longest hold. The comparison between two checkpoints is
  then paired: the same portfolios, measured for a shorter or a longer
  time.
- All valid dates. A shorter hold ends earlier, so a later date also has
  a full window. Each checkpoint then has more windows than the longest
  hold. The comparison between two checkpoints is not paired.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quant import backtest


def parse_hold_days(text: str) -> list[int]:
    """Read a list of holding periods, for example "90,120,150,180".

    Return the periods sorted and without repeats. Raise ValueError for an
    empty item, for a value that is not a whole number, and for a value
    below 1.
    """
    periods = set()
    for item in text.split(","):
        item = item.strip()
        if not item:
            raise ValueError(f"empty holding period in {text!r}")
        value = int(item)
        if value < 1:
            raise ValueError(f"a holding period must be 1 or more, not {value}")
        periods.add(value)
    return sorted(periods)


def run_checkpoints(returns: pd.DataFrame, selection_dates: list[Any],
                    holding_periods: list[int],
                    build_portfolio: backtest.BuildPortfolio,
                    benchmark: str, risk_free: float = 0.045,
                    trading_days: int = 252) -> dict[int, list[dict]]:
    """Run the walk-forward test and score each window at each checkpoint.

    Build the portfolio once on each date, from the past only. Score the
    same weights for each holding period. A checkpoint keeps a date only
    when the data holds the full period after that date. A short window
    with the label of a long period gives a wrong result.

    Return one list of windows for each holding period.
    """
    by_hold: dict[int, list[dict]] = {period: [] for period in holding_periods}
    for date in selection_dates:
        train, test = backtest.split_by_date(returns, date)
        weights = build_portfolio(train)
        for period in holding_periods:
            if len(test) < period:
                continue
            by_hold[period].append(backtest.backtest_window(
                returns, date, period, lambda _train, w=weights: w,
                benchmark, risk_free, trading_days))
    return by_hold


def same_dates(by_hold: dict[int, list[dict]]) -> dict[int, list[dict]]:
    """Keep, for each checkpoint, only the dates of the longest hold.

    The longest hold has the fewest valid dates. With the same dates at
    every checkpoint, two checkpoints compare the same portfolios.
    """
    longest = max(by_hold)
    keep = {w["selection_date"] for w in by_hold[longest]}
    return {period: [w for w in windows if w["selection_date"] in keep]
            for period, windows in by_hold.items()}


def max_non_overlapping(positions: list[int], period: int) -> int:
    """Count the most windows that share no day.

    `positions` holds the row numbers of the selection dates in the
    returns index. A window covers the `period` days after its date. Take
    the first date, then each next date that starts after the end of the
    window before it. For windows of one length, this count is the
    largest possible.
    """
    count = 0
    free_from = None
    for position in sorted(positions):
        if free_from is None or position >= free_from:
            count += 1
            free_from = position + period
    return count


def _annual_excess(window: dict) -> float:
    """Return the annual return of the portfolio minus that of the benchmark.

    A raw 90-day excess and a raw 180-day excess are not comparable. Each
    annual return compounds the total return to 252 days first.
    """
    return (window["portfolio"]["annual_return"]
            - window["benchmark"]["annual_return"])


def checkpoint_table(by_hold: dict[int, list[dict]],
                     index: pd.DatetimeIndex) -> pd.DataFrame:
    """Summarize each checkpoint in one row.

    Each row gives the count of the windows, the share that beats the
    benchmark on the return and on the Sharpe ratio, the raw and the
    annual excess return, the mean Sharpe ratios, the mean realized beta,
    and the count of windows that share no day. The windows overlap, so
    that last count says how many independent periods the row holds.
    """
    nan = float("nan")
    rows = []
    for period in sorted(by_hold):
        windows = by_hold[period]
        summary = backtest.summarize_windows(windows)
        scored = [w for w in windows if backtest.window_is_scored(w)]
        annual = np.array([_annual_excess(w) for w in scored])
        positions = [index.get_loc(w["selection_date"]) for w in scored]
        rows.append({
            "hold_days": period,
            "windows": summary["n_scored"],
            "win_return": summary["win_return"],
            "win_sharpe": summary["win_sharpe"],
            "median_excess": summary["median_excess"],
            "mean_excess": summary["mean_excess"],
            "median_excess_annual": (float(np.median(annual))
                                     if annual.size else nan),
            "mean_excess_annual": float(annual.mean()) if annual.size else nan,
            "mean_sharpe": summary["mean_sharpe"],
            "mean_benchmark_sharpe": summary["mean_benchmark_sharpe"],
            "mean_beta": summary["mean_beta"],
            "non_overlapping": max_non_overlapping(positions, period),
        })
    return pd.DataFrame(rows)


def format_table(table: pd.DataFrame) -> str:
    """Return the checkpoint table as text for the console."""
    shown = table.copy()
    for column in ("win_return", "win_sharpe"):
        shown[column] = shown[column].map(lambda v: f"{v:.1%}")
    for column in ("median_excess", "mean_excess", "median_excess_annual",
                   "mean_excess_annual"):
        shown[column] = shown[column].map(lambda v: f"{v:+.2%}")
    for column in ("mean_sharpe", "mean_benchmark_sharpe", "mean_beta"):
        shown[column] = shown[column].map(lambda v: f"{v:.2f}")
    return shown.to_string(index=False)
