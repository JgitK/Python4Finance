# ============================================================================
# Stock Info Service - Fetches company information from Yahoo Finance
# ============================================================================

import json
import os
import time
import yfinance as yf

# Persistent file cache so results survive server restarts
_CACHE_FILE = os.path.join(os.path.dirname(__file__), "../db/seed_data/stock_info_cache.json")

def _load_cache() -> dict:
    try:
        with open(_CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_cache(cache: dict):
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w") as f:
        json.dump(cache, f)

_cache = _load_cache()


def get_stock_info(ticker: str) -> dict:
    """
    Fetch company information for a given ticker symbol.

    Uses yfinance to retrieve company details and caches results to a file
    to avoid repeated API calls across server restarts.

    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Dictionary with company_name, sector, industry, description, market_cap
    """
    if ticker in _cache:
        return _cache[ticker]

    result = _fetch_with_retry(ticker)
    if result.get("sector") != "N/A":  # Only cache successful fetches
        _cache[ticker] = result
        _save_cache(_cache)
    return result


def _fetch_with_retry(ticker: str, max_retries: int = 3) -> dict:
    """Fetch ticker info with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "sector": info.get("sector") or "N/A",
                "industry": info.get("industry") or "N/A",
                "description": info.get("longBusinessSummary") or "No description available.",
                "market_cap": info.get("marketCap"),
                "market_cap_formatted": _format_market_cap(info.get("marketCap"))
            }
        except Exception as e:
            error_msg = str(e)
            is_rate_limit = any(x in error_msg.lower() for x in ["too many requests", "rate limit", "429"])

            if is_rate_limit and attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)
                continue

            return {
                "company_name": ticker,
                "sector": "N/A",
                "industry": "N/A",
                "description": f"Unable to fetch company information: {error_msg}",
                "market_cap": None,
                "market_cap_formatted": "N/A"
            }


def _format_market_cap(market_cap: int | None) -> str:
    """Format market cap as human-readable string."""
    if market_cap is None:
        return "N/A"

    if market_cap >= 1_000_000_000_000:
        return f"${market_cap / 1_000_000_000_000:.2f}T"
    elif market_cap >= 1_000_000_000:
        return f"${market_cap / 1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        return f"${market_cap / 1_000_000:.2f}M"
    else:
        return f"${market_cap:,.0f}"
