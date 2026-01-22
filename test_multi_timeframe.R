#!/usr/bin/env Rscript
# ============================================================================
# TEST: Multi-Timeframe Analysis
# ============================================================================
# Purpose: Test portfolio robustness across different time periods
# This helps identify look-ahead bias and validate strategy consistency

source("utils_validation.R")

cat("============================================================\n")
cat("CHECKPOINT 2: MULTI-TIMEFRAME ANALYSIS\n")
cat("============================================================\n")

# Load portfolio
portfolio <- run_strategy_for_period(
  start_date = Sys.Date() - 365,
  end_date = Sys.Date()
)

cat(sprintf("\nPortfolio: %d stocks\n", length(portfolio$ticker)))
cat("Tickers:", paste(portfolio$ticker, collapse = ", "), "\n")

# Run multi-timeframe analysis
results <- run_multi_timeframe_analysis(portfolio)

cat("\n============================================================\n")
cat("CHECKPOINT 2 COMPLETE\n")
cat("============================================================\n")
cat("\nNext steps:\n")
cat("- If results are consistent: Strategy appears robust\n")
cat("- If Sharpe drops significantly in longer periods: Possible look-ahead bias\n")
cat("- If high variation: Consider rolling window analysis\n")
