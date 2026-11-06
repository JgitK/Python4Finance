"""Tests for the ingest step.

The download list comes from the S&P 500 membership seed. The prices go to
a Parquet file. These tests do not use the network.
"""

from __future__ import annotations

import duckdb

from quant import ingest, universe


def test_download_symbols_come_from_the_membership_seed(tmp_path):
    seed = tmp_path / "sp500_membership.csv"
    seed.write_text(
        "ticker,start_date,end_date\n"
        "OLD,2000-01-03,2010-05-03\n"
        "LEFT,2001-01-02,2024-03-18\n"
        "STAY,2005-06-01,\n"
    )
    symbols = ingest.download_symbols(seed, "2022-11-01", "2026-11-01")
    # OLD left the index before the range. The benchmark is always in the list.
    assert symbols == ["LEFT", "STAY", universe.BENCHMARK]


def test_write_prices_parquet_round_trips(tmp_path):
    path = tmp_path / "raw_prices.parquet"
    records = [
        {"ticker": "AAA", "date": "2024-01-02", "open": 1.0, "high": 2.0,
         "low": 0.5, "close": 1.5, "volume": 100},
        {"ticker": "AAA", "date": "2024-01-03", "open": 1.5, "high": 2.5,
         "low": 1.0, "close": 2.0, "volume": None},
    ]
    ingest.write_prices_parquet(records, path)
    rows = duckdb.sql(
        f"select ticker, date, close, volume from read_parquet('{path}') order by date"
    ).fetchall()
    assert [r[0] for r in rows] == ["AAA", "AAA"]
    assert str(rows[0][1]) == "2024-01-02"
    assert rows[1][2] == 2.0
    assert rows[1][3] is None


# --- the download cache -----------------------------------------------------
# The download takes about one hour. A cache file for each symbol lets a
# stopped download continue without a new call for the finished symbols.

def test_cached_download_calls_the_api_one_time(tmp_path):
    calls = []

    def fake_fetch(symbol):
        calls.append(symbol)
        return [{"ticker": symbol, "date": "2024-01-02", "open": 1.0,
                 "high": 1.0, "low": 1.0, "close": 1.0, "volume": 5}]

    first = ingest.cached_download("AAA", tmp_path, fake_fetch)
    second = ingest.cached_download("AAA", tmp_path, fake_fetch)
    assert calls == ["AAA"]
    assert first == second


def test_cached_download_caches_a_symbol_with_no_rows(tmp_path):
    calls = []

    def fake_fetch(symbol):
        calls.append(symbol)
        return []

    ingest.cached_download("GONE", tmp_path, fake_fetch)
    ingest.cached_download("GONE", tmp_path, fake_fetch)
    # The API has no data for GONE. A new call does not change that.
    assert calls == ["GONE"]


def test_cached_download_does_not_cache_an_error(tmp_path):
    def broken_fetch(symbol):
        raise ConnectionError("network down")

    try:
        ingest.cached_download("AAA", tmp_path, broken_fetch)
    except ConnectionError:
        pass
    # The next run must try AAA again.
    assert not list(tmp_path.iterdir())
