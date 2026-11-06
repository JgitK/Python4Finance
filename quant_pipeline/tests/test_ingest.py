"""Tests for the ingest step.

The download list comes from the S&P 500 membership seed. The prices go to
a Parquet file. These tests do not use the network.
"""

from __future__ import annotations

import duckdb

from quant import ingest, nasdaq, universe


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


def test_download_symbols_join_every_membership_seed(tmp_path):
    sp500 = tmp_path / "sp500_membership.csv"
    sp500.write_text("ticker,start_date,end_date\nAAPL,1982-11-30,\nKO,1957-03-04,\n")
    nasdaq = tmp_path / "nasdaq_membership.csv"
    nasdaq.write_text("ticker,start_date,end_date\nAAPL,2022-11-01,\nZZZ,2023-02-01,\n")
    symbols = ingest.download_symbols([sp500, nasdaq], "2022-11-01", "2026-11-01")
    # AAPL is in both seeds. The list has it one time.
    assert symbols == ["AAPL", "KO", "ZZZ", universe.BENCHMARK]


# ---------------------------------------------------------------------------
# The two kinds of problem.
#
# The API does not have a symbol of a company that left the market. That is
# a known gap, and the download must record it and continue. Another error,
# for example a busy service, is a failure, and the download must stop
# before it writes a price file with a hole in it. See D19.


def _rows(symbol: str) -> list[dict]:
    return [{"ticker": symbol, "date": "2023-01-03", "open": 1.0, "high": 1.0,
             "low": 1.0, "close": 1.0, "volume": 100}]


def test_download_all_separates_a_missing_symbol_from_a_failure(tmp_path):
    def fake_fetch(symbol):
        if symbol == "GONE":
            raise nasdaq.SymbolNotFound("GONE: the nasdaq API answered "
                                       "rCode 400. Symbol not exists.")
        if symbol == "BROKEN":
            raise RuntimeError("the network is down")
        if symbol == "QUIET":
            return []
        return _rows(symbol)

    report = ingest.download_all(["AAA", "GONE", "BROKEN", "QUIET"],
                                 fake_fetch, tmp_path, workers=1)
    assert [r["ticker"] for r in report["records"]] == ["AAA"]
    assert list(report["missing"]) == ["GONE"]
    assert report["failed"] == ["BROKEN"]
    assert report["no_rows"] == ["QUIET"]
    # The message of the API goes into the report, as the evidence.
    assert "Symbol not exists." in report["missing"]["GONE"]


def test_download_all_does_not_cache_a_missing_symbol(tmp_path):
    # The old code cached the empty answer of an error, so the gap stayed
    # out of sight for every later run. The next run must ask again.
    calls = []

    def fake_fetch(symbol):
        calls.append(symbol)
        raise nasdaq.SymbolNotFound("GONE: Symbol not exists.")

    ingest.download_all(["GONE"], fake_fetch, tmp_path, workers=1)
    ingest.download_all(["GONE"], fake_fetch, tmp_path, workers=1)
    assert calls == ["GONE", "GONE"]
    assert not (tmp_path / "GONE.json").exists()


def test_download_all_caches_a_symbol_with_no_trades(tmp_path):
    # A symbol that exists and has no trade is not an error. One call only.
    calls = []

    def fake_fetch(symbol):
        calls.append(symbol)
        return []

    ingest.download_all(["QUIET"], fake_fetch, tmp_path, workers=1)
    ingest.download_all(["QUIET"], fake_fetch, tmp_path, workers=1)
    assert calls == ["QUIET"]


def test_write_missing_report_holds_each_symbol_and_the_date(tmp_path):
    path = tmp_path / "missing_symbols.csv"
    ingest.write_missing_report(path, {"GONE": "Symbol not exists.",
                                       "ALSO": "Symbol not exists."},
                                checked_on="2026-11-06")
    # The file must use one line ending, so git does not change it.
    assert b"\r" not in path.read_bytes()
    lines = path.read_text().splitlines()
    assert lines[0] == "ticker,checked_on,message"
    # The order is alphabetic, so the file does not change between runs.
    assert lines[1].startswith("ALSO,2026-11-06,")
    assert lines[2].startswith("GONE,2026-11-06,")


def test_run_writes_the_prices_when_only_a_symbol_is_missing(tmp_path):
    def fake_fetch(symbol):
        if symbol == "GONE":
            raise nasdaq.SymbolNotFound("GONE: Symbol not exists.")
        return _rows(symbol)

    prices = tmp_path / "raw_prices.parquet"
    missing = tmp_path / "missing_symbols.csv"
    rows = ingest.run("2023-01-01", "2023-01-31", pause=0.0, workers=1,
                      fetch=fake_fetch, symbols=["AAA", "GONE"],
                      cache_dir=tmp_path / "cache", prices_file=prices,
                      missing_file=missing)
    # The file holds the one symbol that the source has.
    assert rows == 1
    assert prices.exists()
    assert "GONE" in missing.read_text()


def test_run_does_not_write_the_prices_after_a_failure(tmp_path):
    def fake_fetch(symbol):
        if symbol == "BROKEN":
            raise RuntimeError("the network is down")
        return _rows(symbol)

    prices = tmp_path / "raw_prices.parquet"
    rows = ingest.run("2023-01-01", "2023-01-31", pause=0.0, workers=1,
                      fetch=fake_fetch, symbols=["AAA", "BROKEN"],
                      cache_dir=tmp_path / "cache", prices_file=prices,
                      missing_file=tmp_path / "missing_symbols.csv")
    assert rows == 0
    assert not prices.exists()
