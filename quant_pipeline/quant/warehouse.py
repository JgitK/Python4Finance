"""Read the dbt marts from the DuckDB warehouse.

dbt builds the warehouse file. This module opens that file and returns the
marts as pandas frames. The stats layer works on these frames.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

# The dbt project writes the warehouse here.
DEFAULT_WAREHOUSE = Path(__file__).resolve().parents[1] / "dbt" / "warehouse.duckdb"


def connect(path: Path = DEFAULT_WAREHOUSE,
            read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open the warehouse file."""
    return duckdb.connect(str(path), read_only=read_only)


def read_candidates(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return the screened candidate stocks, best first in each sector."""
    return con.execute(
        "select * from main.mart_screen_candidates order by sharpe_ratio desc"
    ).fetchdf()


def read_returns_matrix(con: duckdb.DuckDBPyConnection,
                        tickers: list[str] | None = None) -> pd.DataFrame:
    """Return the daily returns as a wide matrix.

    The rows are dates. The columns are tickers. When you supply a list,
    keep only those tickers.
    """
    frame = con.execute(
        "select ticker, price_date, daily_return from main.mart_daily_returns"
    ).fetchdf()
    wide = frame.pivot(index="price_date", columns="ticker",
                       values="daily_return").sort_index()
    if tickers is not None:
        wide = wide[tickers]
    return wide


def read_latest_prices(con: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """Return the most recent close of each stock."""
    frame = con.execute(
        """
        select ticker, close
        from (
            select ticker, close,
                   row_number() over (partition by ticker order by price_date desc) as rn
            from main.stg_prices
        )
        where rn = 1
        """
    ).fetchdf()
    return dict(zip(frame["ticker"], frame["close"]))


def read_sector_map(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """Return the sector of each stock."""
    frame = con.execute("select ticker, sector from main.dim_ticker").fetchdf()
    return dict(zip(frame["ticker"], frame["sector"]))


def read_screen_history(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return the screen on each date.

    Each row is one stock that passed the screen on one date. The screen on a
    date uses only the data up to that date. The backtest uses this frame.
    """
    frame = con.execute(
        "select as_of_date, ticker from main.mart_screen_history "
        "order by as_of_date, ticker"
    ).fetchdf()
    frame["as_of_date"] = pd.to_datetime(frame["as_of_date"])
    return frame


def read_universe_coverage(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return each index member on each trading day, with data flags."""
    frame = con.execute(
        "select as_of_date, ticker, has_prices, has_sector "
        "from main.mart_universe_coverage"
    ).fetchdf()
    frame["as_of_date"] = pd.to_datetime(frame["as_of_date"])
    return frame
