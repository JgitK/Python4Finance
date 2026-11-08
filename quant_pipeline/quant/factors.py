"""The momentum factor and the two-factor regression (D30).

The screen ranks the stocks on the trailing compound return (D22). That is
the classic momentum signal. Momentum is a known premium: a portfolio of
past winners less a portfolio of past losers earns a positive return on
average. The CAPM of D25 has only the market factor. Thus the alpha of D25
can be the momentum premium and not skill.

This module adds the momentum factor UMD ("up minus down", also "winners
minus losers"). It regresses the excess return of the portfolio on the
market excess return and on UMD. The momentum loading says how much the
portfolio follows UMD. The two-factor alpha is the return that neither
factor explains.

The module has two sources of UMD:

- The Ken French Data Library. It uses all NYSE, AMEX and NASDAQ stocks
  of CRSP, with the dead stocks. `read_french_csv` reads its files.
- An in-house factor from the prices of the project. `build_umd` makes it.
  It has the survivorship bias of the project, and it uses the same
  universe as the portfolio.

All the functions use simple daily returns, the same as the backtest.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

# The regression has 3 coefficients. It needs at least 2 more days to
# estimate the variance of the residual with some freedom.
MIN_DAYS = 5
# A |t| at or above this value is significant at the 5% level.
T_SIGNIFICANT = 1.96

_KEYS = ("alpha", "alpha_t", "beta", "beta_t", "umd_loading", "umd_t",
         "r_squared")


def _empty(n_days: int) -> dict[str, Any]:
    result: dict[str, Any] = {key: float("nan") for key in _KEYS}
    result["n_days"] = n_days
    return result


def regress_two_factor(asset: pd.Series, market: pd.Series, umd: pd.Series,
                       risk_free: float = 0.045,
                       trading_days: int = 252) -> dict[str, Any]:
    """Regress the excess return of one series on the market and on UMD.

    The model is: asset - rf = alpha + beta * (market - rf) + loading * UMD.
    The function subtracts the daily risk-free rate from the asset and from
    the market, the same as `quant.capm`. It does not subtract the rate
    from UMD, because UMD is a long-short return that costs nothing.

    Return the annual alpha (the daily intercept times the trading days),
    the beta, the momentum loading, the t statistic of each coefficient,
    the R squared, and the count of days. The t statistics use the
    ordinary least-squares standard errors.

    The function uses only the dates that hold a value in all three series.
    With fewer than `MIN_DAYS` days, or with a factor that does not move,
    the function gives NaN for each measure.
    """
    frame = pd.concat([pd.Series(asset), pd.Series(market), pd.Series(umd)],
                      axis=1, join="inner").dropna()
    n_days = int(len(frame))
    if n_days < MIN_DAYS:
        return _empty(n_days)

    rf_daily = risk_free / trading_days
    y = frame.iloc[:, 0].to_numpy() - rf_daily
    x = np.column_stack([np.ones(n_days),
                         frame.iloc[:, 1].to_numpy() - rf_daily,
                         frame.iloc[:, 2].to_numpy()])
    xtx = x.T @ x
    # A factor that does not move makes the matrix singular. Such a factor
    # has no loading.
    if np.linalg.matrix_rank(xtx) < 3:
        return _empty(n_days)

    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ coef
    sigma2 = float(residual @ residual) / (n_days - 3)
    std_err = np.sqrt(np.diag(sigma2 * np.linalg.inv(xtx)))
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = coef / std_err

    total = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - float(residual @ residual) / total if total > 0 \
        else float("nan")
    return {
        "alpha": float(coef[0]) * trading_days,
        "alpha_t": float(t_stat[0]),
        "beta": float(coef[1]),
        "beta_t": float(t_stat[1]),
        "umd_loading": float(coef[2]),
        "umd_t": float(t_stat[2]),
        "r_squared": r_squared,
        "n_days": n_days,
    }
