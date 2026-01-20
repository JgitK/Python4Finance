#!/usr/bin/env python3
"""
Complete Portfolio Strategy Runner
Integrates all modules and runs full validation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from module_1_data_collection import DataCollector
from module_2_technical_screening import TechnicalScreener
from module_3_correlation_analysis import CorrelationAnalyzer
from module_5_portfolio_optimization import PortfolioOptimizer
from module_6_backtest_engine import BacktestEngine
from validation_framework import PortfolioValidator, print_validation_summary, BacktestResult


class CompleteStrategy:
    """
    Complete portfolio strategy integrating all modules
    """

    def __init__(self, params: Dict = None):
        """
        Initialize strategy with parameters

        Args:
            params: Strategy parameters
        """
        if params is None:
            params = {}

        # Default parameters
        self.params = {
            'universe': params.get('universe', 'sp500'),
            'max_stocks_download': params.get('max_stocks_download', 200),
            'data_days': params.get('data_days', 730),
            'rsi_threshold': params.get('rsi_threshold', 70),
            'correlation_threshold': params.get('correlation_threshold', 0.4),
            'target_stocks': params.get('target_stocks', 10),
            'risk_free_rate': params.get('risk_free_rate', 0.02),
            'initial_capital': params.get('initial_capital', 100000)
        }

        # Initialize modules
        self.collector = DataCollector()
        self.screener = TechnicalScreener(rsi_overbought=self.params['rsi_threshold'])
        self.analyzer = CorrelationAnalyzer(correlation_threshold=self.params['correlation_threshold'])
        self.optimizer = PortfolioOptimizer(risk_free_rate=self.params['risk_free_rate'])
        self.backtester = BacktestEngine(initial_capital=self.params['initial_capital'])

    def run_strategy(
        self,
        start_date: datetime,
        end_date: datetime,
        params: Dict = None
    ) -> Dict:
        """
        Run complete strategy workflow

        Args:
            start_date: Data start date
            end_date: Data end date
            params: Optional parameter overrides

        Returns:
            Dict with strategy results including selected portfolio
        """
        # Override params if provided
        if params:
            for key, value in params.items():
                if key in self.params:
                    self.params[key] = value

        print(f"\n{'='*70}")
        print(f"RUNNING COMPLETE STRATEGY")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"{'='*70}")

        # Step 1: Load universe and download data
        print(f"\n📥 Step 1: Data Collection")
        tickers = self.collector.load_stock_universe(self.params['universe'])

        # Limit number of stocks to download for speed
        if len(tickers) > self.params['max_stocks_download']:
            tickers = tickers[:self.params['max_stocks_download']]
            print(f"  Limited to {self.params['max_stocks_download']} stocks for performance")

        stock_data = self.collector.download_stock_data(
            tickers,
            start_date,
            end_date
        )

        if len(stock_data) == 0:
            return {
                'success': False,
                'message': 'No data downloaded'
            }

        # Step 2: Technical screening
        print(f"\n🔍 Step 2: Technical Screening")
        screening_results = self.screener.screen_universe(stock_data, params)

        candidates = screening_results[screening_results['pass'] == True]['ticker'].tolist()

        if len(candidates) == 0:
            return {
                'success': False,
                'message': 'No stocks passed technical screening'
            }

        print(f"  {len(candidates)} candidates passed screening")

        # Step 3: Correlation analysis
        print(f"\n🔗 Step 3: Correlation Analysis")
        selected_tickers = self.analyzer.select_low_correlation_stocks(
            candidates,
            stock_data,
            max_correlation=self.params['correlation_threshold'],
            target_count=self.params['target_stocks']
        )

        if len(selected_tickers) < 2:
            return {
                'success': False,
                'message': 'Insufficient stocks after correlation filtering'
            }

        print(f"  Selected {len(selected_tickers)} low-correlation stocks")

        # Step 4: Portfolio optimization
        print(f"\n📈 Step 4: Portfolio Optimization")
        opt_result = self.optimizer.optimize_max_sharpe(selected_tickers, stock_data)

        if not opt_result['success']:
            return {
                'success': False,
                'message': f"Optimization failed: {opt_result['message']}"
            }

        print(f"  Optimized portfolio:")
        print(f"    Expected Return: {opt_result['expected_return']*100:.2f}%")
        print(f"    Volatility: {opt_result['volatility']*100:.2f}%")
        print(f"    Sharpe Ratio: {opt_result['sharpe_ratio']:.3f}")

        # Return portfolio
        return {
            'success': True,
            'stocks': selected_tickers,
            'weights': opt_result['weights'],
            'expected_return': opt_result['expected_return'],
            'volatility': opt_result['volatility'],
            'sharpe_ratio': opt_result['sharpe_ratio'],
            'num_candidates': len(candidates),
            'stock_data': stock_data  # Include for backtesting
        }

    def backtest_strategy(
        self,
        portfolio: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Backtest a portfolio

        Args:
            portfolio: Portfolio dict from run_strategy()
            start_date: Backtest start
            end_date: Backtest end

        Returns:
            Backtest results
        """
        return self.backtester.backtest_portfolio(
            portfolio['weights'],
            portfolio['stock_data'],
            start_date,
            end_date
        )


# Integration with validation framework
def strategy_function_for_validation(start_date, end_date, params=None):
    """
    Wrapper function for validation framework

    This is the function that gets called by PortfolioValidator
    """
    strategy = CompleteStrategy(params)

    result = strategy.run_strategy(start_date, end_date, params)

    if result['success']:
        return {
            'stocks': result['stocks'],
            'weights': result['weights'],
            'stock_data': result['stock_data']
        }
    else:
        # Return empty portfolio if strategy fails
        return {
            'stocks': [],
            'weights': {},
            'stock_data': {}
        }


# Mock data source for validation (uses real yfinance data)
class RealDataSource:
    def __init__(self):
        self.collector = DataCollector()

    def get_data(self, ticker, start_date, end_date):
        """Get real stock data"""
        data = self.collector.download_stock_data(
            [ticker],
            start_date,
            end_date
        )

        if ticker in data:
            return data[ticker]['Close'].values
        else:
            return np.array([])


def run_full_validation():
    """
    Run complete validation with real strategy
    """
    print("\n" + "="*70)
    print("COMPLETE PORTFOLIO STRATEGY VALIDATION")
    print("="*70)
    print("\nThis will run a comprehensive validation of your strategy")
    print("Testing across multiple timeframes, walk-forward windows,")
    print("and Monte Carlo parameter sensitivity.\n")

    # Initialize validator
    data_source = RealDataSource()

    # Update the validator to use actual backtesting
    class RealPortfolioValidator(PortfolioValidator):
        """Extended validator that uses actual backtesting"""

        def _run_backtest(self, start_date, end_date, period_name, predefined_portfolio=None):
            """Override to use real backtesting"""

            # Get portfolio
            if predefined_portfolio is None:
                portfolio = self.strategy_function(
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                portfolio = predefined_portfolio

            if len(portfolio.get('stocks', [])) == 0:
                # Return failed backtest
                return BacktestResult(
                    period=period_name,
                    start_date=start_date,
                    end_date=end_date,
                    total_return=-0.05,
                    sharpe_ratio=-0.5,
                    max_drawdown=-0.1,
                    win_rate=0.3,
                    num_trades=0,
                    stocks_selected=[],
                    annual_return=-0.05,
                    volatility=0.2
                )

            # Run actual backtest
            backtester = BacktestEngine()
            result = backtester.backtest_portfolio(
                portfolio['weights'],
                portfolio['stock_data'],
                start_date,
                end_date
            )

            if result['success']:
                return BacktestResult(
                    period=period_name,
                    start_date=start_date,
                    end_date=end_date,
                    total_return=result['total_return'],
                    sharpe_ratio=result['sharpe_ratio'],
                    max_drawdown=result['max_drawdown'],
                    win_rate=result['win_rate'],
                    num_trades=len(portfolio['stocks']),
                    stocks_selected=portfolio['stocks'],
                    annual_return=result['annual_return'],
                    volatility=result['volatility']
                )
            else:
                # Failed backtest
                return BacktestResult(
                    period=period_name,
                    start_date=start_date,
                    end_date=end_date,
                    total_return=-0.05,
                    sharpe_ratio=-0.5,
                    max_drawdown=-0.1,
                    win_rate=0.3,
                    num_trades=0,
                    stocks_selected=[],
                    annual_return=-0.05,
                    volatility=0.2
                )

    validator = RealPortfolioValidator(
        strategy_function=strategy_function_for_validation,
        data_source=data_source
    )

    # Run validations
    print("\n📊 Phase 1: Multi-Timeframe Analysis")
    mt_results = validator.multi_timeframe_backtest(
        timeframes={
            '6mo': 180,
            '1yr': 365,
            '2yr': 730
        }
    )

    print("\n🔄 Phase 2: Walk-Forward Analysis")
    wf_results = validator.walk_forward_analysis(
        train_period_days=365,
        test_period_days=90,
        step_size_days=90,
        total_history_days=730
    )

    print("\n🎲 Phase 3: Monte Carlo Parameter Sensitivity")
    mc_results = validator.monte_carlo_parameter_sensitivity(
        parameter_ranges={
            'rsi_threshold': (60, 80),
            'target_stocks': (8, 12),
            'correlation_threshold': (0.3, 0.5)
        },
        num_simulations=30,  # Reduced for speed
        test_period_days=365
    )

    # Generate report
    report = validator.generate_validation_report(
        multi_timeframe_results=mt_results,
        walk_forward_results=wf_results,
        monte_carlo_results=mc_results
    )

    print_validation_summary(report)

    return report


def main():
    """Run complete strategy and validation"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--validate':
        # Run full validation
        report = run_full_validation()
    else:
        # Run single strategy instance
        strategy = CompleteStrategy()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2 years

        # Run strategy
        result = strategy.run_strategy(start_date, end_date)

        if result['success']:
            print(f"\n✓ Strategy completed successfully!")
            print(f"\n💼 Final Portfolio ({len(result['stocks'])} stocks):")

            weights_df = pd.DataFrame([
                {'Ticker': ticker, 'Weight %': result['weights'][ticker] * 100}
                for ticker in result['stocks']
            ]).sort_values('Weight %', ascending=False)

            print(weights_df.to_string(index=False))

            # Backtest on last 6 months
            backtest_start = end_date - timedelta(days=180)
            backtest_result = strategy.backtest_strategy(result, backtest_start, end_date)

            if backtest_result['success']:
                print(f"\n📈 Backtest (Last 6 Months):")
                print(f"  Return: {backtest_result['total_return']*100:.2f}%")
                print(f"  Sharpe: {backtest_result['sharpe_ratio']:.3f}")
                print(f"  Max DD: {backtest_result['max_drawdown']*100:.2f}%")
        else:
            print(f"\n❌ Strategy failed: {result['message']}")


if __name__ == "__main__":
    main()
