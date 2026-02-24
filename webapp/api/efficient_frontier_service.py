# ============================================================================
# Efficient Frontier Service - Loads and processes portfolio simulation data
# ============================================================================

import csv
from pathlib import Path
from functools import lru_cache


# Risk-free rate (annualized, e.g., 4.5% Treasury yield)
RISK_FREE_RATE = 0.045

# Strategy display info
STRATEGY_INFO = {
    'max_sharpe': {'name': 'Max Sharpe', 'color': '#22c55e', 'symbol': 'star'},
    'min_variance': {'name': 'Min Variance', 'color': '#3b82f6', 'symbol': 'diamond'},
    'max_sortino': {'name': 'Max Sortino', 'color': '#a855f7', 'symbol': 'triangle-up'},
    'min_cvar': {'name': 'Min CVaR', 'color': '#f97316', 'symbol': 'square'},
    'risk_parity': {'name': 'Risk Parity', 'color': '#06b6d4', 'symbol': 'circle'},
    'equal_weight': {'name': 'Equal Weight', 'color': '#6b7280', 'symbol': 'x'}
}


def load_strategy_positions() -> list:
    """
    Load the optimal portfolio position for each strategy.

    Returns:
        List of strategy positions with risk/return/sharpe.
    """
    csv_path = Path(__file__).parent.parent / "db" / "seed_data" / "strategy_positions.csv"

    if not csv_path.exists():
        return []

    positions = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            strategy = row['strategy']
            info = STRATEGY_INFO.get(strategy, {'name': strategy, 'color': '#888', 'symbol': 'circle'})

            positions.append({
                'strategy': strategy,
                'name': info['name'],
                'color': info['color'],
                'symbol': info['symbol'],
                'return': float(row['expected_return']),
                'risk': float(row['risk']),
                'sharpe': float(row['sharpe']),
                'sortino': float(row['sortino']) if row.get('sortino') and row['sortino'] != 'NA' else None
            })

    return positions


@lru_cache(maxsize=1)
def get_efficient_frontier_data() -> dict:
    """
    Load efficient frontier data from CSV and identify key portfolios.

    Returns:
        Dictionary with:
        - portfolios: List of all portfolio data points
        - optimal: The portfolio with max Sharpe ratio
        - min_variance: The portfolio with minimum risk
        - strategy_positions: All strategy portfolio positions
        - risk_free_rate: The risk-free rate used
    """
    csv_path = Path(__file__).parent.parent.parent / "analysis" / "efficient_frontier.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Efficient frontier data not found: {csv_path}")

    portfolios = []
    max_sharpe = -float('inf')
    min_risk = float('inf')
    optimal_portfolio = None
    min_variance_portfolio = None

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            portfolio = {
                "id": int(row["portfolio"]),
                "return": float(row["return"]),
                "risk": float(row["risk"]),
                "sharpe": float(row["sharpe"])
            }
            portfolios.append(portfolio)

            # Track optimal (max Sharpe)
            if portfolio["sharpe"] > max_sharpe:
                max_sharpe = portfolio["sharpe"]
                optimal_portfolio = portfolio

            # Track minimum variance
            if portfolio["risk"] < min_risk:
                min_risk = portfolio["risk"]
                min_variance_portfolio = portfolio

    # Load strategy positions
    strategy_positions = load_strategy_positions()

    return {
        "portfolios": portfolios,
        "optimal": optimal_portfolio,
        "min_variance": min_variance_portfolio,
        "strategy_positions": strategy_positions,
        "risk_free_rate": RISK_FREE_RATE,
        "total_portfolios": len(portfolios)
    }
