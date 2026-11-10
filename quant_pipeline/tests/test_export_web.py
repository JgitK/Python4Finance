"""Tests for the web export.

The export changes warehouse frames into the JSON files of the web page.
These tests use small frames. They do not open the warehouse.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from quant import export_web as ew


def make_returns(columns: dict[str, list[float | None]]) -> pd.DataFrame:
    """Make a wide returns frame with business-day dates."""
    n = len(next(iter(columns.values())))
    index = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame(columns, index=index, dtype=float)


# --- clean values ------------------------------------------------------

def test_clean_rounds_to_six_places():
    assert ew.clean(0.123456789) == 0.123457


def test_clean_turns_nan_and_none_into_none():
    assert ew.clean(float("nan")) is None
    assert ew.clean(None) is None
    assert ew.clean(np.nan) is None


def test_clean_gives_a_python_float_for_numpy_values():
    assert type(ew.clean(np.float64(1.5))) is float


# --- window leaders ----------------------------------------------------

WINDOWS = {"1M": 2, "3M": 3}


def test_cumulative_return_compounds_the_daily_returns():
    frame = make_returns({"A": [0.10, 0.10, 0.10]})
    cum = ew.window_cum_returns(frame, 2)
    assert cum["A"] == pytest.approx(1.1 * 1.1 - 1)


def test_cumulative_return_skips_a_ticker_with_a_short_history():
    frame = make_returns({"A": [0.1, 0.1, 0.1], "B": [None, None, 0.1]})
    cum = ew.window_cum_returns(frame, 3)
    assert "A" in cum.index
    assert "B" not in cum.index


def test_leaders_rank_inside_each_sector_and_keep_the_top_n():
    frame = make_returns({
        "A": [0.03, 0.03, 0.03], "B": [0.02, 0.02, 0.02],
        "C": [0.01, 0.01, 0.01], "X": [0.05, 0.05, 0.05],
    })
    sectors = {"A": "S1", "B": "S1", "C": "S1", "X": "S2"}
    leaders = ew.build_leaders(frame, sectors, WINDOWS, top_n=2)
    s1 = [row for row in leaders["1M"] if row["sector"] == "S1"]
    assert [row["ticker"] for row in s1] == ["A", "B"]
    assert [row["rank"] for row in s1] == [1, 2]
    s2 = [row for row in leaders["1M"] if row["sector"] == "S2"]
    assert [row["ticker"] for row in s2] == ["X"]


def test_leader_fields_use_the_contract_formulas():
    rng = np.random.default_rng(0)
    values = rng.normal(0.001, 0.01, 10)
    frame = make_returns({"A": list(values)})
    leaders = ew.build_leaders(frame, {"A": "S1"}, {"1M": 5}, top_n=5)
    row = leaders["1M"][0]
    tail = values[-5:]
    cum = np.prod(1 + tail) - 1
    vol = np.std(tail, ddof=1) * math.sqrt(252)
    half = 1.96 * vol * math.sqrt(5 / 252)
    assert row["cumReturn"] == pytest.approx(cum, abs=1e-6)
    assert row["annualVol"] == pytest.approx(vol, abs=1e-6)
    assert row["rangeLow"] == pytest.approx(cum - half, abs=1e-6)
    assert row["rangeHigh"] == pytest.approx(cum + half, abs=1e-6)
    assert set(row) == {"ticker", "sector", "rank", "cumReturn", "annualVol",
                        "rangeLow", "rangeHigh", "stable"}


def test_stable_means_top_n_on_3m_6m_and_1y():
    windows = {"3M": 2, "6M": 3, "1Y": 4, "1M": 1}
    # A leads its sector on every window. B leads on 1M only.
    frame = make_returns({
        "A": [0.02, 0.02, 0.02, 0.0],
        "B": [-0.05, -0.05, -0.05, 0.03],
    })
    sectors = {"A": "S1", "B": "S1"}
    leaders = ew.build_leaders(frame, sectors, windows, top_n=1)
    assert leaders["1M"][0]["ticker"] == "B"
    assert leaders["1M"][0]["stable"] is False
    a_row = [r for r in leaders["1Y"] if r["ticker"] == "A"][0]
    assert a_row["stable"] is True


def test_a_ticker_outside_the_top_n_is_not_stable():
    windows = {"3M": 2, "6M": 2, "1Y": 2}
    frame = make_returns({"A": [0.02, 0.02], "B": [0.01, 0.01]})
    leaders = ew.build_leaders(frame, {"A": "S1", "B": "S1"}, windows, top_n=1)
    assert [r["ticker"] for r in leaders["1Y"]] == ["A"]


def test_tickers_without_a_sector_are_not_ranked():
    frame = make_returns({"A": [0.02, 0.02], "B": [0.5, 0.5]})
    leaders = ew.build_leaders(frame, {"A": "S1"}, {"1M": 2}, top_n=5)
    assert [r["ticker"] for r in leaders["1M"]] == ["A"]


# --- meta --------------------------------------------------------------

def test_union_tickers_covers_every_window_and_is_sorted():
    leaders = {
        "1M": [{"ticker": "B", "sector": "S1"}],
        "3M": [{"ticker": "A", "sector": "S1"}, {"ticker": "B", "sector": "S1"}],
    }
    assert ew.union_tickers(leaders) == ["A", "B"]


def test_build_meta_has_the_contract_fields():
    leaders = {
        "1M": [{"ticker": "B", "sector": "S2"}],
        "3M": [{"ticker": "A", "sector": "S1"}],
    }
    meta = ew.build_meta("2026-10-30", leaders, {"A": 10.5, "B": 20.0})
    assert meta["asOf"] == "2026-10-30"
    assert meta["universe"] == "sp500"
    assert meta["riskFree"] == 0.045
    assert meta["tradingDays"] == 252
    assert meta["benchmark"] == "SPY"
    assert meta["sectors"] == ["S1", "S2"]
    assert meta["tickers"] == [
        {"ticker": "A", "sector": "S1", "lastPrice": 10.5},
        {"ticker": "B", "sector": "S2", "lastPrice": 20.0},
    ]
    keys = [w["key"] for w in meta["windows"]]
    assert keys == ["1M", "3M", "6M", "1Y", "2Y", "5Y"]
    days = [w["days"] for w in meta["windows"]]
    assert days == [21, 63, 126, 252, 504, 1260]
    assert meta["windows"][0]["label"] == "Short-term reversal"
    assert meta["windows"][0]["effect"] == "Past winners tend to fall back"
    assert meta["windows"][2]["label"] == "Momentum"
    assert meta["windows"][5]["label"] == "Long-term reversal"


# --- returns -----------------------------------------------------------

def test_build_returns_keeps_the_last_n_dates_and_the_given_columns():
    frame = make_returns({"A": [0.1, 0.2, 0.3, 0.4], "B": [0.0, 0.0, None, 0.1],
                          "Z": [9, 9, 9, 9]})
    out = ew.build_returns(frame, ["A", "B"], n_days=3)
    assert len(out["dates"]) == 3
    assert out["dates"][-1] == frame.index[-1].strftime("%Y-%m-%d")
    assert set(out["series"]) == {"A", "B"}
    assert out["series"]["A"] == [0.2, 0.3, 0.4]
    assert out["series"]["B"] == [0.0, None, 0.1]


# --- ichimoku ----------------------------------------------------------

def make_prices(n: int) -> pd.DataFrame:
    """A rising series with a high and a low around the close."""
    close = np.arange(1.0, n + 1.0) * 2
    return pd.DataFrame({
        "price_date": pd.bdate_range("2025-01-01", periods=n),
        "high": close + 1, "low": close - 1, "close": close,
    })


def test_ichimoku_lines_follow_the_midpoint_rule():
    prices = make_prices(120)
    out = ew.build_ichimoku("T", prices, n_days=60)
    # Date index in the full series of the last real date is 119.
    close = prices["close"].to_numpy()
    high, low = close + 1, close - 1
    i = 119
    conv = (high[i - 8:i + 1].max() + low[i - 8:i + 1].min()) / 2
    base = (high[i - 25:i + 1].max() + low[i - 25:i + 1].min()) / 2
    assert out["conversion"][59] == pytest.approx(conv, abs=1e-6)
    assert out["base"][59] == pytest.approx(base, abs=1e-6)
    assert out["close"][59] == pytest.approx(close[i], abs=1e-6)


def test_ichimoku_adds_26_future_dates_and_spans_are_moved_ahead():
    prices = make_prices(120)
    out = ew.build_ichimoku("T", prices, n_days=60)
    assert len(out["dates"]) == 60 + 26
    for key in ("close", "conversion", "base", "spanA", "spanB", "lagging"):
        assert len(out[key]) == 86
    # The future dates follow the last date, one business day each.
    last = prices["price_date"].iloc[-1]
    future = pd.bdate_range(last + pd.Timedelta(days=1), periods=26)
    assert out["dates"][60:] == [d.strftime("%Y-%m-%d") for d in future]
    # Close and the two lines are null in the future.
    assert out["close"][60:] == [None] * 26
    assert out["conversion"][60:] == [None] * 26
    # The last future span A is the average of the lines on the last real date.
    close = prices["close"].to_numpy()
    high, low = close + 1, close - 1
    i = 119
    conv = (high[i - 8:i + 1].max() + low[i - 8:i + 1].min()) / 2
    base = (high[i - 25:i + 1].max() + low[i - 25:i + 1].min()) / 2
    assert out["spanA"][-1] == pytest.approx((conv + base) / 2, abs=1e-6)
    span_b = (high[i - 51:i + 1].max() + low[i - 51:i + 1].min()) / 2
    assert out["spanB"][-1] == pytest.approx(span_b, abs=1e-6)
    # On the last real date the span is the line value of 26 days earlier.
    j = i - 26
    conv_j = (high[j - 8:j + 1].max() + low[j - 8:j + 1].min()) / 2
    base_j = (high[j - 25:j + 1].max() + low[j - 25:j + 1].min()) / 2
    assert out["spanA"][59] == pytest.approx((conv_j + base_j) / 2, abs=1e-6)


def test_ichimoku_lagging_line_is_the_close_moved_back_26_days():
    prices = make_prices(120)
    out = ew.build_ichimoku("T", prices, n_days=60)
    close = prices["close"].to_numpy()
    # Position k of the output is the full-series index 60 + k.
    assert out["lagging"][0] == pytest.approx(close[60 + 26], abs=1e-6)
    # The last 26 real dates have no lagging value yet.
    assert out["lagging"][59 - 25:60] == [None] * 26
    assert out["lagging"][59 - 26] is not None


def test_ichimoku_signals_on_a_rising_series():
    prices = make_prices(120)
    out = ew.build_ichimoku("T", prices, n_days=60)
    assert out["signals"] == {"priceAboveCloud": True,
                              "conversionAboveBase": True,
                              "laggingAbovePrice": True}
    assert out["score"] == 3


def test_ichimoku_signals_on_a_falling_series():
    prices = make_prices(120)
    for col in ("high", "low", "close"):
        prices[col] = prices[col].iloc[::-1].to_numpy()
    out = ew.build_ichimoku("T", prices, n_days=60)
    assert out["signals"] == {"priceAboveCloud": False,
                              "conversionAboveBase": False,
                              "laggingAbovePrice": False}
    assert out["score"] == 0


def test_ichimoku_has_the_contract_keys():
    out = ew.build_ichimoku("T", make_prices(120), n_days=60)
    assert set(out) == {"ticker", "dates", "close", "conversion", "base",
                        "spanA", "spanB", "lagging", "score", "signals"}
    assert out["ticker"] == "T"


# --- scorecard ---------------------------------------------------------

def make_windows(shift: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({
        "selection_date": ["2025-08-12", "2025-02-10", "2025-05-12"],
        "portfolio_return": [0.10 + shift, -0.01 + shift, 0.20 + shift],
        "portfolio_sharpe": [0.6, -0.2, 1.1],
        "benchmark_return": [0.11, 0.13, 0.05],
        "benchmark_sharpe": [0.9, 0.7, 0.5],
        "n_stocks": [10, 10, 10],
    })


def make_null() -> pd.DataFrame:
    return pd.DataFrame({
        "measure": ["win_return", "win_sharpe", "median_excess", "mean_sharpe"],
        "real": [0.6, 0.5, 0.04, 0.7],
        "null_median": [0.51, 0.47, 0.002, 0.62],
        "null_best": [0.6, 0.6, 0.04, 0.9],
        "percentile": [0.9, 0.7, 1.0, 0.7],
    })


def make_card(null: pd.DataFrame | None = None) -> dict:
    return ew.build_scorecard(make_windows(), make_windows(0.05),
                              make_null() if null is None else null,
                              in_sample_sharpe=4.26, hold_days=180)


def test_scorecard_per_window_is_sorted_by_date_and_renamed():
    card = make_card()
    assert [r["date"] for r in card["perWindow"]] == [
        "2025-02-10", "2025-05-12", "2025-08-12"]
    assert card["perWindow"][0] == {
        "date": "2025-02-10", "portfolioReturn": -0.01,
        "benchmarkReturn": 0.13, "portfolioSharpe": -0.2,
        "benchmarkSharpe": 0.7}


def test_scorecard_rows_come_from_the_window_tables():
    card = make_card()
    assert card["windows"] == 3
    assert card["holdDays"] == 180
    assert card["inSampleSharpe"] == 4.26
    names = [r["name"] for r in card["rows"]]
    assert names == ["Optimizer", "Equal weight", "SPY", "Random order"]
    by_name = {r["name"]: r for r in card["rows"]}
    opt = by_name["Optimizer"]
    # The mean of 0.6, -0.2 and 1.1.
    assert opt["meanSharpe"] == pytest.approx(0.5)
    # The realized figure is the mean Sharpe ratio of the optimizer.
    assert card["realizedSharpe"] == opt["meanSharpe"]
    # The excess returns are -0.01, -0.14 and 0.15. The median is -0.01.
    assert opt["medianExcess"] == pytest.approx(-0.01)
    assert opt["winReturn"] == pytest.approx(1 / 3)
    assert opt["winSharpe"] == pytest.approx(1 / 3)
    # The equal-weight table has a return that is 0.05 higher.
    equal = by_name["Equal weight"]
    assert equal["medianExcess"] == pytest.approx(0.04)
    assert equal["winReturn"] == pytest.approx(2 / 3)
    # The SPY row holds the mean Sharpe ratio of the benchmark only.
    assert by_name["SPY"]["meanSharpe"] == pytest.approx(0.7)
    assert by_name["SPY"]["winReturn"] is None
    # The random-order row reads the null median from the file.
    assert by_name["Random order"]["meanSharpe"] == 0.62
    assert by_name["Random order"]["winReturn"] == 0.51
    assert by_name["Random order"]["medianExcess"] == 0.002
    assert all(r["note"] for r in card["rows"])


def test_scorecard_random_row_is_null_when_the_file_has_no_rows():
    card = make_card(make_null().iloc[0:0])
    row = [r for r in card["rows"] if r["name"] == "Random order"][0]
    assert row["meanSharpe"] is None
    assert row["winReturn"] is None


# --- write -------------------------------------------------------------

def test_write_json_writes_compact_valid_json_with_null(tmp_path):
    path = tmp_path / "sub" / "x.json"
    ew.write_json(path, {"a": [1.5, None]})
    assert json.loads(path.read_text()) == {"a": [1.5, None]}
    assert "NaN" not in path.read_text()
