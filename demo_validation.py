#!/usr/bin/env python3
"""
Demo: How to use the validation framework
"""

from validation_framework import PortfolioValidator, print_validation_summary
import numpy as np
from datetime import datetime, timedelta


# Example strategy function (placeholder - you'll replace with your real strategy)
def example_strategy(start_date, end_date, params=None):
    """
    Example portfolio selection strategy

    In reality, this would:
    1. Load stock data for the period
    2. Run technical screening (RSI, MACD, Ichimoku)
    3. Filter by correlation
    4. Optimize weights
    5. Return selected portfolio

    For demo purposes, we just return a dummy portfolio
    """
    if params is None:
        params = {'rsi_threshold': 30, 'num_stocks': 10, 'correlation_cutoff': 0.4}

    # Simulate stock selection
    stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'JPM', 'V']
    weights = np.random.dirichlet(np.ones(10))  # Random weights that sum to 1

    return {
        'stocks': stocks[:params.get('num_stocks', 10)],
        'weights': weights[:params.get('num_stocks', 10)],
        'params_used': params
    }


# Mock data source (you'll replace with real data loader)
class MockDataSource:
    def get_data(self, ticker, start_date, end_date):
        # Return dummy price data
        days = (end_date - start_date).days
        return np.random.randn(days).cumsum() + 100


def run_demo():
    """Run a complete validation demo"""

    print("="*70)
    print("PORTFOLIO STRATEGY VALIDATION - DEMO")
    print("="*70)
    print()
    print("This demo shows how to validate your strategy's robustness")
    print("using multi-timeframe, walk-forward, and Monte Carlo analysis.")
    print()

    # Initialize validator
    data_source = MockDataSource()
    validator = PortfolioValidator(
        strategy_function=example_strategy,
        data_source=data_source
    )

    print("\n📊 Step 1: Multi-Timeframe Backtesting")
    print("-" * 70)
    print("Testing if strategy works across different time periods...")

    mt_results = validator.multi_timeframe_backtest(
        timeframes={
            '6mo': 180,
            '1yr': 365,
            '2yr': 730
        }
    )

    print("\n🔄 Step 2: Walk-Forward Analysis")
    print("-" * 70)
    print("Testing if the PROCESS consistently works...")

    wf_results = validator.walk_forward_analysis(
        train_period_days=365,
        test_period_days=90,
        step_size_days=90,
        total_history_days=730
    )

    print("\n🎲 Step 3: Monte Carlo Parameter Sensitivity")
    print("-" * 70)
    print("Testing robustness to parameter variations...")

    mc_results = validator.monte_carlo_parameter_sensitivity(
        parameter_ranges={
            'rsi_threshold': (25, 40),
            'num_stocks': (8, 12),
            'correlation_cutoff': (0.3, 0.5)
        },
        num_simulations=50,
        test_period_days=365
    )

    print("\n📈 Step 4: Generate Comprehensive Report")
    print("-" * 70)

    report = validator.generate_validation_report(
        multi_timeframe_results=mt_results,
        walk_forward_results=wf_results,
        monte_carlo_results=mc_results
    )

    # Print the report
    print_validation_summary(report)

    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Replace example_strategy() with your real strategy")
    print("2. Connect MockDataSource to your actual data")
    print("3. Run the full validation")
    print("4. Review the robustness score")
    print("5. If score > 70, proceed to paper trading!")
    print()


if __name__ == "__main__":
    run_demo()
