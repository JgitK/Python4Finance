# ============================================================================
# MODULE 5: PORTFOLIO OPTIMIZATION & EFFICIENT FRONTIER
# ============================================================================
# Calculates optimal portfolio weights using Modern Portfolio Theory
# Optimizes each strategy using its own selected stocks
#
# Inputs: Strategy-specific portfolios from Module 3
# Outputs: Optimal weights per strategy, efficient frontier per strategy
#
# Author: Portfolio Optimization System
# Date: 2026-02-07

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("quadprog", quietly = TRUE)) install.packages("quadprog")
if (!require("ggplot2", quietly = TRUE)) install.packages("ggplot2")
library(quadprog)
library(ggplot2)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 5: STRATEGY-SPECIFIC PORTFOLIO OPTIMIZATION ===\n\n")

# Optimization parameters
NUM_PORTFOLIOS <- 10000       # Number of random portfolios per strategy
RISK_FREE_RATE <- 0.045       # 4.5% annual (10-year Treasury as of 2026)
OPTIMIZATION_PERIOD <- 252    # Trading days for return calculation (1 year)

# Investment parameters (can be changed)
INVESTMENT_AMOUNT <- 10000    # Default: $10,000 (user can modify)

# Strategy definitions (must match Module 3)
STRATEGIES <- c("max_sharpe", "min_variance", "max_sortino", "min_cvar", "risk_parity")

# Output directories
OUTPUT_DIR <- "analysis"
PORTFOLIOS_DIR <- file.path(OUTPUT_DIR, "portfolios")
WEIGHTS_DIR <- file.path(OUTPUT_DIR, "weights")

# Create weights output directory
if (!dir.exists(WEIGHTS_DIR)) {
  dir.create(WEIGHTS_DIR, recursive = TRUE)
  cat("Created directory: analysis/weights/\n\n")
}

# Legacy output files (for backward compatibility)
WEIGHTS_FILE <- file.path(OUTPUT_DIR, "optimal_weights.csv")
WEIGHTS_RDS <- file.path(OUTPUT_DIR, "optimal_weights.rds")
ALLOCATION_FILE <- file.path(OUTPUT_DIR, "dollar_allocation.csv")
FRONTIER_FILE <- file.path(OUTPUT_DIR, "efficient_frontier.csv")
FRONTIER_RDS <- file.path(OUTPUT_DIR, "efficient_frontier.rds")

# ============================================================================
# STEP 1: LOAD STRATEGY-SPECIFIC PORTFOLIOS
# ============================================================================

cat("Step 1: Loading strategy-specific portfolios from Module 3...\n")

# Load all strategy portfolios
all_portfolios <- readRDS(file.path(OUTPUT_DIR, "all_strategy_portfolios.rds"))

# Display summary
for (strategy in names(all_portfolios)) {
  p <- all_portfolios[[strategy]]
  cat(sprintf("  %s: %d stocks - %s\n",
              strategy, nrow(p), paste(p$ticker, collapse = ", ")))
}

# Get all unique stocks across strategies for loading data
all_tickers <- unique(unlist(lapply(all_portfolios, function(p) p$ticker)))
cat(sprintf("\n  Total unique stocks across strategies: %d\n", length(all_tickers)))

# Legacy: keep default portfolio reference (max_sharpe)
portfolio <- all_portfolios[["max_sharpe"]]
tickers <- portfolio$ticker

# ============================================================================
# STEP 2: CREATE RETURNS MATRIX (FOR ALL UNIQUE STOCKS)
# ============================================================================

cat("\nStep 2: Creating returns matrix for all unique stocks...\n")

# Load stock data for ALL unique stocks across strategies
stock_data_list <- load_multiple_stocks(all_tickers)

cat(sprintf("  Successfully loaded: %d / %d stocks\n",
            length(stock_data_list), length(all_tickers)))

# Calculate returns for all stocks
returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    arrange(date) %>%
    mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted)) %>%
    select(date, daily_return) %>%
    tail(OPTIMIZATION_PERIOD + 1) %>%  # +1 for lag
    rename(!!ticker := daily_return)
})

# Join all returns
returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

cat(sprintf("  Returns matrix: %d days × %d stocks\n",
            nrow(returns_matrix), ncol(returns_matrix) - 1))

# Extract returns only (remove date column)
returns_df <- returns_matrix %>% select(-date)

# Convert to matrix
returns_mat_full <- as.matrix(returns_df)

# Remove any rows with NA
returns_mat_full <- returns_mat_full[complete.cases(returns_mat_full), ]

cat(sprintf("  Clean returns matrix: %d days × %d stocks\n",
            nrow(returns_mat_full), ncol(returns_mat_full)))

# Helper function to extract returns matrix for a specific strategy
get_strategy_returns <- function(strategy_portfolio, full_returns) {
  strategy_tickers <- strategy_portfolio$ticker
  available_tickers <- intersect(strategy_tickers, colnames(full_returns))
  full_returns[, available_tickers, drop = FALSE]
}

# ============================================================================
# STEP 3: HELPER FUNCTIONS FOR OPTIMIZATION
# ============================================================================

cat("\nStep 3: Setting up optimization functions...\n")

# Function to calculate portfolio statistics (Sharpe, Sortino, CVaR)
calc_portfolio_stats <- function(weights, mean_returns, cov_matrix, rf_rate,
                                  returns_mat = NULL, cvar_alpha = 0.05) {
  port_return <- sum(weights * mean_returns)
  port_variance <- t(weights) %*% cov_matrix %*% weights
  port_sd <- sqrt(port_variance)
  sharpe_ratio <- (port_return - rf_rate) / port_sd

  # Initialize advanced metrics
  sortino_ratio <- NA
  downside_dev <- NA
  cvar <- NA
  var_95 <- NA

  if (!is.null(returns_mat)) {
    # Calculate portfolio daily returns
    port_daily_returns <- as.numeric(returns_mat %*% weights)

    # --- SORTINO RATIO ---
    daily_rf <- rf_rate / 252
    downside_returns <- port_daily_returns - daily_rf
    downside_returns <- pmin(downside_returns, 0)
    downside_dev <- sqrt(mean(downside_returns^2)) * sqrt(252)

    if (downside_dev > 0) {
      sortino_ratio <- (port_return - rf_rate) / downside_dev
    }

    # --- CVaR (Conditional Value at Risk / Expected Shortfall) ---
    sorted_returns <- sort(port_daily_returns)
    cutoff_idx <- floor(length(sorted_returns) * cvar_alpha)
    if (cutoff_idx > 0) {
      var_95 <- sorted_returns[cutoff_idx]
      cvar <- mean(sorted_returns[1:cutoff_idx])
      cvar <- cvar * sqrt(252)
    }
  }

  # Calculate risk contribution per asset
  marginal_contrib <- as.numeric(cov_matrix %*% weights)
  risk_contrib <- weights * marginal_contrib / as.numeric(port_variance)

  return(list(
    return = as.numeric(port_return),
    risk = as.numeric(port_sd),
    sharpe = as.numeric(sharpe_ratio),
    sortino = as.numeric(sortino_ratio),
    downside_dev = as.numeric(downside_dev),
    cvar = as.numeric(cvar),
    var_95 = as.numeric(var_95),
    risk_contrib = risk_contrib
  ))
}

# Function to calculate Risk Parity portfolio (equal risk contribution)
calc_risk_parity_weights <- function(cov_matrix, tol = 1e-8, max_iter = 1000) {
  n <- ncol(cov_matrix)
  weights <- rep(1/n, n)

  for (iter in 1:max_iter) {
    port_var <- as.numeric(t(weights) %*% cov_matrix %*% weights)
    marginal_contrib <- as.numeric(cov_matrix %*% weights)
    risk_contrib <- weights * marginal_contrib / port_var
    target_contrib <- rep(1/n, n)

    new_weights <- weights * (target_contrib / risk_contrib)^0.5
    new_weights <- new_weights / sum(new_weights)

    if (max(abs(new_weights - weights)) < tol) break
    weights <- new_weights
  }

  return(weights)
}

# Function to find optimal weights based on strategy objective
find_optimal_portfolio <- function(portfolios_df, weights_mat, strategy) {
  valid_idx <- switch(strategy,
    "max_sharpe" = which.max(portfolios_df$sharpe),
    "min_variance" = which.min(portfolios_df$risk),
    "max_sortino" = {
      valid <- which(!is.na(portfolios_df$sortino) & is.finite(portfolios_df$sortino))
      if (length(valid) > 0) valid[which.max(portfolios_df$sortino[valid])] else which.max(portfolios_df$sharpe)
    },
    "min_cvar" = {
      valid <- which(!is.na(portfolios_df$cvar) & is.finite(portfolios_df$cvar))
      if (length(valid) > 0) valid[which.max(portfolios_df$cvar[valid])] else which.min(portfolios_df$risk)
    },
    which.max(portfolios_df$sharpe)  # Default
  )

  list(
    portfolio = portfolios_df[valid_idx, ],
    weights = weights_mat[valid_idx, ]
  )
}

# ============================================================================
# NEW: LEDOIT-WOLF SHRINKAGE ESTIMATOR
# ============================================================================

# Implements Ledoit & Wolf (2004) covariance shrinkage toward scaled identity
# Reduces estimation error in sample covariance when observations < assets^2
ledoit_wolf_shrinkage <- function(returns_mat) {
  n <- nrow(returns_mat)
  p <- ncol(returns_mat)

  # Sample covariance (annualized)
  sample_cov <- cov(returns_mat) * 252

  # Shrinkage target: scaled identity matrix (average variance)
  mu <- sum(diag(sample_cov)) / p
  target <- diag(mu, p)

  # Compute optimal shrinkage intensity using Ledoit-Wolf formula
  X <- scale(returns_mat, scale = FALSE)
  sum_sq <- 0
  for (i in 1:n) {
    xi <- X[i, , drop=FALSE]
    sum_sq <- sum_sq + sum((t(xi) %*% xi - sample_cov/252)^2)
  }

  delta <- sum_sq / (n^2)
  gamma <- sum((sample_cov - target)^2)

  # Shrinkage intensity (bounded [0,1])
  shrinkage_intensity <- min(max(delta / gamma, 0), 1)

  # Shrunk covariance matrix
  shrunk_cov <- (1 - shrinkage_intensity) * sample_cov + shrinkage_intensity * target

  cat(sprintf("    Ledoit-Wolf shrinkage intensity: %.3f\n", shrinkage_intensity))
  cat(sprintf("    (0 = use sample cov, 1 = use scaled identity)\n"))

  return(list(cov = shrunk_cov, intensity = shrinkage_intensity, sample_cov = sample_cov))
}

# ============================================================================
# NEW: QUADRATIC PROGRAMMING OPTIMIZATION
# ============================================================================

# Solves for optimal weights using quadratic programming (exact solution)
# Enforces weight constraints: min_weight <= w_i <= max_weight
optimize_portfolio_qp <- function(mean_returns, cov_matrix, strategy,
                                    min_weight = 0.02, max_weight = 0.25) {
  n <- length(mean_returns)

  # Quadprog format: minimize (-d'b + 0.5*b'Db) subject to A'b >= b0
  # For min variance: d=0, minimize b'Db (quadratic form)
  # For max return/Sharpe: d = mean_returns

  Dmat <- 2 * cov_matrix  # Must be positive definite

  # Add small ridge to ensure positive definiteness
  Dmat <- Dmat + diag(1e-8, n)

  # Constraints matrix (transposed for quadprog):
  # 1. sum(w) = 1 (equality constraint)
  # 2. w_i >= min_weight for all i
  # 3. -w_i >= -max_weight for all i (equivalent to w_i <= max_weight)

  Amat <- cbind(
    rep(1, n),           # sum(w) = 1
    diag(n),             # w >= min_weight
    -diag(n)             # -w >= -max_weight (i.e. w <= max_weight)
  )

  bvec <- c(1, rep(min_weight, n), rep(-max_weight, n))
  meq <- 1  # First constraint is equality

  # Objective function
  if (strategy == "min_variance") {
    dvec <- rep(0, n)  # Minimize variance only
  } else {
    # For return-focused strategies, maximize return subject to constraints
    dvec <- mean_returns
  }

  result <- tryCatch({
    solve.QP(Dmat, dvec, Amat, bvec, meq = meq)
  }, error = function(e) {
    cat(sprintf("    QP solver failed: %s\n", e$message))
    cat("    Falling back to constrained random weights\n")
    NULL
  })

  if (!is.null(result)) {
    weights <- result$solution
    # Ensure constraints (numerical precision)
    weights <- pmax(weights, min_weight)
    weights <- pmin(weights, max_weight)
    weights <- weights / sum(weights)  # Renormalize
    return(weights)
  }

  # Fallback: equal weights within constraints
  weights <- rep(1/n, n)
  weights <- pmax(weights, min_weight)
  weights <- pmin(weights, max_weight)
  weights <- weights / sum(weights)
  return(weights)
}

# ============================================================================
# NEW: RESAMPLED EFFICIENT FRONTIER
# ============================================================================

# Bootstrap averaging to reduce overfitting
# Runs optimization on 500 resampled datasets, averages the weights
resample_efficient_frontier <- function(returns_mat, mean_returns, cov_matrix,
                                         strategy, n_resamples = 500,
                                         min_weight = 0.02, max_weight = 0.25) {
  n_obs <- nrow(returns_mat)
  n_assets <- ncol(returns_mat)
  all_weights <- matrix(0, nrow = n_resamples, ncol = n_assets)

  cat(sprintf("    Resampling %d bootstrap iterations...\n", n_resamples))

  for (b in 1:n_resamples) {
    # Bootstrap: resample returns with replacement
    boot_idx <- sample(1:n_obs, n_obs, replace = TRUE)
    boot_returns <- returns_mat[boot_idx, ]

    # Recalculate moments from bootstrap sample
    boot_mean <- colMeans(boot_returns) * 252
    boot_lw <- ledoit_wolf_shrinkage(boot_returns)
    boot_cov <- boot_lw$cov

    # Optimize on bootstrap sample
    w <- optimize_portfolio_qp(boot_mean, boot_cov, strategy, min_weight, max_weight)

    if (!is.null(w) && all(is.finite(w))) {
      all_weights[b, ] <- w
    } else {
      all_weights[b, ] <- rep(1/n_assets, n_assets)  # Fallback to equal
    }

    if (b %% 100 == 0) {
      cat(sprintf("      Progress: %d/%d\n", b, n_resamples))
    }
  }

  # Average weights across all bootstrap samples
  avg_weights <- colMeans(all_weights)
  avg_weights <- pmax(avg_weights, min_weight)
  avg_weights <- pmin(avg_weights, max_weight)
  avg_weights <- avg_weights / sum(avg_weights)  # Renormalize

  cat(sprintf("    Resampling complete. Averaged %d portfolios.\n", n_resamples))

  return(list(weights = avg_weights, all_weights = all_weights))
}

# ============================================================================
# STEP 4: OPTIMIZE EACH STRATEGY WITH ITS OWN STOCKS
# ============================================================================

cat("\nStep 4: Optimizing each strategy with strategy-specific stocks...\n")

# Store results for each strategy
strategy_results <- list()
all_strategy_weights <- list()

for (strategy in STRATEGIES) {
  cat(sprintf("\n  === OPTIMIZING: %s ===\n", toupper(strategy)))

  # Get this strategy's portfolio and returns
  strategy_portfolio <- all_portfolios[[strategy]]
  strategy_tickers <- strategy_portfolio$ticker
  returns_mat <- get_strategy_returns(strategy_portfolio, returns_mat_full)

  cat(sprintf("    Stocks: %s\n", paste(strategy_tickers, collapse = ", ")))

  # Calculate mean returns (sample)
  mean_returns <- colMeans(returns_mat, na.rm = TRUE) * 252

  # Apply Ledoit-Wolf shrinkage to covariance matrix
  cat(sprintf("    Applying Ledoit-Wolf covariance shrinkage...\n"))
  lw_result <- ledoit_wolf_shrinkage(returns_mat)
  cov_matrix <- lw_result$cov

  num_assets <- length(strategy_tickers)

  # NEW: Use resampled efficient frontier instead of Monte Carlo
  cat(sprintf("    Optimizing via resampled efficient frontier...\n"))
  MIN_WEIGHT <- 0.02  # 2% minimum position
  MAX_WEIGHT <- 0.25  # 25% maximum position

  resampled <- resample_efficient_frontier(
    returns_mat,
    mean_returns,
    cov_matrix,
    strategy,
    n_resamples = 500,
    min_weight = MIN_WEIGHT,
    max_weight = MAX_WEIGHT
  )

  optimal_weights_resampled <- resampled$weights
  names(optimal_weights_resampled) <- strategy_tickers

  # Calculate stats for resampled optimal
  optimal_stats <- calc_portfolio_stats(
    optimal_weights_resampled,
    mean_returns,
    cov_matrix,
    RISK_FREE_RATE,
    returns_mat = returns_mat
  )

  # STILL generate Monte Carlo frontier for VISUALIZATION ONLY
  cat(sprintf("    Generating Monte Carlo frontier for visualization...\n"))
  set.seed(123 + which(STRATEGIES == strategy))

  frontier_portfolios <- data.frame(
    portfolio = integer(),
    return = numeric(),
    risk = numeric(),
    sharpe = numeric(),
    sortino = numeric(),
    cvar = numeric()
  )

  frontier_weights <- matrix(nrow = NUM_PORTFOLIOS, ncol = num_assets)
  colnames(frontier_weights) <- strategy_tickers

  for (i in 1:NUM_PORTFOLIOS) {
    # Random weights WITHOUT constraints (for frontier visualization)
    weights <- runif(num_assets)
    weights <- weights / sum(weights)

    stats <- calc_portfolio_stats(weights, mean_returns, cov_matrix, RISK_FREE_RATE,
                                   returns_mat = returns_mat)

    frontier_portfolios <- rbind(frontier_portfolios, data.frame(
      portfolio = i,
      return = stats$return,
      risk = stats$risk,
      sharpe = stats$sharpe,
      sortino = stats$sortino,
      cvar = stats$cvar
    ))

    frontier_weights[i, ] <- weights

    if (i %% 2500 == 0) {
      cat(sprintf("      Frontier visualization: %s / %s\n",
                  format(i, big.mark = ","), format(NUM_PORTFOLIOS, big.mark = ",")))
    }
  }

  # Use resampled weights as optimal (NOT Monte Carlo)
  optimal <- list(
    portfolio = data.frame(
      return = optimal_stats$return,
      risk = optimal_stats$risk,
      sharpe = optimal_stats$sharpe,
      sortino = optimal_stats$sortino,
      cvar = optimal_stats$cvar
    ),
    weights = optimal_weights_resampled
  )

  # Also calculate equal weight and risk parity for comparison
  equal_weights <- rep(1/num_assets, num_assets)
  names(equal_weights) <- strategy_tickers
  equal_stats <- calc_portfolio_stats(equal_weights, mean_returns, cov_matrix,
                                       RISK_FREE_RATE, returns_mat = returns_mat)

  risk_parity_weights <- calc_risk_parity_weights(cov_matrix)
  names(risk_parity_weights) <- strategy_tickers
  risk_parity_stats <- calc_portfolio_stats(risk_parity_weights, mean_returns, cov_matrix,
                                             RISK_FREE_RATE, returns_mat = returns_mat)

  # Display results for this strategy
  cat(sprintf("    Optimal Portfolio:\n"))
  cat(sprintf("      Return: %.2f%% | Risk: %.2f%% | Sharpe: %.3f\n",
              100 * optimal$portfolio$return,
              100 * optimal$portfolio$risk,
              optimal$portfolio$sharpe))

  if (!is.na(optimal$portfolio$sortino)) {
    cat(sprintf("      Sortino: %.3f | CVaR: %.2f%%\n",
                optimal$portfolio$sortino,
                100 * optimal$portfolio$cvar))
  }

  # Store results
  strategy_results[[strategy]] <- list(
    portfolio = strategy_portfolio,
    tickers = strategy_tickers,
    optimal_portfolio = optimal$portfolio,
    optimal_weights = optimal$weights,
    equal_weights = equal_weights,
    equal_stats = equal_stats,
    risk_parity_weights = risk_parity_weights,
    risk_parity_stats = risk_parity_stats,
    mean_returns = mean_returns,
    cov_matrix = cov_matrix,
    frontier = frontier_portfolios,
    frontier_weights = frontier_weights
  )

  # Save strategy-specific frontier
  saveRDS(list(
    portfolios = frontier_portfolios,
    weights = frontier_weights,
    tickers = strategy_tickers,
    optimal = optimal
  ), file.path(WEIGHTS_DIR, paste0(strategy, "_frontier.rds")))
}

cat("\n  Optimization complete for all strategies.\n")

# ============================================================================
# STEP 5: DISPLAY STRATEGY COMPARISON
# ============================================================================

cat("\nStep 5: Strategy comparison summary...\n")

cat("\n  === STRATEGY-SPECIFIC PORTFOLIOS ===\n")
cat("  Each strategy uses DIFFERENT stocks optimized for its objective:\n\n")

# Create comparison dataframe
comparison_df <- data.frame(
  Strategy = character(),
  Stocks = character(),
  Return = numeric(),
  Risk = numeric(),
  Sharpe = numeric(),
  Sortino = numeric(),
  stringsAsFactors = FALSE
)

for (strategy in STRATEGIES) {
  res <- strategy_results[[strategy]]
  comparison_df <- rbind(comparison_df, data.frame(
    Strategy = strategy,
    Stocks = paste(res$tickers, collapse = ", "),
    Return = res$optimal_portfolio$return,
    Risk = res$optimal_portfolio$risk,
    Sharpe = res$optimal_portfolio$sharpe,
    Sortino = ifelse(is.na(res$optimal_portfolio$sortino), NA, res$optimal_portfolio$sortino),
    stringsAsFactors = FALSE
  ))
}

# Display comparison (without stocks column for readability)
cat("  Optimal Portfolio Metrics by Strategy:\n")
comparison_display <- comparison_df %>%
  select(-Stocks) %>%
  mutate(
    Return = sprintf("%.1f%%", 100 * Return),
    Risk = sprintf("%.1f%%", 100 * Risk),
    Sharpe = sprintf("%.2f", Sharpe),
    Sortino = ifelse(is.na(Sortino), "N/A", sprintf("%.2f", Sortino))
  )
print(comparison_display, row.names = FALSE)

# Show stock differences
cat("\n  === STOCK DIFFERENCES BY STRATEGY ===\n")
for (strategy in STRATEGIES) {
  res <- strategy_results[[strategy]]
  cat(sprintf("  %s (%d stocks):\n    %s\n\n",
              toupper(strategy), length(res$tickers),
              paste(res$tickers, collapse = ", ")))
}

# ============================================================================
# STEP 6: SAVE OPTIMAL WEIGHTS (PER STRATEGY)
# ============================================================================

cat("\nStep 6: Saving optimal weights...\n")

# Save individual strategy weights
for (strategy in STRATEGIES) {
  res <- strategy_results[[strategy]]

  # Create weights dataframe for this strategy
  strategy_weights <- data.frame(
    ticker = res$tickers,
    optimal_weight = as.numeric(res$optimal_weights),
    risk_parity_weight = as.numeric(res$risk_parity_weights),
    equal_weight = as.numeric(res$equal_weights),
    stringsAsFactors = FALSE
  )

  # Add stock info
  strategy_weights <- strategy_weights %>%
    left_join(res$portfolio %>% select(ticker, sector, cumulative_return_1y, sharpe_ratio,
                                        sortino_ratio, annual_variance, cvar, current_price),
              by = "ticker") %>%
    arrange(desc(optimal_weight))

  # Save per-strategy weights
  write.csv(strategy_weights, file.path(WEIGHTS_DIR, paste0(strategy, "_weights.csv")), row.names = FALSE)
  saveRDS(strategy_weights, file.path(WEIGHTS_DIR, paste0(strategy, "_weights.rds")))

  cat(sprintf("  Saved: %s_weights.csv (%d stocks)\n", strategy, nrow(strategy_weights)))
}

# Create combined weights file for webapp (one row per strategy-stock combination)
combined_weights <- bind_rows(lapply(STRATEGIES, function(strategy) {
  res <- strategy_results[[strategy]]
  data.frame(
    strategy = strategy,
    ticker = res$tickers,
    weight = as.numeric(res$optimal_weights),
    sector = res$portfolio$sector,
    sharpe_ratio = res$portfolio$sharpe_ratio,
    sortino_ratio = res$portfolio$sortino_ratio,
    current_price = res$portfolio$current_price,
    stringsAsFactors = FALSE
  )
}))

# Add equal_weight strategy (uses max_sharpe stocks with equal weights)
max_sharpe_res <- strategy_results[["max_sharpe"]]
combined_weights <- rbind(combined_weights, data.frame(
  strategy = "equal_weight",
  ticker = max_sharpe_res$tickers,
  weight = as.numeric(max_sharpe_res$equal_weights),
  sector = max_sharpe_res$portfolio$sector,
  sharpe_ratio = max_sharpe_res$portfolio$sharpe_ratio,
  sortino_ratio = max_sharpe_res$portfolio$sortino_ratio,
  current_price = max_sharpe_res$portfolio$current_price,
  stringsAsFactors = FALSE
))

write.csv(combined_weights, file.path(OUTPUT_DIR, "all_strategy_weights.csv"), row.names = FALSE)
saveRDS(combined_weights, file.path(OUTPUT_DIR, "all_strategy_weights.rds"))
cat(sprintf("  Saved: all_strategy_weights.csv (combined, %d rows)\n", nrow(combined_weights)))

# Legacy: Create backward-compatible optimal_weights.csv (max_sharpe only)
legacy_weights <- data.frame(
  ticker = max_sharpe_res$tickers,
  max_sharpe_weight = as.numeric(max_sharpe_res$optimal_weights),
  min_variance_weight = as.numeric(strategy_results[["min_variance"]]$optimal_weights[match(max_sharpe_res$tickers, strategy_results[["min_variance"]]$tickers)]),
  max_sortino_weight = as.numeric(strategy_results[["max_sortino"]]$optimal_weights[match(max_sharpe_res$tickers, strategy_results[["max_sortino"]]$tickers)]),
  min_cvar_weight = as.numeric(strategy_results[["min_cvar"]]$optimal_weights[match(max_sharpe_res$tickers, strategy_results[["min_cvar"]]$tickers)]),
  risk_parity_weight = as.numeric(max_sharpe_res$risk_parity_weights),
  equal_weight = as.numeric(max_sharpe_res$equal_weights),
  stringsAsFactors = FALSE
)

# Replace NAs with 0 (stock not in that strategy)
legacy_weights[is.na(legacy_weights)] <- 0

legacy_weights <- legacy_weights %>%
  left_join(max_sharpe_res$portfolio %>% select(ticker, sector, cumulative_return_1y, sharpe_ratio),
            by = "ticker")

write.csv(legacy_weights, WEIGHTS_FILE, row.names = FALSE)
saveRDS(legacy_weights, WEIGHTS_RDS)
cat(sprintf("  Saved: optimal_weights.csv (legacy format)\n"))

# Display max_sharpe weights as example
cat("\n  === MAX SHARPE STRATEGY WEIGHTS ===\n")
weight_display <- strategy_results[["max_sharpe"]]$portfolio %>%
  select(ticker, sector) %>%
  mutate(weight = sprintf("%.1f%%", 100 * strategy_results[["max_sharpe"]]$optimal_weights))
print(weight_display, row.names = FALSE)

# ============================================================================
# STEP 7: CALCULATE DOLLAR ALLOCATIONS (PER STRATEGY)
# ============================================================================

cat("\nStep 7: Calculating dollar allocations for each strategy...\n")
cat(sprintf("  Investment amount: $%s\n", format(INVESTMENT_AMOUNT, big.mark = ",")))

# Load regime data for position sizing adjustment
POSITION_ADJ <- 1.0  # Default: full allocation
regime_file <- file.path(OUTPUT_DIR, "market_regime.rds")

if (file.exists(regime_file)) {
  regime_data <- readRDS(regime_file)
  POSITION_ADJ <- regime_data$position_size_adjustment
  cat(sprintf("  Regime: %s\n", regime_data$regime_label))
  cat(sprintf("  Position size adjustment: %.0f%% of full allocation\n", POSITION_ADJ * 100))

  if (POSITION_ADJ < 1.0) {
    cat(sprintf("  → Allocating $%s to stocks, $%s to cash\n",
                format(INVESTMENT_AMOUNT * POSITION_ADJ, big.mark = ","),
                format(INVESTMENT_AMOUNT * (1 - POSITION_ADJ), big.mark = ",")))
  }
} else {
  cat("  No regime data found. Using 100% allocation.\n")
}

# Function to calculate allocations for a strategy (with regime adjustment)
calculate_strategy_allocation <- function(strategy_result, investment, position_adj = 1.0) {
  weights <- strategy_result$optimal_weights
  names(weights) <- strategy_result$tickers
  prices <- strategy_result$portfolio$current_price
  names(prices) <- strategy_result$tickers

  # Apply regime position sizing
  adjusted_investment <- investment * position_adj

  allocation <- data.frame(
    ticker = strategy_result$tickers,
    weight = as.numeric(weights),
    dollar_amount = as.numeric(weights) * adjusted_investment,  # Regime-adjusted
    current_price = prices,
    stringsAsFactors = FALSE
  ) %>%
    mutate(
      shares = floor(dollar_amount / current_price),
      actual_invested = shares * current_price,
      remaining = dollar_amount - actual_invested
    )

  return(allocation)
}

# Calculate and save allocation for each strategy (with regime position sizing)
all_allocations <- list()
for (strategy in STRATEGIES) {
  res <- strategy_results[[strategy]]
  alloc <- calculate_strategy_allocation(res, INVESTMENT_AMOUNT, POSITION_ADJ)
  all_allocations[[strategy]] <- alloc

  # Save per-strategy allocation
  write.csv(alloc, file.path(WEIGHTS_DIR, paste0(strategy, "_allocation.csv")), row.names = FALSE)
}

# Display max_sharpe allocation as example
cat("\n  === DOLLAR ALLOCATION (Max Sharpe Strategy) ===\n")
max_sharpe_allocation <- all_allocations[["max_sharpe"]]
print(max_sharpe_allocation %>%
        select(ticker, weight, dollar_amount, current_price, shares, actual_invested) %>%
        mutate(
          weight_pct = sprintf("%.1f%%", 100 * weight),
          dollar_amount = sprintf("$%.2f", dollar_amount),
          current_price = sprintf("$%.2f", current_price),
          actual_invested = sprintf("$%.2f", actual_invested)
        ) %>%
        select(-weight),
      row.names = FALSE)

# Summary for max_sharpe
total_invested <- sum(max_sharpe_allocation$actual_invested)
adjusted_total <- INVESTMENT_AMOUNT * POSITION_ADJ
cash_remaining <- adjusted_total - total_invested
regime_cash_reserve <- INVESTMENT_AMOUNT * (1 - POSITION_ADJ)

cat(sprintf("\n  Total allocated to stocks: $%.2f\n", total_invested))
cat(sprintf("  Cash from rounding: $%.2f\n", cash_remaining))
if (regime_cash_reserve > 0) {
  cat(sprintf("  Regime cash reserve (%.0f%%): $%.2f\n",
              (1 - POSITION_ADJ) * 100, regime_cash_reserve))
  cat(sprintf("  Total cash: $%.2f\n", cash_remaining + regime_cash_reserve))
}
cat(sprintf("  Investment efficiency: %.2f%%\n", 100 * total_invested / adjusted_total))

# Save legacy allocation file
write.csv(max_sharpe_allocation, ALLOCATION_FILE, row.names = FALSE)
cat(sprintf("  Saved allocation files for all strategies in: %s\n", WEIGHTS_DIR))

# ============================================================================
# STEP 8: PLOT EFFICIENT FRONTIERS
# ============================================================================

cat("\nStep 8: Creating efficient frontier visualizations...\n")

# Create a combined frontier plot using max_sharpe frontier as base
max_sharpe_frontier <- strategy_results[["max_sharpe"]]$frontier

# Get optimal points from all strategies
optimal_points <- data.frame(
  Portfolio = c("Max Sharpe", "Min Variance", "Max Sortino", "Min CVaR", "Risk Parity"),
  risk = sapply(STRATEGIES, function(s) strategy_results[[s]]$optimal_portfolio$risk),
  return = sapply(STRATEGIES, function(s) strategy_results[[s]]$optimal_portfolio$return),
  stringsAsFactors = FALSE
)

# Add equal weight from max_sharpe strategy
optimal_points <- rbind(optimal_points, data.frame(
  Portfolio = "Equal Weight",
  risk = strategy_results[["max_sharpe"]]$equal_stats$risk,
  return = strategy_results[["max_sharpe"]]$equal_stats$return,
  stringsAsFactors = FALSE
))

# Create plot using max_sharpe frontier as background
frontier_plot <- ggplot(max_sharpe_frontier, aes(x = risk, y = return)) +
  geom_point(aes(color = sharpe), alpha = 0.5, size = 0.8) +
  scale_color_gradient(low = "red", high = "green", name = "Sharpe\nRatio") +

  # Add all optimal portfolios
  geom_point(data = optimal_points,
             aes(x = risk, y = return),
             size = 5, shape = 17,
             color = c("darkgreen", "blue", "purple", "orange", "cyan", "gray40")) +

  # Labels
  geom_text(data = optimal_points,
            aes(x = risk, y = return, label = Portfolio),
            hjust = -0.1, vjust = -0.5, size = 3,
            color = c("darkgreen", "blue", "purple", "orange", "cyan", "gray40")) +

  # Formatting
  labs(
    title = "Efficient Frontier - Strategy-Specific Portfolios",
    subtitle = sprintf("5 strategies with different stock selections | %s simulated portfolios each",
                       format(NUM_PORTFOLIOS, big.mark = ",")),
    x = "Risk (Annual Standard Deviation)",
    y = "Expected Return (Annual)"
  ) +
  scale_x_continuous(labels = scales::percent) +
  scale_y_continuous(labels = scales::percent) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "right"
  )

# Save plot
ggsave(file.path(OUTPUT_DIR, "efficient_frontier.pdf"),
       frontier_plot, width = 12, height = 8)
ggsave(file.path(OUTPUT_DIR, "efficient_frontier.png"),
       frontier_plot, width = 12, height = 8, dpi = 300)

cat("  Saved plots:\n")
cat(sprintf("    - %s\n", file.path(OUTPUT_DIR, "efficient_frontier.pdf")))
cat(sprintf("    - %s\n", file.path(OUTPUT_DIR, "efficient_frontier.png")))

# Save frontier data (use max_sharpe for webapp backward compatibility)
write.csv(max_sharpe_frontier, FRONTIER_FILE, row.names = FALSE)
saveRDS(list(
  portfolios = max_sharpe_frontier,
  weights = strategy_results[["max_sharpe"]]$frontier_weights,
  tickers = strategy_results[["max_sharpe"]]$tickers,
  all_strategies = strategy_results
), FRONTIER_RDS)

cat(sprintf("  Saved frontier data: %s\n", FRONTIER_FILE))

# ============================================================================
# STEP 9: GENERATE SUMMARY REPORT
# ============================================================================

cat("\nStep 9: Creating summary report...\n")

# Extract key values for report
max_sharpe_res <- strategy_results[["max_sharpe"]]
min_var_res <- strategy_results[["min_variance"]]
max_sharpe_portfolio <- max_sharpe_res$optimal_portfolio
min_var_portfolio <- min_var_res$optimal_portfolio
equal_stats <- max_sharpe_res$equal_stats

summary_report <- sprintf("
=== MODULE 5: STRATEGY-SPECIFIC PORTFOLIO OPTIMIZATION ===
Generated: %s

OPTIMIZATION PARAMETERS:
- Number of portfolios simulated: %s per strategy
- Risk-free rate: %.2f%% (10-year Treasury)
- Optimization period: %d trading days (~1 year)
- Investment amount: $%s
- Strategies: %s

NEW: STRATEGY-SPECIFIC STOCK SELECTION
Each strategy now selects its own optimal stocks (different stocks per strategy)

STRATEGY COMPARISON:
%s

MAX SHARPE PORTFOLIO (Example):
- Stocks: %s
- Expected Return: %.2f%%
- Expected Risk: %.2f%%
- Sharpe Ratio: %.3f

MIN VARIANCE PORTFOLIO:
- Stocks: %s
- Expected Return: %.2f%%
- Expected Risk: %.2f%%
- Sharpe Ratio: %.3f

DOLLAR ALLOCATION (Max Sharpe, for $%s investment):
%s

ALLOCATION SUMMARY:
- Total invested: $%.2f
- Cash remaining: $%.2f
- Investment efficiency: %.1f%%

FILES GENERATED:
Per-Strategy:
- analysis/weights/<strategy>_weights.csv
- analysis/weights/<strategy>_allocation.csv
- analysis/weights/<strategy>_frontier.rds

Combined:
- analysis/all_strategy_weights.csv (all strategies in one file)
- analysis/optimal_weights.csv (legacy format)
- analysis/efficient_frontier.csv
- analysis/efficient_frontier.png

INTERPRETATION:
- Each strategy uses stocks best suited for its objective
- Max Sharpe: High return per unit total risk
- Min Variance: Lowest volatility stocks
- Max Sortino: Best downside protection
- Min CVaR: Protection against tail risk (worst days)
- Risk Parity: Equal risk contribution from each stock

NEXT STEPS:
- Run Module 6 for backtesting validation
- Use webapp to compare strategies and allocations
- Consider strategy based on your risk tolerance
",
Sys.time(),
format(NUM_PORTFOLIOS, big.mark = ","),
100 * RISK_FREE_RATE,
OPTIMIZATION_PERIOD,
format(INVESTMENT_AMOUNT, big.mark = ","),
paste(STRATEGIES, collapse = ", "),
paste(capture.output(print(comparison_display, row.names = FALSE)), collapse = "\n"),
paste(max_sharpe_res$tickers, collapse = ", "),
100 * max_sharpe_portfolio$return,
100 * max_sharpe_portfolio$risk,
max_sharpe_portfolio$sharpe,
paste(min_var_res$tickers, collapse = ", "),
100 * min_var_portfolio$return,
100 * min_var_portfolio$risk,
min_var_portfolio$sharpe,
format(INVESTMENT_AMOUNT, big.mark = ","),
paste(capture.output(print(
  max_sharpe_allocation %>%
    select(ticker, shares, actual_invested) %>%
    mutate(invested = sprintf("$%.2f", actual_invested)) %>%
    select(ticker, shares, invested),
  row.names = FALSE
)), collapse = "\n"),
total_invested,
cash_remaining,
100 * total_invested / INVESTMENT_AMOUNT
)

# Save summary
summary_file <- file.path(OUTPUT_DIR, "module_5_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 5 COMPLETE ===\n\n")

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

cat("=== STRATEGY-SPECIFIC INVESTMENT CALCULATOR ===\n")
cat("To calculate allocation for a specific strategy:\n\n")
cat("# Example: $25,000 in max_sortino strategy\n")
cat("strategy <- 'max_sortino'\n")
cat("investment <- 25000\n")
cat("weights <- readRDS(paste0('analysis/weights/', strategy, '_weights.rds'))\n")
cat("allocation <- weights %>%\n")
cat("  mutate(\n")
cat("    dollar_amount = optimal_weight * investment,\n")
cat("    shares = floor(dollar_amount / current_price),\n")
cat("    actual_invested = shares * current_price\n")
cat("  )\n")
cat("print(allocation %>% select(ticker, shares, actual_invested))\n\n")

cat("=== COMPARE ALL STRATEGIES ===\n")
cat("all_weights <- read.csv('analysis/all_strategy_weights.csv')\n")
cat("table(all_weights$strategy)\n\n")
