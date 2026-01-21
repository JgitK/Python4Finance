#!/usr/bin/env python3
"""
Quick test to verify yfinance works and download sample data
"""

print("Testing yfinance installation and connectivity...\n")

# Step 1: Import test
print("1. Testing imports...")
try:
    import yfinance as yf
    import pandas as pd
    from datetime import datetime, timedelta
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    print("\n   Install missing packages:")
    print("   pip install yfinance pandas")
    exit(1)

# Step 2: Download test
print("\n2. Testing download for AAPL...")
try:
    # Use simpler date range
    data = yf.download('AAPL', period='1y', progress=False)

    if data is not None and len(data) > 0:
        print(f"   ✓ Downloaded {len(data)} days of data")
        print(f"\n   Latest prices:")
        print(data[['Open', 'High', 'Low', 'Close']].tail(3))
    else:
        print("   ✗ Download returned empty data")
        print("\n   Possible issues:")
        print("   - Yahoo Finance API is down")
        print("   - Network connectivity issues")
        print("   - Rate limiting")

except Exception as e:
    print(f"   ✗ Download failed!")
    print(f"   Error: {e}")
    print(f"\n   Troubleshooting:")
    print(f"   1. Check internet connection")
    print(f"   2. Try: pip install --upgrade yfinance")
    print(f"   3. Wait a few minutes (rate limiting)")
    exit(1)

# Step 3: Test multiple stocks
print("\n3. Testing multiple stock download...")
try:
    tickers = ['MSFT', 'GOOGL', 'AMZN']
    data = yf.download(tickers, period='6mo', progress=False, group_by='ticker')

    if data is not None and len(data) > 0:
        print(f"   ✓ Downloaded data for {len(tickers)} stocks")
        for ticker in tickers:
            if ticker in data.columns.get_level_values(0):
                count = len(data[ticker].dropna())
                print(f"     {ticker}: {count} days")
    else:
        print("   ✗ Multiple stock download failed")

except Exception as e:
    print(f"   ⚠️ Multiple download failed: {e}")
    print(f"   Note: Single stock downloads work, so you can still use the system")

# Step 4: Date range test
print("\n4. Testing specific date range...")
try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print(f"   Requesting: {start_date.date()} to {end_date.date()}")

    data = yf.download('NVDA', start=start_date, end=end_date, progress=False)

    if data is not None and len(data) > 0:
        print(f"   ✓ Downloaded {len(data)} days")
        print(f"   Actual range: {data.index.min().date()} to {data.index.max().date()}")
    else:
        print("   ✗ No data returned for date range")

except Exception as e:
    print(f"   ✗ Date range download failed: {e}")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)

print("\nIf tests passed, yfinance is working correctly!")
print("The issue might be with the specific stock tickers in your universe.")
print("\nNext steps:")
print("1. Check which stocks are in your universe")
print("2. Try with a smaller set first")
print("3. Run: python run_complete_strategy.py")
