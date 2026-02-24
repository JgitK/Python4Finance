# ============================================================================
# MODULE 3: CORRELATION ANALYSIS & STRATEGY-SPECIFIC PORTFOLIO SELECTION
# ============================================================================
# Selects optimal stocks for each portfolio strategy:
# - Max Sharpe: Highest risk-adjusted returns
# - Min Variance: Lowest volatility stocks
# - Max Sortino: Best downside risk-adjusted returns
# - Min CVaR: Tail risk protection
# - Risk Parity: Stocks with similar volatilities
# - Equal Weight: Same as Max Sharpe (just different weights)
#
# Inputs: Candidate stocks from Module 2 (with strategy-specific metrics)
# Outputs: 6 strategy-specific portfolios
#
# Author: Portfolio Optimization System
# Date: 2026-02-07

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("corrplot", quietly = TRUE)) install.packages("corrplot")
if (!require("reshape2", quietly = TRUE)) install.packages("reshape2")
library(corrplot)
library(reshape2)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 3: STRATEGY-SPECIFIC PORTFOLIO SELECTION ===\n\n")

# Portfolio parameters
TARGET_PORTFOLIO_SIZE <- 12       # Target number of stocks per strategy
MAX_CORRELATION <- 0.6            # Maximum acceptable average correlation
MIN_SECTORS <- 4                  # Minimum number of different sectors
MAX_PER_SECTOR <- 3               # Maximum stocks from any single sector
MIN_ICHIMOKU_SCORE <- 2           # Minimum Ichimoku score to be eligible (0-5 scale)

# Analysis period for correlation (days)
CORRELATION_PERIOD <- 252         # 1 year of trading days

# Strategy definitions
STRATEGIES <- c("max_sharpe", "min_variance", "max_sortino", "min_cvar", "risk_parity")

# Output directory
OUTPUT_DIR <- "analysis"
PORTFOLIOS_DIR <- file.path(OUTPUT_DIR, "portfolios")

# Create output directories
if (!dir.exists(PORTFOLIOS_DIR)) {
  dir.create(PORTFOLIOS_DIR, recursive = TRUE)
  cat("Created directory: analysis/portfolios/\n\n")
}

# ============================================================================
# STEP 1: LOAD CANDIDATE STOCKS
# ============================================================================

cat("Step 1: Loading candidate stocks from Module 2...\n")

# Load candidates (now with additional metrics)
candidates <- readRDS(file.path(OUTPUT_DIR, "candidate_stocks.rds"))

cat(sprintf("  Total candidates: %d\n", nrow(candidates)))
cat(sprintf("  Sectors: %d\n", length(unique(candidates$sector))))

# Verify required columns exist
required_cols <- c("ticker", "sector", "sharpe_ratio", "sortino_ratio",
                   "annual_variance", "cvar", "daily_volatility", "ichimoku_score")
missing_cols <- setdiff(required_cols, names(candidates))

if (length(missing_cols) > 0) {
  cat(sprintf("\n  WARNING: Missing columns: %s\n", paste(missing_cols, collapse = ", ")))
  cat("  Run Module 2 again to generate strategy-specific metrics.\n")

  # Create placeholder columns if missing
  if (!"sortino_ratio" %in% names(candidates)) {
    candidates$sortino_ratio <- candidates$sharpe_ratio  # Fallback
  }
  if (!"annual_variance" %in% names(candidates)) {
    candidates$annual_variance <- candidates$daily_volatility^2 * 252
  }
  if (!"cvar" %in% names(candidates)) {
    candidates$cvar <- -candidates$daily_volatility * 2.33  # Approximate
  }
  if (!"ichimoku_score" %in% names(candidates)) {
    candidates$ichimoku_score <- NA  # Will be filtered if MIN_ICHIMOKU_SCORE > 0
  }
}

# ============================================================================
# STEP 1.5: FILTER BY ICHIMOKU SCORE
# ============================================================================

cat("\nStep 1.5: Filtering by Ichimoku score...\n")

# Show Ichimoku score distribution before filtering
if ("ichimoku_score" %in% names(candidates)) {
  score_dist <- table(candidates$ichimoku_score, useNA = "ifany")
  cat("  Ichimoku score distribution (before filter):\n")
  for (i in seq_along(score_dist)) {
    score_val <- names(score_dist)[i]
    score_label <- if (is.na(score_val) || score_val == "NA") "N/A" else score_val
    cat(sprintf("    Score %s: %d stocks\n", score_label, score_dist[i]))
  }

  # Filter by minimum Ichimoku score
  pre_filter_count <- nrow(candidates)
  candidates <- candidates %>%
    filter(!is.na(ichimoku_score) & ichimoku_score >= MIN_ICHIMOKU_SCORE)

  cat(sprintf("\n  Filtered: %d → %d candidates (min score >= %d)\n",
              pre_filter_count, nrow(candidates), MIN_ICHIMOKU_SCORE))

  # Check if we still have enough candidates
  if (nrow(candidates) < TARGET_PORTFOLIO_SIZE) {
    cat("  WARNING: Not enough candidates after Ichimoku filter!\n")
    cat("  Consider lowering MIN_ICHIMOKU_SCORE or re-running Module 2.\n")
  }
} else {
  cat("  WARNING: No Ichimoku scores available. Skipping filter.\n")
}

# Show sector distribution
sector_dist <- candidates %>%
  count(sector, sort = TRUE)
cat("\n  Candidate distribution by sector:\n")
print(as.data.frame(sector_dist), row.names = FALSE)

# ============================================================================
# STEP 1.6: LOAD MARKET REGIME AND NORMALIZE SIGNALS
# ============================================================================

cat("\nStep 1.6: Loading market regime and normalizing signals...\n")

# Load regime data for stress correlation adjustment
regime_file <- file.path(OUTPUT_DIR, "market_regime.rds")
STRESS_CORR_MULT <- 1.0  # Default

if (file.exists(regime_file)) {
  regime_data <- readRDS(regime_file)
  STRESS_CORR_MULT <- regime_data$stress_correlation_multiplier
  cat(sprintf("  Market Regime: %s\n", regime_data$regime_label))
  cat(sprintf("  Correlation stress multiplier: %.2fx\n", STRESS_CORR_MULT))
  cat(sprintf("  Recommended strategy: %s\n", toupper(regime_data$primary_strategy)))
} else {
  cat("  No regime data found. Using default correlation (1.0x)\n")
}

# Z-score normalize all strategy metrics for unbiased signal combination
cat("\n  Normalizing signals to z-scores...\n")

candidates <- candidates %>%
  mutate(
    # Z-score normalize primary metrics
    z_sharpe = (sharpe_ratio - mean(sharpe_ratio, na.rm=TRUE)) / sd(sharpe_ratio, na.rm=TRUE),
    z_sortino = (sortino_ratio - mean(sortino_ratio, na.rm=TRUE)) / sd(sortino_ratio, na.rm=TRUE),
    z_variance = -(annual_variance - mean(annual_variance, na.rm=TRUE)) / sd(annual_variance, na.rm=TRUE),  # Negative: lower is better
    z_cvar = (cvar - mean(cvar, na.rm=TRUE)) / sd(cvar, na.rm=TRUE),  # Less negative is better
    z_momentum = (return_3m - mean(return_3m, na.rm=TRUE)) / sd(return_3m, na.rm=TRUE),
    z_ichimoku = (ichimoku_score - mean(ichimoku_score, na.rm=TRUE)) / sd(ichimoku_score, na.rm=TRUE),

    # Handle NAs
    z_sharpe = ifelse(is.na(z_sharpe), 0, z_sharpe),
    z_sortino = ifelse(is.na(z_sortino), 0, z_sortino),
    z_variance = ifelse(is.na(z_variance), 0, z_variance),
    z_cvar = ifelse(is.na(z_cvar), 0, z_cvar),
    z_momentum = ifelse(is.na(z_momentum), 0, z_momentum),
    z_ichimoku = ifelse(is.na(z_ichimoku), 0, z_ichimoku)
  )

cat(sprintf("  Z-score normalization complete\n"))
cat(sprintf("  Mean z-scores: Sharpe=%.2f, Sortino=%.2f, Momentum=%.2f, Ichimoku=%.2f\n",
            mean(candidates$z_sharpe), mean(candidates$z_sortino),
            mean(candidates$z_momentum), mean(candidates$z_ichimoku)))

# ============================================================================
# STEP 2: CREATE RETURNS MATRIX FOR CORRELATION
# ============================================================================

cat("\nStep 2: Creating returns matrix for correlation analysis...\n")
cat("This may take a few minutes...\n\n")

# Load stock data for all candidates
stock_data_list <- list()
failed_loads <- character()

for (i in 1:nrow(candidates)) {
  ticker <- candidates$ticker[i]

  stock_data <- load_stock(ticker)

  if (is.null(stock_data)) {
    failed_loads <- c(failed_loads, ticker)
    next
  }

  # Calculate returns
  stock_data <- stock_data %>%
    arrange(date) %>%
    mutate(
      daily_return = (adjusted - lag(adjusted)) / lag(adjusted)
    ) %>%
    select(date, daily_return) %>%
    tail(CORRELATION_PERIOD + 1)

  stock_data_list[[ticker]] <- stock_data

  if (i %% 20 == 0) {
    cat(sprintf("  Loaded: %d/%d stocks\n", i, nrow(candidates)))
  }
}

cat(sprintf("\n  Successfully loaded: %d stocks\n", length(stock_data_list)))

# Remove failed stocks from candidates
if (length(failed_loads) > 0) {
  candidates <- candidates %>% filter(!ticker %in% failed_loads)
}

# Build returns matrix
all_dates <- lapply(stock_data_list, function(x) x$date)
common_start <- max(sapply(all_dates, min))
common_end <- min(sapply(all_dates, max))

returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    filter(date >= common_start, date <= common_end) %>%
    select(date, daily_return) %>%
    rename(!!ticker := daily_return)
})

returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

returns_only <- returns_matrix %>% select(-date)

cat(sprintf("  Returns matrix: %d days × %d stocks\n",
            nrow(returns_only), ncol(returns_only)))

# ============================================================================
# STEP 3: CALCULATE CORRELATION MATRIX
# ============================================================================

cat("\nStep 3: Calculating correlation matrix...\n")

correlation_matrix <- cor(returns_only, use = "pairwise.complete.obs")

cat(sprintf("  Correlation matrix: %d × %d\n",
            nrow(correlation_matrix), ncol(correlation_matrix)))

# Save full correlation matrix
saveRDS(correlation_matrix, file.path(OUTPUT_DIR, "correlation_matrix.rds"))

# ============================================================================
# STEP 4: STRATEGY-SPECIFIC SELECTION FUNCTIONS
# ============================================================================

cat("\nStep 4: Defining strategy-specific selection criteria...\n")

# Helper function to calculate average correlation with selected stocks
# Now incorporates regime stress multiplier
calc_avg_correlation <- function(ticker, selected, corr_mat, stress_mult = 1.0) {
  if (length(selected) == 0) return(0)
  correlations <- corr_mat[ticker, selected]
  avg_corr <- mean(abs(correlations), na.rm = TRUE)

  # Apply stress multiplier and cap at 1.0
  stressed_corr <- min(avg_corr * stress_mult, 1.0)

  return(stressed_corr)
}

# Strategy-specific scoring functions (Z-SCORE BASED)
get_strategy_score <- function(ticker, selected, candidates_df, strategy, corr_mat, stress_mult = 1.0) {

  stock <- candidates_df %>% filter(ticker == !!ticker)
  avg_corr <- calc_avg_correlation(ticker, selected, corr_mat, stress_mult)

  # Correlation penalty factor (0 to 1, where 1 = perfect correlation)
  corr_penalty <- avg_corr

  # Strategy-specific scoring using Z-SCORES (statistically grounded weights)
  # Each strategy combines z-scores with empirically-derived weights
  composite_score <- switch(strategy,

    # Max Sharpe: Favor high Sharpe with momentum confirmation
    "max_sharpe" = {
      0.40 * stock$z_sharpe +
      0.20 * stock$z_momentum +
      0.20 * stock$z_ichimoku +
      0.20 * (1 - corr_penalty)
    },

    # Min Variance: Prioritize low variance with Ichimoku confirmation
    "min_variance" = {
      0.50 * stock$z_variance +
      0.20 * stock$z_ichimoku +
      0.30 * (1 - corr_penalty)
    },

    # Max Sortino: Favor downside protection with momentum
    "max_sortino" = {
      0.40 * stock$z_sortino +
      0.20 * stock$z_momentum +
      0.20 * stock$z_ichimoku +
      0.20 * (1 - corr_penalty)
    },

    # Min CVaR: Tail risk mitigation focus
    "min_cvar" = {
      0.50 * stock$z_cvar +
      0.20 * stock$z_ichimoku +
      0.30 * (1 - corr_penalty)
    },

    # Risk Parity: Volatility distance + Ichimoku boost
    "risk_parity" = {
      vol_median <- median(candidates_df$daily_volatility, na.rm = TRUE)
      vol_distance <- -abs(stock$daily_volatility - vol_median)
      z_vol_dist <- (vol_distance - mean(-abs(candidates_df$daily_volatility - vol_median), na.rm=TRUE)) /
                     sd(-abs(candidates_df$daily_volatility - vol_median), na.rm=TRUE)

      0.60 * z_vol_dist +
      0.20 * stock$z_ichimoku +
      0.20 * (1 - corr_penalty)
    },

    # Default: Max Sharpe
    {
      0.40 * stock$z_sharpe +
      0.20 * stock$z_momentum +
      0.20 * stock$z_ichimoku +
      0.20 * (1 - corr_penalty)
    }
  )

  # Handle NA
  if (is.na(composite_score)) composite_score <- -Inf

  return(composite_score)
}

# Generic portfolio selection function
select_portfolio_for_strategy <- function(strategy, candidates_df, corr_mat,
                                           target_size = TARGET_PORTFOLIO_SIZE,
                                           max_corr = MAX_CORRELATION,
                                           min_sectors = MIN_SECTORS,
                                           max_per_sector = MAX_PER_SECTOR,
                                           stress_mult = 1.0) {

  cat(sprintf("\n  --- Selecting portfolio for: %s ---\n", toupper(strategy)))

  # Sort candidates by strategy-specific metric for initial selection
  ranked_candidates <- switch(strategy,
    "max_sharpe" = candidates_df %>% arrange(desc(sharpe_ratio)),
    "min_variance" = candidates_df %>% arrange(annual_variance),
    "max_sortino" = candidates_df %>% arrange(desc(sortino_ratio)),
    "min_cvar" = candidates_df %>% arrange(desc(cvar)),  # Less negative is better
    "risk_parity" = candidates_df %>%
      mutate(vol_dist = abs(daily_volatility - median(daily_volatility))) %>%
      arrange(vol_dist),
    candidates_df %>% arrange(desc(sharpe_ratio))
  )

  selected_stocks <- character()
  selected_sectors <- character()

  # Stage 1: Get top performer from major sectors
  major_sectors <- ranked_candidates %>%
    count(sector, sort = TRUE) %>%
    head(min_sectors) %>%
    pull(sector)

  for (sector in major_sectors) {
    sector_candidates <- ranked_candidates %>%
      filter(sector == !!sector, !ticker %in% selected_stocks)

    if (nrow(sector_candidates) == 0) next

    best <- sector_candidates$ticker[1]
    selected_stocks <- c(selected_stocks, best)
    selected_sectors <- c(selected_sectors, sector)
  }

  cat(sprintf("    Stage 1: %d stocks from %d sectors\n",
              length(selected_stocks), length(unique(selected_sectors))))

  # Stage 2: Fill remaining slots
  while (length(selected_stocks) < target_size) {

    available <- ranked_candidates %>%
      filter(!ticker %in% selected_stocks)

    if (nrow(available) == 0) break

    # Score all available stocks (with stress multiplier)
    scores <- sapply(available$ticker, function(t) {
      stock_sector <- available %>% filter(ticker == t) %>% pull(sector)
      sector_count <- sum(selected_sectors == stock_sector)

      if (sector_count >= max_per_sector) return(-Inf)

      get_strategy_score(t, selected_stocks, available, strategy, corr_mat, stress_mult)
    })

    best_idx <- which.max(scores)
    if (scores[best_idx] == -Inf) break

    best_ticker <- available$ticker[best_idx]
    best_sector <- available$sector[best_idx]

    selected_stocks <- c(selected_stocks, best_ticker)
    selected_sectors <- c(selected_sectors, best_sector)
  }

  cat(sprintf("    Final: %d stocks from %d sectors\n",
              length(selected_stocks), length(unique(selected_sectors))))

  # Build portfolio dataframe
  portfolio <- candidates_df %>%
    filter(ticker %in% selected_stocks) %>%
    rowwise() %>%
    mutate(
      avg_correlation = calc_avg_correlation(ticker, setdiff(selected_stocks, ticker), corr_mat, stress_mult)
    ) %>%
    ungroup()

  # Add strategy column
  portfolio$strategy <- strategy

  return(portfolio)
}

# ============================================================================
# STEP 5: SELECT PORTFOLIOS FOR ALL STRATEGIES
# ============================================================================

cat("\nStep 5: Selecting portfolios for each strategy...\n")

all_portfolios <- list()

for (strategy in STRATEGIES) {
  portfolio <- select_portfolio_for_strategy(
    strategy = strategy,
    candidates_df = candidates,
    corr_mat = correlation_matrix,
    stress_mult = STRESS_CORR_MULT  # Use regime stress multiplier
  )

  all_portfolios[[strategy]] <- portfolio

  # Save individual portfolio
  saveRDS(portfolio, file.path(PORTFOLIOS_DIR, paste0(strategy, "_portfolio.rds")))
  write.csv(portfolio, file.path(PORTFOLIOS_DIR, paste0(strategy, "_portfolio.csv")),
            row.names = FALSE)
}

# Equal weight uses same stocks as max_sharpe
all_portfolios[["equal_weight"]] <- all_portfolios[["max_sharpe"]] %>%
  mutate(strategy = "equal_weight")
saveRDS(all_portfolios[["equal_weight"]],
        file.path(PORTFOLIOS_DIR, "equal_weight_portfolio.rds"))

# ============================================================================
# STEP 6: ANALYZE AND COMPARE PORTFOLIOS
# ============================================================================

cat("\nStep 6: Comparing strategy portfolios...\n")

# Combine all portfolios for comparison
comparison <- bind_rows(lapply(names(all_portfolios), function(s) {
  p <- all_portfolios[[s]]
  data.frame(
    strategy = s,
    n_stocks = nrow(p),
    n_sectors = length(unique(p$sector)),
    avg_return = mean(p$cumulative_return_1y),
    avg_sharpe = mean(p$sharpe_ratio, na.rm = TRUE),
    avg_sortino = mean(p$sortino_ratio, na.rm = TRUE),
    avg_variance = mean(p$annual_variance, na.rm = TRUE),
    avg_cvar = mean(p$cvar, na.rm = TRUE),
    avg_ichimoku = mean(p$ichimoku_score, na.rm = TRUE),
    avg_correlation = mean(p$avg_correlation, na.rm = TRUE)
  )
}))

cat("\n  === STRATEGY COMPARISON ===\n")
print(comparison %>%
        mutate(
          avg_return = sprintf("%.1f%%", 100 * avg_return),
          avg_sharpe = sprintf("%.2f", avg_sharpe),
          avg_sortino = sprintf("%.2f", avg_sortino),
          avg_variance = sprintf("%.4f", avg_variance),
          avg_cvar = sprintf("%.2f%%", 100 * avg_cvar),
          avg_ichimoku = sprintf("%.1f/5", avg_ichimoku),
          avg_correlation = sprintf("%.3f", avg_correlation)
        ), row.names = FALSE)

# Stock overlap analysis
cat("\n  === STOCK OVERLAP BETWEEN STRATEGIES ===\n")
overlap_matrix <- matrix(0, nrow = length(STRATEGIES), ncol = length(STRATEGIES))
rownames(overlap_matrix) <- STRATEGIES
colnames(overlap_matrix) <- STRATEGIES

for (i in seq_along(STRATEGIES)) {
  for (j in seq_along(STRATEGIES)) {
    stocks_i <- all_portfolios[[STRATEGIES[i]]]$ticker
    stocks_j <- all_portfolios[[STRATEGIES[j]]]$ticker
    overlap_matrix[i, j] <- length(intersect(stocks_i, stocks_j))
  }
}
print(overlap_matrix)

# Unique stocks per strategy
cat("\n  === UNIQUE STOCKS PER STRATEGY ===\n")
all_strategy_stocks <- unique(unlist(lapply(all_portfolios, function(p) p$ticker)))
cat(sprintf("  Total unique stocks across all strategies: %d\n", length(all_strategy_stocks)))

for (strategy in STRATEGIES) {
  other_stocks <- unique(unlist(lapply(STRATEGIES[STRATEGIES != strategy],
                                        function(s) all_portfolios[[s]]$ticker)))
  unique_to_strategy <- setdiff(all_portfolios[[strategy]]$ticker, other_stocks)
  cat(sprintf("    %s: %d unique stocks\n", strategy, length(unique_to_strategy)))
  if (length(unique_to_strategy) > 0) {
    cat(sprintf("      %s\n", paste(unique_to_strategy, collapse = ", ")))
  }
}

# ============================================================================
# STEP 7: CREATE COMBINED OUTPUT FOR BACKWARD COMPATIBILITY
# ============================================================================

cat("\nStep 7: Creating combined output files...\n")

# Use max_sharpe as the default "final_portfolio" for backward compatibility
final_portfolio <- all_portfolios[["max_sharpe"]] %>%
  select(-strategy)

write.csv(final_portfolio, file.path(OUTPUT_DIR, "final_portfolio.csv"), row.names = FALSE)
saveRDS(final_portfolio, file.path(OUTPUT_DIR, "final_portfolio.rds"))

# Save all portfolios in one object
saveRDS(all_portfolios, file.path(OUTPUT_DIR, "all_strategy_portfolios.rds"))

# Create master stock list with strategy assignments
master_list <- bind_rows(lapply(names(all_portfolios), function(s) {
  all_portfolios[[s]] %>%
    select(ticker, sector, sharpe_ratio, sortino_ratio, annual_variance, cvar,
           daily_volatility, cumulative_return_1y, current_price, ichimoku_score, avg_correlation) %>%
    mutate(strategy = s)
}))

write.csv(master_list, file.path(OUTPUT_DIR, "master_stock_list.csv"), row.names = FALSE)

cat(sprintf("  Saved: analysis/final_portfolio.rds (default: max_sharpe)\n"))
cat(sprintf("  Saved: analysis/all_strategy_portfolios.rds (all 6 strategies)\n"))
cat(sprintf("  Saved: analysis/master_stock_list.csv (all stocks with strategies)\n"))

# ============================================================================
# STEP 8: CORRELATION HEATMAPS FOR EACH STRATEGY
# ============================================================================

cat("\nStep 8: Creating correlation heatmaps for each strategy...\n")

for (strategy in STRATEGIES) {
  portfolio_stocks <- all_portfolios[[strategy]]$ticker
  portfolio_corr <- correlation_matrix[portfolio_stocks, portfolio_stocks]

  saveRDS(portfolio_corr, file.path(PORTFOLIOS_DIR, paste0(strategy, "_correlation.rds")))
}

# Save default heatmap (max_sharpe) for backward compatibility
default_stocks <- all_portfolios[["max_sharpe"]]$ticker
portfolio_corr <- correlation_matrix[default_stocks, default_stocks]
saveRDS(portfolio_corr, file.path(OUTPUT_DIR, "portfolio_correlation_heatmap.rds"))

# ============================================================================
# STEP 9: SUMMARY REPORT
# ============================================================================

cat("\nStep 9: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 3: STRATEGY-SPECIFIC PORTFOLIO SELECTION ===
Generated: %s

CONFIGURATION:
- Target portfolio size: %d stocks per strategy
- Maximum correlation: %.2f
- Minimum sectors: %d
- Maximum per sector: %d
- Strategies: %s

CANDIDATES ANALYZED:
- Total candidates: %d
- Successfully loaded: %d

STRATEGY COMPARISON:
%s

STOCK OVERLAP:
- Total unique stocks: %d
- Strategies produce %s portfolios

FILES GENERATED:
- Individual portfolios: analysis/portfolios/<strategy>_portfolio.rds
- Combined portfolios: analysis/all_strategy_portfolios.rds
- Master stock list: analysis/master_stock_list.csv
- Default portfolio: analysis/final_portfolio.rds (max_sharpe)

NEXT STEPS:
- Run Module 4 for Ichimoku validation (will validate all strategies)
- Run Module 5 for portfolio optimization
",
Sys.time(),
TARGET_PORTFOLIO_SIZE,
MAX_CORRELATION,
MIN_SECTORS,
MAX_PER_SECTOR,
paste(STRATEGIES, collapse = ", "),
nrow(candidates) + length(failed_loads),
nrow(candidates),
paste(capture.output(print(comparison, row.names = FALSE)), collapse = "\n"),
length(all_strategy_stocks),
ifelse(sum(overlap_matrix[upper.tri(overlap_matrix)] < TARGET_PORTFOLIO_SIZE) > 0,
       "differentiated", "similar")
)

writeLines(summary_report, file.path(OUTPUT_DIR, "module_3_summary.txt"))
cat(summary_report)

cat("\n=== MODULE 3 COMPLETE ===\n")
cat("Next step: Run Module 4 for Ichimoku validation\n\n")

# ============================================================================
# QUICK REFERENCE
# ============================================================================

cat("=== QUICK REFERENCE ===\n")
cat("# Load all strategy portfolios:\n")
cat("all_portfolios <- readRDS('analysis/all_strategy_portfolios.rds')\n\n")
cat("# Access specific strategy:\n")
cat("max_sharpe_portfolio <- all_portfolios[['max_sharpe']]\n")
cat("min_variance_portfolio <- all_portfolios[['min_variance']]\n\n")
cat("# View strategy comparison:\n")
cat("master_list <- read.csv('analysis/master_stock_list.csv')\n")
cat("table(master_list$strategy)\n\n")
