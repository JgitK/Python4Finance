# Portfolio Optimization Functions
# Purpose: Markowitz Mean-Variance Portfolio Optimization

library(tidyverse)
library(xts)
library(PerformanceAnalytics)

#' Calculate portfolio return given weights and mean returns
#'
#' @param weights Vector of portfolio weights
#' @param mean_returns Vector of mean returns
#' @return Portfolio return
portfolio_return <- function(weights, mean_returns) {
  return(sum(weights * mean_returns))
}

#' Calculate portfolio volatility given weights and covariance matrix
#'
#' @param weights Vector of portfolio weights
#' @param cov_matrix Covariance matrix of returns
#' @return Portfolio volatility (standard deviation)
portfolio_volatility <- function(weights, cov_matrix) {
  return(sqrt(t(weights) %*% cov_matrix %*% weights))
}

#' Calculate Sharpe Ratio
#'
#' @param portfolio_return Expected portfolio return
#' @param portfolio_vol Portfolio volatility
#' @param risk_free_rate Risk-free rate
#' @return Sharpe Ratio
sharpe_ratio <- function(portfolio_return, portfolio_vol, risk_free_rate) {
  return((portfolio_return - risk_free_rate) / portfolio_vol)
}

#' Generate random portfolio weights
#'
#' @param num_stocks Number of stocks in portfolio
#' @return Vector of random weights that sum to 1
random_weights <- function(num_stocks) {
  weights <- runif(num_stocks)
  weights <- weights / sum(weights)
  return(weights)
}

#' Optimize portfolio using Monte Carlo simulation
#'
#' @param stock_data List of xts objects or merged xts object with stock data
#' @param num_portfolios Number of random portfolios to generate
#' @param risk_free_rate Risk-free rate (default 0.0125)
#' @return List containing optimization results
optimize_portfolio <- function(stock_data,
                                num_portfolios = 10000,
                                risk_free_rate = 0.0125) {

  # Get closing prices
  if (is.list(stock_data) && !is.data.frame(stock_data)) {
    # If it's a list of xts objects, extract closing prices
    prices <- get_closing_prices_from_list(stock_data)
  } else {
    # Assume it's already a merged xts object with closing prices
    prices <- stock_data
  }

  # Calculate log returns
  returns <- na.omit(ROC(prices, type = "continuous"))

  # Annualize returns (252 trading days)
  mean_returns <- colMeans(returns, na.rm = TRUE) * 252

  # Calculate covariance matrix (annualized)
  cov_matrix <- cov(returns, use = "complete.obs") * 252

  # Number of stocks
  num_stocks <- ncol(returns)
  stock_names <- colnames(returns)

  # Storage for portfolio metrics
  portfolio_returns <- numeric(num_portfolios)
  portfolio_volatilities <- numeric(num_portfolios)
  portfolio_sharpe_ratios <- numeric(num_portfolios)
  portfolio_weights_matrix <- matrix(0, nrow = num_portfolios, ncol = num_stocks)

  # Generate random portfolios
  message(sprintf("Generating %d random portfolios...", num_portfolios))

  for (i in 1:num_portfolios) {
    # Generate random weights
    weights <- random_weights(num_stocks)

    # Calculate portfolio metrics
    port_return <- portfolio_return(weights, mean_returns)
    port_vol <- portfolio_volatility(weights, cov_matrix)
    port_sharpe <- sharpe_ratio(port_return, port_vol, risk_free_rate)

    # Store results
    portfolio_returns[i] <- port_return
    portfolio_volatilities[i] <- port_vol
    portfolio_sharpe_ratios[i] <- port_sharpe
    portfolio_weights_matrix[i, ] <- weights

    # Progress update
    if (i %% 1000 == 0) {
      message(sprintf("Progress: %d/%d portfolios generated", i, num_portfolios))
    }
  }

  # Create results dataframe
  portfolios_df <- data.frame(
    Return = portfolio_returns,
    Volatility = portfolio_volatilities,
    SharpeRatio = portfolio_sharpe_ratios
  )

  # Find optimal portfolio (maximum Sharpe Ratio)
  optimal_idx <- which.max(portfolio_sharpe_ratios)

  optimal_portfolio <- data.frame(
    Return = portfolio_returns[optimal_idx],
    Volatility = portfolio_volatilities[optimal_idx],
    SharpeRatio = portfolio_sharpe_ratios[optimal_idx]
  )

  optimal_weights_vec <- portfolio_weights_matrix[optimal_idx, ]

  optimal_weights <- data.frame(
    Stock = stock_names,
    Weight = optimal_weights_vec
  ) %>%
    arrange(desc(Weight))

  # Calculate correlation matrix
  correlation_matrix <- cor(returns, use = "complete.obs")

  # Return results
  results <- list(
    portfolios = portfolios_df,
    optimal_portfolio = optimal_portfolio,
    optimal_weights = optimal_weights,
    mean_returns = mean_returns,
    cov_matrix = cov_matrix,
    correlation_matrix = correlation_matrix,
    returns = returns,
    prices = prices,
    num_portfolios = num_portfolios,
    risk_free_rate = risk_free_rate
  )

  message("\nOptimization complete!")
  message(sprintf("Optimal Sharpe Ratio: %.4f", optimal_portfolio$SharpeRatio))
  message(sprintf("Expected Return: %.2f%%", optimal_portfolio$Return * 100))
  message(sprintf("Volatility: %.2f%%", optimal_portfolio$Volatility * 100))

  return(results)
}

#' Helper function to extract closing prices from list of xts objects
#'
#' @param stock_list List of xts objects
#' @return Merged xts object with closing prices
get_closing_prices_from_list <- function(stock_list) {
  closing_prices <- lapply(names(stock_list), function(ticker) {
    data <- stock_list[[ticker]]
    close_col <- grep("Close", colnames(data), value = TRUE)

    if (length(close_col) > 0) {
      close_prices <- data[, close_col]
      colnames(close_prices) <- ticker
      return(close_prices)
    }
    return(NULL)
  })

  # Remove NULL entries
  closing_prices <- closing_prices[!sapply(closing_prices, is.null)]

  # Merge all closing prices
  merged_data <- do.call(merge, closing_prices)

  # Remove rows with NA values
  merged_data <- na.omit(merged_data)

  return(merged_data)
}

#' Calculate portfolio performance metrics
#'
#' @param weights Vector of portfolio weights
#' @param returns xts object with returns
#' @return Data frame with performance metrics
calculate_portfolio_metrics <- function(weights, returns) {
  # Calculate portfolio returns
  portfolio_returns <- Return.portfolio(returns, weights = weights)

  # Calculate metrics
  total_return <- Return.cumulative(portfolio_returns)
  annual_return <- Return.annualized(portfolio_returns)
  annual_vol <- StdDev.annualized(portfolio_returns)
  sharpe <- SharpeRatio.annualized(portfolio_returns)
  max_dd <- maxDrawdown(portfolio_returns)

  metrics <- data.frame(
    Metric = c("Total Return", "Annualized Return", "Annualized Volatility",
               "Sharpe Ratio", "Maximum Drawdown"),
    Value = c(total_return, annual_return, annual_vol, sharpe, max_dd)
  )

  return(metrics)
}

#' Calculate efficient frontier
#'
#' @param mean_returns Vector of mean returns
#' @param cov_matrix Covariance matrix
#' @param num_points Number of points on frontier
#' @return Data frame with efficient frontier points
calculate_efficient_frontier <- function(mean_returns, cov_matrix, num_points = 100) {
  num_stocks <- length(mean_returns)

  # Range of target returns
  min_return <- min(mean_returns)
  max_return <- max(mean_returns)
  target_returns <- seq(min_return, max_return, length.out = num_points)

  # Storage for results
  frontier_volatilities <- numeric(num_points)
  frontier_weights <- matrix(0, nrow = num_points, ncol = num_stocks)

  for (i in seq_along(target_returns)) {
    target <- target_returns[i]

    # Quadratic programming to minimize variance subject to target return
    # This is a simplified version - for production use, consider using
    # PortfolioAnalytics or quadprog package

    # For now, we'll use a simple grid search approach
    best_vol <- Inf
    best_weights <- rep(1/num_stocks, num_stocks)

    for (j in 1:1000) {
      weights <- random_weights(num_stocks)
      port_return <- portfolio_return(weights, mean_returns)

      if (abs(port_return - target) < 0.001) {
        port_vol <- portfolio_volatility(weights, cov_matrix)

        if (port_vol < best_vol) {
          best_vol <- port_vol
          best_weights <- weights
        }
      }
    }

    frontier_volatilities[i] <- best_vol
    frontier_weights[i, ] <- best_weights
  }

  efficient_frontier <- data.frame(
    Return = target_returns,
    Volatility = frontier_volatilities
  )

  return(efficient_frontier)
}

#' Backtest portfolio performance
#'
#' @param weights Vector of portfolio weights
#' @param prices xts object with prices
#' @param initial_investment Initial investment amount
#' @return xts object with portfolio value over time
backtest_portfolio <- function(weights, prices, initial_investment = 10000) {
  # Calculate returns
  returns <- na.omit(ROC(prices, type = "discrete"))

  # Calculate portfolio returns
  portfolio_returns <- Return.portfolio(returns, weights = weights, rebalance_on = "months")

  # Calculate portfolio value
  portfolio_value <- cumprod(1 + portfolio_returns) * initial_investment

  return(portfolio_value)
}

#' Calculate portfolio shares to purchase
#'
#' @param weights Vector of portfolio weights
#' @param stock_names Vector of stock names
#' @param prices Vector of current stock prices
#' @param total_investment Total amount to invest
#' @param force_one Force at least one share of each stock
#' @return Data frame with shares and costs
calculate_shares <- function(weights, stock_names, prices, total_investment, force_one = TRUE) {
  num_stocks <- length(stock_names)

  shares <- numeric(num_stocks)
  costs <- numeric(num_stocks)

  for (i in 1:num_stocks) {
    # Calculate amount to invest in this stock
    stock_investment <- total_investment * weights[i]

    # Calculate number of shares
    num_shares <- floor(stock_investment / prices[i])

    # Force at least one share if specified
    if (force_one && num_shares == 0) {
      num_shares <- 1
    }

    shares[i] <- num_shares
    costs[i] <- num_shares * prices[i]
  }

  # Calculate actual weights based on shares purchased
  actual_weights <- costs / sum(costs)

  results <- data.frame(
    Stock = stock_names,
    TargetWeight = weights,
    Price = prices,
    Shares = shares,
    Cost = costs,
    ActualWeight = actual_weights
  )

  results$WeightDiff <- results$ActualWeight - results$TargetWeight

  return(results)
}

#' Generate portfolio summary report
#'
#' @param optimization_results Results from optimize_portfolio function
#' @return Character string with formatted report
generate_portfolio_report <- function(optimization_results) {
  report <- paste0(
    "═══════════════════════════════════════════════════\n",
    "         PORTFOLIO OPTIMIZATION REPORT\n",
    "═══════════════════════════════════════════════════\n\n",
    "OPTIMAL PORTFOLIO STATISTICS\n",
    "───────────────────────────────────────────────────\n",
    sprintf("Expected Annual Return:  %6.2f%%\n",
            optimization_results$optimal_portfolio$Return * 100),
    sprintf("Annual Volatility:       %6.2f%%\n",
            optimization_results$optimal_portfolio$Volatility * 100),
    sprintf("Sharpe Ratio:            %6.4f\n",
            optimization_results$optimal_portfolio$SharpeRatio),
    sprintf("Risk-Free Rate:          %6.2f%%\n",
            optimization_results$risk_free_rate * 100),
    "\n\nOPTIMAL WEIGHTS\n",
    "───────────────────────────────────────────────────\n"
  )

  # Add weights
  for (i in 1:nrow(optimization_results$optimal_weights)) {
    stock <- optimization_results$optimal_weights$Stock[i]
    weight <- optimization_results$optimal_weights$Weight[i] * 100
    report <- paste0(report, sprintf("%-8s  %6.2f%%\n", stock, weight))
  }

  report <- paste0(
    report,
    "\n═══════════════════════════════════════════════════\n"
  )

  return(report)
}
