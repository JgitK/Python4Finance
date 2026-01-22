#!/usr/bin/env Rscript
# ============================================================================
# TEST: Walk-Forward Validation
# ============================================================================
# True out-of-sample testing - NO look-ahead bias
#
# This test:
# 1. Goes back to a historical date
# 2. Selects a portfolio using ONLY data available at that time
# 3. Backtests forward to see actual performance

source("utils_walkforward.R")

cat("============================================================\n")
cat("WALK-FORWARD VALIDATION TEST\n")
cat("============================================================\n")
cat("This is the CORRECT way to validate a strategy.\n")
cat("We select stocks using only historical data, then test forward.\n")
cat("============================================================\n\n")

# ============================================================================
# TEST 1: Single walk-forward test (1 year ago)
# ============================================================================

cat("TEST 1: What if we selected a portfolio 1 year ago?\n")
cat("------------------------------------------------------------\n")

# Select portfolio using data available 1 year ago
selection_date <- Sys.Date() - 365

result <- run_walkforward_test(
  selection_date = selection_date,
  backtest_end = Sys.Date()
)

cat("\n")

# ============================================================================
# TEST 2: Multiple periods (if time permits)
# ============================================================================

cat("\n============================================================\n")
cat("TEST 2: Multiple Walk-Forward Periods\n")
cat("============================================================\n")
cat("Testing strategy consistency across different start dates\n\n")

# Test 3 different selection dates, each with 6-month holding period
selection_dates <- c(
  Sys.Date() - 730,  # 2 years ago
  Sys.Date() - 545,  # 1.5 years ago
  Sys.Date() - 365   # 1 year ago
)

multi_results <- run_multi_period_walkforward(
  selection_dates = selection_dates,
  holding_period = 180  # 6-month holding period
)

# ============================================================================
# INTERPRETATION
# ============================================================================

cat("\n============================================================\n")
cat("INTERPRETATION GUIDE\n")
cat("============================================================\n")
cat("
These results are TRUE out-of-sample performance.
The portfolio was selected WITHOUT knowing future returns.

Key questions to answer:
1. Is the Sharpe ratio consistently positive across periods?
2. Is there high variation between periods? (suggests luck vs skill)
3. How does it compare to the look-ahead biased results?

If the walk-forward Sharpe is much lower than the original
backtest, that confirms look-ahead bias in the original test.

Typical expectations:
- Sharpe 0.5-1.0: Decent strategy
- Sharpe 1.0-2.0: Good strategy
- Sharpe > 2.0: Either very good or still has some bias

The original test showed Sharpe of 6-13, which is unrealistic.
Walk-forward results will likely be much more modest.
")

cat("\n============================================================\n")
cat("WALK-FORWARD VALIDATION COMPLETE\n")
cat("============================================================\n")
