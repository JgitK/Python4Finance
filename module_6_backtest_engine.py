#!/usr/bin/env python3
"""
Module 6: Backtest Engine
Backtests portfolio strategies with realistic assumptions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class BacktestEngine:
    """Backtests portfolio strategies"""

    def __init__(
        self,
        initial_capital: float = 100000,
        rebalance_frequency: str = 'quarterly'  # 'monthly', 'quarterly', 'annual'
    ):
        self.initial_capital = initial_capital
        self.rebalance_frequency = rebalance_frequency

    def backtest_portfolio(
        self,
        weights: Dict[str, float],
        stock_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Backtest a portfolio with given weights

        Args:
            weights: Dict of {ticker: weight}
            stock_data: Dict of {ticker: DataFrame}
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Dict with backtest results
        """
        # Align all stock data to same date range
        prices = pd.DataFrame()

        for ticker, weight in weights.items():
            if ticker in stock_data and 'Close' in stock_data[ticker].columns:
                prices[ticker] = stock_data[ticker]['Close']

        # Filter by date range
        prices = prices[(prices.index >= start_date) & (prices.index <= end_date)]

        if len(prices) == 0:
            return {
                'success': False,
                'message': 'No data in specified date range'
            }

        # Drop columns with too much missing data
        prices = prices.dropna(axis=1, thresh=len(prices) * 0.7)

        # Forward fill remaining NaNs
        prices = prices.ffill().dropna()

        if len(prices.columns) == 0:
            return {
                'success': False,
                'message': 'Insufficient data after cleaning'
            }

        # Recalculate weights to match available stocks
        available_tickers = prices.columns.tolist()
        total_weight = sum(weights[t] for t in available_tickers if t in weights)

        if total_weight == 0:
            return {
                'success': False,
                'message': 'No valid weights'
            }

        # Normalize weights
        normalized_weights = {t: weights.get(t, 0) / total_weight for t in available_tickers}

        # Calculate daily returns
        returns = prices.pct_change().dropna()

        # Calculate portfolio returns
        weights_array = np.array([normalized_weights[t] for t in returns.columns])
        portfolio_returns = returns.dot(weights_array)

        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # Calculate portfolio value over time
        portfolio_value = cumulative_returns * self.initial_capital

        # Calculate metrics
        total_return = (portfolio_value.iloc[-1] / self.initial_capital) - 1
        annual_return = self._annualize_return(total_return, len(portfolio_returns))

        volatility = portfolio_returns.std() * np.sqrt(252)

        sharpe_ratio = self._calculate_sharpe(portfolio_returns)
        max_drawdown = self._calculate_max_drawdown(cumulative_returns)

        # Win rate (days with positive returns)
        win_rate = (portfolio_returns > 0).sum() / len(portfolio_returns)

        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_value': float(portfolio_value.iloc[-1]),
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'num_days': len(portfolio_returns),
            'portfolio_returns': portfolio_returns,
            'portfolio_value': portfolio_value,
            'cumulative_returns': cumulative_returns,
            'weights_used': normalized_weights
        }

    def _annualize_return(self, total_return: float, num_days: int) -> float:
        """Convert total return to annualized return"""
        years = num_days / 252
        if years <= 0:
            return 0
        return (1 + total_return) ** (1 / years) - 1

    def _calculate_sharpe(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio"""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        return float(np.sqrt(252) * excess_returns.mean() / returns.std())

    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - running_max) / running_max
        return float(drawdown.min())

    def calculate_rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = 63  # ~3 months
    ) -> pd.Series:
        """Calculate rolling Sharpe ratio"""
        rolling_mean = returns.rolling(window=window).mean() * 252
        rolling_std = returns.rolling(window=window).std() * np.sqrt(252)

        rolling_sharpe = (rolling_mean - 0.02) / rolling_std

        return rolling_sharpe

    def compare_to_benchmark(
        self,
        portfolio_returns: pd.Series,
        benchmark_data: pd.DataFrame,
        benchmark_ticker: str = 'SPY'
    ) -> Dict:
        """
        Compare portfolio to benchmark (e.g., S&P 500)

        Args:
            portfolio_returns: Portfolio returns series
            benchmark_data: Benchmark stock data
            benchmark_ticker: Benchmark ticker symbol

        Returns:
            Dict with comparison metrics
        """
        if benchmark_ticker not in benchmark_data or 'Close' not in benchmark_data[benchmark_ticker].columns:
            return {
                'success': False,
                'message': f'Benchmark {benchmark_ticker} not available'
            }

        # Get benchmark returns
        benchmark_prices = benchmark_data[benchmark_ticker]['Close']
        benchmark_returns = benchmark_prices.pct_change().dropna()

        # Align dates
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]

        # Calculate cumulative returns
        portfolio_cumulative = (1 + portfolio_aligned).cumprod()
        benchmark_cumulative = (1 + benchmark_aligned).cumprod()

        # Calculate metrics
        portfolio_total = portfolio_cumulative.iloc[-1] - 1
        benchmark_total = benchmark_cumulative.iloc[-1] - 1

        alpha = portfolio_total - benchmark_total

        # Calculate beta
        covariance = np.cov(portfolio_aligned, benchmark_aligned)[0][1]
        benchmark_variance = np.var(benchmark_aligned)
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

        return {
            'success': True,
            'portfolio_return': float(portfolio_total),
            'benchmark_return': float(benchmark_total),
            'alpha': float(alpha),
            'beta': float(beta),
            'outperformance': float(alpha * 100),
            'correlation': float(portfolio_aligned.corr(benchmark_aligned))
        }


def main():
    """Example usage"""
    from module_1_data_collection import DataCollector
    from module_2_technical_screening import TechnicalScreener
    from module_3_correlation_analysis import CorrelationAnalyzer
    from module_5_portfolio_optimization import PortfolioOptimizer

    print("="*70)
    print("MODULE 6: BACKTEST ENGINE")
    print("="*70)

    # Setup
    collector = DataCollector()
    screener = TechnicalScreener()
    analyzer = CorrelationAnalyzer()
    optimizer = PortfolioOptimizer()
    backtester = BacktestEngine(initial_capital=100000)

    # Get data (2 years)
    tickers = collector.load_stock_universe("sp500")
    stock_data = collector.get_latest_data(tickers[:50], days=730)

    # Screen and select
    screening_results = screener.screen_universe(stock_data)
    candidates = screening_results[screening_results['pass'] == True]['ticker'].tolist()

    selected = analyzer.select_low_correlation_stocks(
        candidates,
        stock_data,
        max_correlation=0.4,
        target_count=10
    )

    # Optimize
    opt_result = optimizer.optimize_max_sharpe(selected, stock_data)

    if not opt_result['success']:
        print(f"❌ Optimization failed: {opt_result['message']}")
        return

    print(f"\n✓ Portfolio optimized with {len(selected)} stocks")

    # Backtest on last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)

    backtest_result = backtester.backtest_portfolio(
        opt_result['weights'],
        stock_data,
        start_date,
        end_date
    )

    if backtest_result['success']:
        print(f"\n📈 Backtest Results (Last 6 Months):")
        print(f"  Initial Capital: ${backtest_result['initial_capital']:,.2f}")
        print(f"  Final Value: ${backtest_result['final_value']:,.2f}")
        print(f"  Total Return: {backtest_result['total_return']*100:.2f}%")
        print(f"  Annual Return: {backtest_result['annual_return']*100:.2f}%")
        print(f"  Volatility: {backtest_result['volatility']*100:.2f}%")
        print(f"  Sharpe Ratio: {backtest_result['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {backtest_result['max_drawdown']*100:.2f}%")
        print(f"  Win Rate: {backtest_result['win_rate']*100:.1f}%")

    else:
        print(f"❌ Backtest failed: {backtest_result['message']}")

    print("\n✓ Module 6 Complete!")


if __name__ == "__main__":
    main()
