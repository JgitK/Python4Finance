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
