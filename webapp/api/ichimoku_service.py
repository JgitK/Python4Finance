# ============================================================================
# Ichimoku Service
# ============================================================================
# This module loads Ichimoku chart data for the frontend.
#
# It reads CSV files exported from R and returns them in JSON format
# for the interactive chart.

import csv
from pathlib import Path

# Path to Ichimoku data files
ICHIMOKU_DIR = Path(__file__).parent.parent / "db" / "seed_data" / "ichimoku"

# Valid tickers (loaded from portfolio + bench)
PORTFOLIO_FILE = Path(__file__).parent.parent / "db" / "seed_data" / "portfolio_stocks.csv"
BENCH_FILE = Path(__file__).parent.parent / "db" / "seed_data" / "bench_stocks.csv"


def get_valid_tickers():
    """
    Get list of valid tickers (portfolio + bench stocks).
    This prevents users from requesting arbitrary tickers.
    """
    tickers = set()

    # Load portfolio tickers
    with open(PORTFOLIO_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.add(row['ticker'])

    # Load bench tickers
    with open(BENCH_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.add(row['ticker'])

    return tickers


def get_ichimoku_data(ticker: str):
    """
    Get Ichimoku chart data for a specific stock.

    Args:
        ticker: Stock ticker symbol (e.g., "BBVA")

    Returns:
        Dictionary with:
        - ticker: The stock symbol
        - data: List of OHLC + Ichimoku values by date

    Raises:
        ValueError: If ticker is not in portfolio or bench
        FileNotFoundError: If data file doesn't exist
    """
    # Validate ticker
    valid_tickers = get_valid_tickers()
    if ticker.upper() not in valid_tickers:
        raise ValueError(f"Ticker '{ticker}' is not in portfolio or bench")

    ticker = ticker.upper()
    csv_path = ICHIMOKU_DIR / f"{ticker}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"No data file for {ticker}")

    # Read CSV data
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'date': row['date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(float(row['volume'])),
                'tenkan_sen': float(row['tenkan_sen']) if row['tenkan_sen'] != 'NA' else None,
                'kijun_sen': float(row['kijun_sen']) if row['kijun_sen'] != 'NA' else None,
                'senkou_span_a': float(row['senkou_span_a']) if row['senkou_span_a'] != 'NA' else None,
                'senkou_span_b': float(row['senkou_span_b']) if row['senkou_span_b'] != 'NA' else None,
                'chikou_span': float(row['chikou_span']) if row['chikou_span'] != 'NA' else None,
            })

    return {
        'ticker': ticker,
        'data': data
    }
