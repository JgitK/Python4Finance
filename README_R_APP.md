# R Portfolio Optimization & Technical Analysis App

A comprehensive R Shiny application for portfolio optimization and technical analysis using the Wilshire 5000 stock index. This app provides daily data refresh capabilities, Markowitz mean-variance portfolio optimization, and Ichimoku cloud charting for technical analysis.

## Features

### 1. **Portfolio Optimization**
- **Markowitz Mean-Variance Optimization**: Implements Harry Markowitz's Modern Portfolio Theory to find the optimal portfolio that maximizes returns while minimizing risk
- **Efficient Frontier Visualization**: Interactive plot showing the risk-return tradeoff across thousands of random portfolios
- **Sharpe Ratio Optimization**: Automatically identifies the portfolio with the maximum Sharpe ratio
- **Correlation Analysis**: Visualize correlation matrices to select uncorrelated stocks
- **Custom Portfolio Selection**: Choose from any stocks in the Wilshire 5000 index
- **Monte Carlo Simulation**: Generate up to 50,000 random portfolio combinations

### 2. **Ichimoku Cloud Technical Analysis**
- **Complete Ichimoku Indicators**:
  - Tenkan-sen (Conversion Line)
  - Kijun-sen (Base Line)
  - Senkou Span A (Leading Span A)
  - Senkou Span B (Leading Span B)
  - Chikou Span (Lagging Span)
- **Interactive Charts**: Fully interactive Plotly charts with zoom, pan, and hover features
- **Trading Signals**: Automated buy/sell/hold signal generation
- **Multiple Timeframes**: Analyze stocks across different periods (1 month to 5 years)
- **Multiple Intervals**: Daily, weekly, or monthly data intervals
- **Signal Interpretation**: Detailed explanation of current market conditions

### 3. **Stock Data Management**
- **Daily Data Refresh**: Update stock prices with the latest market data
- **Wilshire 5000 Coverage**: Access to all stocks in the Wilshire 5000 index
- **Automatic Data Download**: Fetch historical data from Yahoo Finance
- **Data Caching**: Store downloaded data locally for faster access
- **Market Status**: Real-time indication of market open/closed status

### 4. **Interactive Dashboard**
- **Real-time Statistics**: View total stocks, last update time, and market status
- **Customizable Date Ranges**: Select custom time periods for analysis
- **Responsive Design**: Works on desktop and tablet devices
- **Export Capabilities**: Download portfolio weights and stock lists

## Installation

### Prerequisites

- R (version 4.0 or higher)
- RStudio (recommended)

### Required R Packages

Install the required packages by running the following command in R:

```r
install.packages(c(
  "shiny",
  "shinydashboard",
  "quantmod",
  "PerformanceAnalytics",
  "PortfolioAnalytics",
  "plotly",
  "DT",
  "tidyverse",
  "xts",
  "lubridate",
  "quadprog"
))
```

### Installation Steps

1. Clone or download this repository
2. Ensure the Wilshire-5000-Stocks.csv file is in the project directory
3. Open RStudio and set the working directory to the project folder
4. Install the required packages (see above)
5. Run the app

## Usage

### Starting the Application

#### Option 1: Run from RStudio
```r
# Set working directory
setwd("/path/to/Python4Finance")

# Run the app
shiny::runApp("app.R")
```

#### Option 2: Run from R Console
```r
library(shiny)
runApp("/path/to/Python4Finance/app.R")
```

The app will open in your default web browser at `http://127.0.0.1:xxxx`

### Using the Dashboard

1. **Dashboard Tab**
   - View overall statistics
   - Check market status
   - See last data update time

2. **Portfolio Optimization Tab**
   - Select 2-20 stocks from the Wilshire 5000 index
   - Adjust the number of random portfolios (1,000 - 50,000)
   - Set the risk-free rate (default: 1.25%)
   - Click "Optimize Portfolio" to run the optimization
   - View the efficient frontier plot
   - Examine optimal portfolio weights
   - Analyze the correlation matrix

3. **Ichimoku Analysis Tab**
   - Select a stock ticker from the dropdown
   - Choose time period (1 month to 5 years)
   - Select data interval (daily, weekly, monthly)
   - Click "Plot Ichimoku" to generate the chart
   - View trading signals and interpretation

4. **Stock Data Manager Tab**
   - Browse all Wilshire 5000 stocks
   - Download the stock list as CSV
   - Check data update status

## File Structure

```
Python4Finance/
├── app.R                        # Main Shiny application
├── download_stocks.R            # Stock data download functions
├── portfolio_optimization.R     # Portfolio optimization functions
├── ichimoku_analysis.R         # Ichimoku technical analysis functions
├── Wilshire-5000-Stocks.csv    # Wilshire 5000 stock list
├── README_R_APP.md             # This file
└── stock_data/                 # Directory for cached stock data (auto-created)
```

## Portfolio Optimization Theory

### Markowitz Mean-Variance Optimization

The app implements Harry Markowitz's Modern Portfolio Theory (MPT), which demonstrates that investors can construct portfolios to optimize or maximize expected return based on a given level of market risk.

**Key Concepts:**

1. **Expected Return**:
   ```
   E(Rp) = Σ(wi × E(Ri))
   ```
   Where wi is the weight of stock i and E(Ri) is its expected return

2. **Portfolio Variance**:
   ```
   σp² = Σ Σ wi wj σij
   ```
   Where σij is the covariance between stocks i and j

3. **Sharpe Ratio**:
   ```
   Sharpe Ratio = (E(Rp) - Rf) / σp
   ```
   Where Rf is the risk-free rate and σp is portfolio standard deviation

The optimization process:
1. Downloads historical price data for selected stocks
2. Calculates log returns and annualizes them (252 trading days)
3. Computes the covariance matrix of returns
4. Generates thousands of random portfolio combinations
5. Identifies the portfolio with the maximum Sharpe ratio
6. Visualizes the efficient frontier

## Ichimoku Cloud Analysis

### Ichimoku Kinko Hyo Components

The Ichimoku Cloud (Ichimoku Kinko Hyo) is a comprehensive technical indicator that provides information on support/resistance, trend direction, and momentum.

**Five Components:**

1. **Tenkan-sen (Conversion Line)**
   ```
   (9-period high + 9-period low) / 2
   ```
   - Fast-moving average
   - Indicates short-term trend

2. **Kijun-sen (Base Line)**
   ```
   (26-period high + 26-period low) / 2
   ```
   - Slower-moving average
   - Acts as support/resistance
   - Confirms trend changes

3. **Senkou Span A (Leading Span A)**
   ```
   (Tenkan-sen + Kijun-sen) / 2, plotted 26 periods ahead
   ```
   - Forms one edge of the cloud
   - Future support/resistance

4. **Senkou Span B (Leading Span B)**
   ```
   (52-period high + 52-period low) / 2, plotted 26 periods ahead
   ```
   - Forms the other edge of the cloud
   - Thicker support/resistance

5. **Chikou Span (Lagging Span)**
   ```
   Current close price, plotted 26 periods back
   ```
   - Confirms trend strength

### Trading Signals

**Bullish Signals:**
- Price above the cloud
- Tenkan-sen crosses above Kijun-sen (Golden Cross)
- Senkou Span A above Senkou Span B (green cloud)
- Chikou Span above the price from 26 periods ago

**Bearish Signals:**
- Price below the cloud
- Tenkan-sen crosses below Kijun-sen (Dead Cross)
- Senkou Span A below Senkou Span B (red cloud)
- Chikou Span below the price from 26 periods ago

## Data Sources

- **Stock Price Data**: Yahoo Finance (via `quantmod` package)
- **Wilshire 5000 Index**: Provided in `Wilshire-5000-Stocks.csv`
- **Risk-Free Rate**: User configurable (default: 1.25% approximating 10-year Treasury)

## Performance Considerations

### Optimization Speed

- **10,000 portfolios**: ~5-10 seconds for 10 stocks
- **25,000 portfolios**: ~15-30 seconds for 10 stocks
- **50,000 portfolios**: ~30-60 seconds for 10 stocks

The optimization time increases with:
- Number of portfolios generated
- Number of stocks in the portfolio
- Length of historical data period

### Data Download

- First-time download of stock data can take time
- Data is cached locally for faster subsequent access
- Use the "Refresh Data" button to update prices
- Consider downloading data during non-peak hours

## Troubleshooting

### Common Issues

1. **Package Installation Errors**
   ```r
   # Try installing packages individually
   install.packages("shiny")
   install.packages("quantmod")
   # etc.
   ```

2. **Data Download Failures**
   - Check internet connection
   - Verify stock ticker symbols are correct
   - Yahoo Finance may rate-limit requests; try again later

3. **App Won't Start**
   ```r
   # Check for errors in the R console
   # Ensure all required files are present
   # Verify working directory is correct
   getwd()
   ```

4. **Slow Performance**
   - Reduce number of random portfolios
   - Select fewer stocks for optimization
   - Use shorter time periods for analysis

### Error Messages

- **"File Doesn't Exist"**: Ensure Wilshire-5000-Stocks.csv is in the directory
- **"No stock data downloaded"**: Check ticker symbols and internet connection
- **"Please select at least 2 stocks"**: Portfolio optimization requires minimum 2 stocks

## Advanced Usage

### Downloading All Wilshire Stocks

To pre-download all Wilshire 5000 stocks:

```r
source("download_stocks.R")

# Download all stocks (this will take several hours!)
download_all_wilshire_stocks(
  wilshire_file = "Wilshire-5000-Stocks.csv",
  folder = "stock_data/",
  from = Sys.Date() - 365*5,  # 5 years of data
  to = Sys.Date()
)
```

### Custom Portfolio Analysis

```r
source("portfolio_optimization.R")
source("download_stocks.R")

# Select stocks
tickers <- c("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA")

# Get data
stock_data <- download_stock_data(
  tickers,
  from = as.Date("2019-01-01"),
  to = Sys.Date()
)

# Optimize
results <- optimize_portfolio(
  stock_data,
  num_portfolios = 10000,
  risk_free_rate = 0.0125
)

# Print report
cat(generate_portfolio_report(results))
```

### Ichimoku Analysis Script

```r
source("ichimoku_analysis.R")

# Calculate Ichimoku
ichimoku_data <- calculate_ichimoku(
  ticker = "AAPL",
  period = "1y",
  interval = "1d"
)

# Generate signals
signals <- generate_ichimoku_signals(ichimoku_data)
print(signals$interpretation)

# Backtest strategy
backtest_results <- backtest_ichimoku(ichimoku_data, initial_capital = 10000)
print(paste("Total Return:", round(backtest_results$total_return * 100, 2), "%"))
```

## Scheduled Data Updates

To automatically refresh data daily, you can use R's task scheduling:

### On Windows (Task Scheduler)
```r
library(taskscheduleR)

taskscheduler_create(
  taskname = "update_stocks",
  rscript = "path/to/update_script.R",
  schedule = "DAILY",
  starttime = "09:00"
)
```

### On Linux/Mac (cron)
```bash
# Add to crontab
0 9 * * 1-5 Rscript /path/to/update_script.R
```

## Contributing

This project was converted from Python to R. Contributions are welcome!

Areas for improvement:
- Add more optimization algorithms (genetic algorithms, etc.)
- Implement additional technical indicators
- Add backtesting capabilities
- Include fundamental data analysis
- Support for cryptocurrencies and forex

## License

This project is open source and available for educational purposes.

## Acknowledgments

- **Harry Markowitz**: For Modern Portfolio Theory
- **Goichi Hosoda**: For developing the Ichimoku Cloud indicator
- **Yahoo Finance**: For providing free financial data
- **R Community**: For the excellent packages used in this app

## References

1. Markowitz, H. (1952). "Portfolio Selection". The Journal of Finance. 7 (1): 77–91.
2. Hosoda, G. (1996). "Ichimoku Kinko Studies"
3. Sharpe, W. F. (1966). "Mutual Fund Performance". The Journal of Business. 39 (S1): 119–138.

## Contact

For questions, issues, or suggestions, please open an issue on GitHub.

---

**Note**: This application is for educational and research purposes only. Past performance does not guarantee future results. Always do your own research before making investment decisions.
