"""Tests for the overlapping-portfolio momentum regression (D36).

The walk-forward windows overlap, so a regression on each window counts
the same days many times. `quant.overlap` makes one daily series for each
arm: on each day, the mean return of every window that holds on that day
(Jegadeesh and Titman, 1993). It then regresses that series, or the
difference of two arms, on the market and on UMD with Newey-West errors.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import momentum_vs_equal_weight as script
from quant import overlap

DAYS = pd.bdate_range("2024-01-01", periods=10)


def _returns() -> pd.DataFrame:
    return pd.DataFrame({"A": np.arange(10) * 0.001,
                         "B": np.full(10, 0.002),
                         "SPY": np.full(10, 0.001)}, index=DAYS)


def _window(date, weights, scored=True):
    total = 0.01 if scored else float("nan")
    return {"selection_date": pd.Timestamp(date), "weights": weights,
            "portfolio": {"total_return": total},
            "benchmark": {"total_return": 0.01}}


# --- the overlapping series --------------------------------------------------

def test_one_window_gives_its_own_daily_returns():
    frame = overlap.overlapping_returns(
        _returns(), [_window(DAYS[1], {"A": 1.0})], holding_period=3)
    # The window holds the 3 days after the selection date.
    assert list(frame.index) == list(DAYS[2:5])
    assert frame["return"].tolist() == pytest.approx([0.002, 0.003, 0.004])
    assert frame["depth"].tolist() == [1, 1, 1]


def test_a_day_in_two_windows_takes_the_mean_of_both():
    windows = [_window(DAYS[1], {"A": 1.0}),
               _window(DAYS[2], {"B": 1.0})]
    frame = overlap.overlapping_returns(_returns(), windows, holding_period=3)
    assert list(frame.index) == list(DAYS[2:6])
    # Day 2 only window 1. Days 3 and 4 both. Day 5 only window 2.
    assert frame["return"].tolist() == pytest.approx(
        [0.002, (0.003 + 0.002) / 2, (0.004 + 0.002) / 2, 0.002])
    assert frame["depth"].tolist() == [1, 2, 2, 1]


def test_the_weights_of_a_window_blend_the_stocks():
    frame = overlap.overlapping_returns(
        _returns(), [_window(DAYS[4], {"A": 0.5, "B": 0.5})],
        holding_period=1)
    assert frame["return"].iloc[0] == pytest.approx((0.005 + 0.002) / 2)


def test_a_window_with_no_result_does_not_count():
    windows = [_window(DAYS[1], {"A": 1.0}),
               _window(DAYS[1], {"B": 1.0}, scored=False),
               _window(DAYS[1], {})]
    frame = overlap.overlapping_returns(_returns(), windows, holding_period=2)
    assert frame["depth"].tolist() == [1, 1]
    assert frame["return"].tolist() == pytest.approx([0.002, 0.003])


def test_no_scored_window_gives_an_empty_frame():
    frame = overlap.overlapping_returns(_returns(), [], holding_period=2)
    assert frame.empty
    assert list(frame.columns) == ["return", "depth"]


# --- Newey-West --------------------------------------------------------------

def _random_xy(n=400, seed=1):
    rng = np.random.default_rng(seed)
    x = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
    y = x @ np.array([0.1, 0.5, -0.3]) + rng.normal(size=n)
    return x, y


def test_newey_west_gives_the_ols_coefficients():
    x, y = _random_xy()
    coef, _ = overlap.newey_west(y, x, lags=5)
    ols, *_ = np.linalg.lstsq(x, y, rcond=None)
    assert np.allclose(coef, ols, atol=1e-12)


def test_newey_west_with_no_lags_is_the_white_error():
    x, y = _random_xy()
    coef, se = overlap.newey_west(y, x, lags=0)
    u = y - x @ coef
    inv = np.linalg.inv(x.T @ x)
    white = inv @ (x.T @ np.diag(u ** 2) @ x) @ inv
    assert np.allclose(se, np.sqrt(np.diag(white)), rtol=1e-10)


def test_newey_west_of_a_mean_is_the_bartlett_long_run_variance():
    # With only a constant, the variance of the mean is the long-run
    # variance / n. The long-run variance uses the Bartlett weights
    # 1 - l / (L + 1) on the autocovariances.
    rng = np.random.default_rng(3)
    e = rng.normal(size=500)
    y = np.convolve(e, [1.0, 0.8, 0.5], mode="same")
    n, lags = len(y), 4
    x = np.ones((n, 1))
    _, se = overlap.newey_west(y, x, lags=lags)
    u = y - y.mean()
    gamma = [float(u[k:] @ u[:n - k]) / n for k in range(lags + 1)]
    long_run = gamma[0] + 2 * sum((1 - k / (lags + 1)) * gamma[k]
                                  for k in range(1, lags + 1))
    assert se[0] == pytest.approx(math.sqrt(long_run / n), rel=1e-10)


def test_newey_west_matches_the_double_sum_with_two_regressors():
    # The meat is the sum over every pair of days t, s with |t - s| <= L
    # of w(|t - s|) g_t g_s'. This form has no transposes to get wrong.
    x, y = _random_xy(n=120, seed=7)
    lags = 3
    coef, se = overlap.newey_west(y, x, lags=lags)
    g = x * (y - x @ coef)[:, None]
    n = len(y)
    meat = np.zeros((3, 3))
    for t in range(n):
        for s in range(max(0, t - lags), min(n, t + lags + 1)):
            meat += (1 - abs(t - s) / (lags + 1)) * np.outer(g[t], g[s])
    bread = np.linalg.inv(x.T @ x)
    expected = np.sqrt(np.diag(bread @ meat @ bread))
    assert np.allclose(se, expected, rtol=1e-10)


def test_newey_west_rejects_a_negative_lag():
    x, y = _random_xy()
    with pytest.raises(ValueError):
        overlap.newey_west(y, x, lags=-1)


# --- the regression ----------------------------------------------------------

def _factor_data(n=300, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=n)
    market = pd.Series(rng.normal(0.0004, 0.01, n), index=idx)
    umd = pd.Series(rng.normal(0.0002, 0.006, n), index=idx)
    return market, umd


def test_the_regression_recovers_a_known_portfolio():
    market, umd = _factor_data()
    rf = 0.045 / 252
    y = rf + 0.0001 + 1.2 * (market - rf) + 0.4 * umd
    result = overlap.regress(y, market, umd)
    assert result["alpha"] == pytest.approx(0.0001 * 252, abs=1e-10)
    assert result["beta"] == pytest.approx(1.2, abs=1e-10)
    assert result["umd"] == pytest.approx(0.4, abs=1e-10)
    assert result["days"] == 300


def test_a_difference_series_keeps_the_risk_free_rate():
    # A long-short difference costs nothing, so the regression must not
    # subtract the rate from it.
    market, umd = _factor_data()
    rf = 0.045 / 252
    y = 0.0001 + 0.1 * (market - rf) + 0.2 * umd
    result = overlap.regress(y, market, umd, excess=False)
    assert result["alpha"] == pytest.approx(0.0001 * 252, abs=1e-10)
    assert result["beta"] == pytest.approx(0.1, abs=1e-10)


def test_the_market_only_regression_has_no_umd():
    market, _ = _factor_data()
    rf = 0.045 / 252
    y = rf + 0.0002 + 0.9 * (market - rf)
    result = overlap.regress(y, market, None)
    assert result["alpha"] == pytest.approx(0.0002 * 252, abs=1e-10)
    assert result["beta"] == pytest.approx(0.9, abs=1e-10)
    assert math.isnan(result["umd"])


def test_the_regression_uses_only_the_common_days():
    market, umd = _factor_data()
    y = market.copy()
    result = overlap.regress(y, market, umd.iloc[:200])
    assert result["days"] == 200


# --- the table ---------------------------------------------------------------

def test_the_table_has_each_arm_and_each_difference():
    market, umd = _factor_data()
    rf = 0.045 / 252
    base = rf + 1.0 * (market - rf) + 0.1 * umd
    tilt = base + 0.0002 + 0.3 * umd
    table = overlap.difference_table({"ew": base, "robust": tilt}, "ew",
                                     market, {"french": umd, "none": None})
    assert list(table["series"]) == ["ew", "robust", "robust - ew"]
    assert set(table["source"]) == {"french"}
    diff = table.set_index("series").loc["robust - ew"]
    assert diff["alpha_2f"] == pytest.approx(0.0002 * 252, abs=1e-9)
    assert diff["umd"] == pytest.approx(0.3, abs=1e-9)
    assert diff["beta"] == pytest.approx(0.0, abs=1e-9)
    # The market-only alpha of the difference also holds the UMD premium.
    assert diff["alpha_1f"] == pytest.approx(
        (0.0002 + 0.3 * umd.mean()) * 252, abs=1e-3)


# --- the script --------------------------------------------------------------

def test_the_script_has_the_arms_of_d36():
    assert list(script.ARMS) == ["ew", "max_sharpe", "rob_none",
                                 "rob_stderr"]
    assert script.ARMS["ew"]["objective"] == "equal_weight"
    assert script.ARMS["rob_stderr"] == {"objective": "robust",
                                         "rho_rule": "stderr",
                                         "varrho": 0.02}


def test_the_script_defaults():
    args = script.make_parser().parse_args([])
    assert args.window_step == 5
    assert args.pool_size == 33
    assert args.lags == 20
