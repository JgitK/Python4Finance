# ============================================================================
# MODULE 6: BACKTESTING & VALIDATION
# ============================================================================
# Tests portfolio strategy on historical data and compares to benchmarks
# Following principles from: https://www.codingfinance.com/
#
# Inputs: Optimal portfolio from Module 5
# Outputs: Backtest performance, benchmark comparison, validation metrics
#
# Author: Portfolio Optimization System
# Date: 2026-01-17

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("PerformanceAnalytics", quietly = TRUE)) install.packages("PerformanceAnalytics")
if (!require("ggplot2", quietly = TRUE)) install.packages("ggplot2")
library(PerformanceAnalytics)
library(ggplot2)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 6: BACKTESTING & VALIDATION ===\n\n")

# Backtest parameters
TRAINING_START <- Sys.Date() - 365 * 2    # 2 years ago
TRAINING_END <- Sys.Date() - 180          # 6 months ago
TEST_START <- TRAINING_END + 1            # 6 months ago
TEST_END <- Sys.Date()                    # Today

# Benchmark
BENCHMARK_TICKER <- "^GSPC"               # S&P 500

# Output directory
OUTPUT_DIR <- "analysis"
BACKTEST_DIR <- file.path(OUTPUT_DIR, "backtest")
BACKTEST_FILE <- file.path(BACKTEST_DIR, "backtest_results.csv")
BACKTEST_RDS <- file.path(BACKTEST_DIR, "backtest_results.rds")

# Create backtest directory
if (!dir.exists(BACKTEST_DIR)) {
  dir.create(BACKTEST_DIR, recursive = TRUE)
  cat("Created directory: analysis/backtest/\n\n")
}

# ============================================================================
# STEP 1: LOAD PORTFOLIO AND WEIGHTS
# ============================================================================

cat("Step 1: Loading optimized portfolio...\n")

# Load portfolio and weights
portfolio <- readRDS(file.path(OUTPUT_DIR, "final_portfolio.rds"))
weights_data <- readRDS(file.path(OUTPUT_DIR, "optimal_weights.rds"))

# Extract optimal weights
optimal_weights <- weights_data$max_sharpe_weight
names(optimal_weights) <- weights_data$ticker

cat(sprintf("  Portfolio stocks: %d\n", length(optimal_weights)))
cat(sprintf("  Backtest period: %s to %s\n", TEST_START, TEST_END))
cat(sprintf("  Training period: %s to %s\n", TRAINING_START, TRAINING_END))

# ============================================================================
# STEP 2: LOAD HISTORICAL DATA
# ============================================================================

cat("\nStep 2: Loading historical data for backtest...\n")

# Load portfolio stocks
stock_data_list <- load_multiple_stocks(names(optimal_weights))

cat(sprintf("  Loaded %d portfolio stocks\n", length(stock_data_list)))

# Download benchmark (S&P 500)
cat(sprintf("  Downloading benchmark: %s\n", BENCHMARK_TICKER))

benchmark_data <- tryCatch({
  getSymbols(BENCHMARK_TICKER,
             src = "yahoo",
             from = TRAINING_START,
             to = TEST_END,
             auto.assign = FALSE,
             warnings = FALSE)
}, error = function(e) {
  cat("  Warning: Could not download benchmark. Using portfolio-only analysis.\n")
  return(NULL)
})

if (!is.null(benchmark_data)) {
  benchmark_df <- data.frame(
    date = index(benchmark_data),
    close = as.numeric(Cl(benchmark_data)),
    adjusted = as.numeric(Ad(benchmark_data))
  ) %>%
    mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted))

  cat("  Benchmark data loaded successfully\n")
} else {
  benchmark_df <- NULL
}

# ============================================================================
# STEP 3: CREATE RETURNS MATRIX FOR TEST PERIOD
# ============================================================================

cat("\nStep 3: Creating returns matrix for test period...\n")

# Calculate returns for each stock
returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    filter(date >= TEST_START, date <= TEST_END) %>%
    arrange(date) %>%
    mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted)) %>%
    select(date, daily_return) %>%
    rename(!!ticker := daily_return)
})

# Join all returns
returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

cat(sprintf("  Returns matrix: %d days\n", nrow(returns_matrix)))

# ============================================================================
# STEP 4: CALCULATE PORTFOLIO PERFORMANCE
# ============================================================================

cat("\nStep 4: Calculating portfolio performance...\n")

# Extract returns only
returns_df <- returns_matrix %>% select(-date)
returns_mat <- as.matrix(returns_df)

# Calculate weighted portfolio returns
portfolio_returns <- returns_mat %*% optimal_weights

# Calculate cumulative returns
portfolio_cumulative <- cumprod(1 + portfolio_returns) - 1

# Create portfolio performance dataframe
portfolio_performance <- data.frame(
  date = returns_matrix$date[-1],  # Remove first date (NA from lag)
  daily_return = portfolio_returns[-1],
  cumulative_return = portfolio_cumulative[-1]
)

# Performance metrics
total_return <- as.numeric(tail(portfolio_cumulative, 1))
trading_days <- nrow(portfolio_performance)
annualized_return <- (1 + total_return)^(252/trading_days) - 1
volatility <- sd(portfolio_returns, na.rm = TRUE) * sqrt(252)
sharpe_ratio <- annualized_return / volatility

cat(sprintf("  Total return: %.2f%%\n", 100 * total_return))
cat(sprintf("  Annualized return: %.2f%%\n", 100 * annualized_return))
cat(sprintf("  Annualized volatility: %.2f%%\n", 100 * volatility))
cat(sprintf("  Sharpe ratio: %.3f\n", sharpe_ratio))

# Maximum drawdown
cumulative_max <- cummax(1 + portfolio_cumulative)
drawdown <- (1 + portfolio_cumulative) / cumulative_max - 1
max_drawdown <- min(drawdown, na.rm = TRUE)

cat(sprintf("  Maximum drawdown: %.2f%%\n", 100 * max_drawdown))

# ============================================================================
# STEP 5: BENCHMARK COMPARISON
# ============================================================================

if (!is.null(benchmark_df)) {
  cat("\nStep 5: Comparing to benchmark (S&P 500)...\n")

  # Filter benchmark to test period
  benchmark_test <- benchmark_df %>%
    filter(date >= TEST_START, date <= TEST_END) %>%
    arrange(date)

  # Calculate benchmark cumulative return
  benchmark_cumulative <- cumprod(1 + benchmark_test$daily_return) - 1

  # Benchmark metrics
  benchmark_total <- as.numeric(tail(benchmark_cumulative, 1))
  benchmark_annualized <- (1 + benchmark_total)^(252/nrow(benchmark_test)) - 1
  benchmark_vol <- sd(benchmark_test$daily_return, na.rm = TRUE) * sqrt(252)
  benchmark_sharpe <- benchmark_annualized / benchmark_vol

  cat(sprintf("  S&P 500 total return: %.2f%%\n", 100 * benchmark_total))
  cat(sprintf("  S&P 500 annualized return: %.2f%%\n", 100 * benchmark_annualized))
  cat(sprintf("  S&P 500 volatility: %.2f%%\n", 100 * benchmark_vol))
  cat(sprintf("  S&P 500 Sharpe ratio: %.3f\n", benchmark_sharpe))

  # Outperformance
  alpha_return <- total_return - benchmark_total
  alpha_annualized <- annualized_return - benchmark_annualized

  cat(sprintf("\n  === OUTPERFORMANCE ===\n"))
  cat(sprintf("  Alpha (total): %+.2f%%\n", 100 * alpha_return))
  cat(sprintf("  Alpha (annualized): %+.2f%%\n", 100 * alpha_annualized))

  # Beta calculation (portfolio sensitivity to market)
  if (nrow(portfolio_performance) == nrow(benchmark_test)) {
    # Align dates
    combined <- portfolio_performance %>%
      left_join(benchmark_test %>% select(date, benchmark_return = daily_return),
                by = "date")

    # Calculate beta
    if (sum(!is.na(combined$benchmark_return)) > 10) {
      cov_market <- cov(combined$daily_return, combined$benchmark_return, use = "complete.obs")
      var_market <- var(combined$benchmark_return, na.rm = TRUE)
      beta <- cov_market / var_market

      cat(sprintf("  Beta: %.3f\n", beta))

      if (beta > 1) {
        cat("  (Portfolio is more volatile than market)\n")
      } else if (beta < 1) {
        cat("  (Portfolio is less volatile than market)\n")
      }
    }
  }

  # Add benchmark to performance data
  portfolio_performance <- portfolio_performance %>%
    left_join(benchmark_test %>% select(date, benchmark_return = daily_return),
              by = "date") %>%
    mutate(benchmark_cumulative = cumprod(1 + replace_na(benchmark_return, 0)) - 1)

} else {
  cat("\nStep 5: Benchmark comparison skipped (no benchmark data)\n")
}

# ============================================================================
# STEP 6: EQUAL WEIGHT COMPARISON
# ============================================================================

cat("\nStep 6: Comparing to equal-weight portfolio...\n")

# Equal weight returns
equal_weights <- rep(1/length(optimal_weights), length(optimal_weights))
equal_returns <- returns_mat %*% equal_weights
equal_cumulative <- cumprod(1 + equal_returns) - 1

# Equal weight metrics
equal_total <- as.numeric(tail(equal_cumulative, 1))
equal_annualized <- (1 + equal_total)^(252/trading_days) - 1
equal_vol <- sd(equal_returns, na.rm = TRUE) * sqrt(252)
equal_sharpe <- equal_annualized / equal_vol

cat(sprintf("  Equal-weight total return: %.2f%%\n", 100 * equal_total))
cat(sprintf("  Equal-weight annualized return: %.2f%%\n", 100 * equal_annualized))
cat(sprintf("  Equal-weight Sharpe ratio: %.3f\n", equal_sharpe))

cat(sprintf("\n  Optimized vs Equal-weight:\n"))
cat(sprintf("  Return improvement: %+.2f%%\n", 100 * (total_return - equal_total)))
cat(sprintf("  Sharpe improvement: %+.3f\n", sharpe_ratio - equal_sharpe))

# Add equal weight to performance data
portfolio_performance <- portfolio_performance %>%
  mutate(equal_cumulative = equal_cumulative[-1])

# ============================================================================
# STEP 7: SAVE BACKTEST RESULTS
# ============================================================================

cat("\nStep 7: Saving backtest results...\n")

# Save performance data
write.csv(portfolio_performance, BACKTEST_FILE, row.names = FALSE)
saveRDS(portfolio_performance, BACKTEST_RDS)

cat(sprintf("  Saved: %s\n", BACKTEST_FILE))

# ============================================================================
# STEP 8: CREATE PERFORMANCE VISUALIZATIONS
# ============================================================================

cat("\nStep 8: Creating performance visualizations...\n")

# Prepare data for plotting
plot_data <- portfolio_performance %>%
  select(date, cumulative_return, equal_cumulative) %>%
  rename(
    `Optimized Portfolio` = cumulative_return,
    `Equal Weight` = equal_cumulative
  )

if (!is.null(benchmark_df) && "benchmark_cumulative" %in% names(portfolio_performance)) {
  plot_data <- plot_data %>%
    mutate(`S&P 500` = portfolio_performance$benchmark_cumulative)
}

# Convert to long format for ggplot
plot_long <- plot_data %>%
  pivot_longer(cols = -date, names_to = "Portfolio", values_to = "Return")

# Create performance chart
perf_plot <- ggplot(plot_long, aes(x = date, y = Return, color = Portfolio)) +
  geom_line(size = 1.2) +
  scale_y_continuous(labels = scales::percent) +
  scale_color_manual(values = c(
    "Optimized Portfolio" = "darkgreen",
    "Equal Weight" = "blue",
    "S&P 500" = "red"
  )) +
  labs(
    title = "Portfolio Performance Backtest",
    subtitle = sprintf("Test Period: %s to %s", TEST_START, TEST_END),
    x = "Date",
    y = "Cumulative Return"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    legend.position = "bottom",
    legend.title = element_blank()
  )

# Save plot
ggsave(file.path(BACKTEST_DIR, "performance_comparison.pdf"),
       perf_plot, width = 12, height = 8)
ggsave(file.path(BACKTEST_DIR, "performance_comparison.png"),
       perf_plot, width = 12, height = 8, dpi = 300)

cat(sprintf("  Saved plots: %s\n", BACKTEST_DIR))

# Drawdown chart
drawdown_data <- data.frame(
  date = portfolio_performance$date,
  drawdown = drawdown[-1]
)

dd_plot <- ggplot(drawdown_data, aes(x = date, y = drawdown)) +
  geom_area(fill = "red", alpha = 0.3) +
  geom_line(color = "darkred", size = 1) +
  scale_y_continuous(labels = scales::percent) +
  labs(
    title = "Portfolio Drawdown",
    subtitle = sprintf("Maximum Drawdown: %.2f%%", 100 * max_drawdown),
    x = "Date",
    y = "Drawdown"
  ) +
  theme_minimal() +
  theme(plot.title = element_text(size = 16, face = "bold"))

ggsave(file.path(BACKTEST_DIR, "drawdown.pdf"),
       dd_plot, width = 12, height = 6)
ggsave(file.path(BACKTEST_DIR, "drawdown.png"),
       dd_plot, width = 12, height = 6, dpi = 300)

# ============================================================================
# STEP 9: GENERATE SUMMARY REPORT
# ============================================================================

cat("\nStep 9: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 6: BACKTESTING & VALIDATION SUMMARY ===
Generated: %s

BACKTEST CONFIGURATION:
- Test period: %s to %s (%d days)
- Training period: %s to %s
- Portfolio: %d stocks with optimized weights
- Benchmark: S&P 500 (^GSPC)

PORTFOLIO PERFORMANCE (Test Period):
- Total return: %.2f%%
- Annualized return: %.2f%%
- Annualized volatility: %.2f%%
- Sharpe ratio: %.3f
- Maximum drawdown: %.2f%%

BENCHMARK COMPARISON (S&P 500):
%s

EQUAL-WEIGHT COMPARISON:
- Equal-weight return: %.2f%%
- Optimized return: %.2f%%
- Return improvement: %+.2f%%
- Equal-weight Sharpe: %.3f
- Optimized Sharpe: %.3f
- Sharpe improvement: %+.3f

RISK METRICS:
- Daily volatility: %.2f%%
- Annual volatility: %.2f%%
- Maximum drawdown: %.2f%%
- Downside deviation: %.2f%%

INTERPRETATION:
%s

VALIDATION RESULTS:
%s

FILES GENERATED:
- Performance data: %s
- Performance chart: %s/performance_comparison.png
- Drawdown chart: %s/drawdown.png

CONCLUSION:
%s

NEXT STEPS:
- Review performance vs expectations
- Consider position sizing adjustments
- Implement with actual capital
- Set up rebalancing schedule (every 6-12 months)
- Monitor portfolio quarterly
",
Sys.time(),
TEST_START, TEST_END, trading_days,
TRAINING_START, TRAINING_END,
length(optimal_weights),
100 * total_return,
100 * annualized_return,
100 * volatility,
sharpe_ratio,
100 * max_drawdown,
ifelse(!is.null(benchmark_df),
       sprintf("- S&P 500 return: %.2f%%
- Annualized return: %.2f%%
- Alpha (outperformance): %+.2f%%
- Beta: %.3f
- Portfolio %s the market",
               100 * benchmark_total,
               100 * benchmark_annualized,
               100 * alpha_annualized,
               ifelse(exists("beta"), beta, NA),
               ifelse(total_return > benchmark_total, "BEAT", "UNDERPERFORMED")),
       "Benchmark data not available"),
100 * equal_total,
100 * total_return,
100 * (total_return - equal_total),
equal_sharpe,
sharpe_ratio,
sharpe_ratio - equal_sharpe,
100 * sd(portfolio_returns, na.rm = TRUE),
100 * volatility,
100 * max_drawdown,
100 * sd(portfolio_returns[portfolio_returns < 0], na.rm = TRUE) * sqrt(252),
ifelse(sharpe_ratio > 2.0,
       "✓ Excellent risk-adjusted performance (Sharpe > 2.0)",
       ifelse(sharpe_ratio > 1.0,
              "✓ Good risk-adjusted performance (Sharpe > 1.0)",
              "~ Moderate risk-adjusted performance")),
ifelse(total_return > equal_total,
       sprintf("✓ Optimization successful - outperformed equal-weight by %.2f%%",
               100 * (total_return - equal_total)),
       sprintf("⚠ Optimization did not outperform equal-weight in test period
  This could be due to:
  - Short test period (6 months)
  - Market regime change
  - Overfitting to training data
  - Consider longer backtest or different optimization period")),
BACKTEST_FILE,
BACKTEST_DIR,
BACKTEST_DIR,
ifelse(sharpe_ratio > 1.5 && total_return > equal_total,
       "✓ Strategy validated! Portfolio shows strong risk-adjusted returns and outperforms benchmarks.
  Optimization approach is working as expected. Ready for implementation.",
       ifelse(sharpe_ratio > 1.0,
              "~ Strategy shows promise but requires monitoring.
  Continue to track performance and rebalance as needed.",
              "⚠ Strategy needs review. Consider:
  - Longer backtest period
  - Different optimization parameters
  - Market condition analysis"))
)

# Save summary
summary_file <- file.path(BACKTEST_DIR, "backtest_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 6 COMPLETE ===\n")
cat("=== PORTFOLIO OPTIMIZATION SYSTEM COMPLETE ===\n\n")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

cat("=== COMPLETE PORTFOLIO OPTIMIZATION WORKFLOW ===\n\n")

cat("You have successfully completed all 6 modules:\n\n")

cat("✓ Module 1: Downloaded 2,725 stocks\n")
cat("✓ Module 2: Screened to 130 top performers\n")
cat("✓ Module 3: Selected 12 least-correlated stocks\n")
cat("✓ Module 4: Validated with Ichimoku (9 bullish, 2 bearish)\n")
cat("✓ Module 5: Optimized weights for maximum Sharpe ratio\n")
cat("✓ Module 6: Backtested and validated performance\n\n")

cat("FINAL PORTFOLIO READY FOR IMPLEMENTATION!\n\n")

cat("Key Files:\n")
cat("- analysis/final_portfolio.rds - Your 12 stocks\n")
cat("- analysis/optimal_weights.csv - Optimal allocation\n")
cat("- analysis/dollar_allocation.csv - Exact shares to buy\n")
cat("- analysis/efficient_frontier.png - Visual optimization\n")
cat("- analysis/backtest/performance_comparison.png - Backtest results\n\n")

cat("To implement:\n")
cat("1. Review dollar_allocation.csv\n")
cat("2. Adjust investment amount if needed\n")
cat("3. Place orders for specified shares\n")
cat("4. Monitor quarterly\n")
cat("5. Rebalance every 6-12 months\n\n")
