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

  # Use equal weights if no weight column exists
  if ("weight" %in% names(portfolio)) {
    weights <- portfolio$weight
  } else {
    weights <- rep(1 / length(tickers), length(tickers))
    cat(sprintf("  (Using equal weights: %.2f%% each)\n", 100 / length(tickers)))
  }

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
# FUNCTION: Multi-timeframe analysis
# ----------------------------------------------------------------------------
# Tests portfolio across multiple time periods to check robustness

run_multi_timeframe_analysis <- function(portfolio, periods = NULL) {
  cat("\n============================================================\n")
  cat("MULTI-TIMEFRAME ANALYSIS\n")
  cat("============================================================\n")

  # Default periods: 3mo, 6mo, 1yr, 2yr
  if (is.null(periods)) {
    periods <- list(
      "3 months" = 90,
      "6 months" = 180,
      "1 year" = 365,
      "2 years" = 730
    )
  }

  results <- list()
  end_date <- Sys.Date()

  for (period_name in names(periods)) {
    days <- periods[[period_name]]
    start_date <- end_date - days

    cat(sprintf("\n--- %s (%s to %s) ---\n", period_name, start_date, end_date))

    tryCatch({
      result <- backtest_portfolio(portfolio, start_date, end_date)
      results[[period_name]] <- result
    }, error = function(e) {
      cat(sprintf("  ✗ Error: %s\n", e$message))
      results[[period_name]] <- NULL
    })
  }

  # Summary table
  cat("\n============================================================\n")
  cat("SUMMARY: Performance Across Timeframes\n")
  cat("============================================================\n")
  cat(sprintf("%-12s %10s %10s %10s %12s\n",
              "Period", "Return", "Sharpe", "Volatility", "Max DD"))
  cat(paste(rep("-", 58), collapse = ""), "\n")

  for (period_name in names(results)) {
    r <- results[[period_name]]
    if (!is.null(r)) {
      cat(sprintf("%-12s %9.1f%% %10.2f %9.1f%% %11.1f%%\n",
                  period_name,
                  r$total_return * 100,
                  r$sharpe_ratio,
                  r$volatility * 100,
                  r$max_drawdown * 100))
    }
  }

  # Consistency check
  cat("\n------------------------------------------------------------\n")
  cat("ROBUSTNESS CHECK\n")
  cat("------------------------------------------------------------\n")

  sharpes <- sapply(results, function(r) if (!is.null(r)) r$sharpe_ratio else NA)
  sharpes <- sharpes[!is.na(sharpes)]

  if (length(sharpes) > 1) {
    if (all(sharpes > 1)) {
      cat("✓ STRONG: Sharpe > 1.0 across all timeframes\n")
    } else if (all(sharpes > 0.5)) {
      cat("✓ GOOD: Sharpe > 0.5 across all timeframes\n")
    } else if (all(sharpes > 0)) {
      cat("⚠ MODERATE: Positive Sharpe but inconsistent\n")
    } else {
      cat("✗ WEAK: Negative Sharpe in some periods\n")
    }

    sharpe_cv <- sd(sharpes) / mean(sharpes)
    if (sharpe_cv < 0.3) {
      cat("✓ CONSISTENT: Low variation in Sharpe ratios (CV < 0.3)\n")
    } else if (sharpe_cv < 0.5) {
      cat("⚠ VARIABLE: Moderate variation in Sharpe ratios\n")
    } else {
      cat("✗ UNSTABLE: High variation in Sharpe ratios (possible look-ahead bias)\n")
    }
  }

  return(results)
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
