#!/usr/bin/env python3
"""
Data Availability Diagnostic for Backtesting
Checks which portfolio stocks have sufficient historical data
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DATA_DIR = Path("stocks")
PORTFOLIO_FILE = Path("analysis/final_portfolio.rds")
BACKTEST_DAYS = 180  # 6 months

TEST_START = datetime.now() - timedelta(days=BACKTEST_DAYS)
TEST_END = datetime.now()

print("=" * 60)
print("DATA AVAILABILITY CHECK")
print("=" * 60)
print(f"\nBacktest period: {TEST_START.date()} to {TEST_END.date()}")
print(f"Required days: {BACKTEST_DAYS}\n")

# Get list of portfolio stocks
# Since we can't read .rds in Python, let's check the stocks directory
stock_files = sorted(DATA_DIR.glob("*.csv"))

if not stock_files:
    print(f"ERROR: No stock CSV files found in {DATA_DIR}")
    print("Please ensure stock data has been downloaded first.")
    exit(1)

# Check each stock
availability = []

for stock_file in stock_files:
    ticker = stock_file.stem  # filename without extension

    try:
        df = pd.read_csv(stock_file)

        # Assuming date column exists (could be 'date', 'Date', or index)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df['date'] = df['Date']
        else:
            # Try first column
            df['date'] = pd.to_datetime(df.iloc[:, 0])

        first_date = df['date'].min()
        last_date = df['date'].max()
        days_available = len(df)
        covers_backtest = (first_date <= TEST_START) and (last_date >= TEST_END)

        availability.append({
            'ticker': ticker,
            'has_data': True,
            'first_date': first_date.date(),
            'last_date': last_date.date(),
            'days_available': days_available,
            'covers_backtest': covers_backtest
        })

    except Exception as e:
        availability.append({
            'ticker': ticker,
            'has_data': False,
            'first_date': None,
            'last_date': None,
            'days_available': 0,
            'covers_backtest': False,
            'error': str(e)
        })

# Create DataFrame
df_avail = pd.DataFrame(availability)

# Print results
print("\nStock Data Availability:")
print("-" * 60)
print(df_avail.to_string(index=False))

# Summary
print(f"\n{'=' * 60}")
print("SUMMARY")
print("=" * 60)
print(f"Stocks with data: {df_avail['has_data'].sum()}/{len(df_avail)}")
print(f"Stocks covering backtest period: {df_avail['covers_backtest'].sum()}/{len(df_avail)}")

# Stocks with insufficient data
insufficient = df_avail[~df_avail['covers_backtest']]

if len(insufficient) > 0:
    print(f"\n⚠ PROBLEM STOCKS ({len(insufficient)} with insufficient data):")
    print("-" * 60)
    print(insufficient[['ticker', 'first_date', 'last_date']].to_string(index=False))

    print("\nSOLUTION OPTIONS:")
    print("1. Adjust backtest period to match available data")
    print("2. Replace these stocks with alternatives from candidates")
    print("3. Run backtest only on stocks with sufficient data")

    # Show available stocks
    sufficient = df_avail[df_avail['covers_backtest']]
    if len(sufficient) > 0:
        print(f"\n✓ Stocks with sufficient data ({len(sufficient)}):")
        print(", ".join(sufficient['ticker'].tolist()))

    # Calculate adjusted backtest period
    valid_dates = df_avail[df_avail['has_data']]['first_date']
    if len(valid_dates) > 0:
        earliest_common = valid_dates.max()
        print(f"\nADJUSTED BACKTEST PERIOD SUGGESTION:")
        print(f"  Start: {earliest_common} (earliest common date)")
        print(f"  End: {TEST_END.date()} (today)")
else:
    print("\n✓ All stocks have sufficient data for the backtest period!")

print()
