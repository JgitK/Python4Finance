# Quick Start Guide

Get up and running with the R Portfolio Optimization App in 5 minutes!

## Prerequisites

- R installed (version 4.0+)
- RStudio (recommended but not required)
- Internet connection for downloading stock data

## Installation (3 steps)

### Step 1: Install Required Packages

Open R or RStudio and run:

```r
# Set your working directory to the project folder
setwd("/path/to/Python4Finance")

# Run the setup script
source("setup.R")
```

This will automatically install all required packages.

### Step 2: Verify Files

Make sure you have these files in your directory:
- `app.R` - Main Shiny application
- `download_stocks.R` - Stock data functions
- `portfolio_optimization.R` - Optimization functions
- `ichimoku_analysis.R` - Technical analysis functions
- `Wilshire-5000-Stocks.csv` - Stock list

### Step 3: Launch the App

```r
library(shiny)
runApp("app.R")
```

The app will open in your browser automatically!

## First Time Usage

### Try Portfolio Optimization

1. Click on the **Portfolio Optimization** tab
2. Select a few stocks (start with 5-10):
   - Type stock ticker in the "Select Stocks" box
   - Try: AAPL, MSFT, GOOGL, AMZN, TSLA
3. Click **Optimize Portfolio**
4. Wait 10-30 seconds
5. View your results!

### Try Ichimoku Analysis

1. Click on the **Ichimoku Analysis** tab
2. Select a stock (e.g., AAPL)
3. Choose "1 Year" for period
4. Choose "Daily" for interval
5. Click **Plot Ichimoku**
6. View the chart and trading signals!

## Quick Example (Without the App)

Want to try the functions directly? Run the example script:

```r
source("example_usage.R")
```

This will demonstrate:
- Portfolio optimization with 10 stocks
- Ichimoku analysis on AAPL
- Data management
- Correlation analysis

## Common First-Time Issues

### "Package not found"
**Solution**: Run `source("setup.R")` again

### "File doesn't exist"
**Solution**: Make sure `Wilshire-5000-Stocks.csv` is in your directory

### "Download failed"
**Solution**: Check your internet connection; Yahoo Finance might be down temporarily

### App is slow
**Solution**: Start with fewer stocks (5-10) and 10,000 portfolios

## App Features Overview

### 📊 Dashboard
- View statistics
- Check market status
- Monitor last update

### 📈 Portfolio Optimization
- Select stocks from Wilshire 5000
- Generate efficient frontier
- Find optimal weights
- Maximize Sharpe ratio

### 📉 Ichimoku Analysis
- Plot Ichimoku cloud charts
- Get trading signals
- Multiple timeframes
- Buy/sell recommendations

### 💾 Data Manager
- Browse stocks
- Download stock lists
- Update data

## Next Steps

After getting familiar with the app:

1. **Read the full README**: `README_R_APP.md`
2. **Try different stocks**: Experiment with various combinations
3. **Adjust parameters**: Change risk-free rate, number of portfolios
4. **Explore timeframes**: Try different periods for Ichimoku
5. **Learn the theory**: Read about Markowitz optimization and Ichimoku

## Sample Portfolios to Try

### Tech-Heavy Portfolio
AAPL, MSFT, GOOGL, NVDA, AMD, TSLA, META, NFLX

### Diversified Portfolio
AAPL, JPM, JNJ, XOM, PG, WMT, DIS, BA, COST, UNH

### Growth Portfolio
TSLA, NVDA, AMD, SQ, SHOP, ROKU, PLTR, COIN

## Tips for Best Results

1. **Stock Selection**:
   - Choose 8-15 stocks for good diversification
   - Mix different sectors
   - Look for low correlation stocks

2. **Optimization Parameters**:
   - Start with 10,000 portfolios
   - Increase to 25,000-50,000 for final analysis
   - Adjust risk-free rate to current Treasury yield

3. **Ichimoku Analysis**:
   - Use daily interval for short-term trading
   - Use weekly for medium-term
   - Use monthly for long-term trends
   - Works best with trending stocks

4. **Data Management**:
   - Refresh data daily during market hours
   - Use 2-5 years of historical data for optimization
   - Cache data locally for faster access

## Getting Help

If you encounter issues:

1. Check the error message in the R console
2. Verify all files are present
3. Ensure packages are installed correctly
4. Check internet connection
5. Read the full README for detailed troubleshooting

## Performance Tips

- **Faster optimization**: Use fewer portfolios or fewer stocks
- **Faster charts**: Use shorter time periods
- **Save time**: Pre-download stock data using `download_stocks.R`

## What to Expect

### Portfolio Optimization (10 stocks, 10,000 portfolios)
- Download time: 5-15 seconds
- Optimization time: 5-10 seconds
- Total: ~20 seconds

### Ichimoku Chart (1 year daily data)
- Download time: 2-5 seconds
- Calculation time: 1-2 seconds
- Total: ~5 seconds

## Support

For questions or issues, refer to:
- `README_R_APP.md` - Complete documentation
- `example_usage.R` - Usage examples
- R help: `?function_name`

---

**Happy Analyzing!** 🚀

Remember: This is for educational purposes. Always do your own research before making investment decisions.
