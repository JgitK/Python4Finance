#!/usr/bin/env Rscript
# ============================================================================
# Export Ichimoku Data for Web App
# ============================================================================
# This script exports price data with Ichimoku indicators for all portfolio
# and bench stocks so the web app can display interactive charts.

library(dplyr)
library(TTR)

cat("============================================================\n")
cat("EXPORTING ICHIMOKU DATA FOR WEB APP\n")
cat("============================================================\n\n")

# Set working directory
setwd("/Users/jackson/Desktop/Python4Finance")

# Load data loader utility
source("utils_data_loader.R")

# Output directory
OUTPUT_DIR <- "webapp/db/seed_data/ichimoku"
dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)

# Ichimoku parameters (standard settings)
CONVERSION_PERIOD <- 9     # Tenkan-sen
BASE_PERIOD <- 26          # Kijun-sen
SPAN_B_PERIOD <- 52        # Senkou Span B
DISPLACEMENT <- 26         # Cloud displacement

# ============================================================================
# Function to calculate Ichimoku indicators
# ============================================================================
calculate_ichimoku <- function(stock_data) {

  stock_data <- stock_data %>% arrange(date)

  high <- stock_data$high
  low <- stock_data$low
  close <- stock_data$close

  # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
  conversion_high <- runMax(high, n = CONVERSION_PERIOD)
  conversion_low <- runMin(low, n = CONVERSION_PERIOD)
  tenkan_sen <- (conversion_high + conversion_low) / 2

  # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
  base_high <- runMax(high, n = BASE_PERIOD)
  base_low <- runMin(low, n = BASE_PERIOD)
  kijun_sen <- (base_high + base_low) / 2

  # Senkou Span A: (Tenkan + Kijun) / 2
  senkou_span_a <- (tenkan_sen + kijun_sen) / 2

  # Senkou Span B: (52-period high + 52-period low) / 2
  span_b_high <- runMax(high, n = SPAN_B_PERIOD)
  span_b_low <- runMin(low, n = SPAN_B_PERIOD)
  senkou_span_b <- (span_b_high + span_b_low) / 2

  # Chikou Span: Close shifted 26 periods back (for display, we store close)
  # The frontend will handle the visual shift

  stock_data$tenkan_sen <- round(tenkan_sen, 4)
  stock_data$kijun_sen <- round(kijun_sen, 4)
  stock_data$senkou_span_a <- round(senkou_span_a, 4)
  stock_data$senkou_span_b <- round(senkou_span_b, 4)
  stock_data$chikou_span <- round(close, 4)  # Will be shifted in frontend

  return(stock_data)
}

# ============================================================================
# Get list of tickers to export (portfolio + bench)
# ============================================================================
cat("Loading portfolio and bench stocks...\n")

portfolio <- read.csv("webapp/db/seed_data/portfolio_stocks.csv", stringsAsFactors = FALSE)
bench <- read.csv("webapp/db/seed_data/bench_stocks.csv", stringsAsFactors = FALSE)

all_tickers <- c(portfolio$ticker, bench$ticker)
cat(sprintf("  Total stocks to export: %d\n\n", length(all_tickers)))

# ============================================================================
# Export Ichimoku data for each stock
# ============================================================================
cat("Calculating and exporting Ichimoku data...\n\n")

successful <- 0
failed <- 0

for (ticker in all_tickers) {
  cat(sprintf("  Processing %s...", ticker))

  # Load stock data
  stock_data <- tryCatch({
    load_stock(ticker)
  }, error = function(e) {
    NULL
  })

  if (is.null(stock_data) || nrow(stock_data) < 60) {
    cat(" SKIPPED (insufficient data)\n")
    failed <- failed + 1
    next
  }

  # Calculate Ichimoku
  stock_data <- calculate_ichimoku(stock_data)

  # Select only what we need for the web app (last 252 trading days = ~1 year)
  export_data <- stock_data %>%
    tail(252) %>%
    select(
      date,
      open = open,
      high = high,
      low = low,
      close = close,
      volume = volume,
      tenkan_sen,
      kijun_sen,
      senkou_span_a,
      senkou_span_b,
      chikou_span
    )

  # Export to CSV
  output_file <- file.path(OUTPUT_DIR, paste0(ticker, ".csv"))
  write.csv(export_data, output_file, row.names = FALSE)

  cat(sprintf(" OK (%d rows)\n", nrow(export_data)))
  successful <- successful + 1
}

# ============================================================================
# Summary
# ============================================================================
cat("\n============================================================\n")
cat("EXPORT COMPLETE\n")
cat("============================================================\n")
cat(sprintf("  Successful: %d stocks\n", successful))
cat(sprintf("  Failed: %d stocks\n", failed))
cat(sprintf("  Output directory: %s\n", OUTPUT_DIR))
cat("\nThese CSV files contain OHLC + Ichimoku indicators for charting.\n")
