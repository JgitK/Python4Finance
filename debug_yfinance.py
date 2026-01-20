#!/usr/bin/env python3
"""
Debug script to identify yfinance issues
"""

import sys

print("="*70)
print("YFINANCE TROUBLESHOOTING")
print("="*70)

# Test 1: Check if yfinance is installed
print("\n1. Checking if yfinance is installed...")
try:
    import yfinance as yf
    print(f"   ✓ yfinance version: {yf.__version__}")
except ImportError as e:
    print(f"   ✗ yfinance not installed!")
    print(f"   Error: {e}")
    print(f"\n   FIX: Run: pip install yfinance")
    sys.exit(1)

# Test 2: Check internet connection
print("\n2. Testing internet connection...")
try:
    import urllib.request
    urllib.request.urlopen('https://www.google.com', timeout=5)
    print("   ✓ Internet connection OK")
except Exception as e:
    print(f"   ✗ No internet connection")
    print(f"   Error: {e}")
    sys.exit(1)

# Test 3: Try downloading a single stock
print("\n3. Testing single stock download (AAPL)...")
try:
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    print(f"   Period: {start_date.date()} to {end_date.date()}")

    ticker = yf.Ticker('AAPL')
    data = ticker.history(start=start_date, end=end_date)

    if len(data) > 0:
        print(f"   ✓ Downloaded {len(data)} days of AAPL data")
        print(f"\n   Sample data:")
        print(data.tail())
    else:
        print(f"   ✗ No data returned (empty DataFrame)")
        print(f"   This might be a Yahoo Finance API issue")
except Exception as e:
    print(f"   ✗ Download failed!")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {e}")
    print(f"\n   Troubleshooting:")
    print(f"   - Check if Yahoo Finance is accessible")
    print(f"   - Try: pip install --upgrade yfinance")
    sys.exit(1)

# Test 4: Try the yf.download method
print("\n4. Testing yf.download method...")
try:
    data = yf.download('MSFT', start=start_date, end=end_date, progress=False)
    if len(data) > 0:
        print(f"   ✓ Downloaded {len(data)} days of MSFT data")
    else:
        print(f"   ✗ No data returned")
except Exception as e:
    print(f"   ✗ Download failed: {e}")

# Test 5: Check pandas version
print("\n5. Checking dependencies...")
try:
    import pandas as pd
    import numpy as np
    print(f"   ✓ pandas version: {pd.__version__}")
    print(f"   ✓ numpy version: {np.__version__}")
except ImportError as e:
    print(f"   ✗ Missing dependency: {e}")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)

print("\nIf all tests passed, the issue might be:")
print("1. Yahoo Finance rate limiting (wait a few minutes)")
print("2. Invalid ticker symbols in the universe")
print("3. Date range issues")
print("\nTry running with fewer stocks:")
print("  python run_complete_strategy.py")
print("  (it will auto-limit to 200 stocks)")
