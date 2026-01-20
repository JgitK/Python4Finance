#!/usr/bin/env python3
"""
Module 1: Data Collection
Downloads historical stock data from Wilshire 5000 universe
"""

import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class DataCollector:
    """Handles downloading and caching stock data"""

    def __init__(self, data_dir: str = "stocks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.metadata_dir = Path("metadata")
        self.metadata_dir.mkdir(exist_ok=True)

    def load_stock_universe(self, universe: str = "wilshire5000") -> List[str]:
        """
        Load stock universe tickers

        Args:
            universe: "wilshire5000", "sp500", or path to CSV

        Returns:
            List of ticker symbols
        """
        if universe == "wilshire5000":
            # Try to load from existing Wilshire CSV
            csv_path = Path("Wilshire-5000-Stocks.csv")
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                # Handle different column name possibilities
                ticker_col = None
                for col in ['Ticker', 'ticker', 'Symbol', 'symbol']:
                    if col in df.columns:
                        ticker_col = col
                        break

                if ticker_col:
                    tickers = df[ticker_col].dropna().unique().tolist()
                    print(f"✓ Loaded {len(tickers)} tickers from Wilshire 5000")
                    return tickers
                else:
                    print("⚠️ Could not find ticker column in Wilshire CSV")

            # Fallback: Use S&P 500 + common large caps
            print("⚠️ Wilshire CSV not found, using S&P 500 + extended universe")
            return self._get_sp500_extended()

        elif universe == "sp500":
            return self._get_sp500_extended()

        else:
            # Custom CSV file
            df = pd.read_csv(universe)
            return df.iloc[:, 0].dropna().unique().tolist()

    def _get_sp500_extended(self) -> List[str]:
        """Get S&P 500 + common large caps as fallback"""
        # Common large-cap stocks across sectors
        base_tickers = [
            # Technology
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
            'AVGO', 'ORCL', 'ADBE', 'CRM', 'CSCO', 'ACN', 'AMD', 'INTC',
            'IBM', 'QCOM', 'TXN', 'INTU', 'NOW', 'AMAT', 'MU', 'ADI',

            # Financials
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'SPGI',
            'BX', 'CB', 'MMC', 'PGR', 'AON', 'ICE', 'CME', 'USB', 'PNC', 'TFC',

            # Healthcare
            'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'PFE', 'AMGN',
            'CVS', 'BMY', 'GILD', 'MDT', 'CI', 'ISRG', 'REGN', 'VRTX', 'ZTS', 'SYK',

            # Consumer Discretionary
            'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'BKNG', 'MAR',
            'GM', 'F', 'CMG', 'ORLY', 'AZO', 'YUM', 'ROST', 'DHI', 'LEN', 'POOL',

            # Consumer Staples
            'WMT', 'PG', 'COST', 'KO', 'PEP', 'PM', 'MO', 'CL', 'MDLZ', 'KMB',
            'GIS', 'KHC', 'STZ', 'SYY', 'HSY', 'K', 'CAG', 'CPB', 'TSN', 'HRL',

            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL',
            'WMB', 'KMI', 'OKE', 'LNG', 'FANG', 'DVN', 'HES', 'MRO', 'APA', 'CTRA',

            # Industrials
            'CAT', 'BA', 'UPS', 'HON', 'RTX', 'UNP', 'DE', 'LMT', 'GE', 'MMM',
            'FDX', 'NSC', 'CSX', 'EMR', 'ETN', 'ITW', 'PH', 'WM', 'GD', 'NOC',

            # Materials
            'LIN', 'APD', 'SHW', 'ECL', 'DD', 'NEM', 'FCX', 'NUE', 'VMC', 'MLM',

            # Real Estate
            'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'O', 'SBAC', 'SPG',

            # Utilities
            'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'PEG', 'XEL', 'ED',

            # Communication Services
            'META', 'GOOGL', 'GOOG', 'NFLX', 'DIS', 'CMCSA', 'T', 'VZ', 'TMUS', 'CHTR'
        ]

        return sorted(list(set(base_tickers)))  # Remove duplicates

    def download_stock_data(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Download historical stock data

        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            force_refresh: If True, re-download even if cached

        Returns:
            Dict of {ticker: DataFrame}
        """
        print(f"\n📥 Downloading data for {len(tickers)} stocks")
        print(f"Period: {start_date.date()} to {end_date.date()}")

        data = {}
        success_count = 0
        fail_count = 0

        for i, ticker in enumerate(tickers, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(tickers)} ({i/len(tickers)*100:.1f}%)")

            cache_file = self.data_dir / f"{ticker}.csv"

            # Load from cache if available
            if cache_file.exists() and not force_refresh:
                try:
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    # Check if cached data covers our period
                    if df.index.min() <= start_date and df.index.max() >= end_date:
                        data[ticker] = df
                        success_count += 1
                        continue
                except Exception:
                    pass

            # Download from yfinance
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(start=start_date, end=end_date)

                if len(df) > 0:
                    # Save to cache
                    df.to_csv(cache_file)
                    data[ticker] = df
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                fail_count += 1
                continue

        print(f"\n✓ Successfully downloaded: {success_count}/{len(tickers)}")
        print(f"✗ Failed: {fail_count}/{len(tickers)}")

        return data

    def calculate_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily returns from prices"""
        return prices.pct_change().dropna()

    def get_latest_data(
        self,
        tickers: List[str],
        days: int = 730  # 2 years default
    ) -> Dict[str, pd.DataFrame]:
        """
        Get latest data for tickers

        Args:
            tickers: List of ticker symbols
            days: Number of days of history

        Returns:
            Dict of {ticker: DataFrame}
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.download_stock_data(tickers, start_date, end_date)


def main():
    """Example usage"""
    print("="*70)
    print("MODULE 1: DATA COLLECTION")
    print("="*70)

    collector = DataCollector()

    # Load universe
    tickers = collector.load_stock_universe("sp500")

    # Download data (2 years)
    data = collector.get_latest_data(tickers[:50], days=730)  # Test with 50 stocks

    print(f"\nSample data for {list(data.keys())[0]}:")
    print(data[list(data.keys())[0]].tail())

    print("\n✓ Module 1 Complete!")


if __name__ == "__main__":
    main()
