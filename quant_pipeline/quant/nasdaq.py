"""Download and clean historical price data from nasdaq.com.

The nasdaq API sends prices as text. For example "$1,234.56".
It sends the newest day first. It uses month/day/year dates.
This module changes that raw text to clean, sorted records.
The pure functions have no network calls, so the tests can check them.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import requests

# The nasdaq API checks the request headers. It sends a 403 error to a plain
# client. With these headers, the API accepts the request as a browser request.
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

# The API answers with HTTP 200 and an error inside the body. This code in
# the body says that the API does not have the symbol.
SYMBOL_NOT_FOUND_CODE = 1001


class NasdaqError(Exception):
    """The base class of the errors of the nasdaq API."""


class SymbolNotFound(NasdaqError):
    """The API does not have the symbol.

    The API answers in this way for a company that left the market: a
    company that another company bought, or a company that a new name or a
    new ticker replaced. The API serves the symbols that trade now.

    This error is a known gap, not a failure of the download. The caller
    must record the symbol and continue. See decision D19.
    """


class NasdaqApiError(NasdaqError):
    """The API answered with an error that is not a missing symbol."""


def parse_price(text: str | None) -> float | None:
    """Change a price string to a float.

    Remove the dollar sign and the thousands commas.
    Return None when there is no value.
    """
    if text is None:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if cleaned == "" or cleaned.upper() == "N/A":
        return None
    return float(cleaned)


def parse_volume(text: str | None) -> int | None:
    """Change a volume string to an integer.

    Remove the thousands commas. Return None when there is no value.
    """
    if text is None:
        return None
    cleaned = text.replace(",", "").strip()
    if cleaned == "" or cleaned.upper() == "N/A":
        return None
    return int(float(cleaned))


def parse_us_date(text: str) -> str:
    """Change a month/day/year date to a year-month-day string."""
    parsed = dt.datetime.strptime(text.strip(), "%m/%d/%Y").date()
    return parsed.isoformat()


def normalize_rows(ticker: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Change raw nasdaq rows to clean records.

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


def api_error_message(payload: dict[str, Any]) -> tuple[int | None, str]:
    """Read the error code and the message of an answer of the API."""
    status = payload.get("status") or {}
    messages = status.get("bCodeMessage") or []
    first = messages[0] if messages else {}
    return first.get("code"), str(first.get("errorMessage") or "")


def rows_from_payload(symbol: str, payload: dict[str, Any]
                      ) -> list[dict[str, Any]]:
    """Return the price rows of an answer of the API.

    The API uses HTTP 200 for an error, and it puts the error in the body.
    This function reads the body and answers in three ways:

      * The rows, when the answer holds a table.
      * An empty list, when the symbol exists and has no trade in the date
        range. The caller can cache that answer.
      * An error, when the body holds an error. `SymbolNotFound` says that
        the API does not have the symbol. `NasdaqApiError` says that
        something else is wrong, for example a busy service.

    The old code read every answer as rows, and an error gave an empty
    list. A gap in the data then looked the same as a quiet symbol.
    """
    status = payload.get("status") or {}
    code = status.get("rCode")
    if code is not None and int(code) >= 400:
        error_code, message = api_error_message(payload)
        text = f"{symbol}: the nasdaq API answered rCode {code}. {message}"
        if error_code == SYMBOL_NOT_FOUND_CODE:
            raise SymbolNotFound(text)
        raise NasdaqApiError(text)
    table = (payload.get("data") or {}).get("tradesTable") or {}
    return table.get("rows") or []


def fetch_historical(symbol: str, fromdate: str, todate: str,
                     session: requests.Session | None = None,
                     timeout: int = 30,
                     assetclass: str = "stocks") -> list[dict[str, Any]]:
    """Download raw historical rows for one symbol.

    This function uses the network. Return an empty list when the symbol
    exists and has no trade in the date range. Raise `SymbolNotFound` when
    the API does not have the symbol, and `NasdaqApiError` for another
    error of the API.
    """
    url = build_historical_url(symbol, fromdate, todate, assetclass=assetclass)
    client = session or requests.Session()
    response = client.get(url, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    return rows_from_payload(symbol, response.json())
