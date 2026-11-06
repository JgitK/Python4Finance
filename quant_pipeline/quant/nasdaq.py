"""Download and clean historical price data from nasdaq.com.

The nasdaq API sends prices as text. For example "$1,234.56".
It sends the newest day first. It uses month/day/year dates.
This module turns that raw text into clean, sorted records.
The pure functions have no network calls, so the tests can check them.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

# The nasdaq API checks the request headers. A plain client gets a 403 error.
# These headers make the request look like a normal browser.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/market-activity/stocks",
}

_BASE_URL = "https://api.nasdaq.com/api/quote/{symbol}/historical"


def parse_price(text: str | None) -> float | None:
    """Turn a price string into a float.

    Remove the dollar sign and the thousands commas.
    Return None when the value is missing.
    """
    if text is None:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned == "" or cleaned.upper() == "N/A":
        return None
    return float(cleaned)


def parse_volume(text: str | None) -> int | None:
    """Turn a volume string into an integer.

    Remove the thousands commas. Return None when the value is missing.
    """
    if text is None:
        return None
    cleaned = text.replace(",", "").strip()
    if cleaned == "" or cleaned.upper() == "N/A":
        return None
    return int(float(cleaned))


def parse_us_date(text: str) -> str:
    """Turn a month/day/year date into a year-month-day string."""
    parsed = dt.datetime.strptime(text.strip(), "%m/%d/%Y").date()
    return parsed.isoformat()


def normalize_rows(ticker: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn raw nasdaq rows into clean records.

    Add the ticker to each record. Cast the price and volume fields.
    Drop any row that has no close price. Sort the records oldest first.
    """
    records: list[dict[str, Any]] = []
    for row in rows:
        close = parse_price(row.get("close"))
        if close is None:
            # A row with no close price is not useful. Skip it.
            continue
        records.append(
            {
                "ticker": ticker,
                "date": parse_us_date(row["date"]),
                "open": parse_price(row.get("open")),
                "high": parse_price(row.get("high")),
                "low": parse_price(row.get("low")),
                "close": close,
                "volume": parse_volume(row.get("volume")),
            }
        )
    records.sort(key=lambda r: r["date"])
    return records


def build_historical_url(symbol: str, fromdate: str, todate: str,
                         limit: int = 9999, assetclass: str = "stocks") -> str:
    """Build the nasdaq historical data URL for one symbol.

    Use assetclass "stocks" for a normal stock. Use "etf" for a fund like SPY.
    """
    base = _BASE_URL.format(symbol=symbol.upper())
    return (
        f"{base}?assetclass={assetclass}"
        f"&fromdate={fromdate}&todate={todate}&limit={limit}"
    )


def fetch_historical(symbol: str, fromdate: str, todate: str,
                     session: requests.Session | None = None,
                     timeout: int = 30,
                     assetclass: str = "stocks") -> list[dict[str, Any]]:
    """Download raw historical rows for one symbol.

    This function uses the network. Return an empty list when no rows exist.
    """
    url = build_historical_url(symbol, fromdate, todate, assetclass=assetclass)
    client = session or requests.Session()
    response = client.get(url, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    table = (payload.get("data") or {}).get("tradesTable") or {}
    return table.get("rows") or []
