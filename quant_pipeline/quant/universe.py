"""The stock universe for the pipeline.

The universe holds large, liquid stocks. The stocks cover all 11 GICS sectors.
This gives the screen enough breadth to pick a diversified portfolio.
SPY is the benchmark. The backtest compares the portfolio against SPY.
"""

from __future__ import annotations

# Each stock has a ticker and a GICS sector.
# Keep the list sorted by sector, then by ticker. This makes it easy to read.
UNIVERSE: dict[str, str] = {
    # Communication Services.
    "DIS": "Communication Services",
    "GOOGL": "Communication Services",
    "META": "Communication Services",
    "NFLX": "Communication Services",
    # Consumer Discretionary.
    "AMZN": "Consumer Discretionary",
    "HD": "Consumer Discretionary",
    "MCD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    # Consumer Staples.
    "COST": "Consumer Staples",
    "KO": "Consumer Staples",
    "PEP": "Consumer Staples",
    "PG": "Consumer Staples",
    "WMT": "Consumer Staples",
    # Energy.
    "COP": "Energy",
    "CVX": "Energy",
    "XOM": "Energy",
    # Financials.
    "BAC": "Financials",
    "GS": "Financials",
    "JPM": "Financials",
    "MA": "Financials",
    "V": "Financials",
    # Health Care.
    "ABBV": "Health Care",
    "JNJ": "Health Care",
    "LLY": "Health Care",
    "PFE": "Health Care",
    "UNH": "Health Care",
    # Industrials.
    "BA": "Industrials",
    "CAT": "Industrials",
    "HON": "Industrials",
    "UPS": "Industrials",
    # Information Technology.
    "AAPL": "Information Technology",
    "ADBE": "Information Technology",
    "AVGO": "Information Technology",
    "CRM": "Information Technology",
    "MSFT": "Information Technology",
    "NVDA": "Information Technology",
    # Materials.
    "LIN": "Materials",
    "SHW": "Materials",
    # Real Estate.
    "AMT": "Real Estate",
    "PLD": "Real Estate",
    # Utilities.
    "DUK": "Utilities",
    "NEE": "Utilities",
}

# The benchmark ticker. The pipeline downloads it, but does not screen it.
BENCHMARK: str = "SPY"


def tickers() -> list[str]:
    """Return the universe tickers in sorted order."""
    return sorted(UNIVERSE)


def all_download_symbols() -> list[str]:
    """Return the universe tickers plus the benchmark."""
    return sorted(set(UNIVERSE) | {BENCHMARK})
