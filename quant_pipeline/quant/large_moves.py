"""Classify a large one-day move with the volume of the day.

A one-day move larger than the review limit has two causes.

A corporate action, for example a reverse split, divides the share count.
The price source adjusts most of them, but not all. An unadjusted action
gives a gap between the close of one day and the open of the next day.
Nobody trades on the gap, so the volume stays normal and the close of the
day stays near the open. Such a gap is not a return. The pipeline must
back-adjust the prices before it.

Real news gives a different picture. Many people trade, so the volume
jumps far above the normal level of the stock. Such a move is a return,
and it must stay in the data.

The rule reads these three signals:

  1. The volume of the day, divided by the median volume of the days
     around it. A value at or above SPIKE_RATIO is a spike.
  2. The move of the price from the open to the close of the day. A value
     within FLAT_INTRADAY is a day with no trading after the gap. A value
     above TRADED_INTRADAY is a day of heavy trading.
  3. The gap: the open of the day, divided by the close of the day before.
     A gap by a factor of SPLIT_FACTOR is not a price change.

The rule names a cause only when the signals agree. For every other move
it answers "unclear", and a person reads that move. A spin-off has no
clear signal, so the rule leaves such a move to a person. See decision D14.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# The number of trading days on each side of a move in the volume baseline.
VOLUME_WINDOW = 60
# A volume at or above this multiple of the baseline is a spike.
SPIKE_RATIO = 6.0
# A volume below this multiple of the baseline is not a spike.
QUIET_RATIO = 2.0
# A move from the open to the close within this limit is a flat day.
FLAT_INTRADAY = 0.05
# A move larger than this limit from the open to the close is trading.
TRADED_INTRADAY = 0.20
# A price change by this factor in one day is not a price change. No share
# rises or falls by a factor of 5 in one day on real news.
SPLIT_FACTOR = 5.0
# The window must hold at least this many days with a volume. The price
# source has no volume for some days of a thin stock. A baseline from a
# few days is not a normal volume, so the rule says "unclear" instead.
MIN_BASELINE_DAYS = 20

REAL_MOVE = "real_move"
CORPORATE_ACTION = "corporate_action"
UNCLEAR = "unclear"

# The columns of the output, in order.
COLUMNS = ["ticker", "price_date", "prev_close", "open", "close", "volume",
           "baseline", "ratio", "intraday", "daily_return", "kind", "reason"]


def neighbour_median(volume: np.ndarray, position: int,
                     window: int = VOLUME_WINDOW,
                     min_days: int = MIN_BASELINE_DAYS) -> float:
    """Return the median volume of the days around one day.

    The day itself is not in the median. A move brings its own volume, so
    the volume of the move day is not a part of its baseline. The window
    reaches up to `window` days on each side. A move near the start or the
    end of a history has fewer days on one side, so this function uses the
    days that are there.

    A day with no volume in the price source is not in the median. The
    function answers "not a number" when fewer than `min_days` days of the
    window have a volume.
    """
    low = max(0, position - window)
    high = min(len(volume), position + window + 1)
    around = np.concatenate([volume[low:position], volume[position + 1:high]])
    around = around[np.isfinite(around)]
    if len(around) < min_days:
        return float("nan")
    return float(np.median(around))


def decide(ratio: float, intraday: float, gap: float = float("nan"),
           spike_ratio: float = SPIKE_RATIO,
           quiet_ratio: float = QUIET_RATIO,
           flat_intraday: float = FLAT_INTRADAY,
           traded_intraday: float = TRADED_INTRADAY,
           split_factor: float = SPLIT_FACTOR) -> tuple[str, str]:
    """Name the cause of one large move, and give the test that named it.

    The tests come in this order:

      1. A gap by a factor of `split_factor`, with no volume spike, is a
         corporate action. A share does not change its price by a factor
         of 5 in one day.
      2. A low volume with a flat day is a corporate action. The price
         gapped, and then nobody traded on the new price.
      3. A volume spike is a real move. Many people traded.
      4. A big move from the open to the close is a real move. A corporate
         action gives a gap at the open, and then it does not trade.

    For every other move the signals do not agree, and this function
    answers "unclear". A spin-off is such a move: the index funds bring
    some volume, and the price holds near the open.
    """
    if not np.isfinite(intraday):
        return UNCLEAR, "The price source gives no open for the day."
    spike = np.isfinite(ratio) and ratio >= spike_ratio
    quiet = np.isfinite(ratio) and ratio < quiet_ratio
    if (np.isfinite(gap) and gap > 0 and not spike
            and (gap >= split_factor or gap <= 1 / split_factor)):
        return CORPORATE_ACTION, (
            f"The price changed by a factor of {max(gap, 1 / gap):.3g} at the "
            "open, and the volume was not a spike. A share does not change "
            "its price by such a factor in one day.")
    if quiet and abs(intraday) <= flat_intraday:
        return CORPORATE_ACTION, (
            "The volume was below the normal level, and the day was flat "
            "after the gap. Nobody traded on the new price.")
    if spike:
        return REAL_MOVE, (
            "The volume was a spike, so many people traded. The move is a "
            "return.")
    if abs(intraday) > traded_intraday:
        return REAL_MOVE, (
            "The price moved by a large amount after the open, so people "
            "traded. A corporate action gives a gap, and then it does not "
            "trade. The move is a return.")
    return UNCLEAR, (
        "The signals do not agree. The volume is between the two limits, "
        "and the day moved only a little after the gap.")


def classify(ratio: float, intraday: float, gap: float = float("nan"),
             **limits: float) -> str:
    """Name the cause of one large move, or answer "unclear"."""
    return decide(ratio, intraday, gap, **limits)[0]


def large_moves(prices: pd.DataFrame, limit: float,
                window: int = VOLUME_WINDOW, **limits: float) -> pd.DataFrame:
    """Find each one-day move larger than the limit, then name its cause.

    The price frame needs the columns ticker, price_date, open, close and
    volume. The frame holds the prices of the price source, with no
    adjustment. The output holds one row for each large move, with the
    three signals, the answer of the rule, and the reason for the answer.
    """
    frame = prices.sort_values(["ticker", "price_date"]).reset_index(drop=True)
    rows = []
    for ticker, group in frame.groupby("ticker", sort=True):
        close = group["close"].to_numpy(dtype=float)
        volume = group["volume"].to_numpy(dtype=float)
        openings = group["open"].to_numpy(dtype=float)
        dates = group["price_date"].to_numpy()
        for position in range(1, len(group)):
            daily_return = close[position] / close[position - 1] - 1
            if abs(daily_return) <= limit:
                continue
            baseline = neighbour_median(volume, position, window)
            ratio = (volume[position] / baseline
                     if baseline and np.isfinite(baseline) else float("nan"))
            intraday = (close[position] / openings[position] - 1
                        if openings[position] > 0 else float("nan"))
            gap = (openings[position] / close[position - 1]
                   if close[position - 1] > 0 else float("nan"))
            kind, reason = decide(ratio, intraday, gap, **limits)
            rows.append({
                "ticker": ticker,
                "price_date": dates[position],
                "prev_close": close[position - 1],
                "open": openings[position],
                "close": close[position],
                "volume": volume[position],
                "baseline": baseline,
                "ratio": ratio,
                "intraday": intraday,
                "daily_return": daily_return,
                "kind": kind,
                "reason": reason,
            })
    return pd.DataFrame(rows, columns=COLUMNS)


def note(row: pd.Series) -> str:
    """Write the evidence of one move in short sentences."""
    gap = row["open"] / row["prev_close"] if row["prev_close"] else float("nan")
    volume = (f"on {row['ratio']:.1f}x the median volume of the days around it"
              if np.isfinite(row["ratio"])
              else "and the price source gives no normal volume for the stock")
    return (f"Volume rule (D14): close {row['daily_return']:+.0%} "
            f"{volume}. The gap is {gap:.3g}x, and the day moved "
            f"{row['intraday']:+.0%} from the open. {row['reason']}")


def seed_rows(moves: pd.DataFrame) -> pd.DataFrame:
    """Make the rows of the corporate_actions seed for the named moves.

    An unclear move is not in the output. A person reads such a move and
    writes its row by hand.
    """
    named = moves[moves["kind"] != UNCLEAR]
    return pd.DataFrame({
        "ticker": named["ticker"],
        "date": pd.to_datetime(named["price_date"]).dt.strftime("%Y-%m-%d"),
        "kind": named["kind"],
        "note": [note(row) for _, row in named.iterrows()],
    }).reset_index(drop=True)
