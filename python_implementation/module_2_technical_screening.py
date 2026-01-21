#!/usr/bin/env python3
"""
Module 2: Technical Screening
Filters stocks using RSI, MACD, and Ichimoku indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class TechnicalScreener:
    """Screens stocks based on technical indicators"""

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9
    ):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Returns:
            (macd, signal, histogram)
        """
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()

        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line

        return macd, signal_line, histogram

    def calculate_ichimoku(
        self,
        df: pd.DataFrame,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_span_b_period: int = 52
    ) -> pd.DataFrame:
        """
        Calculate Ichimoku Cloud indicators

        Returns:
            DataFrame with Ichimoku components
        """
        high = df['High']
        low = df['Low']
        close = df['Close']

        # Tenkan-sen (Conversion Line)
        tenkan_sen = (high.rolling(window=tenkan_period).max() +
                      low.rolling(window=tenkan_period).min()) / 2

        # Kijun-sen (Base Line)
        kijun_sen = (high.rolling(window=kijun_period).max() +
                     low.rolling(window=kijun_period).min()) / 2

        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)

        # Senkou Span B (Leading Span B)
        senkou_span_b = ((high.rolling(window=senkou_span_b_period).max() +
                         low.rolling(window=senkou_span_b_period).min()) / 2).shift(kijun_period)

        # Chikou Span (Lagging Span)
        chikou_span = close.shift(-kijun_period)

        result = pd.DataFrame({
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span,
            'close': close
        })

        return result

    def is_bullish_ichimoku(self, df: pd.DataFrame) -> bool:
        """
        Check if Ichimoku shows bullish signal

        Bullish conditions:
        1. Price above cloud (above both Senkou Span A and B)
        2. Tenkan-sen above Kijun-sen
        3. Cloud is green (Senkou Span A > Senkou Span B)
        """
        ichimoku = self.calculate_ichimoku(df)

        # Get latest values (last valid data point)
        latest = ichimoku.dropna().iloc[-1] if len(ichimoku.dropna()) > 0 else None

        if latest is None:
            return False

        # Check bullish conditions
        price_above_cloud = (latest['close'] > latest['senkou_span_a'] and
                            latest['close'] > latest['senkou_span_b'])

        tenkan_above_kijun = latest['tenkan_sen'] > latest['kijun_sen']

        green_cloud = latest['senkou_span_a'] > latest['senkou_span_b']

        return price_above_cloud and tenkan_above_kijun and green_cloud

    def screen_stock(
        self,
        ticker: str,
        df: pd.DataFrame,
        params: Dict = None
    ) -> Dict:
        """
        Screen a single stock

        Returns:
            Dict with screening results and indicators
        """
        if params is None:
            params = {
                'rsi_threshold': self.rsi_oversold,
                'require_macd_bullish': True,
                'require_ichimoku_bullish': True
            }

        if len(df) < 100:  # Need sufficient data
            return {
                'ticker': ticker,
                'pass': False,
                'reason': 'Insufficient data'
            }

        try:
            # Calculate indicators
            close = df['Close']

            rsi = self.calculate_rsi(close, self.rsi_period)
            macd, signal, hist = self.calculate_macd(close, self.macd_fast, self.macd_slow, self.macd_signal)
            ichimoku_bullish = self.is_bullish_ichimoku(df)

            # Get latest values
            latest_rsi = rsi.iloc[-1]
            latest_macd = macd.iloc[-1]
            latest_signal = signal.iloc[-1]
            latest_hist = hist.iloc[-1]

            # Screening criteria
            checks = {
                'rsi_valid': not np.isnan(latest_rsi),
                'rsi_not_overbought': latest_rsi < self.rsi_overbought,
                'macd_bullish': latest_macd > latest_signal if params.get('require_macd_bullish', True) else True,
                'macd_positive': latest_hist > 0,
                'ichimoku_bullish': ichimoku_bullish if params.get('require_ichimoku_bullish', True) else True,
            }

            passed = all(checks.values())

            return {
                'ticker': ticker,
                'pass': passed,
                'rsi': latest_rsi,
                'macd': latest_macd,
                'macd_signal': latest_signal,
                'macd_histogram': latest_hist,
                'ichimoku_bullish': ichimoku_bullish,
                'checks': checks,
                'reason': 'Pass' if passed else self._get_fail_reason(checks)
            }

        except Exception as e:
            return {
                'ticker': ticker,
                'pass': False,
                'reason': f'Error: {str(e)}'
            }

    def _get_fail_reason(self, checks: Dict) -> str:
        """Get reason for failing screening"""
        failed = [k for k, v in checks.items() if not v]
        if failed:
            return f"Failed: {', '.join(failed)}"
        return "Unknown"

    def screen_universe(
        self,
        stock_data: Dict[str, pd.DataFrame],
        params: Dict = None
    ) -> pd.DataFrame:
        """
        Screen entire universe of stocks

        Args:
            stock_data: Dict of {ticker: DataFrame}
            params: Screening parameters

        Returns:
            DataFrame with screening results
        """
        print(f"\n🔍 Screening {len(stock_data)} stocks...")

        results = []

        for ticker, df in stock_data.items():
            result = self.screen_stock(ticker, df, params)
            results.append(result)

        df_results = pd.DataFrame(results)

        # Summary
        passed = df_results['pass'].sum()
        total = len(df_results)

        print(f"\n✓ Screening complete:")
        print(f"  Passed: {passed}/{total} ({passed/total*100:.1f}%)")

        return df_results


def main():
    """Example usage"""
    from module_1_data_collection import DataCollector

    print("="*70)
    print("MODULE 2: TECHNICAL SCREENING")
    print("="*70)

    # Load data
    collector = DataCollector()
    tickers = collector.load_stock_universe("sp500")
    stock_data = collector.get_latest_data(tickers[:30], days=365)  # Test with 30 stocks

    # Screen
    screener = TechnicalScreener()
    results = screener.screen_universe(stock_data)

    # Show results
    passed = results[results['pass'] == True].sort_values('rsi')
    print(f"\n📊 Stocks that passed screening ({len(passed)}):")
    print(passed[['ticker', 'rsi', 'macd_histogram', 'ichimoku_bullish']].to_string(index=False))

    print("\n✓ Module 2 Complete!")


if __name__ == "__main__":
    main()
