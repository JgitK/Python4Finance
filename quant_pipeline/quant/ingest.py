"""Download the universe and write the dbt seed files.

This script calls the nasdaq API for each stock. It cleans the rows.
It writes two seed files for dbt:
  - raw_prices.csv   one long table of daily prices for all stocks.
  - stock_sectors.csv  the sector of each stock.
Run this script to refresh the data. The dbt models read the seed files.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any

import requests

from quant import nasdaq, universe

# The default date range. The nasdaq API returns clean data for this range.
DEFAULT_FROMDATE = "2022-11-01"
DEFAULT_TODATE = "2026-11-01"

# The columns in the price seed file, in order.
PRICE_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]

# The folder that holds the dbt seed files.
SEEDS_DIR = Path(__file__).resolve().parents[1] / "dbt" / "seeds"


def download_symbol(symbol: str, fromdate: str, todate: str,
                    session: requests.Session,
                    assetclass: str = "stocks") -> list[dict[str, Any]]:
    """Download and clean the price records for one symbol."""
    rows = nasdaq.fetch_historical(symbol, fromdate, todate, session=session,
                                   assetclass=assetclass)
    return nasdaq.normalize_rows(symbol, rows)


def write_prices_csv(records: list[dict[str, Any]], path: Path) -> None:
    """Write the price records to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRICE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def write_sectors_csv(path: Path) -> None:
    """Write the ticker and sector of each stock to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "sector"])
        for ticker in universe.tickers():
            writer.writerow([ticker, universe.UNIVERSE[ticker]])


def run(fromdate: str, todate: str, pause: float = 1.0) -> int:
    """Download every symbol and write the seed files.

    Return the count of price rows written.
    Wait a short time between calls. This decreases the load on the API.
    """
    session = requests.Session()
    all_records: list[dict[str, Any]] = []
    symbols = universe.all_download_symbols()

    for symbol in symbols:
        # The benchmark is an ETF. Every other symbol is a stock.
        assetclass = "etf" if symbol == universe.BENCHMARK else "stocks"
        try:
            records = download_symbol(symbol, fromdate, todate, session,
                                      assetclass=assetclass)
        except Exception as error:  # noqa: BLE001 - report and continue.
            print(f"  WARN {symbol}: {error}", file=sys.stderr)
            records = []
        print(f"  {symbol:<6} {len(records):>4} rows")
        all_records.extend(records)
        time.sleep(pause)

    write_prices_csv(all_records, SEEDS_DIR / "raw_prices.csv")
    write_sectors_csv(SEEDS_DIR / "stock_sectors.csv")
    print(f"\nWrote {len(all_records)} price rows for {len(symbols)} symbols.")
    return len(all_records)


def main() -> None:
    """Parse the command line and run the download."""
    parser = argparse.ArgumentParser(description="Download the stock universe.")
    parser.add_argument("--fromdate", default=DEFAULT_FROMDATE)
    parser.add_argument("--todate", default=DEFAULT_TODATE)
    parser.add_argument("--pause", type=float, default=1.0)
    args = parser.parse_args()
    run(args.fromdate, args.todate, args.pause)


if __name__ == "__main__":
    main()
