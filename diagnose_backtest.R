# ============================================================================
# DATA AVAILABILITY DIAGNOSTIC
# ============================================================================
# Checks which portfolio stocks have sufficient data for backtesting

source("utils_data_loader.R")

# Load portfolio
portfolio <- readRDS("analysis/final_portfolio.rds")
tickers <- portfolio$ticker

# Backtest period
TEST_START <- Sys.Date() - 180  # 6 months ago
TEST_END <- Sys.Date()

cat("=== DATA AVAILABILITY CHECK ===\n\n")
cat(sprintf("Backtest period: %s to %s\n\n", TEST_START, TEST_END))

# Check each stock
availability <- data.frame(
  ticker = character(),
  has_data = logical(),
  first_date = as.Date(character()),
  last_date = as.Date(character()),
  days_available = integer(),
  covers_backtest = logical(),
  stringsAsFactors = FALSE
)

for (ticker in tickers) {
  stock <- load_stock(ticker)

  if (is.null(stock)) {
    availability <- rbind(availability, data.frame(
      ticker = ticker,
      has_data = FALSE,
      first_date = as.Date(NA),
      last_date = as.Date(NA),
      days_available = 0,
      covers_backtest = FALSE
    ))
  } else {
    first <- min(stock$date)
    last <- max(stock$date)
    days <- nrow(stock)
    covers <- first <= TEST_START && last >= TEST_END

    availability <- rbind(availability, data.frame(
      ticker = ticker,
      has_data = TRUE,
      first_date = first,
      last_date = last,
      days_available = days,
      covers_backtest = covers
    ))
  }
}

# Print results
cat("Stock Data Availability:\n")
print(availability)

# Summary
cat(sprintf("\n\nSummary:\n"))
cat(sprintf("  Stocks with data: %d/%d\n",
            sum(availability$has_data), nrow(availability)))
cat(sprintf("  Stocks covering backtest period: %d/%d\n",
            sum(availability$covers_backtest), nrow(availability)))

# Stocks with insufficient data
insufficient <- availability %>% filter(!covers_backtest)

if (nrow(insufficient) > 0) {
  cat("\n⚠ PROBLEM STOCKS (insufficient data for backtest):\n")
  print(insufficient %>% select(ticker, first_date, last_date))

  cat("\nSOLUTION OPTIONS:\n")
  cat("1. Adjust backtest period to match available data\n")
  cat("2. Replace these stocks with alternatives from candidates\n")
  cat("3. Run backtest only on stocks with sufficient data\n\n")

  # Show available stocks
  sufficient <- availability %>% filter(covers_backtest)
  if (nrow(sufficient) > 0) {
    cat(sprintf("Stocks with sufficient data (%d):\n", nrow(sufficient)))
    cat(paste(sufficient$ticker, collapse = ", "), "\n")
  }

  # Calculate new backtest period
  earliest_last <- max(availability$first_date, na.rm = TRUE)
  cat(sprintf("\nAdjusted backtest period suggestion:\n"))
  cat(sprintf("  Start: %s (earliest common date)\n", earliest_last))
  cat(sprintf("  End: %s (today)\n", TEST_END))
}

cat("\n")
