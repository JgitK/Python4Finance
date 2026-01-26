# ============================================================================
# Portfolio Service
# ============================================================================
# This module handles the business logic for portfolio allocation.
#
# It reads the portfolio data (exported from R) and calculates how many
# shares to buy given an investment amount.
#
# Think of it like a helper function in R that does the calculation work.

import csv
from pathlib import Path
from math import floor

# Path to our seed data (exported from R pipeline)
DATA_DIR = Path(__file__).parent.parent / "db" / "seed_data"


def load_portfolio_stocks():
    """
    Load the 12 selected portfolio stocks from CSV.

    Returns a list of dictionaries with stock info.
    """
    csv_path = DATA_DIR / "portfolio_stocks.csv"

    stocks = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'ticker': row['ticker'],
                'sector': row['sector'],
                'sharpe_ratio': float(row['sharpe_ratio']),
                'weight': float(row['weight']),
                'current_price': float(row['current_price']),
                'ichimoku_signal': row['ichimoku_signal']
            })

    return stocks


def load_bench_stocks():
    """
    Load the 10 bench (alternate) stocks from CSV.

    Returns a list of dictionaries with stock info.
    """
    csv_path = DATA_DIR / "bench_stocks.csv"

    stocks = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stocks.append({
                'ticker': row['ticker'],
                'sector': row['sector'],
                'sharpe_ratio': float(row['sharpe_ratio']),
                'current_price': float(row['current_price'])
            })

    return stocks


def calculate_allocation(amount: float):
    """
    Calculate how many shares to buy given an investment amount.

    This uses the optimal weights from the R analysis pipeline.

    Args:
        amount: Dollar amount to invest (e.g., 3500)

    Returns:
        Dictionary with:
        - stocks: List of stocks with shares to buy
        - total_invested: Actual amount invested
        - cash_remaining: Leftover cash
        - efficiency: Percentage of money invested
    """
    portfolio = load_portfolio_stocks()

    result_stocks = []
    total_invested = 0.0

    for stock in portfolio:
        # Calculate dollar amount for this stock
        dollar_amount = stock['weight'] * amount

        # Calculate whole shares we can buy (no fractional shares)
        shares = floor(dollar_amount / stock['current_price'])

        # Only include if we can buy at least 1 share
        if shares > 0:
            actual_amount = shares * stock['current_price']
            total_invested += actual_amount

            result_stocks.append({
                'ticker': stock['ticker'],
                'shares': shares,
                'price': round(stock['current_price'], 2),
                'amount': round(actual_amount, 2),
                'sector': stock['sector']
            })

    cash_remaining = amount - total_invested
    efficiency = total_invested / amount if amount > 0 else 0

    return {
        'stocks': result_stocks,
        'total_invested': round(total_invested, 2),
        'cash_remaining': round(cash_remaining, 2),
        'efficiency': round(efficiency, 4)
    }


def get_bench():
    """
    Get the bench stocks (alternates ready to promote).

    Returns:
        Dictionary with:
        - stocks: List of bench stocks
    """
    bench = load_bench_stocks()

    return {
        'stocks': [
            {
                'ticker': s['ticker'],
                'sector': s['sector'],
                'sharpe_ratio': round(s['sharpe_ratio'], 4),
                'current_price': round(s['current_price'], 2)
            }
            for s in bench
        ]
    }
