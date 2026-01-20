#!/usr/bin/env python3
"""
Module 5: Portfolio Optimization
Uses Modern Portfolio Theory to calculate optimal weights
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')


class PortfolioOptimizer:
    """Optimizes portfolio weights using MPT"""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def calculate_returns_and_cov(
        self,
        stock_data: Dict[str, pd.DataFrame]
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Calculate expected returns and covariance matrix

        Args:
            stock_data: Dict of {ticker: DataFrame}

        Returns:
            (expected_returns, covariance_matrix)
        """
        # Extract close prices
        prices = pd.DataFrame()

        for ticker, df in stock_data.items():
            if 'Close' in df.columns:
                prices[ticker] = df['Close']

        # Calculate returns
        returns = prices.pct_change().dropna()

        # Expected returns (annualized)
        expected_returns = returns.mean() * 252

        # Covariance matrix (annualized)
        cov_matrix = returns.cov() * 252

        return expected_returns, cov_matrix

    def portfolio_performance(
        self,
        weights: np.ndarray,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio performance metrics

        Args:
            weights: Portfolio weights
            expected_returns: Expected returns for each asset
            cov_matrix: Covariance matrix

        Returns:
            (return, volatility, sharpe_ratio)
        """
        portfolio_return = np.sum(weights * expected_returns)
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std

        return portfolio_return, portfolio_std, sharpe_ratio

    def neg_sharpe_ratio(
        self,
        weights: np.ndarray,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame
    ) -> float:
        """Negative Sharpe ratio for optimization (scipy minimizes)"""
        return -self.portfolio_performance(weights, expected_returns, cov_matrix)[2]

    def optimize_max_sharpe(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Find portfolio weights that maximize Sharpe ratio

        Args:
            tickers: List of tickers to include
            stock_data: Dict of {ticker: DataFrame}

        Returns:
            Dict with optimal weights and performance metrics
        """
        # Filter stock data
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}

        if len(filtered_data) < 2:
            return {
                'success': False,
                'message': 'Need at least 2 stocks'
            }

        # Calculate returns and covariance
        expected_returns, cov_matrix = self.calculate_returns_and_cov(filtered_data)

        # Number of assets
        n_assets = len(expected_returns)

        # Constraints and bounds
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        bounds = tuple((0, 1) for _ in range(n_assets))  # No short selling

        # Initial guess (equal weights)
        init_guess = np.array([1 / n_assets] * n_assets)

        # Optimize
        result = minimize(
            self.neg_sharpe_ratio,
            init_guess,
            args=(expected_returns, cov_matrix),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            return {
                'success': False,
                'message': f'Optimization failed: {result.message}'
            }

        # Calculate performance metrics
        optimal_weights = result.x
        ret, vol, sharpe = self.portfolio_performance(optimal_weights, expected_returns, cov_matrix)

        # Create results dict
        weights_dict = {ticker: weight for ticker, weight in zip(expected_returns.index, optimal_weights)}

        return {
            'success': True,
            'tickers': list(expected_returns.index),
            'weights': weights_dict,
            'weights_array': optimal_weights,
            'expected_return': float(ret),
            'volatility': float(vol),
            'sharpe_ratio': float(sharpe),
            'expected_returns': expected_returns.to_dict(),
            'cov_matrix': cov_matrix
        }

    def optimize_min_volatility(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Find portfolio weights that minimize volatility

        Args:
            tickers: List of tickers to include
            stock_data: Dict of {ticker: DataFrame}

        Returns:
            Dict with optimal weights and performance metrics
        """
        # Filter stock data
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}

        if len(filtered_data) < 2:
            return {
                'success': False,
                'message': 'Need at least 2 stocks'
            }

        # Calculate returns and covariance
        expected_returns, cov_matrix = self.calculate_returns_and_cov(filtered_data)

        # Number of assets
        n_assets = len(expected_returns)

        # Objective: minimize volatility
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # Constraints and bounds
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(n_assets))
        init_guess = np.array([1 / n_assets] * n_assets)

        # Optimize
        result = minimize(
            portfolio_volatility,
            init_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            return {
                'success': False,
                'message': f'Optimization failed: {result.message}'
            }

        # Calculate performance metrics
        optimal_weights = result.x
        ret, vol, sharpe = self.portfolio_performance(optimal_weights, expected_returns, cov_matrix)

        weights_dict = {ticker: weight for ticker, weight in zip(expected_returns.index, optimal_weights)}

        return {
            'success': True,
            'tickers': list(expected_returns.index),
            'weights': weights_dict,
            'weights_array': optimal_weights,
            'expected_return': float(ret),
            'volatility': float(vol),
            'sharpe_ratio': float(sharpe)
        }

    def generate_efficient_frontier(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame],
        num_portfolios: int = 100
    ) -> pd.DataFrame:
        """
        Generate efficient frontier

        Args:
            tickers: List of tickers
            stock_data: Dict of {ticker: DataFrame}
            num_portfolios: Number of portfolios to generate

        Returns:
            DataFrame with returns, volatility, and Sharpe ratios
        """
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}
        expected_returns, cov_matrix = self.calculate_returns_and_cov(filtered_data)

        n_assets = len(expected_returns)

        results = []

        for _ in range(num_portfolios):
            # Random weights
            weights = np.random.random(n_assets)
            weights /= np.sum(weights)

            # Calculate performance
            ret, vol, sharpe = self.portfolio_performance(weights, expected_returns, cov_matrix)

            results.append({
                'return': ret,
                'volatility': vol,
                'sharpe': sharpe
            })

        return pd.DataFrame(results)


def main():
    """Example usage"""
    from module_1_data_collection import DataCollector
    from module_2_technical_screening import TechnicalScreener
    from module_3_correlation_analysis import CorrelationAnalyzer

    print("="*70)
    print("MODULE 5: PORTFOLIO OPTIMIZATION")
    print("="*70)

    # Load data
    collector = DataCollector()
    tickers = collector.load_stock_universe("sp500")
    stock_data = collector.get_latest_data(tickers[:50], days=730)

    # Screen
    screener = TechnicalScreener()
    screening_results = screener.screen_universe(stock_data)
    candidates = screening_results[screening_results['pass'] == True]['ticker'].tolist()

    # Select low correlation
    analyzer = CorrelationAnalyzer()
    selected = analyzer.select_low_correlation_stocks(
        candidates,
        stock_data,
        max_correlation=0.4,
        target_count=10
    )

    print(f"\n✓ Optimizing portfolio with {len(selected)} stocks:")
    print(", ".join(selected))

    # Optimize
    optimizer = PortfolioOptimizer(risk_free_rate=0.02)
    result = optimizer.optimize_max_sharpe(selected, stock_data)

    if result['success']:
        print(f"\n📈 Optimal Portfolio (Max Sharpe Ratio):")
        print(f"  Expected Return: {result['expected_return']*100:.2f}%")
        print(f"  Volatility: {result['volatility']*100:.2f}%")
        print(f"  Sharpe Ratio: {result['sharpe_ratio']:.3f}")

        print(f"\n💼 Portfolio Weights:")
        weights_df = pd.DataFrame([
            {'Ticker': ticker, 'Weight': weight, 'Weight %': weight * 100}
            for ticker, weight in result['weights'].items()
        ]).sort_values('Weight', ascending=False)

        print(weights_df.to_string(index=False))

    else:
        print(f"❌ Optimization failed: {result['message']}")

    print("\n✓ Module 5 Complete!")


if __name__ == "__main__":
    main()
