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
