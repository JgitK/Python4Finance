# ============================================================================
# MODULE 3: CORRELATION ANALYSIS & PORTFOLIO SELECTION
# ============================================================================
# Selects least-correlated stocks from candidates for optimal diversification
# Following principles from: https://www.codingfinance.com/
#
# Inputs: Candidate stocks from Module 2
# Outputs: Final 12 stocks for portfolio optimization
#
# Author: Portfolio Optimization System
# Date: 2026-01-17

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

cat("\n=== MODULE 3: CORRELATION ANALYSIS & PORTFOLIO SELECTION ===\n\n")

# Portfolio parameters
TARGET_PORTFOLIO_SIZE <- 12       # Target number of stocks
MAX_CORRELATION <- 0.5            # Maximum acceptable average correlation
MIN_SECTORS <- 6                  # Minimum number of different sectors
MAX_PER_SECTOR <- 3               # Maximum stocks from any single sector

# Selection preferences
USE_SHARPE_WEIGHTING <- TRUE      # Weight selection by Sharpe ratio
EXCLUDE_UNKNOWN_SECTOR <- FALSE   # Whether to exclude "Unknown" sector (flagged instead)

# Analysis period for correlation (days)
CORRELATION_PERIOD <- 252         # 1 year of trading days

# Output directory
OUTPUT_DIR <- "analysis"
PORTFOLIO_FILE <- file.path(OUTPUT_DIR, "final_portfolio.csv")
PORTFOLIO_RDS <- file.path(OUTPUT_DIR, "final_portfolio.rds")
CORRELATION_FILE <- file.path(OUTPUT_DIR, "correlation_matrix.csv")
CORRELATION_RDS <- file.path(OUTPUT_DIR, "correlation_matrix.rds")

# ============================================================================
# STEP 1: LOAD CANDIDATE STOCKS
# ============================================================================

cat("Step 1: Loading candidate stocks from Module 2...\n")

# Load candidates
candidates <- readRDS(file.path(OUTPUT_DIR, "candidate_stocks.rds"))

cat(sprintf("  Total candidates: %d\n", nrow(candidates)))
cat(sprintf("  Sectors: %d\n", length(unique(candidates$sector))))

# Flag "Unknown" sector stocks
unknown_stocks <- candidates %>% filter(sector == "Unknown")
if (nrow(unknown_stocks) > 0) {
  cat(sprintf("\n  WARNING: %d stocks in 'Unknown' sector:\n", nrow(unknown_stocks)))
  print(unknown_stocks %>% select(ticker, cumulative_return_1y, sharpe_ratio))
  cat("  These will be flagged but included in analysis unless excluded.\n")
}

# Remove Unknown sector if configured
if (EXCLUDE_UNKNOWN_SECTOR) {
  candidates <- candidates %>% filter(sector != "Unknown")
  cat(sprintf("\n  Excluded Unknown sector. Remaining: %d candidates\n", nrow(candidates)))
}

# Show sector distribution
sector_dist <- candidates %>%
  count(sector, sort = TRUE)
cat("\n  Candidate distribution by sector:\n")
print(as.data.frame(sector_dist), row.names = FALSE)

# ============================================================================
# STEP 2: CREATE RETURNS MATRIX
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
    tail(CORRELATION_PERIOD + 1)  # +1 for lag

  stock_data_list[[ticker]] <- stock_data

  # Progress indicator
  if (i %% 20 == 0) {
    cat(sprintf("  Loaded: %d/%d stocks\n", i, nrow(candidates)))
  }
}

cat(sprintf("\n  Successfully loaded: %d stocks\n", length(stock_data_list)))
if (length(failed_loads) > 0) {
  cat(sprintf("  Failed to load: %d stocks\n", length(failed_loads)))

  # Remove failed stocks from candidates
  candidates <- candidates %>% filter(!ticker %in% failed_loads)
}

# Create wide-format returns matrix
cat("\n  Creating returns matrix...\n")

# Find common date range
all_dates <- lapply(stock_data_list, function(x) x$date)
common_start <- max(sapply(all_dates, min))
common_end <- min(sapply(all_dates, max))

cat(sprintf("  Common date range: %s to %s\n", common_start, common_end))

# Build returns matrix
returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    filter(date >= common_start, date <= common_end) %>%
    select(date, daily_return) %>%
    rename(!!ticker := daily_return)
})

# Join all returns
returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

# Remove date column for correlation calculation
returns_only <- returns_matrix %>% select(-date)

cat(sprintf("  Returns matrix: %d days × %d stocks\n",
            nrow(returns_only), ncol(returns_only)))

# ============================================================================
# STEP 3: CALCULATE CORRELATION MATRIX
# ============================================================================

cat("\nStep 3: Calculating correlation matrix...\n")

# Calculate Pearson correlation
correlation_matrix <- cor(returns_only, use = "pairwise.complete.obs")

cat(sprintf("  Correlation matrix: %d × %d\n",
            nrow(correlation_matrix), ncol(correlation_matrix)))

# Summary statistics
upper_tri <- correlation_matrix[upper.tri(correlation_matrix)]
cat(sprintf("  Average correlation: %.3f\n", mean(upper_tri, na.rm = TRUE)))
cat(sprintf("  Median correlation: %.3f\n", median(upper_tri, na.rm = TRUE)))
cat(sprintf("  Max correlation: %.3f\n", max(upper_tri, na.rm = TRUE)))
cat(sprintf("  Min correlation: %.3f\n", min(upper_tri, na.rm = TRUE)))

# Save correlation matrix
write.csv(correlation_matrix, CORRELATION_FILE)
saveRDS(correlation_matrix, CORRELATION_RDS)
cat(sprintf("\n  Saved correlation matrix: %s\n", CORRELATION_FILE))

# ============================================================================
# STEP 4: GREEDY SELECTION ALGORITHM WITH SECTOR CONSTRAINTS
# ============================================================================

cat("\nStep 4: Selecting portfolio using greedy algorithm...\n")
cat(sprintf("  Target: %d stocks\n", TARGET_PORTFOLIO_SIZE))
cat(sprintf("  Max correlation: %.2f\n", MAX_CORRELATION))
cat(sprintf("  Min sectors: %d\n", MIN_SECTORS))
cat(sprintf("  Max per sector: %d\n", MAX_PER_SECTOR))

# Initialize portfolio
selected_stocks <- character()
selected_sectors <- character()

# Helper function to calculate average correlation with selected stocks
calc_avg_correlation <- function(ticker, selected) {
  if (length(selected) == 0) return(0)

  correlations <- correlation_matrix[ticker, selected]
  mean(abs(correlations), na.rm = TRUE)
}

# Helper function to get selection score
get_selection_score <- function(ticker, selected, candidates_df) {

  avg_corr <- calc_avg_correlation(ticker, selected)

  # Get stock metrics
  stock_metrics <- candidates_df %>% filter(ticker == !!ticker)

  if (USE_SHARPE_WEIGHTING) {
    # Higher Sharpe = better, lower correlation = better
    # Normalize both to 0-1 scale and combine
    sharpe_score <- stock_metrics$sharpe_ratio
    corr_penalty <- avg_corr

    # Score: high Sharpe, low correlation
    score <- sharpe_score * (1 - corr_penalty)
  } else {
    # Pure correlation-based
    score <- -avg_corr
  }

  return(score)
}

# Stage 1: Select top performer from each major sector first
# This ensures sector diversity
cat("\n  Stage 1: Selecting top performer from each major sector...\n")

major_sectors <- candidates %>%
  count(sector, sort = TRUE) %>%
  head(MIN_SECTORS) %>%
  pull(sector)

for (sector in major_sectors) {

  sector_candidates <- candidates %>%
    filter(sector == !!sector, !ticker %in% selected_stocks)

  if (nrow(sector_candidates) == 0) next

  # Pick top Sharpe ratio from this sector
  best_in_sector <- sector_candidates %>%
    arrange(desc(sharpe_ratio)) %>%
    head(1) %>%
    pull(ticker)

  selected_stocks <- c(selected_stocks, best_in_sector)
  selected_sectors <- c(selected_sectors, sector)

  cat(sprintf("    Added %s from %s (Sharpe: %.2f)\n",
              best_in_sector, sector,
              sector_candidates %>% filter(ticker == best_in_sector) %>% pull(sharpe_ratio)))
}

cat(sprintf("\n  Stage 1 complete: %d stocks selected from %d sectors\n",
            length(selected_stocks), length(unique(selected_sectors))))

# Stage 2: Fill remaining slots with best available stocks
cat("\n  Stage 2: Filling remaining slots with best candidates...\n")

while (length(selected_stocks) < TARGET_PORTFOLIO_SIZE) {

  # Get candidates not yet selected
  available <- candidates %>%
    filter(!ticker %in% selected_stocks)

  if (nrow(available) == 0) {
    cat("    No more candidates available.\n")
    break
  }

  # Calculate scores for all available stocks
  scores <- sapply(available$ticker, function(t) {

    # Check sector constraint
    stock_sector <- available %>% filter(ticker == t) %>% pull(sector)
    sector_count <- sum(selected_sectors == stock_sector)

    if (sector_count >= MAX_PER_SECTOR) {
      return(-Inf)  # Exclude if sector maxed out
    }

    get_selection_score(t, selected_stocks, available)
  })

  # Select best scoring stock
  best_idx <- which.max(scores)

  if (scores[best_idx] == -Inf) {
    cat("    All remaining stocks violate sector constraints.\n")
    break
  }

  best_ticker <- available$ticker[best_idx]
  best_sector <- available$sector[best_idx]
  best_corr <- calc_avg_correlation(best_ticker, selected_stocks)

  selected_stocks <- c(selected_stocks, best_ticker)
  selected_sectors <- c(selected_sectors, best_sector)

  cat(sprintf("    [%d/%d] Added %s (%s) - Avg corr: %.3f, Score: %.3f\n",
              length(selected_stocks), TARGET_PORTFOLIO_SIZE,
              best_ticker, best_sector, best_corr, scores[best_idx]))
}

cat(sprintf("\n  Selection complete: %d stocks from %d sectors\n",
            length(selected_stocks), length(unique(selected_sectors))))

# ============================================================================
# STEP 5: ANALYZE FINAL PORTFOLIO
# ============================================================================

cat("\nStep 5: Analyzing final portfolio...\n")

# Create portfolio dataframe
final_portfolio <- candidates %>%
  filter(ticker %in% selected_stocks) %>%
  arrange(desc(sharpe_ratio))

# Add correlation metrics
final_portfolio <- final_portfolio %>%
  rowwise() %>%
  mutate(
    avg_correlation = calc_avg_correlation(ticker, setdiff(selected_stocks, ticker))
  ) %>%
  ungroup()

# Portfolio statistics
cat("\n  === FINAL PORTFOLIO ===\n")
print(final_portfolio %>%
        select(ticker, sector, cumulative_return_1y, sharpe_ratio,
               daily_volatility, avg_correlation) %>%
        mutate(
          return_pct = sprintf("%.1f%%", 100 * cumulative_return_1y),
          vol_pct = sprintf("%.2f%%", 100 * daily_volatility)
        ) %>%
        select(-cumulative_return_1y, -daily_volatility),
      n = TARGET_PORTFOLIO_SIZE)

# Sector distribution
cat("\n  Sector Distribution:\n")
sector_breakdown <- final_portfolio %>%
  count(sector, sort = TRUE)
print(as.data.frame(sector_breakdown), row.names = FALSE)

# Portfolio-level metrics
cat("\n  Portfolio-Level Metrics:\n")
cat(sprintf("    Total stocks: %d\n", nrow(final_portfolio)))
cat(sprintf("    Sectors represented: %d\n", length(unique(final_portfolio$sector))))
cat(sprintf("    Average 1-year return: %.1f%%\n",
            100 * mean(final_portfolio$cumulative_return_1y)))
cat(sprintf("    Average Sharpe ratio: %.2f\n",
            mean(final_portfolio$sharpe_ratio, na.rm = TRUE)))
cat(sprintf("    Average daily volatility: %.2f%%\n",
            100 * mean(final_portfolio$daily_volatility)))
cat(sprintf("    Average pairwise correlation: %.3f\n",
            mean(final_portfolio$avg_correlation)))

# Check if Unknown sector is included
unknown_in_portfolio <- final_portfolio %>% filter(sector == "Unknown")
if (nrow(unknown_in_portfolio) > 0) {
  cat("\n  ⚠ WARNING: Portfolio includes stocks from 'Unknown' sector:\n")
  print(unknown_in_portfolio %>% select(ticker, cumulative_return_1y, sharpe_ratio))
  cat("  Consider reviewing these stocks' sector classifications.\n")
}

# ============================================================================
# STEP 6: SAVE PORTFOLIO
# ============================================================================

cat("\nStep 6: Saving final portfolio...\n")

# Save portfolio
write.csv(final_portfolio, PORTFOLIO_FILE, row.names = FALSE)
saveRDS(final_portfolio, PORTFOLIO_RDS)

cat(sprintf("  Saved CSV: %s\n", PORTFOLIO_FILE))
cat(sprintf("  Saved RDS: %s\n", PORTFOLIO_RDS))

# ============================================================================
# STEP 7: CORRELATION HEATMAP DATA
# ============================================================================

cat("\nStep 7: Preparing correlation heatmap...\n")

# Extract portfolio correlation submatrix
portfolio_corr <- correlation_matrix[selected_stocks, selected_stocks]

# Save heatmap data
heatmap_file <- file.path(OUTPUT_DIR, "portfolio_correlation_heatmap.rds")
saveRDS(portfolio_corr, heatmap_file)

# Create correlation heatmap plot
pdf(file.path(OUTPUT_DIR, "portfolio_correlation_heatmap.pdf"),
    width = 10, height = 10)
corrplot(portfolio_corr, method = "color", type = "upper",
         addCoef.col = "black", number.cex = 0.7,
         tl.col = "black", tl.srt = 45,
         title = "Portfolio Correlation Matrix",
         mar = c(0,0,2,0))
dev.off()

cat(sprintf("  Saved heatmap: %s\n",
            file.path(OUTPUT_DIR, "portfolio_correlation_heatmap.pdf")))

# Also create text-based visualization
cat("\n  Portfolio Correlation Matrix:\n")
print(round(portfolio_corr, 2))

# ============================================================================
# STEP 8: GENERATE SUMMARY REPORT
# ============================================================================

cat("\nStep 8: Creating summary report...\n")

# Correlation statistics
portfolio_corr_values <- portfolio_corr[upper.tri(portfolio_corr)]

summary_report <- sprintf("
=== MODULE 3: CORRELATION ANALYSIS SUMMARY ===
Generated: %s

SELECTION PARAMETERS:
- Target portfolio size: %d stocks
- Maximum correlation threshold: %.2f
- Minimum sectors required: %d
- Maximum stocks per sector: %d
- Sharpe ratio weighting: %s

INPUT DATA:
- Candidate stocks analyzed: %d
- Analysis period: %d trading days (~1 year)
- Correlation calculation method: Pearson

SELECTION ALGORITHM:
- Stage 1: Top performer from each of %d major sectors
- Stage 2: Greedy selection with sector constraints and Sharpe weighting

FINAL PORTFOLIO:
- Total stocks: %d
- Sectors represented: %d
- Average 1-year return: %.1f%%
- Average Sharpe ratio: %.2f
- Average daily volatility: %.2f%%

CORRELATION METRICS:
- Average pairwise correlation: %.3f
- Median pairwise correlation: %.3f
- Maximum pairwise correlation: %.3f
- Minimum pairwise correlation: %.3f
- Standard deviation: %.3f

SECTOR BREAKDOWN:
%s

PORTFOLIO COMPOSITION:
%s

CORRELATION QUALITY:
%s

FILES GENERATED:
- Final portfolio: %s
- Correlation matrix: %s
- Correlation heatmap: %s

NEXT STEPS:
- Run Module 4 for Ichimoku technical validation
- Review flagged stocks if any
- Proceed to portfolio optimization (efficient frontier)
",
Sys.time(),
TARGET_PORTFOLIO_SIZE,
MAX_CORRELATION,
MIN_SECTORS,
MAX_PER_SECTOR,
ifelse(USE_SHARPE_WEIGHTING, "Yes", "No"),
nrow(candidates),
CORRELATION_PERIOD,
length(major_sectors),
nrow(final_portfolio),
length(unique(final_portfolio$sector)),
100 * mean(final_portfolio$cumulative_return_1y),
mean(final_portfolio$sharpe_ratio, na.rm = TRUE),
100 * mean(final_portfolio$daily_volatility),
mean(portfolio_corr_values),
median(portfolio_corr_values),
max(portfolio_corr_values),
min(portfolio_corr_values),
sd(portfolio_corr_values),
paste(capture.output(print(sector_breakdown, row.names = FALSE)), collapse = "\n"),
paste(capture.output(print(
  final_portfolio %>%
    select(ticker, sector, cumulative_return_1y, sharpe_ratio, avg_correlation) %>%
    mutate(return_pct = sprintf("%.1f%%", 100 * cumulative_return_1y)) %>%
    select(ticker, sector, return_pct, sharpe_ratio, avg_correlation),
  row.names = FALSE
)), collapse = "\n"),
ifelse(mean(portfolio_corr_values) < 0.3,
       "Excellent - Very low correlation, maximum diversification",
       ifelse(mean(portfolio_corr_values) < 0.5,
              "Good - Moderate correlation, well-diversified portfolio",
              "Fair - Higher correlation, consider reviewing selections")),
PORTFOLIO_FILE,
CORRELATION_FILE,
"analysis/portfolio_correlation_heatmap.pdf"
)

# Save summary
summary_file <- file.path(OUTPUT_DIR, "module_3_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 3 COMPLETE ===\n")
cat(sprintf("Next step: Run Module 4 for Ichimoku technical validation\n\n"))

# ============================================================================
# USAGE EXAMPLE FOR NEXT STEPS
# ============================================================================

cat("=== QUICK START FOR MODULE 4 ===\n")
cat("# Load final portfolio:\n")
cat("portfolio <- readRDS('analysis/final_portfolio.rds')\n\n")
cat("# View portfolio:\n")
cat("print(portfolio)\n\n")
cat("# Get ticker list for Ichimoku analysis:\n")
cat("tickers <- portfolio$ticker\n\n")
cat("# View correlation heatmap:\n")
cat("portfolio_corr <- readRDS('analysis/portfolio_correlation_heatmap.rds')\n")
cat("corrplot(portfolio_corr, method='color', type='upper', addCoef.col='black')\n\n")
