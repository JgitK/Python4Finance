"""Tests for the holding-period checkpoints of the backtest (D31).

The user holds a portfolio for 90 to 180 trading days. The backtest
measures each window at several checkpoints. These tests use a small
synthetic returns panel, so a person can check each checkpoint by hand.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant import backtest, holding

# The daily returns of the stock AAA and of the benchmark BBB after the
# selection date. The selection date is day 2 of the panel.
AAA_AFTER = [0.10, -0.05, 0.02, 0.04, 0.00, 0.01]
BBB_AFTER = [0.01, 0.01, 0.00, -0.02, 0.03, 0.00]


def _panel() -> pd.DataFrame:
    """Return a panel of 9 days. Days 0 to 2 are the past."""
    dates = pd.bdate_range("2024-01-01", periods=9)
    return pd.DataFrame({"AAA": [0.01, 0.02, 0.03] + AAA_AFTER,
                         "BBB": [0.00, 0.01, 0.00] + BBB_AFTER},
                        index=dates)


def _all_in_aaa(train: pd.DataFrame) -> dict[str, float]:
    return {"AAA": 1.0}


def _compound(values: list[float]) -> float:
    return float(np.prod([1.0 + v for v in values]) - 1.0)


# --- run_checkpoints: the arithmetic -----------------------------------------

def test_each_checkpoint_compounds_only_its_own_days():
    returns = _panel()
    by_hold = holding.run_checkpoints(
        returns, [returns.index[2]], [1, 2, 3], _all_in_aaa, "BBB",
        risk_free=0.0, trading_days=4)
    # Day 1: +10%. Day 2: 1.10 * 0.95 - 1 = +4.5%.
    # Day 3: 1.045 * 1.02 - 1 = +6.59%.
    assert by_hold[1][0]["portfolio"]["total_return"] == pytest.approx(0.10)
    assert by_hold[2][0]["portfolio"]["total_return"] == pytest.approx(0.045)
    assert by_hold[3][0]["portfolio"]["total_return"] == pytest.approx(0.0659)
    assert by_hold[3][0]["benchmark"]["total_return"] == pytest.approx(
        _compound(BBB_AFTER[:3]))
    assert by_hold[2][0]["portfolio"]["n_days"] == 2


def test_the_selection_is_built_once_for_all_checkpoints():
    returns = _panel()
    calls = []

    def build(train: pd.DataFrame) -> dict[str, float]:
        calls.append(train.index.max())
        return {"AAA": 1.0}

    holding.run_checkpoints(returns, [returns.index[2]], [2, 4, 6], build,
                            "BBB")
    assert calls == [returns.index[2]]


def test_a_checkpoint_without_a_full_window_is_dropped():
    # The selection date of day 4 has 4 days after it. A 6-day checkpoint
    # cannot be full, so it must not hold that date. A short window would
    # give a 4-day result with the label of 6 days.
    returns = _panel()
    dates = [returns.index[2], returns.index[4]]
    by_hold = holding.run_checkpoints(returns, dates, [2, 6], _all_in_aaa,
                                      "BBB")
    assert [w["selection_date"] for w in by_hold[2]] == dates
    assert [w["selection_date"] for w in by_hold[6]] == [returns.index[2]]


def test_the_longest_checkpoint_equals_the_old_walk_forward():
    returns = _panel()
    dates = [returns.index[1], returns.index[2]]
    old = backtest.run_walk_forward(returns, dates, 6, _all_in_aaa, "BBB")
    new = holding.run_checkpoints(returns, dates, [3, 6], _all_in_aaa,
                                  "BBB")[6]
    assert backtest.summarize_windows(new) == pytest.approx(
        backtest.summarize_windows(old), nan_ok=True)


# --- run_checkpoints: no future data ------------------------------------------

def test_a_checkpoint_uses_no_price_after_its_end_date():
    returns = _panel()
    tampered = returns.copy()
    # Put absurd returns on every day after the end of the 3-day checkpoint.
    tampered.iloc[6:] = 5.0
    clean = holding.run_checkpoints(returns, [returns.index[2]], [3],
                                    _all_in_aaa, "BBB")[3][0]
    dirty = holding.run_checkpoints(tampered, [returns.index[2]], [3],
                                    _all_in_aaa, "BBB")[3][0]
    for side in ("portfolio", "benchmark"):
        assert dirty[side]["total_return"] == clean[side]["total_return"]
        assert dirty[side]["sharpe"] == clean[side]["sharpe"]
    assert dirty["capm"]["beta"] == clean["capm"]["beta"]


def test_the_selection_uses_no_price_after_the_selection_date():
    returns = _panel()
    seen = []

    def build(train: pd.DataFrame) -> dict[str, float]:
        seen.append(train.index.max())
        # The weights follow the past returns, so a leak changes them.
        return {"AAA": 1.0 + float(train["AAA"].sum())}

    tampered = returns.copy()
    tampered.iloc[3:] = -0.5
    first = holding.run_checkpoints(returns, [returns.index[2]], [2, 4],
                                    build, "BBB")
    second = holding.run_checkpoints(tampered, [returns.index[2]], [2, 4],
                                     build, "BBB")
    assert max(seen) <= returns.index[2]
    assert first[4][0]["weights"] == second[4][0]["weights"]


# --- the two views -----------------------------------------------------------

def test_the_same_dates_view_keeps_the_dates_of_the_longest_hold():
    returns = _panel()
    dates = [returns.index[1], returns.index[2], returns.index[4]]
    by_hold = holding.run_checkpoints(returns, dates, [2, 6], _all_in_aaa,
                                      "BBB")
    same = holding.same_dates(by_hold)
    # Only day 1 and day 2 have 6 days after them.
    expected = [returns.index[1], returns.index[2]]
    assert [w["selection_date"] for w in same[6]] == expected
    assert [w["selection_date"] for w in same[2]] == expected
    # The view of all valid dates keeps day 4 for the short hold.
    assert len(by_hold[2]) == 3


# --- non-overlapping windows --------------------------------------------------

def test_max_non_overlapping_counts_windows_that_share_no_day():
    # Dates every 5 days. A hold of 10 days needs a gap of 10 days.
    positions = [0, 5, 10, 15, 20, 25]
    assert holding.max_non_overlapping(positions, 10) == 3
    assert holding.max_non_overlapping(positions, 5) == 6
    assert holding.max_non_overlapping(positions, 11) == 2
    assert holding.max_non_overlapping([], 10) == 0


# --- the table ---------------------------------------------------------------

def _scored(date: str, port: float, bench: float, n_days: int,
            beta: float = 1.0) -> dict:
    """Make one window in the shape that backtest_window returns."""
    def perf(total: float) -> dict:
        annual = (1.0 + total) ** (252 / n_days) - 1.0
        return {"total_return": total, "annual_return": annual,
                "sharpe": total * 10, "n_days": n_days}
    return {"selection_date": pd.Timestamp(date), "weights": {"AAA": 1.0},
            "portfolio": perf(port), "benchmark": perf(bench),
            "capm": {"beta": beta, "alpha": 0.0}}


def test_checkpoint_table_reports_raw_and_annual_excess():
    index = pd.bdate_range("2024-01-01", periods=400)
    by_hold = {
        63: [_scored("2024-01-01", 0.10, 0.05, 63),
             _scored("2024-01-08", 0.00, 0.02, 63)],
        126: [_scored("2024-01-01", 0.20, 0.10, 126, beta=1.5),
              _scored("2024-01-08", 0.05, 0.02, 126, beta=0.5)],
    }
    table = holding.checkpoint_table(by_hold, index).set_index("hold_days")
    assert list(table.index) == [63, 126]
    assert table.loc[63, "windows"] == 2
    assert table.loc[63, "win_return"] == pytest.approx(0.5)
    assert table.loc[63, "median_excess"] == pytest.approx(0.015)
    assert table.loc[126, "win_return"] == pytest.approx(1.0)
    assert table.loc[126, "mean_beta"] == pytest.approx(1.0)
    # A 63-day return compounds 4 times in a year of 252 days.
    first = 1.10 ** 4 - 1.05 ** 4
    second = 1.00 ** 4 - 1.02 ** 4
    assert table.loc[63, "mean_excess_annual"] == pytest.approx(
        (first + second) / 2)
    # A 126-day return compounds 2 times.
    first = 1.20 ** 2 - 1.10 ** 2
    second = 1.05 ** 2 - 1.02 ** 2
    assert table.loc[126, "median_excess_annual"] == pytest.approx(
        (first + second) / 2)
    # The two dates are 5 days apart, so a 63-day hold fits one window
    # that shares no day with another.
    assert table.loc[63, "non_overlapping"] == 1


def test_checkpoint_table_counts_non_overlapping_on_the_index():
    index = pd.bdate_range("2024-01-01", periods=400)
    dates = [index[0], index[100], index[200]]
    by_hold = {90: [_scored(str(d.date()), 0.0, 0.0, 90) for d in dates],
               150: [_scored(str(d.date()), 0.0, 0.0, 150) for d in dates]}
    table = holding.checkpoint_table(by_hold, index).set_index("hold_days")
    assert table.loc[90, "non_overlapping"] == 3
    assert table.loc[150, "non_overlapping"] == 2


# --- the command line --------------------------------------------------------

def test_parse_hold_days_reads_a_sorted_list():
    assert holding.parse_hold_days("180") == [180]
    assert holding.parse_hold_days("180,90, 120,150") == [90, 120, 150, 180]
    assert holding.parse_hold_days("90,90") == [90]


@pytest.mark.parametrize("text", ["", "0", "-5", "abc", "90,,"])
def test_parse_hold_days_refuses_a_bad_value(text):
    with pytest.raises(ValueError):
        holding.parse_hold_days(text)


def test_an_empty_checkpoint_gives_no_number():
    table = holding.checkpoint_table({90: []},
                                     pd.bdate_range("2024-01-01", periods=10))
    assert table.loc[0, "windows"] == 0
    assert math.isnan(table.loc[0, "win_return"])
