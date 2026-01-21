#!/usr/bin/env python3
"""
Comprehensive Validation Framework for Portfolio Strategy
Includes: Multi-timeframe, Walk-forward, and Monte Carlo validation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestResult:
    """Container for backtest results"""
    period: str
    start_date: datetime
    end_date: datetime
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    stocks_selected: List[str]
    annual_return: float
    volatility: float


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    multi_timeframe_results: Dict[str, BacktestResult]
    walk_forward_results: List[BacktestResult]
    monte_carlo_results: Dict[str, any]
    robustness_score: float
    recommendation: str
    warnings: List[str]


class PortfolioValidator:
    """
    Comprehensive portfolio strategy validator
    Tests strategy robustness across multiple dimensions
    """

    def __init__(self, strategy_function, data_source):
        """
        Args:
            strategy_function: Function that takes (data, params) and returns portfolio
            data_source: Object that provides historical data
        """
        self.strategy_function = strategy_function
        self.data_source = data_source
        self.validation_history = []

    def multi_timeframe_backtest(
        self,
        timeframes: Dict[str, int] = None
    ) -> Dict[str, BacktestResult]:
        """
        Test strategy across multiple timeframes

        Args:
            timeframes: Dict of {name: days} e.g., {'6mo': 180, '1yr': 365}

        Returns:
            Dict of BacktestResults for each timeframe
        """
        if timeframes is None:
            timeframes = {
                '6mo': 180,
                '1yr': 365,
                '2yr': 730,
                '5yr': 1825,
                '10yr': 3650
            }

        results = {}
        end_date = datetime.now()

        for name, days in timeframes.items():
            start_date = end_date - timedelta(days=days)

            print(f"Testing {name} timeframe ({start_date.date()} to {end_date.date()})...")

            result = self._run_backtest(
                start_date=start_date,
                end_date=end_date,
                period_name=name
            )

            results[name] = result

        return results

    def walk_forward_analysis(
        self,
        train_period_days: int = 730,  # 2 years
        test_period_days: int = 180,   # 6 months
        step_size_days: int = 90,      # 3 months
        total_history_days: int = 1825  # 5 years
    ) -> List[BacktestResult]:
        """
        Walk-forward validation: Train on period A, test on period B, roll forward

        This tests if the PROCESS consistently works, not just one instance

        Args:
            train_period_days: Days to use for training (portfolio selection)
            test_period_days: Days to test the portfolio on
            step_size_days: How much to roll forward each iteration
            total_history_days: Total historical period to cover

        Returns:
            List of BacktestResults for each walk-forward window
        """
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=total_history_days)

        current_train_start = start_date
        window_num = 1

        while True:
            current_train_end = current_train_start + timedelta(days=train_period_days)
            current_test_end = current_train_end + timedelta(days=test_period_days)

            # Stop if we've exceeded available data
            if current_test_end > end_date:
                break

            print(f"\nWalk-Forward Window {window_num}:")
            print(f"  Train: {current_train_start.date()} to {current_train_end.date()}")
            print(f"  Test:  {current_train_end.date()} to {current_test_end.date()}")

            # Train: Run strategy on training period to select portfolio
            portfolio = self.strategy_function(
                start_date=current_train_start,
                end_date=current_train_end
            )

            # Test: Backtest the selected portfolio on out-of-sample period
            result = self._run_backtest(
                start_date=current_train_end,
                end_date=current_test_end,
                period_name=f"WF_Window_{window_num}",
                predefined_portfolio=portfolio
            )

            results.append(result)

            # Step forward
            current_train_start += timedelta(days=step_size_days)
            window_num += 1

        return results

    def monte_carlo_parameter_sensitivity(
        self,
        parameter_ranges: Dict[str, Tuple[float, float]],
        num_simulations: int = 100,
        test_period_days: int = 365
    ) -> Dict[str, any]:
        """
        Test strategy with randomized parameters to check robustness

        If strategy only works with very specific parameters, it's overfitted
        If it works across a range of parameters, it's robust

        Args:
            parameter_ranges: Dict of {param_name: (min, max)}
            num_simulations: Number of random parameter combinations to test
            test_period_days: Period to backtest each combination

        Returns:
            Dict with simulation results and statistics
        """
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=test_period_days)

        print(f"\nRunning {num_simulations} Monte Carlo simulations...")

        for i in range(num_simulations):
            # Generate random parameters
            params = {}
            for param_name, (min_val, max_val) in parameter_ranges.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = np.random.randint(min_val, max_val + 1)
                else:
                    params[param_name] = np.random.uniform(min_val, max_val)

            # Run strategy with these parameters
            try:
                portfolio = self.strategy_function(
                    start_date=start_date,
                    end_date=end_date,
                    params=params
                )

                result = self._run_backtest(
                    start_date=start_date,
                    end_date=end_date,
                    period_name=f"MC_{i+1}",
                    predefined_portfolio=portfolio
                )

                results.append({
                    'simulation': i + 1,
                    'params': params,
                    'sharpe': result.sharpe_ratio,
                    'return': result.total_return,
                    'max_dd': result.max_drawdown
                })

            except Exception as e:
                print(f"  Simulation {i+1} failed: {e}")
                continue

            if (i + 1) % 20 == 0:
                print(f"  Completed {i + 1}/{num_simulations} simulations")

        # Analyze results
        sharpes = [r['sharpe'] for r in results]
        returns = [r['return'] for r in results]

        analysis = {
            'num_simulations': len(results),
            'profitable_pct': len([r for r in returns if r > 0]) / len(results) * 100,
            'positive_sharpe_pct': len([s for s in sharpes if s > 0]) / len(sharpes) * 100,
            'avg_sharpe': np.mean(sharpes),
            'median_sharpe': np.median(sharpes),
            'std_sharpe': np.std(sharpes),
            'min_sharpe': np.min(sharpes),
            'max_sharpe': np.max(sharpes),
            'avg_return': np.mean(returns),
            'std_return': np.std(returns),
            'sharpe_25th_percentile': np.percentile(sharpes, 25),
            'sharpe_75th_percentile': np.percentile(sharpes, 75),
            'all_results': results
        }

        return analysis

    def _run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        period_name: str,
        predefined_portfolio: Optional[Dict] = None
    ) -> BacktestResult:
        """
        Run a single backtest

        Args:
            start_date: Backtest start
            end_date: Backtest end
            period_name: Name for this period
            predefined_portfolio: If provided, use this portfolio instead of running strategy

        Returns:
            BacktestResult
        """
        # Get portfolio (either predefined or run strategy)
        if predefined_portfolio is None:
            portfolio = self.strategy_function(
                start_date=start_date,
                end_date=end_date
            )
        else:
            portfolio = predefined_portfolio

        # Simulate portfolio performance
        # This is a placeholder - you'll replace with actual backtesting logic
        returns = self._calculate_portfolio_returns(portfolio, start_date, end_date)

        # Calculate metrics
        total_return = (returns + 1).prod() - 1
        sharpe_ratio = self._calculate_sharpe(returns)
        max_drawdown = self._calculate_max_drawdown(returns)

        # Annualize
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / days) - 1
        volatility = returns.std() * np.sqrt(252)

        return BacktestResult(
            period=period_name,
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=0.0,  # Placeholder
            num_trades=len(portfolio.get('stocks', [])),
            stocks_selected=portfolio.get('stocks', []),
            annual_return=annual_return,
            volatility=volatility
        )

    def _calculate_portfolio_returns(
        self,
        portfolio: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> pd.Series:
        """Calculate daily returns for a portfolio (placeholder)"""
        # This is a simplified placeholder - you'll implement actual logic
        days = (end_date - start_date).days
        # Simulate some returns for now
        return pd.Series(np.random.randn(days) * 0.01)

    def _calculate_sharpe(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio"""
        excess_returns = returns - (risk_free_rate / 252)
        if returns.std() == 0:
            return 0.0
        return np.sqrt(252) * excess_returns.mean() / returns.std()

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    def generate_validation_report(
        self,
        multi_timeframe_results: Dict[str, BacktestResult],
        walk_forward_results: List[BacktestResult],
        monte_carlo_results: Dict[str, any]
    ) -> ValidationReport:
        """
        Generate comprehensive validation report with robustness score

        Returns:
            ValidationReport with overall assessment
        """
        warnings = []
        scores = []

        # 1. Multi-timeframe consistency (0-100 points)
        mt_sharpes = [r.sharpe_ratio for r in multi_timeframe_results.values()]
        mt_positive_pct = len([s for s in mt_sharpes if s > 0]) / len(mt_sharpes) * 100
        mt_score = mt_positive_pct * 0.5  # Max 50 points

        if mt_positive_pct < 60:
            warnings.append(f"Only {mt_positive_pct:.0f}% of timeframes are profitable")

        scores.append(('Multi-timeframe consistency', mt_score))

        # 2. Walk-forward stability (0-100 points)
        wf_sharpes = [r.sharpe_ratio for r in walk_forward_results]
        wf_positive_pct = len([s for s in wf_sharpes if s > 0]) / len(wf_sharpes) * 100
        wf_score = wf_positive_pct * 0.5  # Max 50 points

        if wf_positive_pct < 50:
            warnings.append(f"Walk-forward: Only {wf_positive_pct:.0f}% of windows are profitable")

        scores.append(('Walk-forward stability', wf_score))

        # 3. Monte Carlo robustness (0-100 points)
        mc_score = monte_carlo_results['positive_sharpe_pct'] * 0.5  # Max 50 points

        if monte_carlo_results['positive_sharpe_pct'] < 70:
            warnings.append(f"Monte Carlo: Only {monte_carlo_results['positive_sharpe_pct']:.0f}% of parameter combinations are profitable")

        scores.append(('Monte Carlo robustness', mc_score))

        # 4. Overall Sharpe quality (0-100 points)
        avg_sharpe = np.mean(mt_sharpes + wf_sharpes)
        sharpe_score = min(avg_sharpe * 50, 50)  # Max 50 points (Sharpe > 1.0)

        scores.append(('Average Sharpe quality', sharpe_score))

        # Calculate final robustness score (0-100)
        robustness_score = (
            mt_score * 0.25 +
            wf_score * 0.35 +
            mc_score * 0.25 +
            sharpe_score * 0.15
        )

        # Generate recommendation
        if robustness_score >= 70:
            recommendation = "STRONG - Strategy is robust and ready for live trading"
        elif robustness_score >= 50:
            recommendation = "MODERATE - Strategy shows promise but needs refinement"
        elif robustness_score >= 30:
            recommendation = "WEAK - Strategy needs significant improvement"
        else:
            recommendation = "FAIL - Strategy is not viable, reconsider approach"

        return ValidationReport(
            multi_timeframe_results=multi_timeframe_results,
            walk_forward_results=walk_forward_results,
            monte_carlo_results=monte_carlo_results,
            robustness_score=robustness_score,
            recommendation=recommendation,
            warnings=warnings
        )


def print_validation_summary(report: ValidationReport):
    """Pretty print validation report"""
    print("\n" + "="*70)
    print("PORTFOLIO STRATEGY VALIDATION REPORT")
    print("="*70)

    print(f"\n🎯 ROBUSTNESS SCORE: {report.robustness_score:.1f}/100")
    print(f"📊 RECOMMENDATION: {report.recommendation}")

    if report.warnings:
        print(f"\n⚠️  WARNINGS ({len(report.warnings)}):")
        for w in report.warnings:
            print(f"   - {w}")

    print("\n" + "-"*70)
    print("MULTI-TIMEFRAME ANALYSIS")
    print("-"*70)
    for name, result in report.multi_timeframe_results.items():
        print(f"{name:10s} | Sharpe: {result.sharpe_ratio:6.2f} | Return: {result.total_return*100:6.1f}% | MaxDD: {result.max_drawdown*100:6.1f}%")

    print("\n" + "-"*70)
    print("WALK-FORWARD ANALYSIS")
    print("-"*70)
    for result in report.walk_forward_results:
        print(f"{result.period:15s} | Sharpe: {result.sharpe_ratio:6.2f} | Return: {result.total_return*100:6.1f}%")

    avg_wf_sharpe = np.mean([r.sharpe_ratio for r in report.walk_forward_results])
    print(f"\nAverage Walk-Forward Sharpe: {avg_wf_sharpe:.2f}")

    print("\n" + "-"*70)
    print("MONTE CARLO ANALYSIS")
    print("-"*70)
    mc = report.monte_carlo_results
    print(f"Simulations run:        {mc['num_simulations']}")
    print(f"Profitable:             {mc['profitable_pct']:.1f}%")
    print(f"Positive Sharpe:        {mc['positive_sharpe_pct']:.1f}%")
    print(f"Average Sharpe:         {mc['avg_sharpe']:.2f}")
    print(f"Sharpe 25th-75th %ile:  {mc['sharpe_25th_percentile']:.2f} to {mc['sharpe_75th_percentile']:.2f}")

    print("\n" + "="*70)


if __name__ == "__main__":
    # Example usage
    print("Validation Framework Module")
    print("Import this module to validate your portfolio strategy")
