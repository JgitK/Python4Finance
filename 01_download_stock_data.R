# ============================================================================
# MODULE 1: STOCK DATA ACQUISITION
# ============================================================================
# Downloads historical stock data by sector with error handling and resume capability
# Following principles from: https://www.codingfinance.com/
#
# Author: Portfolio Optimization System
# Date: 2026-01-16

# Required packages
required_packages <- c("dplyr", "quantmod", "readr", "lubridate", "stringr", "purrr")
for (pkg in required_packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg)
    library(pkg, character.only = TRUE)
  }
}

# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths
TICKER_SOURCE <- "data/Nasdaq Stock Screener.csv"  # Primary source
TICKER_FALLBACK <- "Nasdaq.csv"                    # Fallback if primary not found
SECTOR_DATA <- "big_stock_sectors.csv"             # Sector classifications

# Download parameters
LOOKBACK_YEARS <- 5                                 # Years of historical data
MIN_VOLUME <- 100000                                # Minimum avg daily volume
MIN_MARKET_CAP <- 500e6                            # Minimum market cap ($500M)
RETRY_ATTEMPTS <- 3                                # Number of retry attempts
RETRY_DELAY <- 2                                   # Seconds between retries

# Output directories
STOCKS_DIR <- "stocks"
METADATA_DIR <- "metadata"
DATA_DIR <- "data"

# ============================================================================
# STEP 1: SETUP DIRECTORY STRUCTURE
# ============================================================================

cat("\n=== MODULE 1: STOCK DATA ACQUISITION ===\n\n")
cat("Step 1: Creating directory structure...\n")

# Create directories if they don't exist
for (dir in c(DATA_DIR, STOCKS_DIR, METADATA_DIR)) {
  if (!dir.exists(dir)) {
    dir.create(dir, recursive = TRUE)
    cat(sprintf("  Created: %s/\n", dir))
  } else {
    cat(sprintf("  Exists: %s/\n", dir))
  }
}

# ============================================================================
# STEP 2: LOAD TICKER DATA
# ============================================================================

cat("\nStep 2: Loading ticker data...\n")

# Try to load Nasdaq Stock Screener first
if (file.exists(TICKER_SOURCE)) {
  cat(sprintf("  Loading: %s\n", TICKER_SOURCE))
  tickers_raw <- read_csv(TICKER_SOURCE, show_col_types = FALSE)

  # Standardize column names (handle different screener formats)
  names(tickers_raw) <- tolower(names(tickers_raw))

  # Map common column variations
  if ("symbol" %in% names(tickers_raw)) {
    tickers_raw <- tickers_raw %>% rename(ticker = symbol)
  }
  if ("name" %in% names(tickers_raw)) {
    tickers_raw <- tickers_raw %>% rename(company = name)
  }

} else if (file.exists(TICKER_FALLBACK)) {
  cat(sprintf("  Primary source not found. Loading fallback: %s\n", TICKER_FALLBACK))
  tickers_raw <- read_csv(TICKER_FALLBACK, show_col_types = FALSE)

  # Standardize column names
  names(tickers_raw) <- tolower(names(tickers_raw))
  if ("symbol" %in% names(tickers_raw)) {
    tickers_raw <- tickers_raw %>% rename(ticker = symbol)
  }

  # Load sector data separately
  if (file.exists(SECTOR_DATA)) {
    cat("  Loading sector data...\n")
    sectors <- read_csv(SECTOR_DATA, show_col_types = FALSE) %>%
      rename(ticker = Ticker, sector = Sector) %>%
      select(ticker, sector)

    tickers_raw <- tickers_raw %>%
      left_join(sectors, by = "ticker")
  }
} else {
  stop(sprintf("Error: Could not find ticker data. Please ensure either:\n  - %s exists, OR\n  - %s exists",
               TICKER_SOURCE, TICKER_FALLBACK))
}

cat(sprintf("  Loaded %d tickers\n", nrow(tickers_raw)))

# ============================================================================
# STEP 3: PRE-FILTER TICKERS
# ============================================================================

cat("\nStep 3: Applying pre-filters...\n")

# Get initial count
initial_count <- nrow(tickers_raw)

# Ensure we have a ticker column
if (!"ticker" %in% names(tickers_raw)) {
  stop("Error: Could not find 'ticker' or 'symbol' column in data")
}

# Basic cleaning
tickers_filtered <- tickers_raw %>%
  # Remove NA tickers
  filter(!is.na(ticker), ticker != "") %>%
  # Remove duplicates
  distinct(ticker, .keep_all = TRUE) %>%
  # Remove likely ETFs/funds (common patterns)
  filter(!str_detect(ticker, "\\^")) %>%  # Index symbols
  filter(!str_detect(ticker, "\\-")) %>%  # Multi-class shares
  filter(str_length(ticker) <= 5)         # Normal ticker length

cat(sprintf("  After basic cleaning: %d tickers\n", nrow(tickers_filtered)))

# Apply market cap filter if available
if ("market cap" %in% names(tickers_filtered) | "marketcap" %in% names(tickers_filtered)) {
  mcap_col <- ifelse("market cap" %in% names(tickers_filtered), "market cap", "marketcap")

  tickers_filtered <- tickers_filtered %>%
    filter(!is.na(.data[[mcap_col]])) %>%
    filter(.data[[mcap_col]] >= MIN_MARKET_CAP)

  cat(sprintf("  After market cap filter (>$%.0fM): %d tickers\n",
              MIN_MARKET_CAP / 1e6, nrow(tickers_filtered)))
}

# Apply volume filter if available
if ("volume" %in% names(tickers_filtered)) {
  tickers_filtered <- tickers_filtered %>%
    filter(!is.na(volume)) %>%
    filter(volume >= MIN_VOLUME)

  cat(sprintf("  After volume filter (>%s): %d tickers\n",
              format(MIN_VOLUME, big.mark = ","), nrow(tickers_filtered)))
}

cat(sprintf("  Filtered: %d → %d tickers (%.1f%% reduction)\n",
            initial_count, nrow(tickers_filtered),
            100 * (1 - nrow(tickers_filtered) / initial_count)))

# ============================================================================
# STEP 4: ORGANIZE BY SECTOR
# ============================================================================

cat("\nStep 4: Organizing tickers by sector...\n")

# Check if we have sector data
if ("sector" %in% names(tickers_filtered)) {
  # Clean and standardize sector names
  tickers_filtered <- tickers_filtered %>%
    mutate(
      sector = case_when(
        is.na(sector) ~ "Unknown",
        sector == "" ~ "Unknown",
        TRUE ~ str_trim(sector)
      )
    )

  # Group by sector
  by_sector <- tickers_filtered %>%
    group_by(sector) %>%
    summarise(count = n(), .groups = "drop") %>%
    arrange(desc(count))

  cat("\n  Sector Distribution:\n")
  print(as.data.frame(by_sector), row.names = FALSE)

} else {
  cat("  WARNING: No sector data available. All stocks will be in 'Unknown' sector.\n")
  tickers_filtered <- tickers_filtered %>%
    mutate(sector = "Unknown")

  by_sector <- tibble(sector = "Unknown", count = nrow(tickers_filtered))
}

# Save filtered ticker list
ticker_list_file <- file.path(METADATA_DIR, "filtered_tickers.csv")
write_csv(tickers_filtered, ticker_list_file)
cat(sprintf("\n  Saved filtered ticker list: %s\n", ticker_list_file))

# ============================================================================
# STEP 5: DOWNLOAD FUNCTION WITH ERROR HANDLING
# ============================================================================

cat("\nStep 5: Preparing download function...\n")

# Function to download single stock with retries
download_stock <- function(ticker, start_date, end_date, attempt = 1) {

  tryCatch({
    # Download from Yahoo Finance
    data <- getSymbols(
      Symbols = ticker,
      src = "yahoo",
      from = start_date,
      to = end_date,
      auto.assign = FALSE,
      warnings = FALSE
    )

    # Convert to data frame
    df <- data.frame(
      date = index(data),
      open = as.numeric(Op(data)),
      high = as.numeric(Hi(data)),
      low = as.numeric(Lo(data)),
      close = as.numeric(Cl(data)),
      volume = as.numeric(Vo(data)),
      adjusted = as.numeric(Ad(data))
    )

    # Data validation
    if (nrow(df) < 400) {  # Less than ~2 years of data
      return(list(success = FALSE, error = "Insufficient data", data = NULL))
    }

    if (any(df$close <= 0, na.rm = TRUE)) {
      return(list(success = FALSE, error = "Invalid prices", data = NULL))
    }

    if (sum(is.na(df$close)) / nrow(df) > 0.1) {  # More than 10% missing
      return(list(success = FALSE, error = "Too much missing data", data = NULL))
    }

    # Success
    return(list(success = TRUE, error = NA, data = df))

  }, error = function(e) {

    # Retry logic
    if (attempt < RETRY_ATTEMPTS) {
      Sys.sleep(RETRY_DELAY * attempt)  # Exponential backoff
      return(download_stock(ticker, start_date, end_date, attempt + 1))
    } else {
      return(list(success = FALSE, error = as.character(e$message), data = NULL))
    }
  })
}

# ============================================================================
# STEP 6: DOWNLOAD BY SECTOR
# ============================================================================

cat("\nStep 6: Downloading stock data by sector...\n")
cat(sprintf("  Historical period: %s to %s (%d years)\n",
            format(Sys.Date() - years(LOOKBACK_YEARS)),
            format(Sys.Date()),
            LOOKBACK_YEARS))

# Calculate date range
end_date <- Sys.Date()
start_date <- end_date - years(LOOKBACK_YEARS)

# Initialize download log
download_log <- tibble(
  ticker = character(),
  sector = character(),
  success = logical(),
  error = character(),
  rows = integer(),
  download_time = character()
)

# Check for existing downloads (resume capability)
existing_files <- list.files(STOCKS_DIR, pattern = "\\.rds$")
existing_tickers <- str_remove(existing_files, "\\.rds$")

cat(sprintf("\n  Found %d existing downloads. These will be skipped.\n",
            length(existing_tickers)))

# Process each sector
sectors_list <- unique(tickers_filtered$sector)
total_tickers <- nrow(tickers_filtered)
downloaded <- 0
skipped <- 0
failed <- 0

for (sector_name in sectors_list) {

  cat(sprintf("\n--- Processing Sector: %s ---\n", sector_name))

  # Get tickers for this sector
  sector_tickers <- tickers_filtered %>%
    filter(sector == sector_name) %>%
    pull(ticker)

  cat(sprintf("  Tickers in sector: %d\n", length(sector_tickers)))

  # Download each ticker in sector
  for (i in seq_along(sector_tickers)) {
    ticker <- sector_tickers[i]

    # Skip if already downloaded
    if (ticker %in% existing_tickers) {
      skipped <- skipped + 1
      if (i %% 10 == 0) {
        cat(sprintf("  Progress: %d/%d (skipped: %d)\n",
                    i, length(sector_tickers), skipped))
      }
      next
    }

    # Progress indicator
    cat(sprintf("  [%d/%d] Downloading %s... ", i, length(sector_tickers), ticker))

    # Download
    result <- download_stock(ticker, start_date, end_date)

    # Save result
    if (result$success) {
      # Save to RDS file
      output_file <- file.path(STOCKS_DIR, paste0(ticker, ".rds"))
      saveRDS(result$data, output_file)

      cat(sprintf("✓ (%d rows)\n", nrow(result$data)))
      downloaded <- downloaded + 1

      # Log success
      download_log <- download_log %>%
        add_row(
          ticker = ticker,
          sector = sector_name,
          success = TRUE,
          error = NA_character_,
          rows = nrow(result$data),
          download_time = as.character(Sys.time())
        )

    } else {
      cat(sprintf("✗ %s\n", result$error))
      failed <- failed + 1

      # Log failure
      download_log <- download_log %>%
        add_row(
          ticker = ticker,
          sector = sector_name,
          success = FALSE,
          error = result$error,
          rows = 0L,
          download_time = as.character(Sys.time())
        )
    }

    # Be polite to Yahoo Finance - rate limiting
    Sys.sleep(0.25)

    # Periodic progress update
    if (i %% 25 == 0) {
      cat(sprintf("\n  Sector progress: %d/%d complete\n", i, length(sector_tickers)))
      cat(sprintf("  Overall: Downloaded=%d, Skipped=%d, Failed=%d\n",
                  downloaded, skipped, failed))
    }
  }

  cat(sprintf("  Sector %s complete!\n", sector_name))

  # Save log after each sector (in case of interruption)
  log_file <- file.path(METADATA_DIR, "download_log.csv")
  write_csv(download_log, log_file)
}

# ============================================================================
# STEP 7: SAVE FINAL METADATA
# ============================================================================

cat("\n\nStep 7: Saving metadata...\n")

# Save download log
log_file <- file.path(METADATA_DIR, "download_log.csv")
write_csv(download_log, log_file)
cat(sprintf("  Download log: %s\n", log_file))

# Create summary
summary_text <- sprintf("
=== STOCK DATA DOWNLOAD SUMMARY ===
Date: %s
Historical Period: %s to %s (%d years)

FILTERS APPLIED:
- Minimum Volume: %s shares/day
- Minimum Market Cap: $%.0fM

RESULTS:
- Total tickers processed: %d
- Successfully downloaded: %d
- Skipped (already exists): %d
- Failed: %d
- Success rate: %.1f%%

SECTORS:
%s

FILES:
- Stock data: %s/
- Download log: %s
- Ticker list: %s

To load a stock:
  stock_data <- readRDS('%s/AAPL.rds')
",
Sys.time(),
start_date,
end_date,
LOOKBACK_YEARS,
format(MIN_VOLUME, big.mark = ","),
MIN_MARKET_CAP / 1e6,
total_tickers,
downloaded,
skipped,
failed,
100 * downloaded / (downloaded + failed),
paste(capture.output(print(by_sector)), collapse = "\n"),
STOCKS_DIR,
log_file,
ticker_list_file,
STOCKS_DIR
)

# Save summary
summary_file <- file.path(METADATA_DIR, "download_summary.txt")
writeLines(summary_text, summary_file)
cat(sprintf("  Summary: %s\n", summary_file))

# Print summary to console
cat(summary_text)

# ============================================================================
# STEP 8: DATA QUALITY REPORT
# ============================================================================

cat("\n=== DATA QUALITY REPORT ===\n")

successful_downloads <- download_log %>%
  filter(success == TRUE)

if (nrow(successful_downloads) > 0) {

  # Statistics on successful downloads
  cat(sprintf("Average rows per stock: %.0f\n", mean(successful_downloads$rows)))
  cat(sprintf("Min rows: %d\n", min(successful_downloads$rows)))
  cat(sprintf("Max rows: %d\n", max(successful_downloads$rows)))

  # Success rate by sector
  sector_stats <- download_log %>%
    group_by(sector) %>%
    summarise(
      total = n(),
      successful = sum(success),
      success_rate = 100 * successful / total,
      .groups = "drop"
    ) %>%
    arrange(desc(success_rate))

  cat("\nSuccess rate by sector:\n")
  print(as.data.frame(sector_stats), row.names = FALSE)
}

# Failed downloads
if (failed > 0) {
  cat("\n--- Failed Downloads ---\n")
  failed_tickers <- download_log %>%
    filter(success == FALSE)

  # Group by error type
  error_summary <- failed_tickers %>%
    group_by(error) %>%
    summarise(count = n(), .groups = "drop") %>%
    arrange(desc(count))

  print(as.data.frame(error_summary), row.names = FALSE)

  cat("\nFailed tickers saved to log. You can retry these manually if needed.\n")
}

cat("\n=== MODULE 1 COMPLETE ===\n")
cat(sprintf("Next step: Run module 2 to analyze technical indicators\n\n"))
