#!/usr/bin/env Rscript
# ============================================================================
# Export R Pipeline Data to CSV
# ============================================================================
# This script exports the essential data from R's .rds format to CSV
# so our Python web app can read it.
#
# Updated for strategy-specific portfolios:
# - Each strategy (max_sharpe, min_variance, max_sortino, min_cvar, risk_parity)
#   now has its own optimal stock selection
#
# Run this after running the R analysis pipeline (Modules 1-6).

library(dplyr)
library(tidyr)

cat("============================================================\n")
cat("EXPORTING R DATA TO CSV FOR PYTHON WEB APP\n")
cat("============================================================\n\n")

# Note: Run from project root directory

# Create output directory
output_dir <- "webapp/db/seed_data"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# -------------------------------------------------------------------------
# Export 1: All Strategy Portfolios
# -------------------------------------------------------------------------
cat("1. Exporting strategy-specific portfolios...\n")

# Load all strategy portfolios
all_portfolios <- readRDS("analysis/all_strategy_portfolios.rds")
all_weights <- readRDS("analysis/all_strategy_weights.rds")
ichimoku <- readRDS("analysis/ichimoku_validation.rds")

# Create combined export with all strategies
strategy_export <- all_weights %>%
  left_join(ichimoku %>% select(ticker, signal), by = "ticker") %>%
  rename(ichimoku_signal = signal) %>%
  select(
    strategy,
    ticker,
    weight,
    sector,
    sharpe_ratio,
    sortino_ratio,
    current_price,
    ichimoku_signal
  )

write.csv(strategy_export, file.path(output_dir, "strategy_portfolios.csv"), row.names = FALSE)
cat(sprintf("   Exported %d strategy-stock combinations\n", nrow(strategy_export)))

# Show breakdown by strategy
strategy_summary <- strategy_export %>%
  group_by(strategy) %>%
  summarize(
    n_stocks = n(),
    avg_weight = mean(weight),
    .groups = "drop"
  )
for (i in 1:nrow(strategy_summary)) {
  cat(sprintf("     - %s: %d stocks\n",
              strategy_summary$strategy[i],
              strategy_summary$n_stocks[i]))
}

# -------------------------------------------------------------------------
# Export 2: Legacy portfolio_stocks.csv (max_sharpe for backward compatibility)
# -------------------------------------------------------------------------
cat("\n2. Exporting legacy portfolio stocks (max_sharpe)...\n")

# Load legacy format files
portfolio <- readRDS("analysis/final_portfolio.rds")
legacy_weights <- readRDS("analysis/optimal_weights.rds")

# Combine into legacy format
portfolio_export <- portfolio %>%
  left_join(legacy_weights %>% select(ticker,
                                max_sharpe_weight,
                                min_variance_weight,
                                max_sortino_weight,
                                min_cvar_weight,
                                risk_parity_weight,
                                equal_weight), by = "ticker") %>%
  left_join(ichimoku %>% select(ticker, signal), by = "ticker") %>%
  select(
    ticker,
    sector,
    sharpe_ratio,
    avg_correlation,
    max_sharpe_weight,
    min_variance_weight,
    max_sortino_weight,
    min_cvar_weight,
    risk_parity_weight,
    equal_weight,
    ichimoku_signal = signal,
    current_price
  )

write.csv(portfolio_export, file.path(output_dir, "portfolio_stocks.csv"), row.names = FALSE)
cat(sprintf("   Exported %d portfolio stocks (legacy format)\n", nrow(portfolio_export)))

# -------------------------------------------------------------------------
# Export 3: Bench stocks per strategy
# -------------------------------------------------------------------------
cat("\n3. Exporting bench stocks per strategy...\n")

candidates <- readRDS("analysis/candidate_stocks.rds")

# Create bench for each strategy
bench_list <- list()
for (strategy in names(all_portfolios)) {
  strategy_tickers <- all_portfolios[[strategy]]$ticker

  # Bench = candidates not in this strategy's portfolio
  bench <- candidates %>%
    filter(!ticker %in% strategy_tickers) %>%
    arrange(desc(sharpe_ratio)) %>%
    head(10) %>%
    mutate(strategy = strategy) %>%
    select(strategy, ticker, sector, sharpe_ratio, current_price)

  bench_list[[strategy]] <- bench
}

bench_export <- bind_rows(bench_list)
write.csv(bench_export, file.path(output_dir, "strategy_bench_stocks.csv"), row.names = FALSE)
cat(sprintf("   Exported %d bench stocks across strategies\n", nrow(bench_export)))

# Legacy bench (max_sharpe)
legacy_bench <- candidates %>%
  filter(!ticker %in% portfolio$ticker) %>%
  arrange(desc(sharpe_ratio)) %>%
  head(10) %>%
  select(ticker, sector, sharpe_ratio, current_price)

write.csv(legacy_bench, file.path(output_dir, "bench_stocks.csv"), row.names = FALSE)
cat(sprintf("   Exported %d legacy bench stocks\n", nrow(legacy_bench)))

# -------------------------------------------------------------------------
# Export 4: Correlation matrices per strategy
# -------------------------------------------------------------------------
cat("\n4. Exporting correlation matrices...\n")

# Default correlation (max_sharpe)
corr_matrix <- readRDS("analysis/portfolio_correlation_heatmap.rds")
corr_df <- as.data.frame(corr_matrix)
corr_df$ticker <- rownames(corr_matrix)

corr_long <- corr_df %>%
  pivot_longer(cols = -ticker, names_to = "ticker_b", values_to = "correlation") %>%
  rename(ticker_a = ticker) %>%
  filter(ticker_a < ticker_b)

write.csv(corr_long, file.path(output_dir, "correlations.csv"), row.names = FALSE)
cat(sprintf("   Exported %d correlation pairs (legacy)\n", nrow(corr_long)))

# Strategy-specific correlations
if (dir.exists("analysis/portfolios")) {
  all_corr <- list()
  for (strategy in c("max_sharpe", "min_variance", "max_sortino", "min_cvar", "risk_parity")) {
    corr_file <- file.path("analysis/portfolios", paste0(strategy, "_correlation.rds"))
    if (file.exists(corr_file)) {
      corr_mat <- readRDS(corr_file)
      corr_df <- as.data.frame(corr_mat)
      corr_df$ticker <- rownames(corr_mat)

      corr_strat <- corr_df %>%
        pivot_longer(cols = -ticker, names_to = "ticker_b", values_to = "correlation") %>%
        rename(ticker_a = ticker) %>%
        filter(ticker_a < ticker_b) %>%
        mutate(strategy = strategy)

      all_corr[[strategy]] <- corr_strat
    }
  }

  if (length(all_corr) > 0) {
    all_corr_export <- bind_rows(all_corr)
    write.csv(all_corr_export, file.path(output_dir, "strategy_correlations.csv"), row.names = FALSE)
    cat(sprintf("   Exported %d strategy-specific correlation pairs\n", nrow(all_corr_export)))
  }
}

# -------------------------------------------------------------------------
# Export 5: Strategy metadata
# -------------------------------------------------------------------------
cat("\n5. Exporting strategy metadata...\n")

# Create metadata about each strategy's stocks
strategy_meta <- bind_rows(lapply(names(all_portfolios), function(strategy) {
  p <- all_portfolios[[strategy]]
  data.frame(
    strategy = strategy,
    n_stocks = nrow(p),
    n_sectors = length(unique(p$sector)),
    avg_sharpe = mean(p$sharpe_ratio, na.rm = TRUE),
    avg_sortino = mean(p$sortino_ratio, na.rm = TRUE),
    avg_correlation = mean(p$avg_correlation, na.rm = TRUE),
    tickers = paste(p$ticker, collapse = ","),
    stringsAsFactors = FALSE
  )
}))

write.csv(strategy_meta, file.path(output_dir, "strategy_metadata.csv"), row.names = FALSE)
cat(sprintf("   Exported metadata for %d strategies\n", nrow(strategy_meta)))

# -------------------------------------------------------------------------
# Export 6: Strategy portfolio positions (for efficient frontier chart)
# -------------------------------------------------------------------------
cat("\n6. Exporting strategy portfolio positions...\n")

# Load the efficient frontier results which contain optimal portfolio stats
frontier_data <- readRDS("analysis/efficient_frontier.rds")

if (!is.null(frontier_data$all_strategies)) {
  strategy_positions <- bind_rows(lapply(names(frontier_data$all_strategies), function(strategy) {
    res <- frontier_data$all_strategies[[strategy]]
    opt <- res$optimal_portfolio
    data.frame(
      strategy = strategy,
      expected_return = opt$return,
      risk = opt$risk,
      sharpe = opt$sharpe,
      sortino = ifelse(is.null(opt$sortino) || is.na(opt$sortino), NA, opt$sortino),
      stringsAsFactors = FALSE
    )
  }))

  # Add equal_weight (uses max_sharpe stocks with equal weights)
  eq_stats <- frontier_data$all_strategies[["max_sharpe"]]$equal_stats
  strategy_positions <- rbind(strategy_positions, data.frame(
    strategy = "equal_weight",
    expected_return = eq_stats$return,
    risk = eq_stats$risk,
    sharpe = eq_stats$sharpe,
    sortino = ifelse(is.null(eq_stats$sortino) || is.na(eq_stats$sortino), NA, eq_stats$sortino),
    stringsAsFactors = FALSE
  ))

  write.csv(strategy_positions, file.path(output_dir, "strategy_positions.csv"), row.names = FALSE)
  cat(sprintf("   Exported positions for %d strategies\n", nrow(strategy_positions)))
} else {
  cat("   Skipped: No strategy data in efficient_frontier.rds\n")
}

# -------------------------------------------------------------------------
# Export 7: Ichimoku chart data for webapp
# -------------------------------------------------------------------------
cat("\n7. Exporting Ichimoku chart data...\n")

# Create ichimoku export directory
ichimoku_export_dir <- file.path(output_dir, "ichimoku")
dir.create(ichimoku_export_dir, showWarnings = FALSE, recursive = TRUE)

# Get all unique tickers across strategies
all_tickers <- unique(c(
  unlist(lapply(all_portfolios, function(p) p$ticker)),
  candidates$ticker[1:10]  # Top 10 candidates as bench
))

# Load stock data and export ichimoku CSVs
exported_count <- 0
for (ticker in all_tickers) {
  stock_file <- file.path("stocks", paste0(ticker, ".rds"))

  if (!file.exists(stock_file)) next

  stock_data <- tryCatch({
    readRDS(stock_file)
  }, error = function(e) NULL)

  if (is.null(stock_data)) next

  # Calculate Ichimoku indicators
  stock_data <- stock_data %>% arrange(date)

  if (nrow(stock_data) < 52) next

  # Calculate indicators
  high <- stock_data$high
  low <- stock_data$low

  # Tenkan-sen (Conversion Line)
  conv_high <- zoo::rollmax(high, 9, fill = NA, align = "right")
  conv_low <- zoo::rollapply(low, 9, min, fill = NA, align = "right")
  tenkan_sen <- (conv_high + conv_low) / 2

  # Kijun-sen (Base Line)
  base_high <- zoo::rollmax(high, 26, fill = NA, align = "right")
  base_low <- zoo::rollapply(low, 26, min, fill = NA, align = "right")
  kijun_sen <- (base_high + base_low) / 2

  # Senkou Span A
  senkou_span_a <- (tenkan_sen + kijun_sen) / 2

  # Senkou Span B
  span_b_high <- zoo::rollmax(high, 52, fill = NA, align = "right")
  span_b_low <- zoo::rollapply(low, 52, min, fill = NA, align = "right")
  senkou_span_b <- (span_b_high + span_b_low) / 2

  # Chikou Span (lagging)
  chikou_span <- c(stock_data$close[27:nrow(stock_data)], rep(NA, 26))

  # Create export dataframe (last 252 days)
  export_data <- data.frame(
    date = as.character(stock_data$date),
    open = stock_data$open,
    high = stock_data$high,
    low = stock_data$low,
    close = stock_data$close,
    volume = stock_data$volume,
    tenkan_sen = tenkan_sen,
    kijun_sen = kijun_sen,
    senkou_span_a = senkou_span_a,
    senkou_span_b = senkou_span_b,
    chikou_span = chikou_span
  ) %>%
    tail(252)

  # Export
  write.csv(export_data, file.path(ichimoku_export_dir, paste0(ticker, ".csv")), row.names = FALSE)
  exported_count <- exported_count + 1
}

cat(sprintf("   Exported Ichimoku data for %d stocks\n", exported_count))

# -------------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------------
cat("\n============================================================\n")
cat("EXPORT COMPLETE\n")
cat("============================================================\n")
cat(sprintf("Files created in: %s/\n", output_dir))
cat("\nNew strategy-specific files:\n")
cat("  - strategy_portfolios.csv (all strategies with weights)\n")
cat("  - strategy_bench_stocks.csv (bench per strategy)\n")
cat("  - strategy_correlations.csv (correlation per strategy)\n")
cat("  - strategy_metadata.csv (strategy summary)\n")
cat("\nLegacy files (backward compatible):\n")
cat("  - portfolio_stocks.csv (max_sharpe with all weight columns)\n")
cat("  - bench_stocks.csv (max_sharpe alternates)\n")
cat("  - correlations.csv (max_sharpe correlations)\n")
cat("\nThese files are read by the Python web app.\n")
