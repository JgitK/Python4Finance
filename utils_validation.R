# ============================================================================
# VALIDATION UTILITIES - MINIMAL VERSION 1
# ============================================================================
# Purpose: Core functions to run strategy for validation
# Status: TESTING - Single strategy execution only

library(tidyverse)

# ----------------------------------------------------------------------------
# FUNCTION: Run strategy for a specific period
# ----------------------------------------------------------------------------
# This is the KEY function that wraps Modules 2-6
# Version 1: Just loads existing results (doesn't re-run modules yet)

run_strategy_for_period <- function(start_date, end_date, params = NULL) {
  cat(sprintf("\n=== Running strategy for period: %s to %s ===\n",
              start_date, end_date))

  # For now, just load the existing portfolio from Module 5
  # TODO: Later, we'll make this actually run modules 2-5 with custom dates/params

  if (!file.exists("analysis/final_portfolio.rds")) {
    stop("Error: Run Modules 1-6 first to create final_portfolio.rds")
  }

  portfolio <- readRDS("analysis/final_portfolio.rds")

  cat(sprintf("  ✓ Loaded portfolio with %d stocks\n", length(portfolio$ticker)))

  return(portfolio)
}


# ----------------------------------------------------------------------------
# FUNCTION: Backtest a portfolio for a specific period
# ----------------------------------------------------------------------------
# Version 1: Simple backtest - loads stock data and calculates returns

backtest_portfolio <- function(portfolio, start_date, end_date) {
  cat(sprintf("\n  Backtesting from %s to %s...\n", start_date, end_date))

  # Load stock data
  tickers <- portfolio$ticker
  weights <- portfolio$weight

  returns_list <- list()

  for (i in seq_along(tickers)) {
    ticker <- tickers[i]
    stock_file <- sprintf("stocks/%s.rds", ticker)

    if (!file.exists(stock_file)) {
      cat(sprintf("  ⚠ Warning: No data for %s\n", ticker))
      next
    }

    stock <- readRDS(stock_file)

    # Filter by date range
    stock <- stock %>%
      filter(date >= start_date & date <= end_date)

    if (nrow(stock) == 0) {
      cat(sprintf("  ⚠ Warning: No data in range for %s\n", ticker))
      next
    }

    # Calculate returns
    stock_returns <- stock %>%
      arrange(date) %>%
      mutate(return = (adjusted / lag(adjusted)) - 1) %>%
      filter(!is.na(return)) %>%
      select(date, return)

    returns_list[[ticker]] <- stock_returns
  }

  if (length(returns_list) == 0) {
    stop("Error: No valid stock data for backtesting")
  }

  # Combine returns into matrix
  all_dates <- sort(unique(do.call(c, lapply(returns_list, function(x) x$date))))

  returns_matrix <- matrix(0, nrow = length(all_dates), ncol = length(tickers))
  colnames(returns_matrix) <- tickers

  for (i in seq_along(tickers)) {
    ticker <- tickers[i]
    if (ticker %in% names(returns_list)) {
      stock_returns <- returns_list[[ticker]]
      idx <- match(stock_returns$date, all_dates)
      returns_matrix[idx, i] <- stock_returns$return
    }
  }

  # Calculate portfolio returns
  portfolio_returns <- returns_matrix %*% weights

  # Calculate metrics
  total_return <- prod(1 + portfolio_returns) - 1
  annual_return <- (1 + total_return)^(252 / length(portfolio_returns)) - 1
  volatility <- sd(portfolio_returns) * sqrt(252)

  sharpe_ratio <- if (volatility > 0) {
    (annual_return - 0.02) / volatility  # Assuming 2% risk-free rate
  } else {
    0
  }

  # Max drawdown
  cumulative <- cumprod(1 + portfolio_returns)
  running_max <- cummax(cumulative)
  drawdown <- (cumulative - running_max) / running_max
  max_drawdown <- min(drawdown)

  cat(sprintf("  ✓ Backtest complete\n"))
  cat(sprintf("    Total Return: %.2f%%\n", total_return * 100))
  cat(sprintf("    Sharpe Ratio: %.2f\n", sharpe_ratio))
  cat(sprintf("    Max Drawdown: %.2f%%\n", max_drawdown * 100))

  return(list(
    total_return = total_return,
    annual_return = annual_return,
    volatility = volatility,
    sharpe_ratio = sharpe_ratio,
    max_drawdown = max_drawdown,
    num_days = length(portfolio_returns),
    portfolio_returns = portfolio_returns
  ))
}


# ----------------------------------------------------------------------------
# TEST SECTION
# ----------------------------------------------------------------------------
# Run this to verify the functions work

if (FALSE) {  # Set to TRUE to run tests
  cat("\n============================================================\n")
  cat("TESTING VALIDATION UTILITIES\n")
  cat("============================================================\n")

  # Test 1: Load portfolio
  cat("\nTest 1: Loading portfolio...\n")
  portfolio <- run_strategy_for_period(
    start_date = Sys.Date() - 365,
    end_date = Sys.Date()
  )

  print(portfolio$ticker)

  # Test 2: Backtest for 6 months
  cat("\n\nTest 2: Backtesting 6 months...\n")
  backtest_result <- backtest_portfolio(
    portfolio,
    start_date = Sys.Date() - 180,
    end_date = Sys.Date()
  )

  cat("\nTest 2 Results:\n")
  print(backtest_result[c("sharpe_ratio", "total_return", "max_drawdown")])

  cat("\n✓ Tests complete!\n")
}
