# ============================================================================
# MODULE 4: ICHIMOKU TECHNICAL VALIDATION
# ============================================================================
# Validates portfolio stocks using Ichimoku Cloud technical analysis
# Following principles from: https://www.codingfinance.com/
#
# Inputs: Final 12 stocks from Module 3
# Outputs: Technical validation report with buy/hold/reconsider signals
#
# Author: Portfolio Optimization System
# Date: 2026-01-17

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("TTR", quietly = TRUE)) install.packages("TTR")
if (!require("gridExtra", quietly = TRUE)) install.packages("gridExtra")
library(TTR)
library(gridExtra)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 4: ICHIMOKU TECHNICAL VALIDATION ===\n\n")

# Ichimoku parameters (standard settings)
CONVERSION_PERIOD <- 9     # Tenkan-sen (Conversion Line)
BASE_PERIOD <- 26          # Kijun-sen (Base Line)
SPAN_B_PERIOD <- 52        # Senkou Span B (Leading Span B)
DISPLACEMENT <- 26         # Cloud displacement forward

# Evaluation thresholds
LOOKBACK_DAYS <- 100       # Days to analyze for trend

# Output directory
OUTPUT_DIR <- "analysis"
ICHIMOKU_DIR <- file.path(OUTPUT_DIR, "ichimoku")
VALIDATION_FILE <- file.path(OUTPUT_DIR, "ichimoku_validation.csv")
VALIDATION_RDS <- file.path(OUTPUT_DIR, "ichimoku_validation.rds")

# Create ichimoku directory
if (!dir.exists(ICHIMOKU_DIR)) {
  dir.create(ICHIMOKU_DIR, recursive = TRUE)
  cat("Created directory: analysis/ichimoku/\n\n")
}

# ============================================================================
# STEP 1: LOAD FINAL PORTFOLIO
# ============================================================================

cat("Step 1: Loading final portfolio from Module 3...\n")

# Load portfolio
portfolio <- readRDS(file.path(OUTPUT_DIR, "final_portfolio.rds"))

cat(sprintf("  Portfolio stocks: %d\n", nrow(portfolio)))
cat("\n  Stocks to analyze:\n")
print(portfolio %>% select(ticker, sector, cumulative_return_1y, sharpe_ratio))

# ============================================================================
# STEP 2: CALCULATE ICHIMOKU INDICATORS
# ============================================================================

cat("\nStep 2: Calculating Ichimoku Cloud indicators...\n\n")

# Function to calculate Ichimoku indicators
calculate_ichimoku <- function(stock_data) {

  # Ensure sorted by date
  stock_data <- stock_data %>% arrange(date)

  # High and Low prices
  high <- stock_data$high
  low <- stock_data$low
  close <- stock_data$close

  # Conversion Line (Tenkan-sen): (9-period high + 9-period low) / 2
  conversion_high <- runMax(high, n = CONVERSION_PERIOD)
  conversion_low <- runMin(low, n = CONVERSION_PERIOD)
  conversion_line <- (conversion_high + conversion_low) / 2

  # Base Line (Kijun-sen): (26-period high + 26-period low) / 2
  base_high <- runMax(high, n = BASE_PERIOD)
  base_low <- runMin(low, n = BASE_PERIOD)
  base_line <- (base_high + base_low) / 2

  # Leading Span A (Senkou Span A): (Conversion + Base) / 2, shifted 26 days forward
  span_a <- (conversion_line + base_line) / 2

  # Leading Span B (Senkou Span B): (52-period high + 52-period low) / 2, shifted 26 days forward
  span_b_high <- runMax(high, n = SPAN_B_PERIOD)
  span_b_low <- runMin(low, n = SPAN_B_PERIOD)
  span_b <- (span_b_high + span_b_low) / 2

  # Lagging Span (Chikou Span): Close price shifted 26 days backward
  # (We'll handle this in plotting)

  # Add to dataframe
  stock_data$conversion_line <- conversion_line
  stock_data$base_line <- base_line
  stock_data$span_a <- span_a
  stock_data$span_b <- span_b

  return(stock_data)
}

# Calculate Ichimoku for all portfolio stocks
ichimoku_data <- list()

for (i in 1:nrow(portfolio)) {
  ticker <- portfolio$ticker[i]

  cat(sprintf("  [%d/%d] Processing %s...\n", i, nrow(portfolio), ticker))

  # Load stock data
  stock_data <- load_stock(ticker)

  if (is.null(stock_data)) {
    warning(sprintf("Could not load data for %s", ticker))
    next
  }

  # Calculate Ichimoku
  stock_data <- calculate_ichimoku(stock_data)
  stock_data$ticker <- ticker

  ichimoku_data[[ticker]] <- stock_data
}

cat(sprintf("\n  Successfully calculated Ichimoku for %d stocks\n", length(ichimoku_data)))

# ============================================================================
# STEP 3: EVALUATE ICHIMOKU SIGNALS
# ============================================================================

cat("\nStep 3: Evaluating Ichimoku signals...\n\n")

# Function to evaluate Ichimoku signal
evaluate_ichimoku <- function(stock_data, ticker) {

  # Get recent data (last 100 days)
  recent <- stock_data %>% tail(LOOKBACK_DAYS)

  if (nrow(recent) < 50) {
    return(list(
      ticker = ticker,
      signal = "Insufficient Data",
      score = NA,
      price_vs_cloud = NA,
      tk_cross = NA,
      cloud_color = NA,
      trend_strength = NA
    ))
  }

  # Latest values
  latest <- tail(recent, 1)
  price <- latest$close
  conversion <- latest$conversion_line
  base <- latest$base_line
  span_a <- latest$span_a
  span_b <- latest$span_b

  # Cloud top and bottom
  cloud_top <- max(span_a, span_b, na.rm = TRUE)
  cloud_bottom <- min(span_a, span_b, na.rm = TRUE)

  # Signal components
  signals <- list()

  # 1. Price vs Cloud position
  if (!is.na(price) && !is.na(cloud_top) && !is.na(cloud_bottom)) {
    if (price > cloud_top) {
      signals$price_vs_cloud <- "Above Cloud"
      signals$price_score <- 1
    } else if (price < cloud_bottom) {
      signals$price_vs_cloud <- "Below Cloud"
      signals$price_score <- -1
    } else {
      signals$price_vs_cloud <- "In Cloud"
      signals$price_score <- 0
    }
  } else {
    signals$price_vs_cloud <- "Unknown"
    signals$price_score <- 0
  }

  # 2. TK Cross (Conversion vs Base)
  if (!is.na(conversion) && !is.na(base)) {
    if (conversion > base) {
      signals$tk_cross <- "Bullish (TK > BL)"
      signals$tk_score <- 1
    } else if (conversion < base) {
      signals$tk_cross <- "Bearish (TK < BL)"
      signals$tk_score <- -1
    } else {
      signals$tk_cross <- "Neutral"
      signals$tk_score <- 0
    }
  } else {
    signals$tk_cross <- "Unknown"
    signals$tk_score <- 0
  }

  # 3. Cloud color (Span A vs Span B)
  if (!is.na(span_a) && !is.na(span_b)) {
    if (span_a > span_b) {
      signals$cloud_color <- "Green (Bullish)"
      signals$cloud_score <- 1
    } else if (span_a < span_b) {
      signals$cloud_color <- "Red (Bearish)"
      signals$cloud_score <- -1
    } else {
      signals$cloud_color <- "Neutral"
      signals$cloud_score <- 0
    }
  } else {
    signals$cloud_color <- "Unknown"
    signals$cloud_score <- 0
  }

  # 4. Trend strength (how far price is from cloud)
  if (!is.na(price) && !is.na(cloud_top) && !is.na(cloud_bottom)) {
    if (price > cloud_top) {
      distance_pct <- (price - cloud_top) / cloud_top
      signals$trend_strength <- sprintf("Strong Bullish (+%.1f%%)", 100 * distance_pct)
    } else if (price < cloud_bottom) {
      distance_pct <- (cloud_bottom - price) / price
      signals$trend_strength <- sprintf("Strong Bearish (-%.1f%%)", 100 * distance_pct)
    } else {
      signals$trend_strength <- "Weak/Consolidating"
    }
  } else {
    signals$trend_strength <- "Unknown"
  }

  # Calculate overall score (-3 to +3)
  total_score <- signals$price_score + signals$tk_score + signals$cloud_score

  # Overall signal
  if (total_score >= 2) {
    overall_signal <- "BULLISH"
  } else if (total_score <= -2) {
    overall_signal <- "BEARISH"
  } else {
    overall_signal <- "NEUTRAL"
  }

  return(list(
    ticker = ticker,
    signal = overall_signal,
    score = total_score,
    price_vs_cloud = signals$price_vs_cloud,
    tk_cross = signals$tk_cross,
    cloud_color = signals$cloud_color,
    trend_strength = signals$trend_strength
  ))
}

# Evaluate all stocks
evaluations <- list()

for (ticker in names(ichimoku_data)) {
  stock_data <- ichimoku_data[[ticker]]
  eval_result <- evaluate_ichimoku(stock_data, ticker)
  evaluations[[ticker]] <- eval_result

  cat(sprintf("  %s: %s (Score: %d)\n",
              ticker, eval_result$signal, eval_result$score))
}

# Convert to dataframe
validation_results <- bind_rows(evaluations)

# Merge with portfolio data
validation_full <- portfolio %>%
  left_join(validation_results, by = "ticker") %>%
  arrange(desc(score))

cat("\n  Evaluation complete.\n")

# ============================================================================
# STEP 4: GENERATE ICHIMOKU PLOTS
# ============================================================================

cat("\nStep 4: Generating Ichimoku charts...\n\n")

# Function to plot Ichimoku chart
plot_ichimoku <- function(stock_data, ticker, signal_info) {

  # Get recent 6 months for cleaner visualization
  recent <- stock_data %>% tail(126)

  if (nrow(recent) < 50) {
    cat(sprintf("  Skipping %s - insufficient data\n", ticker))
    return(NULL)
  }

  # Create plot filename
  plot_file <- file.path(ICHIMOKU_DIR, paste0(ticker, "_ichimoku.pdf"))

  pdf(plot_file, width = 12, height = 8)

  par(mfrow = c(1,1), mar = c(5, 4, 4, 2))

  # Price range
  y_range <- range(c(recent$close, recent$span_a, recent$span_b), na.rm = TRUE)

  # Main plot - Price
  plot(recent$date, recent$close, type = "l",
       ylim = y_range,
       main = sprintf("%s - Ichimoku Cloud (%s)", ticker, signal_info$signal),
       xlab = "Date", ylab = "Price",
       lwd = 2)

  # Cloud (filled polygon between Span A and Span B)
  # Green if Span A > Span B, Red otherwise
  for (i in 2:nrow(recent)) {
    if (!is.na(recent$span_a[i]) && !is.na(recent$span_b[i])) {

      cloud_color <- ifelse(recent$span_a[i] > recent$span_b[i],
                           rgb(0, 1, 0, alpha = 0.2),  # Green
                           rgb(1, 0, 0, alpha = 0.2))  # Red

      polygon(c(recent$date[i-1], recent$date[i], recent$date[i], recent$date[i-1]),
              c(recent$span_a[i-1], recent$span_a[i], recent$span_b[i], recent$span_b[i]),
              col = cloud_color, border = NA)
    }
  }

  # Conversion Line (Tenkan-sen) - Blue
  lines(recent$date, recent$conversion_line, col = "blue", lwd = 1.5)

  # Base Line (Kijun-sen) - Red
  lines(recent$date, recent$base_line, col = "red", lwd = 1.5)

  # Span A - Green dashed
  lines(recent$date, recent$span_a, col = "darkgreen", lty = 2)

  # Span B - Red dashed
  lines(recent$date, recent$span_b, col = "darkred", lty = 2)

  # Price line on top
  lines(recent$date, recent$close, col = "black", lwd = 2)

  # Legend
  legend("topleft",
         legend = c("Price", "Conversion (9)", "Base (26)", "Span A", "Span B", "Cloud"),
         col = c("black", "blue", "red", "darkgreen", "darkred", "gray"),
         lty = c(1, 1, 1, 2, 2, 1),
         lwd = c(2, 1.5, 1.5, 1, 1, 8),
         bg = "white")

  # Add signal info
  text(x = recent$date[10], y = y_range[2] * 0.95,
       labels = sprintf("Signal: %s\nScore: %d\n%s\n%s",
                       signal_info$signal,
                       signal_info$score,
                       signal_info$price_vs_cloud,
                       signal_info$tk_cross),
       adj = 0, cex = 0.9)

  dev.off()

  cat(sprintf("  Saved: %s\n", plot_file))
}

# Generate plots for all stocks
for (ticker in names(ichimoku_data)) {
  stock_data <- ichimoku_data[[ticker]]
  signal_info <- validation_results %>% filter(ticker == !!ticker)

  plot_ichimoku(stock_data, ticker, signal_info)
}

cat("\n  All Ichimoku charts saved to: analysis/ichimoku/\n")

# ============================================================================
# STEP 5: SAVE VALIDATION RESULTS
# ============================================================================

cat("\nStep 5: Saving validation results...\n")

# Save validation
write.csv(validation_full, VALIDATION_FILE, row.names = FALSE)
saveRDS(validation_full, VALIDATION_RDS)

cat(sprintf("  Saved CSV: %s\n", VALIDATION_FILE))
cat(sprintf("  Saved RDS: %s\n", VALIDATION_RDS))

# ============================================================================
# STEP 6: GENERATE RECOMMENDATIONS
# ============================================================================

cat("\nStep 6: Generating recommendations...\n\n")

# Categorize stocks
bullish <- validation_full %>% filter(signal == "BULLISH")
neutral <- validation_full %>% filter(signal == "NEUTRAL")
bearish <- validation_full %>% filter(signal == "BEARISH")

cat("  === SIGNAL SUMMARY ===\n")
cat(sprintf("  Bullish: %d stocks\n", nrow(bullish)))
cat(sprintf("  Neutral: %d stocks\n", nrow(neutral)))
cat(sprintf("  Bearish: %d stocks\n", nrow(bearish)))

# Detailed breakdown
cat("\n  BULLISH STOCKS (Strong Technical Confirmation):\n")
if (nrow(bullish) > 0) {
  print(bullish %>%
          select(ticker, sector, signal, score, price_vs_cloud, tk_cross) %>%
          as.data.frame(),
        row.names = FALSE)
} else {
  cat("    (None)\n")
}

cat("\n  NEUTRAL STOCKS (Mixed Signals):\n")
if (nrow(neutral) > 0) {
  print(neutral %>%
          select(ticker, sector, signal, score, price_vs_cloud, tk_cross) %>%
          as.data.frame(),
        row.names = FALSE)
} else {
  cat("    (None)\n")
}

cat("\n  BEARISH STOCKS (Concerning Technical Signals):\n")
if (nrow(bearish) > 0) {
  print(bearish %>%
          select(ticker, sector, signal, score, price_vs_cloud, tk_cross) %>%
          as.data.frame(),
        row.names = FALSE)

  cat("\n  ⚠ RECOMMENDATION: Consider reviewing bearish stocks:\n")
  cat("    - Check recent news/fundamentals\n")
  cat("    - Review correlation with other portfolio stocks\n")
  cat("    - Consider replacement candidates from Module 2\n")
} else {
  cat("    (None)\n")
}

# Portfolio health score
health_score <- sum(validation_full$score, na.rm = TRUE) / nrow(validation_full)
cat(sprintf("\n  Portfolio Technical Health Score: %.2f (out of 3.0)\n", health_score))

if (health_score >= 1.5) {
  cat("  ✓ Portfolio shows strong technical momentum\n")
} else if (health_score >= 0) {
  cat("  ~ Portfolio shows mixed technical signals\n")
} else {
  cat("  ⚠ Portfolio shows weak technical momentum - consider review\n")
}

# ============================================================================
# STEP 7: CREATE SUMMARY REPORT
# ============================================================================

cat("\nStep 7: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 4: ICHIMOKU TECHNICAL VALIDATION SUMMARY ===
Generated: %s

ICHIMOKU PARAMETERS:
- Conversion Line (Tenkan-sen): %d periods
- Base Line (Kijun-sen): %d periods
- Leading Span B (Senkou Span B): %d periods
- Displacement: %d periods

PORTFOLIO ANALYSIS:
- Total stocks validated: %d
- Bullish signals: %d
- Neutral signals: %d
- Bearish signals: %d
- Portfolio health score: %.2f / 3.0

SIGNAL BREAKDOWN:

BULLISH STOCKS:
%s

NEUTRAL STOCKS:
%s

BEARISH STOCKS:
%s

RECOMMENDATIONS:
%s

ICHIMOKU INTERPRETATION GUIDE:
- Bullish: Price above cloud, Conversion > Base, Green cloud
- Neutral: Mixed signals, price near cloud
- Bearish: Price below cloud, Conversion < Base, Red cloud

FILES GENERATED:
- Validation results: %s
- Ichimoku charts: %s (PDF for each stock)

NEXT STEPS:
- Review bearish stocks (if any)
- Consider replacements from candidate list if needed
- Proceed to Module 5: Portfolio Optimization
",
Sys.time(),
CONVERSION_PERIOD,
BASE_PERIOD,
SPAN_B_PERIOD,
DISPLACEMENT,
nrow(validation_full),
nrow(bullish),
nrow(neutral),
nrow(bearish),
health_score,
ifelse(nrow(bullish) > 0,
       paste(capture.output(print(bullish %>%
                                  select(ticker, sector, score, cumulative_return_1y) %>%
                                  as.data.frame(), row.names = FALSE)),
             collapse = "\n"),
       "(None)"),
ifelse(nrow(neutral) > 0,
       paste(capture.output(print(neutral %>%
                                  select(ticker, sector, score, cumulative_return_1y) %>%
                                  as.data.frame(), row.names = FALSE)),
             collapse = "\n"),
       "(None)"),
ifelse(nrow(bearish) > 0,
       paste(capture.output(print(bearish %>%
                                  select(ticker, sector, score, cumulative_return_1y) %>%
                                  as.data.frame(), row.names = FALSE)),
             collapse = "\n"),
       "(None)"),
ifelse(nrow(bearish) > 0,
       sprintf("⚠ %d stocks show bearish signals. Review these stocks:
  - Examine recent price action and news
  - Check if temporary dip or longer-term trend
  - Consider replacement candidates from Module 2 analysis/candidate_stocks.csv
  - Bearish signals don't always mean sell - use judgment", nrow(bearish)),
       "✓ No bearish signals detected. Portfolio shows positive technical momentum."),
VALIDATION_FILE,
ICHIMOKU_DIR
)

# Save summary
summary_file <- file.path(OUTPUT_DIR, "module_4_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 4 COMPLETE ===\n")
cat(sprintf("Next step: Proceed to Module 5 for portfolio optimization\n\n"))

# ============================================================================
# USAGE EXAMPLE FOR NEXT STEPS
# ============================================================================

cat("=== QUICK REFERENCE ===\n")
cat("# Load validation results:\n")
cat("validation <- readRDS('analysis/ichimoku_validation.rds')\n\n")
cat("# View bullish stocks:\n")
cat("validation %>% filter(signal == 'BULLISH')\n\n")
cat("# View bearish stocks that may need review:\n")
cat("validation %>% filter(signal == 'BEARISH')\n\n")
cat("# Get replacement candidates if needed:\n")
cat("candidates <- readRDS('analysis/candidate_stocks.rds')\n")
cat("replacements <- candidates %>% filter(!ticker %in% validation$ticker)\n\n")
