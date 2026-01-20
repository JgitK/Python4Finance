#!/usr/bin/env python3
"""
Module 3: Correlation Analysis
Selects low-correlation stocks for better diversification
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class CorrelationAnalyzer:
    """Analyzes correlations and selects diversified stocks"""

    def __init__(self, correlation_threshold: float = 0.4):
        self.correlation_threshold = correlation_threshold

    def calculate_correlation_matrix(
        self,
        stock_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix for stock returns

        Args:
            stock_data: Dict of {ticker: DataFrame}

        Returns:
            Correlation matrix
        """
        # Extract close prices
        prices = pd.DataFrame()

        for ticker, df in stock_data.items():
            if 'Close' in df.columns:
                prices[ticker] = df['Close']

        # Calculate returns
        returns = prices.pct_change().dropna()

        # Calculate correlation
        corr_matrix = returns.corr()

        return corr_matrix

    def select_low_correlation_stocks(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame],
        max_correlation: float = None,
        target_count: int = 15
    ) -> List[str]:
        """
        Select stocks with low correlation to each other

        Uses greedy algorithm:
        1. Start with stock with highest average return
        2. Add stocks one by one that have lowest correlation with selected
        3. Stop when target count reached or correlation threshold exceeded

        Args:
            tickers: List of candidate tickers
            stock_data: Dict of {ticker: DataFrame}
            max_correlation: Maximum allowed correlation (default: self.correlation_threshold)
            target_count: Target number of stocks to select

        Returns:
            List of selected tickers
        """
        if max_correlation is None:
            max_correlation = self.correlation_threshold

        # Filter stock_data to only include tickers
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}

        if len(filtered_data) == 0:
            return []

        # Calculate correlation matrix
        corr_matrix = self.calculate_correlation_matrix(filtered_data)

        # Calculate average returns for ranking
        returns = pd.DataFrame()
        for ticker, df in filtered_data.items():
            if 'Close' in df.columns:
                returns[ticker] = df['Close'].pct_change()

        avg_returns = returns.mean().sort_values(ascending=False)

        # Greedy selection algorithm
        selected = []

        # Start with highest return stock
        if len(avg_returns) > 0:
            selected.append(avg_returns.index[0])

        # Add stocks iteratively
        candidates = [t for t in avg_returns.index if t not in selected]

        while len(selected) < target_count and len(candidates) > 0:
            best_candidate = None
            lowest_max_corr = float('inf')

            for candidate in candidates:
                # Calculate max correlation with already selected stocks
                correlations = [abs(corr_matrix.loc[candidate, s]) for s in selected]
                max_corr = max(correlations) if correlations else 0

                # Select candidate with lowest maximum correlation
                if max_corr < lowest_max_corr:
                    lowest_max_corr = max_corr
                    best_candidate = candidate

            # Add if below threshold
            if best_candidate and lowest_max_corr < max_correlation:
                selected.append(best_candidate)
                candidates.remove(best_candidate)
            else:
                # No more candidates below threshold
                break

        return selected

    def analyze_portfolio_correlation(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Analyze correlation structure of a portfolio

        Args:
            tickers: Portfolio tickers
            stock_data: Dict of {ticker: DataFrame}

        Returns:
            Dict with correlation statistics
        """
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}

        if len(filtered_data) < 2:
            return {
                'avg_correlation': 0,
                'max_correlation': 0,
                'min_correlation': 0,
                'std_correlation': 0
            }

        corr_matrix = self.calculate_correlation_matrix(filtered_data)

        # Get upper triangle (exclude diagonal)
        mask = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
        correlations = corr_matrix.where(mask).stack().values

        return {
            'avg_correlation': float(np.mean(correlations)),
            'max_correlation': float(np.max(correlations)),
            'min_correlation': float(np.min(correlations)),
            'std_correlation': float(np.std(correlations)),
            'num_pairs': len(correlations)
        }

    def get_highly_correlated_pairs(
        self,
        tickers: List[str],
        stock_data: Dict[str, pd.DataFrame],
        threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of stocks with high correlation

        Args:
            tickers: List of tickers to analyze
            stock_data: Dict of {ticker: DataFrame}
            threshold: Correlation threshold

        Returns:
            List of (ticker1, ticker2, correlation)
        """
        filtered_data = {t: stock_data[t] for t in tickers if t in stock_data}

        if len(filtered_data) < 2:
            return []

        corr_matrix = self.calculate_correlation_matrix(filtered_data)

        pairs = []
        for i, ticker1 in enumerate(corr_matrix.index):
            for ticker2 in corr_matrix.columns[i+1:]:
                corr = corr_matrix.loc[ticker1, ticker2]
                if abs(corr) >= threshold:
                    pairs.append((ticker1, ticker2, corr))

        # Sort by correlation (descending)
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return pairs


def main():
    """Example usage"""
    from module_1_data_collection import DataCollector
    from module_2_technical_screening import TechnicalScreener

    print("="*70)
    print("MODULE 3: CORRELATION ANALYSIS")
    print("="*70)

    # Load data
    collector = DataCollector()
    tickers = collector.load_stock_universe("sp500")
    stock_data = collector.get_latest_data(tickers[:50], days=365)

    # Screen first
    screener = TechnicalScreener()
    screening_results = screener.screen_universe(stock_data)
    candidates = screening_results[screening_results['pass'] == True]['ticker'].tolist()

    print(f"\n✓ {len(candidates)} candidates from technical screening")

    # Analyze correlation
    analyzer = CorrelationAnalyzer(correlation_threshold=0.4)

    # Select low-correlation stocks
    selected = analyzer.select_low_correlation_stocks(
        candidates,
        stock_data,
        max_correlation=0.4,
        target_count=15
    )

    print(f"\n✓ Selected {len(selected)} low-correlation stocks:")
    print(", ".join(selected))

    # Analyze correlation structure
    stats = analyzer.analyze_portfolio_correlation(selected, stock_data)
    print(f"\n📊 Portfolio Correlation Statistics:")
    print(f"  Average: {stats['avg_correlation']:.3f}")
    print(f"  Max: {stats['max_correlation']:.3f}")
    print(f"  Min: {stats['min_correlation']:.3f}")
    print(f"  Std Dev: {stats['std_correlation']:.3f}")

    # Find highly correlated pairs
    high_corr = analyzer.get_highly_correlated_pairs(selected, stock_data, threshold=0.5)
    if high_corr:
        print(f"\n⚠️ Highly correlated pairs (>0.5):")
        for t1, t2, corr in high_corr[:5]:
            print(f"  {t1} - {t2}: {corr:.3f}")

    print("\n✓ Module 3 Complete!")


if __name__ == "__main__":
    main()
