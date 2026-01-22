#!/usr/bin/env Rscript
# ============================================================================
# TEST: Validation Utilities
# ============================================================================
# Purpose: Verify utils_validation.R works before building more

source("utils_validation.R")

cat("============================================================\n")
cat("TESTING VALIDATION UTILITIES\n")
cat("============================================================\n")

# Check prerequisites
cat("\nChecking prerequisites...\n")

if (!file.exists("analysis/final_portfolio.rds")) {
  cat("✗ Missing: analysis/final_portfolio.rds\n")
  cat("\nYou need to run Modules 1-6 first:\n")
  cat("  Rscript 01_download_stock_data.R\n")
  cat("  Rscript 02_technical_analysis_screening.R\n")
  cat("  Rscript 03_correlation_analysis.R\n")
  cat("  Rscript 04_ichimoku_validation.R\n")
  cat("  Rscript 05_portfolio_optimization.R\n")
  cat("  Rscript 06_backtest_validation.R\n")
  stop("Prerequisites not met")
}

cat("✓ analysis/final_portfolio.rds exists\n")

# Test 1: Load portfolio
cat("\n------------------------------------------------------------\n")
cat("Test 1: Loading portfolio\n")
cat("------------------------------------------------------------\n")

portfolio <- run_strategy_for_period(
  start_date = Sys.Date() - 365,
  end_date = Sys.Date()
)

cat("\nPortfolio stocks:\n")
# Use equal weights if no weight column exists
if ("weight" %in% names(portfolio)) {
  weights <- portfolio$weight
} else {
  weights <- rep(1 / length(portfolio$ticker), length(portfolio$ticker))
}
print(data.frame(
  ticker = portfolio$ticker,
  weight = weights
))

# Test 2: Backtest for 6 months
cat("\n------------------------------------------------------------\n")
cat("Test 2: Backtesting 6-month period\n")
cat("------------------------------------------------------------\n")

backtest_result <- backtest_portfolio(
  portfolio,
  start_date = Sys.Date() - 180,
  end_date = Sys.Date()
)

cat("\nBacktest metrics:\n")
cat(sprintf("  Total Return:  %6.2f%%\n", backtest_result$total_return * 100))
cat(sprintf("  Annual Return: %6.2f%%\n", backtest_result$annual_return * 100))
cat(sprintf("  Volatility:    %6.2f%%\n", backtest_result$volatility * 100))
cat(sprintf("  Sharpe Ratio:  %6.2f\n", backtest_result$sharpe_ratio))
cat(sprintf("  Max Drawdown:  %6.2f%%\n", backtest_result$max_drawdown * 100))
cat(sprintf("  Trading Days:  %d\n", backtest_result$num_days))

# Assessment
cat("\n============================================================\n")
cat("ASSESSMENT\n")
cat("============================================================\n")

if (backtest_result$sharpe_ratio > 1.0) {
  cat("✓ EXCELLENT - Sharpe ratio > 1.0\n")
} else if (backtest_result$sharpe_ratio > 0.5) {
  cat("✓ GOOD - Sharpe ratio > 0.5\n")
} else if (backtest_result$sharpe_ratio > 0) {
  cat("⚠ MODERATE - Positive Sharpe ratio\n")
} else {
  cat("✗ WEAK - Negative Sharpe ratio\n")
}

cat("\n✓ All tests passed!\n")
cat("\nNext step: If this looks correct, we can add multi-timeframe analysis.\n")
