# ============================================================================
# DATA LOADER UTILITIES
# ============================================================================
# Helper functions for loading and managing downloaded stock data
# Following principles from: https://www.codingfinance.com/

# Required packages
if (!require("dplyr", quietly = TRUE)) install.packages("dplyr")
if (!require("purrr", quietly = TRUE)) install.packages("purrr")
if (!require("lubridate", quietly = TRUE)) install.packages("lubridate")
if (!require("tidyr", quietly = TRUE)) install.packages("tidyr")

library(dplyr)
library(purrr)
library(lubridate)
library(tidyr)

# ============================================================================
# CONFIGURATION
# ============================================================================

STOCKS_DIR <- "stocks"
METADATA_DIR <- "metadata"

# ============================================================================
# CORE LOADING FUNCTIONS
# ============================================================================

#' Load single stock data
#'
#' @param ticker Stock ticker symbol (e.g., "AAPL")
#' @param dir Directory containing stock RDS files (default: "stocks")
#' @return Data frame with OHLCV data, or NULL if not found
#' @export
load_stock <- function(ticker, dir = STOCKS_DIR) {

  file_path <- file.path(dir, paste0(ticker, ".rds"))

  if (!file.exists(file_path)) {
    warning(sprintf("Stock data not found for %s", ticker))
    return(NULL)
  }

  tryCatch({
    data <- readRDS(file_path)
    return(data)
  }, error = function(e) {
    warning(sprintf("Error loading %s: %s", ticker, e$message))
    return(NULL)
  })
}

#' Load multiple stocks
#'
#' @param tickers Vector of ticker symbols
#' @param dir Directory containing stock RDS files
#' @param combine If TRUE, combine into single data frame with ticker column
#' @return List of data frames (if combine=FALSE) or single data frame (if combine=TRUE)
#' @export
load_multiple_stocks <- function(tickers, dir = STOCKS_DIR, combine = FALSE) {

  cat(sprintf("Loading %d stocks...\n", length(tickers)))

  # Load all stocks
  stock_data <- map(tickers, ~load_stock(.x, dir = dir))
  names(stock_data) <- tickers

  # Remove NULLs (failed loads)
  stock_data <- compact(stock_data)

  cat(sprintf("Successfully loaded: %d/%d stocks\n",
              length(stock_data), length(tickers)))

  if (combine) {
    # Combine into single data frame
    combined <- map2_dfr(stock_data, names(stock_data), function(data, ticker) {
      data %>% mutate(ticker = ticker, .before = 1)
    })
    return(combined)
  } else {
    return(stock_data)
  }
}

#' Load all available stocks
#'
#' @param dir Directory containing stock RDS files
#' @param pattern File pattern to match (default: all .rds files)
#' @return List of all stock data frames
#' @export
load_all_stocks <- function(dir = STOCKS_DIR, pattern = "\\.rds$") {

  files <- list.files(dir, pattern = pattern, full.names = FALSE)
  tickers <- sub("\\.rds$", "", files)

  cat(sprintf("Found %d stock files in %s\n", length(tickers), dir))

  return(load_multiple_stocks(tickers, dir = dir))
}

#' Load stocks by sector
#'
#' @param sector Sector name (e.g., "Technology", "Healthcare")
#' @param metadata_file Path to filtered_tickers.csv with sector info
#' @return List of stock data frames for that sector
#' @export
load_stocks_by_sector <- function(sector, metadata_file = "metadata/filtered_tickers.csv") {

  if (!file.exists(metadata_file)) {
    stop(sprintf("Metadata file not found: %s", metadata_file))
  }

  # Load ticker list
  ticker_info <- read.csv(metadata_file, stringsAsFactors = FALSE)

  # Filter by sector
  sector_tickers <- ticker_info %>%
    filter(sector == !!sector) %>%
    pull(ticker)

  if (length(sector_tickers) == 0) {
    warning(sprintf("No tickers found for sector: %s", sector))
    return(list())
  }

  cat(sprintf("Loading %d stocks from %s sector...\n", length(sector_tickers), sector))

  return(load_multiple_stocks(sector_tickers))
}

# ============================================================================
# DATA QUALITY FUNCTIONS
# ============================================================================

#' Check data availability
#'
#' @param tickers Vector of ticker symbols
#' @param dir Directory containing stock RDS files
#' @return Data frame with availability status
#' @export
check_data_availability <- function(tickers, dir = STOCKS_DIR) {

  results <- map_dfr(tickers, function(ticker) {
    file_path <- file.path(dir, paste0(ticker, ".rds"))

    if (!file.exists(file_path)) {
      return(tibble(ticker = ticker, available = FALSE, rows = 0, start_date = NA, end_date = NA))
    }

    data <- readRDS(file_path)
    return(tibble(
      ticker = ticker,
      available = TRUE,
      rows = nrow(data),
      start_date = min(data$date),
      end_date = max(data$date)
    ))
  })

  return(results)
}

#' Get summary of downloaded data
#'
#' @param dir Directory containing stock RDS files
#' @return Summary statistics
#' @export
get_download_summary <- function(dir = STOCKS_DIR) {

  files <- list.files(dir, pattern = "\\.rds$")

  if (length(files) == 0) {
    cat("No stock data files found.\n")
    return(NULL)
  }

  cat(sprintf("Total stocks downloaded: %d\n", length(files)))

  # Sample a few stocks to get date range
  sample_tickers <- sub("\\.rds$", "", head(files, 10))
  sample_data <- map(sample_tickers, ~load_stock(.x, dir = dir))
  sample_data <- compact(sample_data)

  if (length(sample_data) > 0) {
    date_ranges <- map_dfr(sample_data, function(data) {
      tibble(
        start = min(data$date),
        end = max(data$date),
        rows = nrow(data)
      )
    })

    cat(sprintf("Date range (from sample): %s to %s\n",
                min(date_ranges$start), max(date_ranges$end)))
    cat(sprintf("Average rows per stock: %.0f\n", mean(date_ranges$rows)))
  }

  # Load download log if available
  log_file <- file.path(METADATA_DIR, "download_log.csv")
  if (file.exists(log_file)) {
    log <- read.csv(log_file, stringsAsFactors = FALSE)
    success_rate <- 100 * sum(log$success) / nrow(log)
    cat(sprintf("Download success rate: %.1f%%\n", success_rate))

    # Sector breakdown
    sector_summary <- log %>%
      filter(success == TRUE) %>%
      count(sector, sort = TRUE)

    cat("\nStocks by sector:\n")
    print(as.data.frame(sector_summary), row.names = FALSE)
  }

  invisible(files)
}

# ============================================================================
# DATA TRANSFORMATION FUNCTIONS
# ============================================================================

#' Calculate returns for a stock
#'
#' @param data Stock data frame with 'close' or 'adjusted' column
#' @param use_adjusted Use adjusted close instead of close price
#' @return Data frame with added returns columns
#' @export
calculate_returns <- function(data, use_adjusted = TRUE) {

  price_col <- if (use_adjusted && "adjusted" %in% names(data)) "adjusted" else "close"

  data %>%
    arrange(date) %>%
    mutate(
      daily_return = (!!sym(price_col) - lag(!!sym(price_col))) / lag(!!sym(price_col)),
      cumulative_return = cumprod(1 + replace_na(daily_return, 0)) - 1
    )
}

#' Create returns matrix for multiple stocks
#'
#' @param stock_list List of stock data frames (named list with tickers)
#' @param use_adjusted Use adjusted close instead of close price
#' @return Wide-format data frame with dates and returns for each stock
#' @export
create_returns_matrix <- function(stock_list, use_adjusted = TRUE) {

  # Calculate returns for each stock
  returns_list <- map(stock_list, ~calculate_returns(.x, use_adjusted))

  # Extract date and returns for each stock
  returns_data <- map2(returns_list, names(returns_list), function(data, ticker) {
    data %>%
      select(date, daily_return) %>%
      rename(!!ticker := daily_return)
  })

  # Join all returns into one wide data frame
  returns_matrix <- reduce(returns_data, full_join, by = "date") %>%
    arrange(date)

  return(returns_matrix)
}

# ============================================================================
# FILTERING FUNCTIONS
# ============================================================================

#' Filter stocks by date range
#'
#' @param stock_list List of stock data frames
#' @param start_date Start date (Date or character)
#' @param end_date End date (Date or character)
#' @return Filtered stock list
#' @export
filter_by_date <- function(stock_list, start_date, end_date) {

  start_date <- as.Date(start_date)
  end_date <- as.Date(end_date)

  map(stock_list, function(data) {
    data %>%
      filter(date >= start_date, date <= end_date)
  })
}

#' Filter stocks by minimum data requirements
#'
#' @param stock_list List of stock data frames
#' @param min_days Minimum number of trading days required
#' @return Filtered stock list (removes stocks with insufficient data)
#' @export
filter_by_min_days <- function(stock_list, min_days = 252) {

  keep(stock_list, function(data) {
    nrow(data) >= min_days
  })
}

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

#' Get list of all available tickers
#'
#' @param dir Directory containing stock RDS files
#' @return Character vector of ticker symbols
#' @export
get_available_tickers <- function(dir = STOCKS_DIR) {

  files <- list.files(dir, pattern = "\\.rds$")
  tickers <- sub("\\.rds$", "", files)

  return(tickers)
}

#' Get sectors available in downloaded data
#'
#' @param metadata_file Path to filtered_tickers.csv
#' @return Character vector of sector names
#' @export
get_available_sectors <- function(metadata_file = "metadata/filtered_tickers.csv") {

  if (!file.exists(metadata_file)) {
    warning("Metadata file not found")
    return(character(0))
  }

  ticker_info <- read.csv(metadata_file, stringsAsFactors = FALSE)
  unique(ticker_info$sector)
}

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

#' Print usage examples
#'
#' @export
show_usage_examples <- function() {
  cat("
=== DATA LOADER USAGE EXAMPLES ===

# Load single stock
aapl <- load_stock('AAPL')

# Load multiple stocks
tech_stocks <- load_multiple_stocks(c('AAPL', 'MSFT', 'GOOGL'))

# Load all stocks (warning: memory intensive!)
all_stocks <- load_all_stocks()

# Load by sector
healthcare <- load_stocks_by_sector('Healthcare')

# Check what's available
available <- get_available_tickers()
sectors <- get_available_sectors()

# Get summary
get_download_summary()

# Check specific tickers
check_data_availability(c('AAPL', 'MSFT', 'INVALID'))

# Calculate returns
aapl_with_returns <- calculate_returns(aapl)

# Create returns matrix for portfolio analysis
my_portfolio <- load_multiple_stocks(c('AAPL', 'MSFT', 'GOOGL'))
returns_matrix <- create_returns_matrix(my_portfolio)

# Filter by date
recent_data <- filter_by_date(my_portfolio, '2025-01-01', Sys.Date())

# Filter by minimum data requirement (1 year)
valid_stocks <- filter_by_min_days(my_portfolio, min_days = 252)

")
}

cat("\n✓ Data loader utilities loaded successfully\n")
cat("Run show_usage_examples() to see usage examples\n\n")
