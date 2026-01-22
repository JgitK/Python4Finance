# ============================================================================
# WALK-FORWARD VALIDATION UTILITIES
# ============================================================================
# Purpose: True out-of-sample testing with NO look-ahead bias
#
# Key principle: At any selection date, we only know information
# that was available at that time - no future data allowed.
#
# Author: Portfolio Optimization System
# Date: 2026-01-20

library(tidyverse)
library(TTR)

source("utils_data_loader.R")

# ============================================================================
# CONFIGURATION (same as modules)
# ============================================================================

# Module 2 parameters
ANALYSIS_PERIOD <- 252
MIN_TRADING_DAYS <- 400
TOP_N_PER_SECTOR <- 10
MIN_AVG_VOLUME <- 100000
MAX_VOLATILITY <- 0.05

# Module 3 parameters
TARGET_PORTFOLIO_SIZE <- 12
CORRELATION_PERIOD <- 252
MAX_PER_SECTOR <- 3
MIN_SECTORS <- 6

# ============================================================================
# CORE FUNCTION: Load stock data with date cutoff
# ============================================================================

#' Load stock data as of a specific date (no future data)
#'
#' @param ticker Stock ticker
#' @param as_of_date The cutoff date - only data up to this date is returned
#' @return Stock data frame with only historical data
load_stock_as_of <- function(ticker, as_of_date) {

  stock_data <- load_stock(ticker)

  if (is.null(stock_data)) return(NULL)

  # Filter to only include data up to as_of_date
  stock_data <- stock_data %>%
    filter(date <= as_of_date)

  return(stock_data)
}


# ============================================================================
# FUNCTION: Calculate technical indicators (from Module 2)
# ============================================================================

calculate_technical_indicators_asof <- function(ticker, sector, as_of_date) {

  stock_data <- load_stock_as_of(ticker, as_of_date)

  if (is.null(stock_data) || nrow(stock_data) < MIN_TRADING_DAYS) {
    return(NULL)
  }

  tryCatch({
    stock_data <- stock_data %>% arrange(date)

    # Calculate returns
    stock_data <- stock_data %>%
      mutate(
        daily_return = (adjusted - lag(adjusted)) / lag(adjusted),
        log_return = log(adjusted / lag(adjusted))
      )

    # Use last ANALYSIS_PERIOD days for metrics
    recent_data <- stock_data %>% tail(ANALYSIS_PERIOD + 1)

    if (nrow(recent_data) < ANALYSIS_PERIOD) return(NULL)

    cumulative_return <- prod(1 + recent_data$daily_return, na.rm = TRUE) - 1

    # Performance metrics
    avg_volume <- mean(stock_data$volume, na.rm = TRUE)
    daily_volatility <- sd(stock_data$daily_return, na.rm = TRUE)
    sharpe_ratio <- mean(stock_data$daily_return, na.rm = TRUE) / daily_volatility * sqrt(252)

    # Momentum
    return_6m <- prod(1 + tail(stock_data$daily_return, 126), na.rm = TRUE) - 1
    return_3m <- prod(1 + tail(stock_data$daily_return, 63), na.rm = TRUE) - 1

    latest <- tail(stock_data, 1)

    return(data.frame(
      ticker = ticker,
      sector = sector,
      cumulative_return_1y = cumulative_return,
      return_6m = return_6m,
      return_3m = return_3m,
      daily_volatility = daily_volatility,
      sharpe_ratio = sharpe_ratio,
      avg_volume = avg_volume,
      current_price = latest$adjusted,
      latest_date = latest$date,
      stringsAsFactors = FALSE
    ))

  }, error = function(e) {
    return(NULL)
  })
}


# ============================================================================
# FUNCTION: Select portfolio as of a date (Modules 2-3 combined)
# ============================================================================

#' Select portfolio using only data available at selection_date
#'
#' @param selection_date The "as of" date - only use data up to this point
#' @param verbose Print progress messages
#' @return Data frame with selected portfolio stocks
select_portfolio_asof <- function(selection_date, verbose = TRUE) {

  selection_date <- as.Date(selection_date)

  if (verbose) {
    cat(sprintf("\n=== SELECTING PORTFOLIO AS OF %s ===\n", selection_date))
    cat("(Using ONLY data available at that time - no future information)\n\n")
  }

  # Load metadata (this is static info about tickers/sectors)
  download_log <- read.csv("metadata/download_log.csv", stringsAsFactors = FALSE)

  valid_stocks <- download_log %>%
    filter(success == TRUE, rows >= MIN_TRADING_DAYS) %>%
    select(ticker, sector)

  if (verbose) cat(sprintf("Step 1: Analyzing %d stocks...\n", nrow(valid_stocks)))

  # -------------------------------------------------------------------------
  # STEP 1: Calculate technical indicators (Module 2 logic)
  # -------------------------------------------------------------------------

  all_metrics <- list()

  for (i in 1:nrow(valid_stocks)) {
    ticker <- valid_stocks$ticker[i]
    sector <- valid_stocks$sector[i]

    metrics <- calculate_technical_indicators_asof(ticker, sector, selection_date)

    if (!is.null(metrics)) {
      all_metrics[[ticker]] <- metrics
    }

    if (verbose && i %% 100 == 0) {
      cat(sprintf("  Progress: %d/%d stocks\n", i, nrow(valid_stocks)))
    }
  }

  performance_data <- bind_rows(all_metrics)

  if (verbose) cat(sprintf("  Analyzed: %d stocks with sufficient data\n", nrow(performance_data)))

  # -------------------------------------------------------------------------
  # STEP 2: Apply screening filters (Module 2 logic)
  # -------------------------------------------------------------------------

  if (verbose) cat("\nStep 2: Applying screening filters...\n")

  screened <- performance_data %>%
    filter(avg_volume >= MIN_AVG_VOLUME) %>%
    filter(daily_volatility <= MAX_VOLATILITY) %>%
    filter(return_3m > 0)  # Positive momentum

  if (verbose) cat(sprintf("  After filters: %d stocks\n", nrow(screened)))

  if (nrow(screened) < TARGET_PORTFOLIO_SIZE) {
    warning("Not enough stocks pass filters")
    return(NULL)
  }

  # -------------------------------------------------------------------------
  # STEP 3: Rank by sector and select top N (Module 2 logic)
  # -------------------------------------------------------------------------

  candidates <- screened %>%
    group_by(sector) %>%
    mutate(
      sector_rank = rank(-cumulative_return_1y, ties.method = "first"),
      sector_size = n()
    ) %>%
    ungroup() %>%
    filter(sector_rank <= TOP_N_PER_SECTOR)

  if (verbose) cat(sprintf("  Candidates after sector ranking: %d stocks\n", nrow(candidates)))

  # -------------------------------------------------------------------------
  # STEP 4: Build correlation matrix (Module 3 logic)
  # -------------------------------------------------------------------------

  if (verbose) cat("\nStep 3: Calculating correlations...\n")

  # Load returns for correlation calculation
  returns_list <- list()

  for (ticker in candidates$ticker) {
    stock_data <- load_stock_as_of(ticker, selection_date)

    if (is.null(stock_data)) next

    stock_returns <- stock_data %>%
      arrange(date) %>%
      mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted)) %>%
      select(date, daily_return) %>%
      tail(CORRELATION_PERIOD + 1)

    returns_list[[ticker]] <- stock_returns
  }

  # Find common date range
  all_dates <- lapply(returns_list, function(x) x$date)
  common_start <- max(sapply(all_dates, min))
  common_end <- min(sapply(all_dates, max))

  # Build returns matrix
  returns_data <- lapply(names(returns_list), function(ticker) {
    returns_list[[ticker]] %>%
      filter(date >= common_start, date <= common_end) %>%
      select(date, daily_return) %>%
      rename(!!ticker := daily_return)
  })

  returns_matrix <- reduce(returns_data, full_join, by = "date") %>%
    arrange(date) %>%
    select(-date)

  # Calculate correlation
  correlation_matrix <- cor(returns_matrix, use = "pairwise.complete.obs")

  # -------------------------------------------------------------------------
  # STEP 5: Greedy selection with sector constraints (Module 3 logic)
  # -------------------------------------------------------------------------

  if (verbose) cat("\nStep 4: Selecting final portfolio...\n")

  selected_stocks <- character()
  selected_sectors <- character()

  # Helper function
  calc_avg_corr <- function(ticker, selected) {
    if (length(selected) == 0) return(0)
    correlations <- correlation_matrix[ticker, selected]
    mean(abs(correlations), na.rm = TRUE)
  }

  # Stage 1: Top from each major sector
  major_sectors <- candidates %>%
    count(sector, sort = TRUE) %>%
    head(MIN_SECTORS) %>%
    pull(sector)

  for (sector in major_sectors) {
    sector_cands <- candidates %>%
      filter(sector == !!sector, !ticker %in% selected_stocks)

    if (nrow(sector_cands) == 0) next

    best <- sector_cands %>%
      arrange(desc(sharpe_ratio)) %>%
      head(1) %>%
      pull(ticker)

    selected_stocks <- c(selected_stocks, best)
    selected_sectors <- c(selected_sectors, sector)
  }

  # Stage 2: Fill remaining with best scores
  while (length(selected_stocks) < TARGET_PORTFOLIO_SIZE) {
    available <- candidates %>%
      filter(!ticker %in% selected_stocks)

    if (nrow(available) == 0) break

    scores <- sapply(available$ticker, function(t) {
      stock_sector <- available %>% filter(ticker == t) %>% pull(sector)
      sector_count <- sum(selected_sectors == stock_sector)

      if (sector_count >= MAX_PER_SECTOR) return(-Inf)

      avg_corr <- calc_avg_corr(t, selected_stocks)
      sharpe <- available %>% filter(ticker == t) %>% pull(sharpe_ratio)

      sharpe * (1 - avg_corr)
    })

    best_idx <- which.max(scores)
    if (scores[best_idx] == -Inf) break

    best_ticker <- available$ticker[best_idx]
    best_sector <- available$sector[best_idx]

    selected_stocks <- c(selected_stocks, best_ticker)
    selected_sectors <- c(selected_sectors, best_sector)
  }

  # Build final portfolio
  final_portfolio <- candidates %>%
    filter(ticker %in% selected_stocks)

  if (verbose) {
    cat(sprintf("\n  Selected %d stocks from %d sectors\n",
                nrow(final_portfolio), length(unique(final_portfolio$sector))))
    cat("  Tickers:", paste(final_portfolio$ticker, collapse = ", "), "\n")
  }

  return(final_portfolio)
}


# ============================================================================
# FUNCTION: Backtest portfolio forward from selection date
# ============================================================================

#' Backtest a portfolio from selection_date forward
#'
#' @param portfolio Portfolio data frame with ticker column
#' @param start_date Start of backtest (typically day after selection)
#' @param end_date End of backtest
#' @param weights Optional weights vector (default: equal weight)
#' @return List with backtest results
backtest_forward <- function(portfolio, start_date, end_date, weights = NULL) {

  start_date <- as.Date(start_date)
  end_date <- as.Date(end_date)

  tickers <- portfolio$ticker
  n_stocks <- length(tickers)

  if (is.null(weights)) {
    weights <- rep(1 / n_stocks, n_stocks)
  }

  cat(sprintf("\n  Backtesting %d stocks from %s to %s...\n",
              n_stocks, start_date, end_date))

  # Load FULL stock data (we need future data for backtesting)
  returns_list <- list()

  for (ticker in tickers) {
    stock_data <- load_stock(ticker)  # Full data, not truncated

    if (is.null(stock_data)) next

    stock_returns <- stock_data %>%
      filter(date >= start_date, date <= end_date) %>%
      arrange(date) %>%
      mutate(return = (adjusted / lag(adjusted)) - 1) %>%
      filter(!is.na(return)) %>%
      select(date, return)

    if (nrow(stock_returns) > 0) {
      returns_list[[ticker]] <- stock_returns
    }
  }

  if (length(returns_list) == 0) {
    return(list(error = "No valid data for backtest period"))
  }

  # Combine returns
  all_dates <- sort(unique(do.call(c, lapply(returns_list, function(x) x$date))))

  returns_matrix <- matrix(0, nrow = length(all_dates), ncol = n_stocks)
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
  n_days <- length(portfolio_returns)
  annual_return <- (1 + total_return)^(252 / n_days) - 1
  volatility <- sd(portfolio_returns) * sqrt(252)
  sharpe_ratio <- if (volatility > 0) (annual_return - 0.02) / volatility else 0

  # Max drawdown
  cumulative <- cumprod(1 + portfolio_returns)
  running_max <- cummax(cumulative)
  drawdown <- (cumulative - running_max) / running_max
  max_drawdown <- min(drawdown)

  cat(sprintf("  Total Return: %.2f%%\n", total_return * 100))
  cat(sprintf("  Sharpe Ratio: %.2f\n", sharpe_ratio))
  cat(sprintf("  Max Drawdown: %.2f%%\n", max_drawdown * 100))

  return(list(
    total_return = total_return,
    annual_return = annual_return,
    volatility = volatility,
    sharpe_ratio = sharpe_ratio,
    max_drawdown = max_drawdown,
    num_days = n_days,
    start_date = start_date,
    end_date = end_date
  ))
}


# ============================================================================
# MAIN FUNCTION: Walk-forward validation
# ============================================================================

#' Run complete walk-forward validation
#'
#' @param selection_date Date to select portfolio (using only prior data)
#' @param backtest_end End date for backtesting (default: today)
#' @return List with portfolio and backtest results
run_walkforward_test <- function(selection_date, backtest_end = Sys.Date()) {

  selection_date <- as.Date(selection_date)
  backtest_end <- as.Date(backtest_end)

  cat("============================================================\n")
  cat("WALK-FORWARD VALIDATION\n")
  cat("============================================================\n")
  cat(sprintf("Selection Date: %s (portfolio selected using data up to this date)\n", selection_date))
  cat(sprintf("Backtest Period: %s to %s (out-of-sample testing)\n",
              selection_date + 1, backtest_end))
  cat("============================================================\n")

  # Step 1: Select portfolio using only historical data
  portfolio <- select_portfolio_asof(selection_date, verbose = TRUE)

  if (is.null(portfolio) || nrow(portfolio) == 0) {
    return(list(error = "Failed to select portfolio"))
  }

  # Step 2: Backtest forward (out-of-sample)
  cat("\n============================================================\n")
  cat("OUT-OF-SAMPLE BACKTEST\n")
  cat("============================================================\n")

  backtest <- backtest_forward(
    portfolio,
    start_date = selection_date + 1,  # Day after selection
    end_date = backtest_end
  )

  # Summary
  cat("\n============================================================\n")
  cat("WALK-FORWARD RESULTS\n")
  cat("============================================================\n")
  cat(sprintf("Portfolio selected on: %s\n", selection_date))
  cat(sprintf("Stocks: %s\n", paste(portfolio$ticker, collapse = ", ")))
  cat(sprintf("Out-of-sample period: %d trading days\n", backtest$num_days))
  cat(sprintf("Total Return: %.2f%%\n", backtest$total_return * 100))
  cat(sprintf("Annualized Return: %.2f%%\n", backtest$annual_return * 100))
  cat(sprintf("Sharpe Ratio: %.2f\n", backtest$sharpe_ratio))
  cat(sprintf("Max Drawdown: %.2f%%\n", backtest$max_drawdown * 100))

  return(list(
    selection_date = selection_date,
    portfolio = portfolio,
    backtest = backtest
  ))
}


# ============================================================================
# FUNCTION: Multi-period walk-forward analysis
# ============================================================================

#' Run walk-forward tests for multiple selection dates
#'
#' @param selection_dates Vector of dates to test
#' @param holding_period Days to hold after selection (default: 180)
#' @return Data frame with results for each period
run_multi_period_walkforward <- function(selection_dates, holding_period = 180) {

  cat("============================================================\n")
  cat("MULTI-PERIOD WALK-FORWARD ANALYSIS\n")
  cat("============================================================\n")
  cat(sprintf("Testing %d selection dates\n", length(selection_dates)))
  cat(sprintf("Holding period: %d days each\n\n", holding_period))

  results <- list()

  for (i in seq_along(selection_dates)) {
    sel_date <- as.Date(selection_dates[i])
    end_date <- sel_date + holding_period

    cat(sprintf("\n--- Period %d: Select on %s, hold until %s ---\n",
                i, sel_date, end_date))

    tryCatch({
      result <- run_walkforward_test(sel_date, end_date)

      results[[i]] <- data.frame(
        period = i,
        selection_date = sel_date,
        end_date = end_date,
        n_stocks = nrow(result$portfolio),
        total_return = result$backtest$total_return,
        sharpe_ratio = result$backtest$sharpe_ratio,
        max_drawdown = result$backtest$max_drawdown,
        num_days = result$backtest$num_days
      )

    }, error = function(e) {
      cat(sprintf("  Error: %s\n", e$message))
      results[[i]] <- NULL
    })
  }

  # Combine results
  results_df <- bind_rows(results)

  # Summary
  cat("\n============================================================\n")
  cat("MULTI-PERIOD SUMMARY\n")
  cat("============================================================\n")

  cat("\nResults by period:\n")
  print(results_df %>%
          mutate(
            return_pct = sprintf("%.1f%%", total_return * 100),
            sharpe = sprintf("%.2f", sharpe_ratio),
            drawdown = sprintf("%.1f%%", max_drawdown * 100)
          ) %>%
          select(selection_date, return_pct, sharpe, drawdown))

  cat("\nAggregate statistics:\n")
  cat(sprintf("  Average Return: %.2f%%\n", mean(results_df$total_return) * 100))
  cat(sprintf("  Average Sharpe: %.2f\n", mean(results_df$sharpe_ratio)))
  cat(sprintf("  Sharpe Std Dev: %.2f\n", sd(results_df$sharpe_ratio)))
  cat(sprintf("  Win Rate: %.1f%% (positive return periods)\n",
              100 * mean(results_df$total_return > 0)))

  return(results_df)
}


cat("\n Walk-forward validation utilities loaded\n")
cat("Use run_walkforward_test(selection_date) to test\n\n")
