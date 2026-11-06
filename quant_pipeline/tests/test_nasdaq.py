"""Tests for the nasdaq parser.

These tests use fixed sample rows. They do not use the network.
They make sure that the rules that clean the raw nasdaq fields do not change.
"""

from __future__ import annotations

import pytest

from quant import nasdaq


# --- parse_price -----------------------------------------------------------

def test_parse_price_strips_dollar_sign():
    assert nasdaq.parse_price("$271.86") == pytest.approx(271.86)


def test_parse_price_strips_thousands_comma():
    assert nasdaq.parse_price("$1,234.56") == pytest.approx(1234.56)


def test_parse_price_returns_none_for_missing():
    # Nasdaq uses "N/A" or an empty value when there is no price.
    assert nasdaq.parse_price("N/A") is None
    assert nasdaq.parse_price("") is None
    assert nasdaq.parse_price(None) is None


# --- parse_volume ----------------------------------------------------------

def test_parse_volume_strips_commas_and_casts_int():
    result = nasdaq.parse_volume("27,293,640")
    assert result == 27293640
    assert isinstance(result, int)


def test_parse_volume_returns_none_for_missing():
    assert nasdaq.parse_volume("N/A") is None
    assert nasdaq.parse_volume("") is None


# --- parse_us_date ---------------------------------------------------------

def test_parse_us_date_converts_to_iso():
    # Nasdaq sends month/day/year. The pipeline needs year-month-day.
    assert nasdaq.parse_us_date("12/31/2025") == "2025-12-31"
    assert nasdaq.parse_us_date("01/03/2023") == "2023-01-03"


# --- normalize_rows --------------------------------------------------------

SAMPLE_ROWS = [
    # Nasdaq sends the newest row first.
    {"date": "01/04/2023", "close": "$126.36", "volume": "89,113,640",
     "open": "$126.89", "high": "$128.66", "low": "$125.08"},
    {"date": "01/03/2023", "close": "$125.07", "volume": "112,117,500",
     "open": "$130.28", "high": "$130.90", "low": "$124.17"},
]


def test_normalize_rows_sorts_oldest_first():
    records = nasdaq.normalize_rows("AAPL", SAMPLE_ROWS)
    dates = [r["date"] for r in records]
    assert dates == ["2023-01-03", "2023-01-04"]


def test_normalize_rows_adds_ticker_and_numeric_fields():
    records = nasdaq.normalize_rows("AAPL", SAMPLE_ROWS)
    first = records[0]
    assert first["ticker"] == "AAPL"
    assert first["open"] == pytest.approx(130.28)
    assert first["high"] == pytest.approx(130.90)
    assert first["low"] == pytest.approx(124.17)
    assert first["close"] == pytest.approx(125.07)
    assert first["volume"] == 112117500


def test_normalize_rows_drops_rows_with_missing_close():
    rows = SAMPLE_ROWS + [{"date": "01/05/2023", "close": "N/A",
                           "volume": "N/A", "open": "N/A",
                           "high": "N/A", "low": "N/A"}]
    records = nasdaq.normalize_rows("AAPL", rows)
    # The bad row has no close price, so the function drops it.
    assert len(records) == 2


# --- build_historical_url --------------------------------------------------

def test_build_historical_url_has_expected_parts():
    url = nasdaq.build_historical_url("AAPL", "2023-01-01", "2025-12-31")
    assert url.startswith("https://api.nasdaq.com/api/quote/AAPL/historical")
    assert "assetclass=stocks" in url
    assert "fromdate=2023-01-01" in url
    assert "todate=2025-12-31" in url
    assert "limit=9999" in url


def test_build_historical_url_supports_etf_asset_class():
    # SPY is an ETF, so the URL must ask for the etf asset class.
    url = nasdaq.build_historical_url("SPY", "2023-01-01", "2025-12-31",
                                      assetclass="etf")
    assert "assetclass=etf" in url


# --- rows_from_payload -----------------------------------------------------
#
# The API answers with HTTP 200 and an error inside the body. For a symbol
# that it does not have, the body holds rCode 400 and the message
# "Symbol not exists.". The old code read the rows of such a body as an
# empty list, so an error looked the same as a symbol with no trades. The
# download then cached the empty list, and nobody saw the gap. See D19.

OK_PAYLOAD = {
    "data": {"tradesTable": {"rows": SAMPLE_ROWS}},
    "status": {"rCode": 200, "bCodeMessage": None},
}
NOT_EXISTS_PAYLOAD = {
    "data": None,
    "status": {"rCode": 400,
               "bCodeMessage": [{"code": 1001,
                                 "errorMessage": "Symbol not exists."}]},
}
EMPTY_PAYLOAD = {
    "data": {"tradesTable": {"rows": []}},
    "status": {"rCode": 200, "bCodeMessage": None},
}
SERVER_ERROR_PAYLOAD = {
    "data": None,
    "status": {"rCode": 500,
               "bCodeMessage": [{"code": 9999,
                                 "errorMessage": "Service unavailable."}]},
}


def test_rows_from_payload_returns_the_rows():
    assert nasdaq.rows_from_payload("AAPL", OK_PAYLOAD) == SAMPLE_ROWS


def test_rows_from_payload_raises_for_a_symbol_that_the_source_lacks():
    with pytest.raises(nasdaq.SymbolNotFound) as error:
        nasdaq.rows_from_payload("EA", NOT_EXISTS_PAYLOAD)
    # The message must name the symbol and repeat the words of the API.
    assert "EA" in str(error.value)
    assert "Symbol not exists." in str(error.value)


def test_rows_from_payload_returns_empty_for_a_symbol_with_no_trades():
    # The symbol exists, and it has no trade in the date range. That is not
    # an error, and the download can cache it.
    assert nasdaq.rows_from_payload("AAA", EMPTY_PAYLOAD) == []


def test_rows_from_payload_raises_another_error_for_another_code():
    with pytest.raises(nasdaq.NasdaqApiError) as error:
        nasdaq.rows_from_payload("AAA", SERVER_ERROR_PAYLOAD)
    assert not isinstance(error.value, nasdaq.SymbolNotFound)
    assert "Service unavailable." in str(error.value)


def test_a_missing_symbol_is_not_a_general_failure():
    # The two errors need different answers. A symbol that the source does
    # not have is a known gap, and it must not stop the download of the
    # other symbols. Both come from one base class.
    assert issubclass(nasdaq.SymbolNotFound, nasdaq.NasdaqError)
    assert issubclass(nasdaq.NasdaqApiError, nasdaq.NasdaqError)
    assert not issubclass(nasdaq.SymbolNotFound, nasdaq.NasdaqApiError)
