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
import zipfile
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from quant import backtest, capm

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



def formation_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Give the last trading day of each calendar month in the index.

    The factor forms its legs at the close of these days. The last month of
    the data can end before the calendar month ends. Its last day is then a
    formation date with no hold after it.
    """
    index = pd.DatetimeIndex(index)
    if index.empty:
        return []
    months = index.to_period("M")
    last = pd.Series(index, index=index).groupby(months).max()
    return [pd.Timestamp(day) for day in last.sort_values()]


def _members_on(members: pd.DataFrame | None, date: pd.Timestamp,
                columns: pd.Index) -> list[str]:
    """Give the index members on a date that have a column of returns.

    Use the latest membership on or before the date. A later membership is
    future data. With no membership frame, every column is a member.
    """
    if members is None:
        return list(columns)
    dates = pd.to_datetime(members["as_of_date"])
    past = dates[dates <= date]
    if past.empty:
        return []
    on_day = set(members.loc[dates == past.max(), "ticker"])
    return [ticker for ticker in columns if ticker in on_day]


def umd_legs(returns: pd.DataFrame, members: pd.DataFrame | None,
             lookback: int = 252, skip: int = 21,
             quantile: float = 0.3) -> list[dict[str, Any]]:
    """Give the long leg and the short leg on each formation date.

    This is the rule of the in-house momentum factor:

    1. The formation date is the last trading day of each month.
    2. A stock is eligible when it is an index member on the formation date
       and it has a return on each day of the formation window.
    3. The signal is the compound return from the close `lookback` rows
       before the formation date to the close `skip` rows before it. With
       252 and 21, this is the 12-month return without the last month.
    4. The long leg holds the top `quantile` of the eligible stocks by the
       signal. The short leg holds the bottom `quantile`. Each leg holds
       floor(count * quantile) stocks. A tie goes to the ticker order.

    The rule reads only the returns up to the formation date, and the
    membership on or before it. Return one entry for each formation date
    with a full window and with at least one stock in each leg.
    """
    legs = []
    for date in formation_dates(returns.index):
        position = returns.index.get_loc(date)
        start = position - lookback + 1
        end = position - skip
        if start < 0 or end < start:
            continue
        eligible = _members_on(members, date, returns.columns)
        window = returns.iloc[start:end + 1][eligible].dropna(axis=1)
        count = int(math.floor(window.shape[1] * quantile + 1e-9))
        if count < 1:
            continue
        signal = (1.0 + window).prod() - 1.0
        order = (pd.DataFrame({"ticker": signal.index,
                               "signal": signal.to_numpy()})
                 .sort_values(["signal", "ticker"],
                              ascending=[False, True]))
        ranked = order["ticker"].tolist()
        legs.append({"formation_date": date,
                     "long": sorted(ranked[:count]),
                     "short": sorted(ranked[-count:])})
    return legs


def build_umd(returns: pd.DataFrame, members: pd.DataFrame | None,
              lookback: int = 252, skip: int = 21,
              quantile: float = 0.3) -> pd.Series:
    """Build the in-house daily UMD factor: winners minus losers.

    `umd_legs` forms the legs at the close of each formation date. The
    factor holds the legs from the next trading day to the next formation
    date, and the next formation date too. On each day, the factor return
    is the equal-weight mean return of the long leg less the equal-weight
    mean return of the short leg. A stock with no return on a day does not
    count on that day.

    The factor inherits the survivorship bias of the price data. A company
    that left the market has no prices, so it is in no leg. Dead losers are
    missing from the short leg, and the factor return is too high.
    """
    legs = umd_legs(returns, members, lookback, skip, quantile)
    pieces = []
    for number, leg in enumerate(legs):
        first = returns.index.get_loc(leg["formation_date"]) + 1
        if number + 1 < len(legs):
            last = returns.index.get_loc(legs[number + 1]["formation_date"])
        else:
            last = len(returns.index) - 1
        hold = returns.iloc[first:last + 1]
        if hold.empty:
            continue
        pieces.append(hold[leg["long"]].mean(axis=1)
                      - hold[leg["short"]].mean(axis=1))
    if not pieces:
        return pd.Series(dtype=float, name="umd")
    return pd.concat(pieces).dropna().rename("umd")



# The Ken French Data Library. The files are free to use with a citation.
FRENCH_URL = ("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
              "ftp/")
FRENCH_FILES = {
    "momentum": "F-F_Momentum_Factor_daily_CSV.zip",
    "three_factor": "F-F_Research_Data_Factors_daily_CSV.zip",
}
# The project keeps a copy of the files here. Git holds the copy.
FRENCH_DIR = Path(__file__).resolve().parents[1] / "data" / "french"
# The French files mark a missing value with one of these numbers.
_FRENCH_MISSING = (-99.99, -999.0)
_FRENCH_NAMES = {"Mom": "umd", "Mkt-RF": "mkt_rf", "SMB": "smb",
                 "HML": "hml", "RF": "rf"}


def read_french_csv(text: str) -> pd.DataFrame:
    """Read the first daily table of a Ken French CSV file.

    The file has lines of text, then a header line that starts with a
    comma, then one line for each day (YYYYMMDD, values in percent), then
    a blank line. The function gives the values as decimals, with a date
    index. It names the columns umd, mkt_rf, smb, hml and rf. A value of
    -99.99 or -999 is missing, so it becomes NaN.
    """
    lines = text.splitlines()
    start = next(number for number, line in enumerate(lines)
                 if line.startswith(","))
    names = [_FRENCH_NAMES.get(name.strip(), name.strip().lower())
             for name in lines[start].split(",")[1:]]
    dates, rows = [], []
    for line in lines[start + 1:]:
        cells = [cell.strip() for cell in line.split(",")]
        if len(cells[0]) != 8 or not cells[0].isdigit():
            break
        dates.append(pd.Timestamp(cells[0]))
        rows.append([float(cell) for cell in cells[1:]])
    frame = pd.DataFrame(rows, index=pd.DatetimeIndex(dates), columns=names)
    frame = frame.mask(frame.isin(_FRENCH_MISSING))
    return frame / 100.0


def _read_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist()
                    if n.lower().endswith(".csv"))
        text = archive.read(name).decode("latin-1")
    return read_french_csv(text)


def load_french_factors(folder: Path = FRENCH_DIR) -> pd.DataFrame | None:
    """Read the French momentum factor and the three factors from a folder.

    Return one frame with the columns umd, mkt_rf, smb, hml and rf, on the
    dates that hold every value. Return None when a file is not in the
    folder.
    """
    folder = Path(folder)
    paths = [folder / FRENCH_FILES[key]
             for key in ("momentum", "three_factor")]
    if not all(path.exists() for path in paths):
        return None
    frames = [_read_zip(path) for path in paths]
    return pd.concat(frames, axis=1, join="inner").dropna()


def _fetch(url: str) -> bytes:
    import requests
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def download_french(folder: Path = FRENCH_DIR,
                    fetch: Callable[[str], bytes] | None = None,
                    refresh: bool = False) -> list[Path]:
    """Download the two French files into a folder.

    Keep a file that is already in the folder, unless `refresh` is True.
    Return the paths of the files.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fetch = fetch or _fetch
    paths = []
    for name in FRENCH_FILES.values():
        path = folder / name
        if refresh or not path.exists():
            path.write_bytes(fetch(FRENCH_URL + name))
        paths.append(path)
    return paths



def portfolio_two_factor(returns: pd.DataFrame, weights: dict[str, float],
                         benchmark: str, umd: pd.Series,
                         risk_free: float = 0.045,
                         trading_days: int = 252) -> dict[str, Any]:
    """Regress a portfolio with fixed weights on the market and on UMD.

    Return the measures of `regress_two_factor`, and `capm_alpha`: the
    one-factor alpha of `quant.capm` on the same days. The UMD series can
    end before the returns. The two alphas must use the same days, or the
    comparison mixes two periods.
    """
    daily = backtest.portfolio_daily_returns(returns, weights)
    result = regress_two_factor(daily, returns[benchmark], umd, risk_free,
                                trading_days)
    common = pd.concat([daily, returns[benchmark], umd], axis=1,
                       join="inner").dropna()
    one = capm.regress_on_market(common.iloc[:, 0], common.iloc[:, 1],
                                 risk_free, trading_days)
    result["capm_alpha"] = one["alpha"]
    result["capm_beta"] = one["beta"]
    return result


def window_two_factor(returns: pd.DataFrame, window: dict[str, Any],
                      holding_period: int, benchmark: str, umd: pd.Series,
                      risk_free: float = 0.045,
                      trading_days: int = 252) -> dict[str, Any]:
    """Regress one walk-forward window on the market and on UMD.

    The window is a result of `quant.backtest.backtest_window`. The
    function takes the same holding days as the backtest: the
    `holding_period` days after the selection date. It holds the weights
    of the window.
    """
    _, test = backtest.split_by_date(returns, window["selection_date"])
    held = backtest.holding_window(test, holding_period)
    result = portfolio_two_factor(held, window["weights"], benchmark, umd,
                                  risk_free, trading_days)
    return {"selection_date": pd.Timestamp(window["selection_date"]),
            **result}


def factor_table(returns: pd.DataFrame, windows: list[dict[str, Any]],
                 holding_period: int, benchmark: str, umd: pd.Series,
                 risk_free: float = 0.045,
                 trading_days: int = 252) -> pd.DataFrame:
    """Give one row of two-factor measures for each scored window.

    A window that `quant.backtest.window_is_scored` rejects has no row.
    """
    rows = [window_two_factor(returns, window, holding_period, benchmark,
                              umd, risk_free, trading_days)
            for window in windows if backtest.window_is_scored(window)]
    return pd.DataFrame(rows)


def summarize_factor_table(table: pd.DataFrame) -> dict[str, Any]:
    """Summarize the two-factor measures of many windows.

    Return the count of the windows, the median and the mean momentum
    loading, the share of the windows with a significant positive loading
    (t at or above 1.96), the share with a significant loading of either
    sign, the median and the mean of the one-factor and the two-factor
    alpha, the share of the windows with a positive two-factor alpha, and
    the share of the one-factor alpha that the momentum explains:
    1 - two-factor alpha / one-factor alpha, for the mean and the median.

    The windows overlap. A share is a measure, not a test of significance.
    """
    nothing = float("nan")
    summary: dict[str, Any] = {
        "n_windows": 0, "median_umd_loading": nothing,
        "mean_umd_loading": nothing, "share_umd_positive_significant": nothing,
        "share_umd_significant": nothing, "median_capm_alpha": nothing,
        "mean_capm_alpha": nothing, "median_alpha": nothing,
        "mean_alpha": nothing, "share_alpha_positive": nothing,
        "explained_mean": nothing, "explained_median": nothing,
    }
    if table is None or table.empty:
        return summary
    rows = table.dropna(subset=["umd_loading", "umd_t", "alpha",
                                "capm_alpha"])
    summary["n_windows"] = int(len(rows))
    if rows.empty:
        return summary
    loading = rows["umd_loading"].to_numpy(dtype=float)
    t_stat = rows["umd_t"].to_numpy(dtype=float)
    alpha = rows["alpha"].to_numpy(dtype=float)
    one = rows["capm_alpha"].to_numpy(dtype=float)
    summary.update({
        "median_umd_loading": float(np.median(loading)),
        "mean_umd_loading": float(loading.mean()),
        "share_umd_positive_significant": float((t_stat >= T_SIGNIFICANT)
                                                .mean()),
        "share_umd_significant": float((np.abs(t_stat) >= T_SIGNIFICANT)
                                       .mean()),
        "median_capm_alpha": float(np.median(one)),
        "mean_capm_alpha": float(one.mean()),
        "median_alpha": float(np.median(alpha)),
        "mean_alpha": float(alpha.mean()),
        "share_alpha_positive": float((alpha > 0).mean()),
    })
    if summary["mean_capm_alpha"] != 0:
        summary["explained_mean"] = (1.0 - summary["mean_alpha"]
                                     / summary["mean_capm_alpha"])
    if summary["median_capm_alpha"] != 0:
        summary["explained_median"] = (1.0 - summary["median_alpha"]
                                       / summary["median_capm_alpha"])
    return summary



# The limits of the SPY sanity check. SPY holds the 500 largest US stocks
# and the French market holds all of them, so the beta is near 1 and not
# exactly 1. SPY also pays a fee of 0.09% a year.
SPY_BETA_TOLERANCE = 0.05
SPY_UMD_TOLERANCE = 0.05
SPY_ALPHA_TOLERANCE = 0.02


def spy_sanity_check(spy: pd.Series, french: pd.DataFrame,
                     trading_days: int = 252) -> dict[str, Any]:
    """Regress SPY on the French market factor and the French UMD.

    SPY is the market, so the result must give a beta near 1, a momentum
    loading near 0 and an alpha near 0. The function subtracts the daily
    French risk-free rate from SPY, because the French market factor uses
    that rate. Return the measures of `regress_two_factor` and `passed`.
    """
    frame = pd.concat([pd.Series(spy, name="spy"),
                       french[["mkt_rf", "umd", "rf"]]],
                      axis=1, join="inner").dropna()
    result = regress_two_factor(frame["spy"] - frame["rf"], frame["mkt_rf"],
                                frame["umd"], 0.0, trading_days)
    result["passed"] = bool(
        abs(result["beta"] - 1.0) <= SPY_BETA_TOLERANCE
        and abs(result["umd_loading"]) <= SPY_UMD_TOLERANCE
        and abs(result["alpha"]) <= SPY_ALPHA_TOLERANCE)
    return result



def momentum_sources(returns: pd.DataFrame, members: pd.DataFrame | None,
                     benchmark: str, french_dir: Path = FRENCH_DIR,
                     lookback: int = 252, skip: int = 21,
                     quantile: float = 0.3) -> dict[str, Any]:
    """Give the two UMD series and the facts that compare them.

    Return a dict with these keys:

    - `french`: the French UMD series, or None without the cached files.
    - `french_frame`: all the French factors, or None.
    - `in_house`: the in-house UMD of `build_umd`. The benchmark is never
      in a leg.
    - `primary`: "french" when the French files exist, else "in_house".
      The French factor is the primary source, because it has no
      survivorship bias and it does not come from the universe of the
      portfolio.
    - `correlation` and `correlation_days`: the daily correlation of the
      two series on their common days. NaN without the French files.
    """
    stocks = returns.drop(columns=[benchmark], errors="ignore")
    in_house = build_umd(stocks, members, lookback, skip, quantile)
    french_frame = load_french_factors(french_dir)
    french = None if french_frame is None else french_frame["umd"]
    correlation, days = float("nan"), 0
    if french is not None:
        both = pd.concat([in_house, french], axis=1, join="inner").dropna()
        days = int(len(both))
        if days > 2:
            correlation = float(both.iloc[:, 0].corr(both.iloc[:, 1]))
    return {"french": french, "french_frame": french_frame,
            "in_house": in_house,
            "primary": "french" if french is not None else "in_house",
            "correlation": correlation, "correlation_days": days}


def backtest_columns(returns: pd.DataFrame, windows: list[dict[str, Any]],
                     holding_period: int, benchmark: str, umd: pd.Series,
                     risk_free: float = 0.045,
                     trading_days: int = 252) -> pd.DataFrame:
    """Give the momentum columns of the backtest table, one row a window.

    The columns are the UMD loading, its t statistic and the two-factor
    annual alpha. A window with no result gets NaN.
    """
    rows = []
    for window in windows:
        if backtest.window_is_scored(window):
            result = window_two_factor(returns, window, holding_period,
                                       benchmark, umd, risk_free,
                                       trading_days)
        else:
            result = _empty(0)
        rows.append({"umd_loading": result["umd_loading"],
                     "umd_t": result["umd_t"],
                     "two_factor_alpha": result["alpha"]})
    return pd.DataFrame(rows, columns=["umd_loading", "umd_t",
                                       "two_factor_alpha"])


def summary_lines(label: str, summary: dict[str, Any]) -> list[str]:
    """Write the summary of `summarize_factor_table` as lines of text."""
    return [
        f"{label}: {summary['n_windows']} windows. UMD loading median "
        f"{summary['median_umd_loading']:+.2f}, mean "
        f"{summary['mean_umd_loading']:+.2f}. Significant and positive in "
        f"{summary['share_umd_positive_significant']:.1%} of the windows "
        f"(either sign {summary['share_umd_significant']:.1%}).",
        f"    alpha with the market only: median "
        f"{summary['median_capm_alpha']:+.2%}, mean "
        f"{summary['mean_capm_alpha']:+.2%}. With the market and UMD: median "
        f"{summary['median_alpha']:+.2%}, mean {summary['mean_alpha']:+.2%}, "
        f"positive in {summary['share_alpha_positive']:.1%}.",
        f"    UMD explains {summary['explained_median']:.0%} of the median "
        f"alpha and {summary['explained_mean']:.0%} of the mean alpha.",
    ]


def live_two_factor(returns: pd.DataFrame, weights: dict[str, float],
                    benchmark: str, umd: pd.Series, lookback_days: int,
                    risk_free: float = 0.045,
                    trading_days: int = 252) -> dict[str, Any]:
    """Regress the live portfolio on the market and on UMD.

    The function uses the last `lookback_days` rows, the same window as
    `quant.pipeline.live_capm`. The measures are in-sample, because the
    weights come from the same window.
    """
    window = returns[list(weights) + [benchmark]].tail(lookback_days)
    return portfolio_two_factor(window, weights, benchmark, umd, risk_free,
                                trading_days)
