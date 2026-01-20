#!/usr/bin/env python3
"""
Test Complete Strategy with Synthetic Data
Demonstrates full workflow without requiring yfinance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from module_2_technical_screening import TechnicalScreener
from module_3_correlation_analysis import CorrelationAnalyzer
from module_5_portfolio_optimization import PortfolioOptimizer
from module_6_backtest_engine import BacktestEngine


def generate_synthetic_stock_data(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
    initial_price: float = 100,
    annual_return: float = 0.10,
    volatility: float = 0.20,
    seed: int = None
) -> pd.DataFrame:
    """Generate realistic synthetic stock data"""

    if seed:
        np.random.seed(seed)

    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(dates)

    # Generate daily returns (geometric Brownian motion)
    daily_return = annual_return / 252
    daily_vol = volatility / np.sqrt(252)

    returns = np.random.normal(daily_return, daily_vol, n_days)

    # Generate price series
    prices = initial_price * np.exp(np.cumsum(returns))

    # Add some intraday variation for OHLC
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
    opens = lows + (highs - lows) * np.random.random(n_days)
    closes = prices

    # Volume
    avg_volume = 1000000
    volumes = np.random.poisson(avg_volume, n_days)

    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)

    return df


def test_complete_workflow():
    """Test the complete strategy workflow with synthetic data"""

    print("="*70)
    print("TESTING COMPLETE STRATEGY WITH SYNTHETIC DATA")
    print("="*70)

    # Generate synthetic data for 30 stocks
    tickers = [f'STOCK{i:02d}' for i in range(1, 31)]

    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years

    print(f"\n📊 Generating synthetic data for {len(tickers)} stocks...")
    print(f"Period: {start_date.date()} to {end_date.date()}")

    stock_data = {}
    for i, ticker in enumerate(tickers, 1):
        # Vary parameters to create different stock behaviors
        annual_return = np.random.uniform(0.05, 0.20)
        volatility = np.random.uniform(0.15, 0.35)

        stock_data[ticker] = generate_synthetic_stock_data(
            ticker,
            start_date,
            end_date,
            initial_price=np.random.uniform(50, 200),
            annual_return=annual_return,
            volatility=volatility,
            seed=i
        )

    print(f"✓ Generated {len(stock_data)} stocks")

    # Step 1: Technical Screening
    print(f"\n🔍 Step 1: Technical Screening")
    screener = TechnicalScreener()
    screening_results = screener.screen_universe(stock_data)

    candidates = screening_results[screening_results['pass'] == True]['ticker'].tolist()
    print(f"✓ {len(candidates)} stocks passed screening")

    if len(candidates) < 5:
        print("⚠️ Not enough candidates, lowering thresholds...")
        # Take top 15 by RSI
        candidates = screening_results.nsmallest(15, 'rsi')['ticker'].tolist()
        print(f"✓ Selected top {len(candidates)} candidates")

    # Step 2: Correlation Analysis
    print(f"\n🔗 Step 2: Correlation Analysis")
    analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
    selected = analyzer.select_low_correlation_stocks(
        candidates,
        stock_data,
        max_correlation=0.5,
        target_count=10
    )

    print(f"✓ Selected {len(selected)} low-correlation stocks")
    print(f"  Stocks: {', '.join(selected)}")

    # Correlation stats
    stats = analyzer.analyze_portfolio_correlation(selected, stock_data)
    print(f"\n  Portfolio Correlation:")
    print(f"    Average: {stats['avg_correlation']:.3f}")
    print(f"    Max: {stats['max_correlation']:.3f}")

    # Step 3: Portfolio Optimization
    print(f"\n📈 Step 3: Portfolio Optimization")
    optimizer = PortfolioOptimizer(risk_free_rate=0.02)
    opt_result = optimizer.optimize_max_sharpe(selected, stock_data)

    if opt_result['success']:
        print(f"✓ Portfolio optimized:")
        print(f"    Expected Return: {opt_result['expected_return']*100:.2f}%")
        print(f"    Volatility: {opt_result['volatility']*100:.2f}%")
        print(f"    Sharpe Ratio: {opt_result['sharpe_ratio']:.3f}")

        print(f"\n💼 Top 5 Holdings:")
        weights_sorted = sorted(opt_result['weights'].items(), key=lambda x: x[1], reverse=True)
        for ticker, weight in weights_sorted[:5]:
            print(f"    {ticker}: {weight*100:.1f}%")

    else:
        print(f"❌ Optimization failed: {opt_result['message']}")
        return

    # Step 4: Backtest
    print(f"\n✅ Step 4: Backtesting")
    backtester = BacktestEngine(initial_capital=100000)

    # Backtest on last 6 months
    backtest_start = end_date - timedelta(days=180)
    backtest_result = backtester.backtest_portfolio(
        opt_result['weights'],
        stock_data,
        backtest_start,
        end_date
    )

    if backtest_result['success']:
        print(f"✓ Backtest Results (6 months):")
        print(f"    Initial: ${backtest_result['initial_capital']:,.0f}")
        print(f"    Final: ${backtest_result['final_value']:,.0f}")
        print(f"    Return: {backtest_result['total_return']*100:.2f}%")
        print(f"    Annual Return: {backtest_result['annual_return']*100:.2f}%")
        print(f"    Sharpe Ratio: {backtest_result['sharpe_ratio']:.3f}")
        print(f"    Max Drawdown: {backtest_result['max_drawdown']*100:.2f}%")
        print(f"    Win Rate: {backtest_result['win_rate']*100:.1f}%")

        # Assess results
        print(f"\n📊 Assessment:")
        if backtest_result['sharpe_ratio'] > 1.0:
            print(f"    ✅ EXCELLENT - Sharpe ratio > 1.0")
        elif backtest_result['sharpe_ratio'] > 0.5:
            print(f"    ✓ GOOD - Sharpe ratio > 0.5")
        elif backtest_result['sharpe_ratio'] > 0:
            print(f"    ⚠️ MODERATE - Positive Sharpe ratio")
        else:
            print(f"    ❌ WEAK - Negative Sharpe ratio")

    else:
        print(f"❌ Backtest failed: {backtest_result['message']}")

    print(f"\n{'='*70}")
    print(f"WORKFLOW COMPLETE!")
    print(f"{'='*70}\n")

    print(f"Next steps:")
    print(f"1. Install yfinance on your local machine: pip install yfinance")
    print(f"2. Run: python run_complete_strategy.py")
    print(f"3. For full validation: python run_complete_strategy.py --validate")
    print(f"4. Launch UI: streamlit run app.py")


if __name__ == "__main__":
    test_complete_workflow()
