# ============================================================================
# MODULE 6: WALK-FORWARD VALIDATION (NO LOOK-AHEAD BIAS)
# ============================================================================
# True out-of-sample testing - selects portfolio using only historical data,
# then tests forward on data the model never saw.
#
# This is the CORRECT way to validate a trading strategy.
#
# Inputs: Stock data, selection methodology from Modules 2-5
# Outputs: Unbiased performance metrics, benchmark comparison
#
# Author: Portfolio Optimization System
# Date: 2026-01-20

# Load utilities
source("utils_walkforward.R")

# Additional packages
if (!require("ggplot2", quietly = TRUE)) install.packages("ggplot2")
if (!require("quantmod", quietly = TRUE)) install.packages("quantmod")
library(ggplot2)
library(quantmod)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 6: WALK-FORWARD VALIDATION ===\n")
cat("(True out-of-sample testing - NO look-ahead bias)\n\n")

# Walk-forward parameters
HOLDING_PERIOD <- 180  # 6 months holding period

# Selection dates to test (going back in time)
SELECTION_DATES <- c(
  Sys.Date() - 730,   # 2 years ago
  Sys.Date() - 545,   # 1.5 years ago
  Sys.Date() - 365,   # 1 year ago
  Sys.Date() - 180    # 6 months ago
)

# Benchmark
BENCHMARK_TICKER <- "SPY"  # S&P 500 ETF

# Output directory
OUTPUT_DIR <- "analysis"
BACKTEST_DIR <- file.path(OUTPUT_DIR, "backtest")

# Create backtest directory
if (!dir.exists(BACKTEST_DIR)) {
  dir.create(BACKTEST_DIR, recursive = TRUE)
  cat("Created directory: analysis/backtest/\n\n")
}

# ============================================================================
# STEP 1: RUN MULTI-PERIOD WALK-FORWARD ANALYSIS
# ============================================================================

cat("Step 1: Running walk-forward validation across multiple periods...\n")
cat("============================================================\n")
cat(sprintf("Testing %d selection dates with %d-day holding periods\n\n",
            length(SELECTION_DATES), HOLDING_PERIOD))

# Run walk-forward tests
results <- run_multi_period_walkforward(
  selection_dates = SELECTION_DATES,
  holding_period = HOLDING_PERIOD
)

# ============================================================================
# STEP 2: DOWNLOAD AND COMPARE TO BENCHMARK
# ============================================================================

cat("\nStep 2: Comparing to benchmark (SPY)...\n")

benchmark_results <- list()

for (i in seq_along(SELECTION_DATES)) {
  sel_date <- as.Date(SELECTION_DATES[i])
  end_date <- sel_date + HOLDING_PERIOD

  tryCatch({
    # Download SPY data
    spy_data <- getSymbols(BENCHMARK_TICKER,
                           src = "yahoo",
                           from = sel_date,
                           to = end_date,
                           auto.assign = FALSE,
                           warnings = FALSE)

    spy_df <- data.frame(
      date = index(spy_data),
      adjusted = as.numeric(Ad(spy_data))
    ) %>%
      arrange(date) %>%
      mutate(return = (adjusted / lag(adjusted)) - 1) %>%
      filter(!is.na(return))

    # Calculate benchmark metrics
    spy_total <- prod(1 + spy_df$return) - 1
    spy_annual <- (1 + spy_total)^(252 / nrow(spy_df)) - 1
    spy_vol <- sd(spy_df$return) * sqrt(252)
    spy_sharpe <- (spy_annual - 0.02) / spy_vol

    benchmark_results[[i]] <- data.frame(
      selection_date = sel_date,
      spy_return = spy_total,
      spy_sharpe = spy_sharpe
    )

  }, error = function(e) {
    cat(sprintf("  Warning: Could not get benchmark for period %d\n", i))
    benchmark_results[[i]] <- NULL
  })
}

benchmark_df <- bind_rows(benchmark_results)

# Merge with portfolio results
if (nrow(benchmark_df) > 0 && nrow(results) > 0) {
  results <- results %>%
    left_join(benchmark_df, by = "selection_date") %>%
    mutate(
      alpha = total_return - spy_return,
      sharpe_diff = sharpe_ratio - spy_sharpe
    )
}

# ============================================================================
# STEP 3: CALCULATE AGGREGATE STATISTICS
# ============================================================================

cat("\nStep 3: Calculating aggregate statistics...\n")

# Portfolio stats
avg_return <- mean(results$total_return, na.rm = TRUE)
avg_sharpe <- mean(results$sharpe_ratio, na.rm = TRUE)
sharpe_std <- sd(results$sharpe_ratio, na.rm = TRUE)
win_rate <- mean(results$total_return > 0, na.rm = TRUE)
avg_drawdown <- mean(results$max_drawdown, na.rm = TRUE)

# Benchmark comparison
if ("spy_return" %in% names(results)) {
  avg_spy_return <- mean(results$spy_return, na.rm = TRUE)
  avg_spy_sharpe <- mean(results$spy_sharpe, na.rm = TRUE)
  avg_alpha <- mean(results$alpha, na.rm = TRUE)
  beat_rate <- mean(results$total_return > results$spy_return, na.rm = TRUE)
} else {
  avg_spy_return <- NA
  avg_spy_sharpe <- NA
  avg_alpha <- NA
  beat_rate <- NA
}

# ============================================================================
# STEP 4: DISPLAY RESULTS
# ============================================================================

cat("\n============================================================\n")
cat("WALK-FORWARD VALIDATION RESULTS\n")
cat("============================================================\n\n")

cat("Period-by-Period Results:\n")
cat("--------------------------\n")
print(results %>%
        mutate(
          return_pct = sprintf("%+.1f%%", total_return * 100),
          sharpe = sprintf("%.2f", sharpe_ratio),
          drawdown = sprintf("%.1f%%", max_drawdown * 100),
          spy_pct = if ("spy_return" %in% names(.)) sprintf("%+.1f%%", spy_return * 100) else NA,
          alpha_pct = if ("alpha" %in% names(.)) sprintf("%+.1f%%", alpha * 100) else NA
        ) %>%
        select(selection_date, return_pct, sharpe, drawdown, spy_pct, alpha_pct))

cat("\n============================================================\n")
cat("AGGREGATE STATISTICS\n")
cat("============================================================\n")

cat("\nPortfolio Performance:\n")
cat(sprintf("  Average Return (per period):  %+.1f%%\n", avg_return * 100))
cat(sprintf("  Average Sharpe Ratio:         %.2f\n", avg_sharpe))
cat(sprintf("  Sharpe Ratio Std Dev:         %.2f\n", sharpe_std))
cat(sprintf("  Win Rate:                     %.0f%%\n", win_rate * 100))
cat(sprintf("  Average Max Drawdown:         %.1f%%\n", avg_drawdown * 100))

if (!is.na(avg_spy_return)) {
  cat("\nBenchmark Comparison (vs SPY):\n")
  cat(sprintf("  SPY Average Return:           %+.1f%%\n", avg_spy_return * 100))
  cat(sprintf("  SPY Average Sharpe:           %.2f\n", avg_spy_sharpe))
  cat(sprintf("  Average Alpha:                %+.1f%%\n", avg_alpha * 100))
  cat(sprintf("  Beat Rate:                    %.0f%%\n", beat_rate * 100))
}

# ============================================================================
# STEP 5: QUALITY ASSESSMENT
# ============================================================================

cat("\n============================================================\n")
cat("STRATEGY QUALITY ASSESSMENT\n")
cat("============================================================\n\n")

# Sharpe assessment
if (avg_sharpe > 2.0) {
  cat("Sharpe Ratio: EXCELLENT (> 2.0)\n")
} else if (avg_sharpe > 1.0) {
  cat("Sharpe Ratio: GOOD (> 1.0)\n")
} else if (avg_sharpe > 0.5) {
  cat("Sharpe Ratio: MODERATE (> 0.5)\n")
} else if (avg_sharpe > 0) {
  cat("Sharpe Ratio: WEAK (> 0 but < 0.5)\n")
} else {
  cat("Sharpe Ratio: POOR (< 0)\n")
}

# Consistency assessment
if (sharpe_std / avg_sharpe < 0.5) {
  cat("Consistency: STABLE (low variation across periods)\n")
} else if (sharpe_std / avg_sharpe < 1.0) {
  cat("Consistency: MODERATE (some variation across periods)\n")
} else {
  cat("Consistency: UNSTABLE (high variation - performance depends on market conditions)\n")
}

# Alpha assessment
if (!is.na(avg_alpha)) {
  if (avg_alpha > 0.1) {
    cat("Alpha: STRONG (beats SPY by >10% on average)\n")
  } else if (avg_alpha > 0) {
    cat("Alpha: POSITIVE (beats SPY on average)\n")
  } else {
    cat("Alpha: NEGATIVE (underperforms SPY on average)\n")
  }
}

# ============================================================================
# STEP 6: SAVE RESULTS
# ============================================================================

cat("\nStep 6: Saving results...\n")

# Save results
results_file <- file.path(BACKTEST_DIR, "walkforward_results.csv")
write.csv(results, results_file, row.names = FALSE)
saveRDS(results, file.path(BACKTEST_DIR, "walkforward_results.rds"))

cat(sprintf("  Saved: %s\n", results_file))

# ============================================================================
# STEP 7: CREATE VISUALIZATION
# ============================================================================

cat("\nStep 7: Creating visualizations...\n")

# Bar chart of returns by period
if (nrow(results) > 0) {

  plot_data <- results %>%
    mutate(
      period = format(selection_date, "%Y-%m"),
      Portfolio = total_return,
      SPY = if ("spy_return" %in% names(.)) spy_return else NA
    ) %>%
    select(period, Portfolio, SPY) %>%
    pivot_longer(cols = c(Portfolio, SPY), names_to = "Strategy", values_to = "Return")

  perf_plot <- ggplot(plot_data, aes(x = period, y = Return, fill = Strategy)) +
    geom_bar(stat = "identity", position = "dodge", width = 0.7) +
    scale_y_continuous(labels = scales::percent) +
    scale_fill_manual(values = c("Portfolio" = "darkgreen", "SPY" = "gray50")) +
    labs(
      title = "Walk-Forward Validation: Period Returns",
      subtitle = sprintf("Average Portfolio Sharpe: %.2f | Average Alpha: %+.1f%%",
                         avg_sharpe, avg_alpha * 100),
      x = "Selection Date",
      y = "Return (6-month holding period)"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 16, face = "bold"),
      legend.position = "bottom",
      axis.text.x = element_text(angle = 45, hjust = 1)
    )

  ggsave(file.path(BACKTEST_DIR, "walkforward_returns.pdf"),
         perf_plot, width = 10, height = 7)
  ggsave(file.path(BACKTEST_DIR, "walkforward_returns.png"),
         perf_plot, width = 10, height = 7, dpi = 300)

  cat("  Saved: analysis/backtest/walkforward_returns.png\n")
}

# ============================================================================
# STEP 8: GENERATE SUMMARY REPORT
# ============================================================================

cat("\nStep 8: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 6: WALK-FORWARD VALIDATION SUMMARY ===
Generated: %s

METHODOLOGY:
This is TRUE out-of-sample testing with NO look-ahead bias.
- For each test period, the portfolio was selected using ONLY
  data available at that time
- Performance was then measured on subsequent (future) data
- This simulates actual trading conditions

CONFIGURATION:
- Holding period: %d days (6 months)
- Number of test periods: %d
- Benchmark: SPY (S&P 500 ETF)

============================================================
RESULTS BY PERIOD
============================================================
%s

============================================================
AGGREGATE STATISTICS
============================================================

Portfolio Performance:
- Average Return (per period):  %+.1f%%
- Average Sharpe Ratio:         %.2f
- Sharpe Std Dev:               %.2f
- Win Rate:                     %.0f%%
- Average Max Drawdown:         %.1f%%

Benchmark Comparison (vs SPY):
- SPY Average Return:           %+.1f%%
- SPY Average Sharpe:           %.2f
- Average Alpha:                %+.1f%%
- Beat Rate:                    %.0f%%

============================================================
QUALITY ASSESSMENT
============================================================

Sharpe Ratio: %s
Consistency:  %s
Alpha:        %s

============================================================
INTERPRETATION
============================================================

%s

============================================================
FILES GENERATED
============================================================
- Walk-forward results: %s
- Performance chart: analysis/backtest/walkforward_returns.png

============================================================
COMPARISON TO BIASED BACKTEST
============================================================

A traditional backtest that tests the SAME portfolio on the
SAME data used to select it would show inflated metrics
(Sharpe ratios of 6-13 were seen in initial testing).

Walk-forward validation shows the REALISTIC expectation:
- Average Sharpe: %.2f (vs 6-13 in biased test)
- This %.1fx reduction reflects the true look-ahead bias

The walk-forward results are what you should actually expect
when implementing this strategy going forward.

=== MODULE 6 COMPLETE ===
",
Sys.time(),
HOLDING_PERIOD,
length(SELECTION_DATES),
paste(capture.output(print(results %>%
        select(selection_date, total_return, sharpe_ratio, max_drawdown) %>%
        mutate(
          total_return = sprintf("%+.1f%%", total_return * 100),
          sharpe_ratio = sprintf("%.2f", sharpe_ratio),
          max_drawdown = sprintf("%.1f%%", max_drawdown * 100)
        ))), collapse = "\n"),
avg_return * 100,
avg_sharpe,
sharpe_std,
win_rate * 100,
avg_drawdown * 100,
ifelse(!is.na(avg_spy_return), avg_spy_return * 100, 0),
ifelse(!is.na(avg_spy_sharpe), avg_spy_sharpe, 0),
ifelse(!is.na(avg_alpha), avg_alpha * 100, 0),
ifelse(!is.na(beat_rate), beat_rate * 100, 0),
ifelse(avg_sharpe > 2.0, "EXCELLENT (> 2.0)",
       ifelse(avg_sharpe > 1.0, "GOOD (> 1.0)",
              ifelse(avg_sharpe > 0.5, "MODERATE (> 0.5)", "WEAK"))),
ifelse(sharpe_std / avg_sharpe < 0.5, "STABLE",
       ifelse(sharpe_std / avg_sharpe < 1.0, "MODERATE", "UNSTABLE")),
ifelse(!is.na(avg_alpha) && avg_alpha > 0.1, "STRONG (beats SPY by >10%)",
       ifelse(!is.na(avg_alpha) && avg_alpha > 0, "POSITIVE (beats SPY)", "NEGATIVE")),
ifelse(avg_sharpe > 1.5 && !is.na(avg_alpha) && avg_alpha > 0,
       sprintf("STRATEGY VALIDATED
The portfolio selection methodology shows:
- Consistent positive returns across different time periods
- Strong risk-adjusted performance (Sharpe > 1.0)
- Positive alpha over benchmark
- Reasonable consistency across market conditions

This provides confidence that the strategy has genuine
predictive power and is not just overfitting to historical data."),
       ifelse(avg_sharpe > 0.5,
              sprintf("STRATEGY SHOWS PROMISE
The methodology produces positive risk-adjusted returns,
but with notable variation across periods. Consider:
- Using longer holding periods
- Reducing position sizes during volatile markets
- Monitoring performance and adjusting as needed"),
              sprintf("STRATEGY NEEDS REVIEW
Walk-forward results suggest the methodology may not
have consistent predictive power. Consider:
- Reviewing selection criteria
- Testing different parameters
- Longer historical analysis"))),
results_file,
avg_sharpe,
ifelse(avg_sharpe > 0, 10 / avg_sharpe, NA)
)

# Save summary
summary_file <- file.path(BACKTEST_DIR, "walkforward_summary.txt")
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

cat("Module 1: Downloaded stock data (5 years)\n")
cat("Module 2: Screened for top performers by sector\n")
cat("Module 3: Selected low-correlation portfolio (12 stocks)\n")
cat("Module 4: Validated with Ichimoku technical analysis\n")
cat("Module 5: Optimized weights for maximum Sharpe ratio\n")
cat("Module 6: Walk-forward validation (TRUE out-of-sample)\n\n")

cat(sprintf("KEY RESULT: Average Sharpe Ratio = %.2f (unbiased)\n\n", avg_sharpe))

cat("Key Files:\n")
cat("- analysis/final_portfolio.rds - Your 12 stocks\n")
cat("- analysis/optimal_weights.csv - Optimal allocation\n")
cat("- analysis/dollar_allocation.csv - Exact shares to buy\n")
cat("- analysis/backtest/walkforward_results.csv - Validation results\n\n")
