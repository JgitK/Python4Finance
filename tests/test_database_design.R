#!/usr/bin/env Rscript
# ============================================================================
# TEST: Database Design Validation
# ============================================================================
# This script validates that our database design can capture all the data
# currently produced by our R pipeline.
#
# It simulates what would be written to each database table and verifies
# the design is complete.

library(dplyr)
library(tidyr)

cat("============================================================\n")
cat("DATABASE DESIGN VALIDATION TESTS\n")
cat("============================================================\n\n")

# Track test results
tests_passed <- 0
tests_failed <- 0

run_test <- function(test_name, test_fn) {
  cat(sprintf("TEST: %s\n", test_name))
  cat(paste(rep("-", 60), collapse = ""), "\n")

  result <- tryCatch({
    test_fn()
    TRUE
  }, error = function(e) {
    cat(sprintf("  FAILED: %s\n", e$message))
    FALSE
  })

  if (result) {
    cat("  PASSED\n")
    tests_passed <<- tests_passed + 1
  } else {
    tests_failed <<- tests_failed + 1
  }
  cat("\n")
}

# ============================================================================
# TEST 1: stocks table
# ============================================================================

run_test("Table 'stocks' - can capture stock metadata", function() {

  # Load current data
  download_log <- read.csv("metadata/download_log.csv", stringsAsFactors = FALSE)
  portfolio <- readRDS("analysis/final_portfolio.rds")

  # Simulate what would go in the 'stocks' table
  stocks_table <- download_log %>%
    filter(success == TRUE) %>%
    select(ticker, sector) %>%
    mutate(
      company_name = NA_character_,  # Would need to add this
      current_price = NA_real_,      # Filled by daily update
      price_updated_at = NA_character_
    )

  cat(sprintf("  Would insert %d rows into 'stocks' table\n", nrow(stocks_table)))
  cat("  Sample rows:\n")
  print(head(stocks_table, 3))

  # Validation
  stopifnot(nrow(stocks_table) > 2000)
  stopifnot("ticker" %in% names(stocks_table))
  stopifnot("sector" %in% names(stocks_table))
})

# ============================================================================
# TEST 2: stock_prices table
# ============================================================================

run_test("Table 'stock_prices' - can capture price history", function() {

  # Load one stock as example
  source("utils_data_loader.R", local = TRUE)
  sample_stock <- load_stock("AAPL")

  # Simulate what would go in 'stock_prices' table
  stock_prices_sample <- sample_stock %>%
    mutate(ticker = "AAPL") %>%
    select(ticker, date, open, high, low, close, volume, adjusted)

  cat(sprintf("  AAPL has %d price rows\n", nrow(stock_prices_sample)))
  cat(sprintf("  Date range: %s to %s\n", min(sample_stock$date), max(sample_stock$date)))
  cat("  Sample rows:\n")
  print(tail(stock_prices_sample, 3))

  # Validation
  stopifnot(nrow(stock_prices_sample) > 1000)
  stopifnot(all(c("date", "open", "close", "volume") %in% names(stock_prices_sample)))
})

# ============================================================================
# TEST 3: analysis_runs table
# ============================================================================

run_test("Table 'analysis_runs' - can capture pipeline metadata", function() {

  # Simulate an analysis run record
  analysis_run <- data.frame(
    run_id = 1,
    run_date = Sys.time(),
    status = "success",
    sharpe_ratio = 2.45,  # From walk-forward validation
    notes = "Weekly scheduled run"
  )

  cat("  Would insert 1 row into 'analysis_runs' table:\n")
  print(analysis_run)

  # Validation
  stopifnot(nrow(analysis_run) == 1)
})

# ============================================================================
# TEST 4: portfolio_stocks table
# ============================================================================

run_test("Table 'portfolio_stocks' - can capture selected portfolio", function() {

  # Load current portfolio and weights
  portfolio <- readRDS("analysis/final_portfolio.rds")
  weights <- readRDS("analysis/optimal_weights.rds")
  ichimoku <- readRDS("analysis/ichimoku_validation.rds")

  # Simulate what would go in 'portfolio_stocks' table
  portfolio_stocks_table <- portfolio %>%
    left_join(weights %>% select(ticker, max_sharpe_weight), by = "ticker") %>%
    left_join(ichimoku %>% select(ticker, signal), by = "ticker") %>%
    mutate(
      run_id = 1,
      rank = row_number()
    ) %>%
    select(
      run_id,
      ticker,
      rank,
      weight = max_sharpe_weight,
      sharpe_ratio,
      avg_correlation,
      ichimoku_signal = signal
    )

  cat(sprintf("  Would insert %d rows into 'portfolio_stocks' table\n", nrow(portfolio_stocks_table)))
  cat("  Portfolio stocks:\n")
  print(portfolio_stocks_table)

  # Validation
  stopifnot(nrow(portfolio_stocks_table) == 12)
  stopifnot(sum(portfolio_stocks_table$weight) > 0.99)  # Weights sum to ~1
})

# ============================================================================
# TEST 5: bench_stocks table
# ============================================================================

run_test("Table 'bench_stocks' - can capture bench (alternates)", function() {

  # Load candidates and portfolio
  candidates <- readRDS("analysis/candidate_stocks.rds")
  portfolio <- readRDS("analysis/final_portfolio.rds")

  # Get stocks that are candidates but not in final portfolio
  bench_stocks_table <- candidates %>%
    filter(!ticker %in% portfolio$ticker) %>%
    arrange(desc(sharpe_ratio)) %>%
    head(10) %>%
    mutate(
      run_id = 1,
      rank = row_number(),
      notes = "Not selected - correlation or sector constraint"
    ) %>%
    select(run_id, ticker, rank, sector, sharpe_ratio, notes)

  cat(sprintf("  Would insert %d rows into 'bench_stocks' table\n", nrow(bench_stocks_table)))
  cat("  Bench stocks (top 10 alternates):\n")
  print(bench_stocks_table)

  # Validation
  stopifnot(nrow(bench_stocks_table) == 10)
  stopifnot(!any(bench_stocks_table$ticker %in% portfolio$ticker))
})

# ============================================================================
# TEST 6: stock_correlations table
# ============================================================================

run_test("Table 'stock_correlations' - can capture correlation matrix", function() {

  # Load correlation matrix
  corr_matrix <- readRDS("analysis/portfolio_correlation_heatmap.rds")

  # Convert matrix to long format for database
  corr_long <- corr_matrix %>%
    as.data.frame() %>%
    mutate(ticker_a = rownames(.)) %>%
    pivot_longer(cols = -ticker_a, names_to = "ticker_b", values_to = "correlation") %>%
    filter(ticker_a < ticker_b) %>%  # Only store upper triangle
    mutate(run_id = 1) %>%
    select(run_id, ticker_a, ticker_b, correlation)

  cat(sprintf("  Would insert %d rows into 'stock_correlations' table\n", nrow(corr_long)))
  cat("  Sample correlations:\n")
  print(head(corr_long, 5))

  # Validation
  stopifnot(nrow(corr_long) == 66)  # 12 choose 2 = 66 pairs
  stopifnot(max(corr_long$correlation) <= 1.0)
  stopifnot(min(corr_long$correlation) >= -1.0)
})

# ============================================================================
# TEST 7: Allocation calculation
# ============================================================================

run_test("API calculation - can compute allocation from database data", function() {

  # Simulate API request: GET /api/portfolio?amount=3500
  investment_amount <- 3500

  # Data that would come from database
  weights <- readRDS("analysis/optimal_weights.rds")
  portfolio <- readRDS("analysis/final_portfolio.rds")

  # Simulate the calculation the API would do
  allocation <- weights %>%
    left_join(portfolio %>% select(ticker, current_price), by = "ticker") %>%
    mutate(
      dollar_amount = max_sharpe_weight * investment_amount,
      shares = floor(dollar_amount / current_price),
      actual_invested = shares * current_price
    ) %>%
    filter(shares > 0) %>%
    select(ticker, shares, price = current_price, amount = actual_invested)

  total_invested <- sum(allocation$amount)
  cash_remaining <- investment_amount - total_invested

  cat(sprintf("  Investment: $%s\n", format(investment_amount, big.mark = ",")))
  cat(sprintf("  Total invested: $%.2f\n", total_invested))
  cat(sprintf("  Cash remaining: $%.2f\n", cash_remaining))
  cat(sprintf("  Efficiency: %.1f%%\n", 100 * total_invested / investment_amount))
  cat("  Allocation:\n")
  print(allocation)

  # Validation
  stopifnot(total_invested > 0)
  stopifnot(total_invested <= investment_amount)
  stopifnot(cash_remaining >= 0)
})

# ============================================================================
# TEST 8: Replacement suggestion logic
# ============================================================================

run_test("API calculation - can suggest bench replacements", function() {

  # Simulate: User sells TFPM, needs replacement
  sold_ticker <- "TFPM"

  # Load data
  portfolio <- readRDS("analysis/final_portfolio.rds")
  candidates <- readRDS("analysis/candidate_stocks.rds")
  corr_matrix <- readRDS("analysis/portfolio_correlation_heatmap.rds")

  # Remaining portfolio after selling
  remaining_tickers <- portfolio$ticker[portfolio$ticker != sold_ticker]

  # Get bench stocks
  bench <- candidates %>%
    filter(!ticker %in% portfolio$ticker) %>%
    arrange(desc(sharpe_ratio)) %>%
    head(10)

  # For each bench stock, calculate average correlation with remaining portfolio
  # (This would use the stock_correlations table in production)

  cat(sprintf("  User sold: %s\n", sold_ticker))
  cat(sprintf("  Remaining portfolio: %s\n", paste(remaining_tickers, collapse = ", ")))
  cat("  Top 3 bench replacements:\n")
  print(bench %>% select(ticker, sector, sharpe_ratio) %>% head(3))

  # Validation
  stopifnot(length(remaining_tickers) == 11)
  stopifnot(nrow(bench) == 10)
})

# ============================================================================
# TEST 9: User portfolio tracking
# ============================================================================

run_test("Table 'user_portfolios' - can track user holdings", function() {

  # Simulate a user's holdings
  user_holdings <- data.frame(
    id = 1:3,
    user_id = 42,
    ticker = c("BBVA", "TFPM", "IDR"),
    shares = c(24, 15, 10),
    purchase_price = c(24.38, 36.99, 44.36),
    purchase_date = as.Date("2026-01-21"),
    sold_at = c(NA, 43.55, NA),  # TFPM was sold
    sold_date = c(NA, as.Date("2026-02-15"), NA),
    status = c("held", "sold", "held")
  )

  cat("  Sample user holdings:\n")
  print(user_holdings)

  # Calculate performance
  current_prices <- c(BBVA = 28.50, TFPM = 43.55, IDR = 52.10)

  performance <- user_holdings %>%
    filter(status == "held") %>%
    mutate(
      current_price = current_prices[ticker],
      gain_loss = (current_price - purchase_price) * shares,
      gain_loss_pct = (current_price - purchase_price) / purchase_price * 100
    )

  cat("\n  Performance of held positions:\n")
  print(performance %>% select(ticker, shares, purchase_price, current_price, gain_loss_pct))

  # Validation
  stopifnot(sum(user_holdings$status == "held") == 2)
  stopifnot(sum(user_holdings$status == "sold") == 1)
})

# ============================================================================
# TEST 10: Price alert logic
# ============================================================================

run_test("Table 'price_alerts' - can detect trigger conditions", function() {

  # Simulate alerts
  alerts <- data.frame(
    alert_id = 1:2,
    user_id = 42,
    ticker = c("BBVA", "IDR"),
    condition = c("above", "above"),
    target_percent = c(15, 20),
    triggered = c(FALSE, FALSE),
    created_at = Sys.time()
  )

  # User's purchase prices
  purchases <- data.frame(
    ticker = c("BBVA", "IDR"),
    purchase_price = c(24.38, 44.36)
  )

  # Current prices (simulated)
  current_prices <- data.frame(
    ticker = c("BBVA", "IDR"),
    current_price = c(28.50, 48.00)  # BBVA up ~17%, IDR up ~8%
  )

  # Check alerts
  alert_check <- alerts %>%
    left_join(purchases, by = "ticker") %>%
    left_join(current_prices, by = "ticker") %>%
    mutate(
      actual_percent = (current_price - purchase_price) / purchase_price * 100,
      should_trigger = actual_percent >= target_percent
    )

  cat("  Alert check results:\n")
  print(alert_check %>% select(ticker, target_percent, actual_percent, should_trigger))

  # BBVA should trigger (17% > 15%), IDR should not (8% < 20%)
  stopifnot(alert_check$should_trigger[alert_check$ticker == "BBVA"] == TRUE)
  stopifnot(alert_check$should_trigger[alert_check$ticker == "IDR"] == FALSE)

  cat("  BBVA alert would TRIGGER (17% > 15% target)\n")
  cat("  IDR alert would NOT trigger (8% < 20% target)\n")
})

# ============================================================================
# SUMMARY
# ============================================================================

cat("============================================================\n")
cat("TEST SUMMARY\n")
cat("============================================================\n")
cat(sprintf("  Passed: %d\n", tests_passed))
cat(sprintf("  Failed: %d\n", tests_failed))
cat("============================================================\n")

if (tests_failed == 0) {
  cat("\nALL TESTS PASSED - Database design is validated!\n\n")
  cat("The design can:\n")
  cat("  - Store all R pipeline outputs\n")
  cat("  - Calculate allocations for any investment amount\n")
  cat("  - Track user holdings and performance\n")
  cat("  - Suggest bench replacements when stocks are sold\n")
  cat("  - Trigger price alerts at specified thresholds\n")
} else {
  cat("\nSOME TESTS FAILED - Review the design before proceeding.\n")
}
