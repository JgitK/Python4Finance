"""Tests for the volume rule that classifies a large one-day move.

A one-day move larger than the review limit has two causes. A corporate
action that the price source did not adjust gives a gap in the price, but
no trading. Real news gives a move with a jump in the volume. The rule
reads the volume and the intraday move, then names the cause.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant import large_moves


def one_ticker(volume: list[float], moves: dict[int, tuple[float, float]],
               days: int | None = None) -> pd.DataFrame:
    """Make a price frame for one quiet stock, then add the moves.

    The stock closes at 10.0 every day. Each item of `moves` names a
    position, the open of that day, and the close of that day. The stock
    keeps the new price level after a move, so the frame holds one large
    move for each item and no move back to the old level.
    """
    days = days if days is not None else len(volume)
    frame = pd.DataFrame({
        "ticker": "AAA",
        "price_date": pd.bdate_range("2024-01-01", periods=days),
        "open": 10.0,
        "close": 10.0,
        "volume": volume,
    })
    for position, (open_price, close_price) in sorted(moves.items()):
        frame.loc[position, "open"] = open_price
        frame.loc[position:, "close"] = close_price
        frame.loc[position + 1:, "open"] = close_price
    return frame


# ---------------------------------------------------------------------------
# The volume baseline.


def test_the_baseline_leaves_out_the_day_of_the_move():
    # The volume of the move day is not a part of its own baseline. The
    # neighbours of position 1 hold 100 and 500, so the baseline is 300.
    # A baseline that holds the day itself gives 500.
    volume = np.array([100.0, 900.0, 500.0])
    assert large_moves.neighbour_median(volume, 1, window=1,
                                    min_days=2) == 300.0


def test_the_baseline_ignores_a_day_with_no_volume():
    # The price source has no volume for some days of a thin stock. Such a
    # day must not enter the median. One missing day must not make the
    # baseline of the whole move unusable.
    volume = np.array([100.0, np.nan, 900.0, np.nan, 300.0])
    assert large_moves.neighbour_median(volume, 2, window=2,
                                        min_days=2) == 200.0


def test_the_baseline_needs_enough_days_with_volume():
    # A stock that trades on two days of the window has no normal volume.
    # The function must answer "not a number", so the rule says "unclear".
    volume = np.array([np.nan] * 60 + [100.0, 900.0, 100.0] + [np.nan] * 60)
    assert np.isnan(large_moves.neighbour_median(volume, 61, window=60))
    assert large_moves.neighbour_median(volume, 61, window=60,
                                        min_days=2) == 100.0
    assert large_moves.classify(float("nan"), 0.0) == large_moves.UNCLEAR


def test_the_baseline_uses_the_days_after_a_move_near_the_start():
    # A move on the second day has one day before it. The baseline must
    # use the days after the move, so the rule can still name the cause.
    volume = np.array([100.0, 900.0, 100.0, 100.0, 100.0])
    assert large_moves.neighbour_median(volume, 1, window=60,
                                    min_days=2) == 100.0


# ---------------------------------------------------------------------------
# The rule.


def test_a_quiet_gap_is_a_corporate_action():
    # The price doubles overnight, and the close equals the open. Nobody
    # traded on the gap, and the volume stayed low. This is a split.
    frame = one_ticker([1000.0] * 130, {65: (20.0, 20.0)})
    frame.loc[65, "volume"] = 500.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["corporate_action"]
    assert found["ratio"].iloc[0] == pytest.approx(0.5)


def test_a_volume_spike_is_a_real_move():
    # The price rose by 100%, and ten times the normal number of shares
    # changed hands. People traded, so the move is real.
    frame = one_ticker([1000.0] * 130, {65: (15.0, 20.0)})
    frame.loc[65, "volume"] = 10000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["real_move"]


def test_a_move_between_the_two_limits_is_unclear():
    # Three times the normal volume is not a spike and not a quiet day.
    # The rule must not guess. A person reads this move.
    frame = one_ticker([1000.0] * 130, {65: (20.0, 20.0)})
    frame.loc[65, "volume"] = 3000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["unclear"]


def test_a_quiet_day_that_moves_after_the_open_is_a_real_move():
    # The volume stayed low, but the price rose by 82% from the open to
    # the close. A corporate action gives a gap at the open, and then it
    # does not trade. This day traded, so the move is real.
    frame = one_ticker([1000.0] * 130, {65: (11.0, 20.0)})
    frame.loc[65, "volume"] = 500.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["real_move"]


def test_a_price_change_by_a_factor_of_five_is_a_corporate_action():
    # The price went up by a factor of 16 overnight, and the volume stayed
    # normal. No share rises by a factor of 16 in one day. The cause is a
    # reverse split that the price source did not adjust.
    frame = one_ticker([1000.0] * 130, {65: (160.0, 200.0)})
    frame.loc[65, "volume"] = 3000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["corporate_action"]


def test_a_volume_spike_beats_the_split_factor():
    # A share can rise by a factor of 5 on real news, for example a buyout
    # of a small company. The volume then rises far above the normal level.
    # A reverse split brings no such volume, so the spike decides.
    frame = one_ticker([1000.0] * 130, {65: (60.0, 62.0)})
    frame.loc[65, "volume"] = 20000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["real_move"]


def test_a_big_move_during_the_day_is_a_real_move():
    # The volume is only three times the normal level, so it is not a
    # spike. But the price rose by 50% from the open to the close. A
    # corporate action gives a gap at the open. It does not trade.
    frame = one_ticker([1000.0] * 130, {65: (12.0, 18.0)})
    frame.loc[65, "volume"] = 3000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["real_move"]


def test_a_gap_with_a_small_day_and_a_middle_volume_is_unclear():
    # This is the shape of a spin-off: the price gapped down by half, the
    # volume rose a little, and the day moved only 5% after the open. The
    # rule must not name a cause. A person reads such a move. The one
    # corporate action that a person found by hand (HON, D11) has this
    # shape, so the rule must not call it a real move.
    frame = one_ticker([1000.0] * 130, {65: (5.2, 4.95)})
    frame.loc[65, "volume"] = 3000.0
    found = large_moves.large_moves(frame, limit=0.5)
    assert list(found["kind"]) == ["unclear"]


def test_a_small_move_is_not_in_the_output():
    frame = one_ticker([1000.0] * 130, {65: (10.4, 10.4)})
    assert large_moves.large_moves(frame, limit=0.5).empty


def test_each_move_keeps_the_evidence_in_a_note():
    frame = one_ticker([1000.0] * 130, {65: (20.0, 20.0)})
    frame.loc[65, "volume"] = 500.0
    rows = large_moves.seed_rows(large_moves.large_moves(frame, limit=0.5))
    assert list(rows.columns) == ["ticker", "date", "kind", "note"]
    note = rows["note"].iloc[0]
    assert "0.5x" in note and "100%" in note


def test_the_note_gives_the_test_that_named_the_cause():
    # Two corporate actions come from two different tests of the rule. The
    # note of each one must give its own test. A note that gives the wrong
    # test is evidence for a cause that nobody examined.
    flat = one_ticker([1000.0] * 130, {65: (20.0, 20.0)})
    flat.loc[65, "volume"] = 500.0
    flat_note = large_moves.seed_rows(
        large_moves.large_moves(flat, limit=0.5))["note"].iloc[0]
    assert "flat" in flat_note and "factor" not in flat_note

    big_gap = one_ticker([1000.0] * 130, {65: (160.0, 20.0)})
    big_gap.loc[65, "volume"] = 3000.0
    gap_note = large_moves.seed_rows(
        large_moves.large_moves(big_gap, limit=0.5))["note"].iloc[0]
    assert "factor" in gap_note and "flat" not in gap_note


def test_the_note_says_when_the_stock_has_no_normal_volume():
    # The price source has no volume for most days of a thin stock. The
    # note must say so. It must not give a multiple that does not exist.
    frame = one_ticker([float("nan")] * 130, {65: (160.0, 200.0)})
    note = large_moves.seed_rows(
        large_moves.large_moves(frame, limit=0.5))["note"].iloc[0]
    assert "no normal volume" in note
    assert "x the median volume" not in note


def test_the_seed_rows_leave_out_an_unclear_move():
    # The rule writes only the moves that it names. A person adds the rest.
    frame = one_ticker([1000.0] * 130, {65: (20.0, 20.0)})
    frame.loc[65, "volume"] = 3000.0
    assert large_moves.seed_rows(large_moves.large_moves(frame, limit=0.5)).empty


# ---------------------------------------------------------------------------
# The rule against the hand reviews.



def hand_reviews():
    """Read the price file and the moves that a person classified."""
    import duckdb

    from quant import warehouse
    prices_file = (warehouse.DEFAULT_WAREHOUSE.parents[1] / "data"
                   / "raw_prices.parquet")
    seeds = warehouse.DEFAULT_WAREHOUSE.parent / "seeds"
    if not prices_file.exists():
        pytest.skip("Run 'python -m quant.ingest' first.")
    seed = pd.read_csv(seeds / "corporate_actions.csv", parse_dates=["date"])
    excluded = set(pd.read_csv(seeds / "price_data_exclusions.csv")["ticker"])
    tickers = sorted(set(seed["ticker"]) - excluded)
    prices = duckdb.sql(
        f"select ticker, date as price_date, open, close, volume "
        f"from read_parquet('{prices_file}') "
        f"where close > 0 and ticker in ({str(tickers)[1:-1]})").df()
    prices["price_date"] = pd.to_datetime(prices["price_date"])
    return prices, seed


def test_the_rule_never_contradicts_a_hand_review():
    # A person classified ten moves by hand (D11). The rule must agree
    # with each one, or say that the move is unclear. A contradiction
    # means that the limits of the rule are wrong.
    prices, seed = hand_reviews()
    found = large_moves.large_moves(prices, limit=0.5)
    merged = found.merge(seed, left_on=["ticker", "price_date"],
                         right_on=["ticker", "date"],
                         suffixes=("_rule", "_hand"))
    assert len(merged) == len(seed), "every hand review must be a large move"
    wrong = merged[(merged["kind_rule"] != "unclear")
                   & (merged["kind_rule"] != merged["kind_hand"])]
    assert wrong.empty, wrong[["ticker", "price_date", "ratio",
                               "kind_rule", "kind_hand"]].to_string()
    # The rule must also decide most of them. A rule that says "unclear"
    # for every move is useless.
    assert (merged["kind_rule"] != "unclear").sum() >= 7
