"""Download the prices of the universe and write them to a Parquet file.

The download list is every stock that was in a universe (the S&P 500 or
the Nasdaq universe) at some time in the date range, plus the benchmark.
The membership seeds list these stocks. Build the seeds first with
quant.reference.

This script calls the nasdaq API for each stock and cleans the rows. It
writes one long table of daily prices to data/raw_prices.parquet. The dbt
project reads that file as a source.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import datetime as dt

import duckdb
import requests

from quant import nasdaq, reference, universe

# The default date range. The nasdaq API returns clean data for this range.
DEFAULT_FROMDATE = "2022-11-01"
DEFAULT_TODATE = "2026-11-01"

# The columns in the price file, in order.
PRICE_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]

ROOT = Path(__file__).resolve().parents[1]
# The membership seeds. The download list joins all of them, so each
# universe in the dbt project has its prices.
MEMBERSHIP_SEEDS = [ROOT / "dbt" / "seeds" / "sp500_membership.csv",
                    ROOT / "dbt" / "seeds" / "nasdaq_membership.csv"]
PRICES_FILE = ROOT / "data" / "raw_prices.parquet"
# The symbols that the price source does not have. The download writes this
# file after each run. See decision D19.
MISSING_FILE = ROOT / "data" / "missing_symbols.csv"
# One cache file for each symbol. A stopped download continues from here.
CACHE_DIR = ROOT / "data" / "cache"


def download_symbols(membership_seeds: Path | list[Path], fromdate: str,
                     todate: str) -> list[str]:
    """Return the stocks to download, then the benchmark.

    A stock is in the list when a membership stint in one of the seeds
    overlaps the range.
    """
    if isinstance(membership_seeds, Path):
        membership_seeds = [membership_seeds]
    intervals = []
    for seed in membership_seeds:
        if seed.exists():
            with seed.open() as handle:
                intervals.extend(csv.DictReader(handle))
    stocks = reference.tickers_in_range(intervals, fromdate, todate)
    return [s for s in stocks if s != universe.BENCHMARK] + [universe.BENCHMARK]


def download_symbol(symbol: str, fromdate: str, todate: str,
                    session: requests.Session,
                    assetclass: str = "stocks") -> list[dict[str, Any]]:
    """Download and clean the price records for one symbol."""
    rows = nasdaq.fetch_historical(symbol, fromdate, todate, session=session,
                                   assetclass=assetclass)
    return nasdaq.normalize_rows(symbol, rows)


def cached_download(symbol: str, cache_dir: Path,
                    fetch: Callable[[str], list[dict[str, Any]]]
                    ) -> list[dict[str, Any]]:
    """Return the records of a symbol. Call the API only when no cache exists.

    The function caches an empty result too, because the API has no data for
    a stock that does not trade now. It does not cache an error, so the next
    run tries the symbol again.
    """
    path = cache_dir / f"{symbol}.json"
    if path.exists():
        return json.loads(path.read_text())
    records = fetch(symbol)
    cache_dir.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(records))
    temp.replace(path)
    return records


def write_prices_parquet(records: list[dict[str, Any]], path: Path) -> None:
    """Write the price records to a Parquet file with fixed column types."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "prices.csv"
        with staging.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=PRICE_COLUMNS)
            writer.writeheader()
            writer.writerows(records)
        duckdb.sql(
            f"""
            copy (
                select * from read_csv('{staging}', header = true, columns = {{
                    'ticker': 'varchar', 'date': 'date', 'open': 'double',
                    'high': 'double', 'low': 'double', 'close': 'double',
                    'volume': 'bigint'}})
                order by ticker, date
            ) to '{path}' (format parquet, compression zstd)
            """
        )


def download_all(symbols: list[str],
                 fetch: Callable[[str], list[dict[str, Any]]],
                 cache_dir: Path, workers: int = 3) -> dict[str, Any]:
    """Download every symbol, and sort the problems into two groups.

    Return a report with four parts:

      * `records`: the price rows of the symbols that the source has.
      * `no_rows`: the symbols that exist and have no trade in the range.
      * `missing`: the symbols that the source does not have, with the
        message of the API for each one. A company that left the market is
        in this group. This is a known gap, not a failure.
      * `failed`: the symbols with another error, for example a busy
        service or a broken connection.

    A symbol of the `missing` group does not go in the cache. The next run
    asks the API again, so the gap stays visible. A symbol with no trade
    does go in the cache, because that answer is a fact about the symbol.
    """
    def task(symbol: str) -> tuple[str, Any, str]:
        try:
            return symbol, cached_download(symbol, cache_dir, fetch), "ok"
        except nasdaq.SymbolNotFound as error:
            return symbol, str(error), "missing"
        except Exception as error:  # noqa: BLE001 - report and continue.
            print(f"  WARN {symbol}: {error}", file=sys.stderr, flush=True)
            return symbol, None, "failed"

    report: dict[str, Any] = {"records": [], "no_rows": [], "missing": {},
                              "failed": []}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for symbol, result, state in pool.map(task, symbols):
            if state == "missing":
                report["missing"][symbol] = result
                print(f"  {symbol:<6} not in the source", flush=True)
                continue
            if state == "failed":
                report["failed"].append(symbol)
                continue
            if not result:
                report["no_rows"].append(symbol)
            print(f"  {symbol:<6} {len(result):>4} rows", flush=True)
            report["records"].extend(result)
    return report


def write_missing_report(path: Path, missing: dict[str, str],
                         checked_on: str) -> None:
    """Write the symbols that the price source does not have.

    The pipeline cannot hold a stock with no prices. Each symbol in this
    file is therefore a hole in the universe of the backtest. The file
    makes the hole visible. The order is alphabetic, so the file changes
    only when the gap changes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        # One line ending, so git does not change the file.
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["ticker", "checked_on", "message"])
        for symbol in sorted(missing):
            writer.writerow([symbol, checked_on, missing[symbol]])


def run(fromdate: str, todate: str, pause: float = 1.0,
        workers: int = 3,
        fetch: Callable[[str], list[dict[str, Any]]] | None = None,
        symbols: list[str] | None = None,
        cache_dir: Path = CACHE_DIR,
        prices_file: Path = PRICES_FILE,
        missing_file: Path = MISSING_FILE) -> int:
    """Download every symbol and write the price file.

    Return the count of price rows written. Return 0 and write nothing
    when a symbol fails for a reason that a later run can repair.

    A symbol that the source does not have does not stop the write. Such a
    symbol is a company that left the market, and no later run can repair
    it. The count goes to the screen, and the symbols go to
    `data/missing_symbols.csv`.

    Use a few workers, and wait a short time after each call. This keeps
    the load on the API low. A finished symbol goes to the cache, so you
    can run this function again after a stop.
    """
    if symbols is None:
        symbols = download_symbols(MEMBERSHIP_SEEDS, fromdate, todate)

    if fetch is None:
        def fetch(symbol: str) -> list[dict[str, Any]]:
            # The benchmark is an ETF. Every other symbol is a stock.
            assetclass = "etf" if symbol == universe.BENCHMARK else "stocks"
            records = download_symbol(symbol, fromdate, todate,
                                      requests.Session(),
                                      assetclass=assetclass)
            time.sleep(pause)
            return records

    report = download_all(symbols, fetch, cache_dir, workers)
    missing, failed = report["missing"], report["failed"]

    write_missing_report(missing_file, missing,
                         checked_on=dt.date.today().isoformat())
    if failed:
        print(f"\n{len(failed)} symbol(s) failed: {' '.join(failed)}")
        print("Run the script again. It downloads only these symbols.")
        return 0
    write_prices_parquet(report["records"], prices_file)
    print(f"\nWrote {len(report['records'])} price rows for "
          f"{len(symbols)} symbol(s).")
    print(f"No trades for {len(report['no_rows'])} symbol(s): "
          f"{' '.join(report['no_rows'])}")
    print(f"\nThe price source does not have {len(missing)} of "
          f"{len(symbols)} symbol(s), which is "
          f"{len(missing) / max(len(symbols), 1):.1%}. These are companies "
          f"that left the market. The pipeline cannot hold them on a past "
          f"date, so the backtest holds a survivor of the period only.")
    print(f"The list is in {missing_file}.")
    return len(report["records"])


def main() -> None:
    """Parse the command line and run the download."""
    parser = argparse.ArgumentParser(description="Download the universe prices.")
    parser.add_argument("--fromdate", default=DEFAULT_FROMDATE)
    parser.add_argument("--todate", default=DEFAULT_TODATE)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    run(args.fromdate, args.todate, args.pause, args.workers)


if __name__ == "__main__":
    main()
