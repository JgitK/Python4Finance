#!/usr/bin/env Rscript
# ============================================================================
# Export R Pipeline Data to CSV
# ============================================================================
# This script exports the essential data from R's .rds format to CSV
# so our Python web app can read it.
#
# Run this after running the R analysis pipeline (Modules 1-6).

library(dplyr)

cat("============================================================\n")
cat("EXPORTING R DATA TO CSV FOR PYTHON WEB APP\n")
cat("============================================================\n\n")

# Set working directory to project root
# (adjust if running from different location)
setwd("/Users/jackson/Desktop/Python4Finance")

# Create output directory
output_dir <- "webapp/db/seed_data"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# -------------------------------------------------------------------------
# Export 1: Portfolio stocks (the 12 selected stocks)
# -------------------------------------------------------------------------
cat("1. Exporting portfolio stocks...\n")

portfolio <- readRDS("analysis/final_portfolio.rds")
weights <- readRDS("analysis/optimal_weights.rds")
ichimoku <- readRDS("analysis/ichimoku_validation.rds")

# Combine into one clean table
portfolio_export <- portfolio %>%
  left_join(weights %>% select(ticker, max_sharpe_weight), by = "ticker") %>%
  left_join(ichimoku %>% select(ticker, signal), by = "ticker") %>%
  select(
    ticker,
    sector,
    sharpe_ratio,
    avg_correlation,
    weight = max_sharpe_weight,
    ichimoku_signal = signal,
    current_price
  )

write.csv(portfolio_export, file.path(output_dir, "portfolio_stocks.csv"), row.names = FALSE)
cat(sprintf("   Exported %d portfolio stocks\n", nrow(portfolio_export)))

# -------------------------------------------------------------------------
# Export 2: Bench stocks (alternates)
# -------------------------------------------------------------------------
cat("2. Exporting bench stocks...\n")

candidates <- readRDS("analysis/candidate_stocks.rds")

# Get stocks that are candidates but not in final portfolio
bench_export <- candidates %>%
  filter(!ticker %in% portfolio$ticker) %>%
  arrange(desc(sharpe_ratio)) %>%
  head(10) %>%
  select(
    ticker,
    sector,
    sharpe_ratio,
    current_price
  )

write.csv(bench_export, file.path(output_dir, "bench_stocks.csv"), row.names = FALSE)
cat(sprintf("   Exported %d bench stocks\n", nrow(bench_export)))

# -------------------------------------------------------------------------
# Export 3: Correlation matrix (for advanced features later)
# -------------------------------------------------------------------------
cat("3. Exporting correlation matrix...\n")

corr_matrix <- readRDS("analysis/portfolio_correlation_heatmap.rds")
corr_df <- as.data.frame(corr_matrix)
corr_df$ticker <- rownames(corr_matrix)

# Reshape to long format for database
corr_long <- corr_df %>%
  tidyr::pivot_longer(cols = -ticker, names_to = "ticker_b", values_to = "correlation") %>%
  rename(ticker_a = ticker) %>%
  filter(ticker_a < ticker_b)  # Only upper triangle

write.csv(corr_long, file.path(output_dir, "correlations.csv"), row.names = FALSE)
cat(sprintf("   Exported %d correlation pairs\n", nrow(corr_long)))

# -------------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------------
cat("\n============================================================\n")
cat("EXPORT COMPLETE\n")
cat("============================================================\n")
cat(sprintf("Files created in: %s/\n", output_dir))
cat("  - portfolio_stocks.csv (12 selected stocks with weights)\n")
cat("  - bench_stocks.csv (10 alternate stocks)\n")
cat("  - correlations.csv (correlation matrix)\n")
cat("\nThese files are read by the Python web app.\n")
