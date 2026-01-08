# Quick Test Script - Run this to verify everything works
# This tests the core functions without requiring the full Shiny app

cat("═══════════════════════════════════════════════════\n")
cat("  Quick Test - R Portfolio Optimization App\n")
cat("═══════════════════════════════════════════════════\n\n")

# Test 1: Check if required packages are installed
cat("Test 1: Checking required packages...\n")

required <- c("quantmod", "tidyverse", "plotly", "xts")
installed <- sapply(required, requireNamespace, quietly = TRUE)

if (all(installed)) {
  cat("✓ All core packages are installed!\n\n")
} else {
  cat("✗ Some packages missing. Run: source('setup.R')\n\n")
  cat("Missing packages:\n")
  print(required[!installed])
  stop("Please install missing packages first")
}

# Test 2: Load functions
cat("Test 2: Loading functions...\n")
tryCatch({
  source("download_stocks.R")
  source("portfolio_optimization.R")
  source("ichimoku_analysis.R")
  cat("✓ All functions loaded successfully!\n\n")
}, error = function(e) {
  cat("✗ Error loading functions:", e$message, "\n")
  stop()
})

# Test 3: Download sample stock data
cat("Test 3: Downloading sample stock data (AAPL)...\n")
tryCatch({
  test_data <- download_single_stock("AAPL",
                                     from = Sys.Date() - 30,
                                     to = Sys.Date())
  if (!is.null(test_data) && nrow(test_data) > 0) {
    cat("✓ Successfully downloaded", nrow(test_data), "days of data for AAPL\n\n")
  } else {
    cat("✗ Download returned no data\n\n")
  }
}, error = function(e) {
  cat("✗ Download failed:", e$message, "\n")
  cat("  (This is normal if you don't have internet access)\n\n")
})

# Test 4: Check for Wilshire stocks file
cat("Test 4: Checking for Wilshire stocks file...\n")
if (file.exists("Wilshire-5000-Stocks.csv")) {
  stocks <- read.csv("Wilshire-5000-Stocks.csv")
  cat("✓ Found Wilshire stocks file with", nrow(stocks), "stocks\n\n")
} else {
  cat("⚠ Wilshire-5000-Stocks.csv not found\n")
  cat("  App will still work, but stock selection will be limited\n\n")
}

cat("═══════════════════════════════════════════════════\n")
cat("  ✓ Tests Complete!\n")
cat("═══════════════════════════════════════════════════\n\n")

cat("Next steps:\n")
cat("  1. If all tests passed, run: shiny::runApp('app.R')\n")
cat("  2. Or try examples: source('example_usage.R')\n")
cat("  3. Read the guide: QUICK_START.md\n\n")
