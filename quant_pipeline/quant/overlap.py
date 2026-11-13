"""The overlapping-portfolio momentum regression (D36).

The walk-forward windows start every few days and each one holds for 180
days, so the windows overlap. A regression on each window uses the same
days many times, and the t statistics are then too large.

This module makes one daily series for each arm. On each day, the series
holds the mean return of every window that holds on that day. Jegadeesh
and Titman (1993) built their momentum portfolios the same way. The
module then regresses the series on the market and on UMD. The t
statistics use Newey-West errors, because the daily series still has some
autocorrelation.

The difference of two arms, for example robust minus equal weight, is a
long-short series. It costs nothing, so the regression does not subtract
the risk-free rate from it.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quant import backtest


def overlapping_returns(returns: pd.DataFrame, windows: list[dict[str, Any]],
                        holding_period: int) -> pd.DataFrame:
    """Give the mean daily return of the windows that hold on each day.

    Return a frame with the columns `return` and `depth`. The depth is the
    count of windows that hold on that day. A window that
    `backtest.window_is_scored` rejects does not count.
    """
    columns = []
    for window in windows:
        if not backtest.window_is_scored(window):
            continue
        _, test = backtest.split_by_date(returns, window["selection_date"])
        held = backtest.holding_window(test, holding_period)
        columns.append(backtest.portfolio_daily_returns(held,
                                                        window["weights"]))
    if not columns:
        return pd.DataFrame(columns=["return", "depth"])
    frame = pd.concat(columns, axis=1)
    return pd.DataFrame({"return": frame.mean(axis=1),
                         "depth": frame.count(axis=1)})


def newey_west(y: np.ndarray, x: np.ndarray,
               lags: int) -> tuple[np.ndarray, np.ndarray]:
    """Give the OLS coefficients and their Newey-West standard errors.

    The errors use the Bartlett weights 1 - l / (lags + 1). With 0 lags,
    they are the White errors.
    """
    if lags < 0:
        raise ValueError(f"lags must be 0 or more, not {lags}.")
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    scores = x * (y - x @ coef)[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1.0 - lag / (lags + 1)) * (cross + cross.T)
    bread = np.linalg.inv(x.T @ x)
    return coef, np.sqrt(np.diag(bread @ meat @ bread))


def regress(series: pd.Series, market: pd.Series, umd: pd.Series | None,
            risk_free: float = 0.045, trading_days: int = 252,
            excess: bool = True, lags: int = 20) -> dict[str, Any]:
    """Regress a daily series on the market, and on UMD when it is given.

    The model is: y = alpha + beta * (market - rf) + loading * UMD. With
    `excess`, y is the series minus the daily rate. Use `excess=False` for
    a long-short difference. Only the days with a value in each series
    count. The alpha is annual.
    """
    parts = [series, market] + ([] if umd is None else [umd])
    frame = pd.concat(parts, axis=1, join="inner").dropna()
    rf = risk_free / trading_days
    y = frame.iloc[:, 0].to_numpy() - (rf if excess else 0.0)
    x = [np.ones(len(frame)), frame.iloc[:, 1].to_numpy() - rf]
    if umd is not None:
        x.append(frame.iloc[:, 2].to_numpy())
    coef, se = newey_west(y, np.column_stack(x), lags)
    t = coef / se
    has_umd = umd is not None
    return {"alpha": float(coef[0]) * trading_days,
            "alpha_t": float(t[0]),
            "beta": float(coef[1]),
            "umd": float(coef[2]) if has_umd else float("nan"),
            "umd_t": float(t[2]) if has_umd else float("nan"),
            "days": int(len(frame))}


def difference_table(series: dict[str, pd.Series], baseline: str,
                     market: pd.Series,
                     umd_sources: dict[str, pd.Series | None],
                     risk_free: float = 0.045, trading_days: int = 252,
                     lags: int = 20) -> pd.DataFrame:
    """Give one row for each arm and each difference from the baseline.

    For each UMD source that is not None, the table holds every arm, then
    each arm minus the baseline. Each row has the market-only alpha
    (`alpha_1f`) and the alpha after the market and UMD (`alpha_2f`).
    """
    rows = []
    for source, umd in umd_sources.items():
        if umd is None:
            continue
        cases = [(name, s, True) for name, s in series.items()]
        cases += [(f"{name} - {baseline}", s - series[baseline], False)
                  for name, s in series.items() if name != baseline]
        for name, s, excess in cases:
            one = regress(s, market, None, risk_free, trading_days, excess,
                          lags)
            two = regress(s, market, umd, risk_free, trading_days, excess,
                          lags)
            rows.append({"source": source, "series": name,
                         "alpha_1f": one["alpha"], "alpha_1f_t": one["alpha_t"],
                         "alpha_2f": two["alpha"], "alpha_2f_t": two["alpha_t"],
                         "beta": two["beta"], "umd": two["umd"],
                         "umd_t": two["umd_t"], "days": two["days"]})
    return pd.DataFrame(rows)
