# ============================================================================
# Portfolio Service
# ============================================================================
# This module handles the business logic for portfolio allocation.
#
# It reads the portfolio data (exported from R) and calculates how many
# shares to buy given an investment amount.
#
# NEW: Strategy-Specific Stock Selection
# Each strategy now has its own optimal set of stocks, not just different weights.
# - max_sharpe: Stocks with best risk-adjusted returns
# - min_variance: Stocks with lowest volatility
# - max_sortino: Stocks with best downside risk protection
# - min_cvar: Stocks that protect against tail risk
# - risk_parity: Stocks with similar volatilities
# - equal_weight: Same stocks as max_sharpe, equal weights

import csv
from pathlib import Path
from math import floor

# Path to our seed data (exported from R pipeline)
DATA_DIR = Path(__file__).parent.parent / "db" / "seed_data"

# Available portfolio types
PORTFOLIO_TYPES = [
    'max_sharpe',
    'min_variance',
    'max_sortino',
    'min_cvar',
    'risk_parity',
    'equal_weight'
]

DEFAULT_PORTFOLIO_TYPE = 'max_sharpe'


def load_strategy_portfolios():
    """
    Load all strategy-specific portfolios from CSV.

    Returns:
        Dictionary with strategy -> list of stocks
    """
    csv_path = DATA_DIR / "strategy_portfolios.csv"

    # Check if new file exists, fallback to legacy
    if not csv_path.exists():
        return None

    portfolios = {strategy: [] for strategy in PORTFOLIO_TYPES}

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            strategy = row['strategy']
            if strategy in portfolios:
                portfolios[strategy].append({
                    'ticker': row['ticker'],
                    'weight': float(row['weight']),
                    'sector': row['sector'],
                    'sharpe_ratio': float(row.get('sharpe_ratio', 0)),
                    'sortino_ratio': float(row.get('sortino_ratio', 0)) if row.get('sortino_ratio') else None,
                    'current_price': float(row['current_price']),
                    'ichimoku_signal': row.get('ichimoku_signal', '')
                })

    return portfolios


def load_portfolio_stocks(portfolio_type: str = DEFAULT_PORTFOLIO_TYPE):
    """
    Load stocks for a specific portfolio strategy.

    Args:
        portfolio_type: One of 'max_sharpe', 'min_variance', 'max_sortino',
                       'min_cvar', 'risk_parity', 'equal_weight'

    Returns a list of dictionaries with stock info.
    """
    # Validate portfolio type
    if portfolio_type not in PORTFOLIO_TYPES:
        portfolio_type = DEFAULT_PORTFOLIO_TYPE

    # Try new strategy-specific portfolios first
    strategy_portfolios = load_strategy_portfolios()

    if strategy_portfolios is not None:
        return strategy_portfolios.get(portfolio_type, [])

    # Fallback to legacy format
    return load_legacy_portfolio_stocks(portfolio_type)


def load_legacy_portfolio_stocks(portfolio_type: str = DEFAULT_PORTFOLIO_TYPE):
    """
    Legacy: Load portfolio stocks from the old format (same stocks, different weights).
    """
    csv_path = DATA_DIR / "portfolio_stocks.csv"

    # Map portfolio type to weight column
    weight_columns = {
        'max_sharpe': 'max_sharpe_weight',
        'min_variance': 'min_variance_weight',
        'max_sortino': 'max_sortino_weight',
        'min_cvar': 'min_cvar_weight',
        'risk_parity': 'risk_parity_weight',
        'equal_weight': 'equal_weight'
    }

    weight_column = weight_columns.get(portfolio_type, 'max_sharpe_weight')

    stocks = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            weight = float(row.get(weight_column, row.get('max_sharpe_weight', 0)))

            stocks.append({
                'ticker': row['ticker'],
                'sector': row['sector'],
                'sharpe_ratio': float(row['sharpe_ratio']),
                'weight': weight,
                'current_price': float(row['current_price']),
                'ichimoku_signal': row.get('ichimoku_signal', '')
            })

    return stocks


def get_available_portfolio_types():
    """Return list of available portfolio optimization strategies."""
    return [
        {'id': 'max_sharpe', 'name': 'Max Sharpe Ratio', 'description': 'Best risk-adjusted returns (aggressive)'},
        {'id': 'min_variance', 'name': 'Min Variance', 'description': 'Lowest volatility stocks (conservative)'},
        {'id': 'max_sortino', 'name': 'Max Sortino Ratio', 'description': 'Best downside risk-adjusted returns'},
        {'id': 'min_cvar', 'name': 'Min CVaR', 'description': 'Tail risk protection (crash-resistant)'},
        {'id': 'risk_parity', 'name': 'Risk Parity', 'description': 'Equal risk contribution per stock'},
        {'id': 'equal_weight', 'name': 'Equal Weight', 'description': 'Simple 1/N allocation (baseline)'}
    ]


def load_bench_stocks(portfolio_type: str = DEFAULT_PORTFOLIO_TYPE):
    """
    Load the bench (alternate) stocks for a strategy.

    Each strategy has its own bench stocks (alternates ready to replace).

    Returns a list of dictionaries with stock info.
    """
    # Try strategy-specific bench first
    csv_path = DATA_DIR / "strategy_bench_stocks.csv"

    if csv_path.exists():
        stocks = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['strategy'] == portfolio_type:
                    stocks.append({
                        'ticker': row['ticker'],
                        'sector': row['sector'],
                        'sharpe_ratio': float(row['sharpe_ratio']),
                        'current_price': float(row['current_price'])
                    })
        if stocks:
            return stocks

    # Fallback to legacy bench
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


def calculate_allocation(amount: float, portfolio_type: str = DEFAULT_PORTFOLIO_TYPE,
                         risk_tolerance: float = None):
    """
    Calculate how many shares to buy given an investment amount.

    This uses the optimal weights from the R analysis pipeline.
    Each strategy now has its own set of stocks.

    Args:
        amount: Dollar amount to invest (e.g., 3500)
        portfolio_type: Optimization strategy ('max_sharpe', 'min_variance', etc.)
        risk_tolerance: Optional float 0-1 to blend between aggressive/conservative.
                       Only works with legacy format (same stocks, different weights).
                       Blends max_sharpe with min_variance.

    Returns:
        Dictionary with:
        - stocks: List of stocks with shares to buy
        - total_invested: Actual amount invested
        - cash_remaining: Leftover cash
        - efficiency: Percentage of money invested
        - portfolio_type: The optimization strategy used
    """
    portfolio = load_portfolio_stocks(portfolio_type)

    result_stocks = []
    total_invested = 0.0

    for stock in portfolio:
        weight = stock['weight']

        # Custom blending only works if stocks have all_weights (legacy format)
        if risk_tolerance is not None and 'all_weights' in stock:
            aggressive_weight = stock['all_weights'].get('max_sharpe', weight)
            conservative_weight = stock['all_weights'].get('min_variance', weight)
            weight = (risk_tolerance * aggressive_weight) + ((1 - risk_tolerance) * conservative_weight)

        # Calculate dollar amount for this stock
        dollar_amount = weight * amount

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
                'sector': stock['sector'],
                'weight': round(weight, 4),
                'ichimoku_signal': stock.get('ichimoku_signal', '')
            })

    cash_remaining = amount - total_invested
    efficiency = total_invested / amount if amount > 0 else 0

    return {
        'stocks': result_stocks,
        'total_invested': round(total_invested, 2),
        'cash_remaining': round(cash_remaining, 2),
        'efficiency': round(efficiency, 4),
        'portfolio_type': portfolio_type if risk_tolerance is None else 'custom_blend',
        'risk_tolerance': risk_tolerance
    }


def get_bench(portfolio_type: str = DEFAULT_PORTFOLIO_TYPE):
    """
    Get the bench stocks (alternates ready to promote) for a strategy.

    Returns:
        Dictionary with:
        - stocks: List of bench stocks
    """
    bench = load_bench_stocks(portfolio_type)

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


def get_strategy_metadata():
    """
    Load strategy metadata (number of stocks, sectors, avg metrics).

    Returns:
        Dictionary with strategy -> metadata
    """
    csv_path = DATA_DIR / "strategy_metadata.csv"

    if not csv_path.exists():
        return {}

    metadata = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metadata[row['strategy']] = {
                'n_stocks': int(row['n_stocks']),
                'n_sectors': int(row['n_sectors']),
                'avg_sharpe': float(row['avg_sharpe']),
                'avg_sortino': float(row.get('avg_sortino', 0)) if row.get('avg_sortino') else None,
                'avg_correlation': float(row.get('avg_correlation', 0)),
                'tickers': row['tickers'].split(',')
            }

    return metadata
