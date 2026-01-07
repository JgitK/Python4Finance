# Example Usage Script
# Demonstrates how to use the portfolio optimization and Ichimoku functions
# without running the full Shiny app

# Load required libraries
library(tidyverse)

# Source the function files
source("download_stocks.R")
source("portfolio_optimization.R")
source("ichimoku_analysis.R")

cat("═══════════════════════════════════════════════════\n")
cat("  R Portfolio Optimization - Example Usage\n")
cat("═══════════════════════════════════════════════════\n\n")

# =====================================================
# EXAMPLE 1: Portfolio Optimization
# =====================================================

cat("\n───────────────────────────────────────────────────\n")
cat("EXAMPLE 1: Portfolio Optimization\n")
cat("───────────────────────────────────────────────────\n\n")

# Select a portfolio of stocks (similar to the Python example)
portfolio_stocks <- c("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
                      "NVDA", "META", "NFLX", "AMD", "COST")

cat("Selected stocks:", paste(portfolio_stocks, collapse = ", "), "\n\n")

# Set date range
start_date <- as.Date("2019-01-01")
end_date <- Sys.Date()

cat("Downloading stock data...\n")

# Download stock data
tryCatch({
  stock_data <- download_stock_data(
    portfolio_stocks,
    from = start_date,
    to = end_date
  )

  cat(sprintf("✓ Downloaded data for %d stocks\n\n", length(stock_data)))

  # Optimize portfolio
  cat("Running portfolio optimization...\n")
  cat("(This may take a minute...)\n\n")

  optimization_results <- optimize_portfolio(
    stock_data,
    num_portfolios = 10000,
    risk_free_rate = 0.0125
  )

  # Print results
  cat("\n")
  cat(generate_portfolio_report(optimization_results))

  # Show top 5 weights
  cat("\nTop 5 Stock Allocations:\n")
  cat("───────────────────────────────────────────────────\n")
  print(head(optimization_results$optimal_weights, 5))

}, error = function(e) {
  cat("Error in portfolio optimization:", e$message, "\n")
  cat("Please check your internet connection and try again.\n\n")
})

# =====================================================
# EXAMPLE 2: Ichimoku Cloud Analysis
# =====================================================

cat("\n\n───────────────────────────────────────────────────\n")
cat("EXAMPLE 2: Ichimoku Cloud Analysis\n")
cat("───────────────────────────────────────────────────\n\n")

# Analyze a single stock with Ichimoku
stock_to_analyze <- "AAPL"

cat(sprintf("Analyzing %s with Ichimoku Cloud...\n\n", stock_to_analyze))

tryCatch({
  # Calculate Ichimoku indicators
  ichimoku_data <- calculate_ichimoku(
    ticker = stock_to_analyze,
    period = "1y",
    interval = "1d"
  )

  cat(sprintf("✓ Calculated Ichimoku for %s\n\n", stock_to_analyze))

  # Generate trading signals
  signals <- generate_ichimoku_signals(ichimoku_data)

  cat(signals$interpretation)

  # Show recent data
  cat("\n\nRecent Ichimoku Data (Last 5 Days):\n")
  cat("───────────────────────────────────────────────────\n")
  recent_data <- tail(ichimoku_data, 5) %>%
    select(Date, Close, Tenkan, Kijun, SenkouA, SenkouB) %>%
    mutate(across(where(is.numeric), ~round(., 2)))
  print(recent_data)

  # Backtest Ichimoku strategy
  cat("\n\nBacktesting Ichimoku Strategy...\n")
  cat("───────────────────────────────────────────────────\n")

  ichimoku_with_signals <- calculate_buy_sell_signals(ichimoku_data)
  backtest_results <- backtest_ichimoku(ichimoku_with_signals, initial_capital = 10000)

  cat(sprintf("Initial Investment: $10,000\n"))
  cat(sprintf("Final Portfolio Value: $%.2f\n", backtest_results$final_value))
  cat(sprintf("Total Return: %.2f%%\n", backtest_results$total_return * 100))
  cat(sprintf("Buy & Hold Return: %.2f%%\n", backtest_results$buy_and_hold_return * 100))
  cat(sprintf("Number of Trades: %d\n", backtest_results$num_trades))

  if (backtest_results$total_return > backtest_results$buy_and_hold_return) {
    cat("\n✓ Ichimoku strategy outperformed buy & hold!\n")
  } else {
    cat("\n✗ Buy & hold outperformed Ichimoku strategy\n")
  }

}, error = function(e) {
  cat("Error in Ichimoku analysis:", e$message, "\n")
  cat("Please check your internet connection and try again.\n\n")
})

# =====================================================
# EXAMPLE 3: Stock Data Management
# =====================================================

cat("\n\n───────────────────────────────────────────────────\n")
cat("EXAMPLE 3: Stock Data Management\n")
cat("───────────────────────────────────────────────────\n\n")

# Save stock data to CSV
cat("Saving stock data to CSV files...\n")

if (exists("stock_data") && length(stock_data) > 0) {
  # Create directory if it doesn't exist
  if (!dir.exists("stock_data")) {
    dir.create("stock_data")
  }

  # Save first 3 stocks as examples
  for (i in 1:min(3, length(stock_data))) {
    ticker <- names(stock_data)[i]
    save_stock_to_csv(stock_data[[ticker]], ticker, "stock_data/")
  }

  cat("\n✓ Saved sample stock data to 'stock_data/' directory\n")
}

# =====================================================
# EXAMPLE 4: Correlation Analysis
# =====================================================

cat("\n\n───────────────────────────────────────────────────\n")
cat("EXAMPLE 4: Correlation Analysis\n")
cat("───────────────────────────────────────────────────\n\n")

if (exists("optimization_results")) {
  cat("Stock Returns Correlation Matrix:\n")
  cat("───────────────────────────────────────────────────\n")

  # Round correlation matrix for display
  corr_matrix <- round(optimization_results$correlation_matrix, 3)

  # Print first 5x5 portion
  print(corr_matrix[1:min(5, nrow(corr_matrix)), 1:min(5, ncol(corr_matrix))])

  cat("\n")
  cat("Interpretation:\n")
  cat("  - Values close to 1: Stocks move together (highly correlated)\n")
  cat("  - Values close to -1: Stocks move opposite (negatively correlated)\n")
  cat("  - Values close to 0: Stocks move independently (uncorrelated)\n")
  cat("\nFor diversification, choose stocks with low correlation!\n")
}

# =====================================================
# Summary
# =====================================================

cat("\n\n═══════════════════════════════════════════════════\n")
cat("  Examples Complete!\n")
cat("═══════════════════════════════════════════════════\n\n")

cat("Next Steps:\n")
cat("  1. Run the full Shiny app: shiny::runApp('app.R')\n")
cat("  2. Modify this script with your own stock selections\n")
cat("  3. Explore different optimization parameters\n")
cat("  4. Try different Ichimoku timeframes\n\n")

cat("Happy investing! (Remember: Past performance doesn't guarantee future results)\n\n")
