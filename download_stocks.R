# Stock Data Download and Management Functions
# Purpose: Download and manage stock price data from Yahoo Finance

library(quantmod)
library(tidyverse)
library(lubridate)

#' Download stock data for a single ticker
#'
#' @param ticker Stock ticker symbol
#' @param from Start date
#' @param to End date
#' @return xts object with stock data
download_single_stock <- function(ticker, from, to) {
  tryCatch({
    message(sprintf("Downloading data for: %s", ticker))

    # Download from Yahoo Finance
    stock_data <- getSymbols(ticker,
                             src = "yahoo",
                             from = from,
                             to = to,
                             auto.assign = FALSE,
                             warnings = FALSE)

    # Add a small delay to avoid rate limiting
    Sys.sleep(0.5)

    return(stock_data)

  }, error = function(e) {
    warning(sprintf("Failed to download %s: %s", ticker, e$message))
    return(NULL)
  })
}

#' Download stock data for multiple tickers
#'
#' @param tickers Vector of stock ticker symbols
#' @param from Start date
#' @param to End date
#' @return List of xts objects with stock data
download_stock_data <- function(tickers, from, to) {
  stock_list <- list()

  for (ticker in tickers) {
    stock_data <- download_single_stock(ticker, from, to)

    if (!is.null(stock_data)) {
      stock_list[[ticker]] <- stock_data
    }
  }

  return(stock_list)
}

#' Get closing prices for multiple stocks and merge into a single dataframe
#'
#' @param tickers Vector of stock ticker symbols
#' @param from Start date
#' @param to End date
#' @return Data frame with closing prices
get_closing_prices <- function(tickers, from, to) {
  stock_data <- download_stock_data(tickers, from, to)

  if (length(stock_data) == 0) {
    stop("No stock data downloaded")
  }

  # Extract closing prices
  closing_prices <- lapply(names(stock_data), function(ticker) {
    data <- stock_data[[ticker]]
    close_col <- grep("Close", colnames(data), value = TRUE)

    if (length(close_col) > 0) {
      close_prices <- data[, close_col]
      colnames(close_prices) <- ticker
      return(close_prices)
    }
    return(NULL)
  })

  # Remove NULL entries
  closing_prices <- closing_prices[!sapply(closing_prices, is.null)]

  if (length(closing_prices) == 0) {
    stop("No closing prices available")
  }

  # Merge all closing prices
  merged_data <- do.call(merge, closing_prices)

  # Remove rows with NA values
  merged_data <- na.omit(merged_data)

  return(merged_data)
}

#' Calculate daily returns from price data
#'
#' @param prices xts object with prices
#' @return xts object with log returns
calculate_returns <- function(prices) {
  returns <- na.omit(ROC(prices, type = "continuous"))
  return(returns)
}

#' Save stock data to CSV file
#'
#' @param stock_data xts object with stock data
#' @param ticker Stock ticker symbol
#' @param folder Folder path to save CSV
save_stock_to_csv <- function(stock_data, ticker, folder = "stock_data/") {
  # Create folder if it doesn't exist
  if (!dir.exists(folder)) {
    dir.create(folder, recursive = TRUE)
  }

  # Create file path
  file_path <- file.path(folder, paste0(ticker, ".csv"))

  # Convert xts to data frame with date column
  df <- data.frame(Date = index(stock_data), coredata(stock_data))

  # Write to CSV
  write.csv(df, file_path, row.names = FALSE)

  message(sprintf("Saved %s to %s", ticker, file_path))
}

#' Load stock data from CSV file
#'
#' @param ticker Stock ticker symbol
#' @param folder Folder path where CSV is stored
#' @return xts object with stock data
load_stock_from_csv <- function(ticker, folder = "stock_data/") {
  file_path <- file.path(folder, paste0(ticker, ".csv"))

  if (!file.exists(file_path)) {
    warning(sprintf("File not found: %s", file_path))
    return(NULL)
  }

  # Read CSV
  df <- read.csv(file_path, stringsAsFactors = FALSE)

  # Convert to xts
  df$Date <- as.Date(df$Date)
  stock_xts <- xts(df[, -1], order.by = df$Date)

  return(stock_xts)
}

#' Download and save all Wilshire 5000 stocks
#'
#' @param wilshire_file Path to Wilshire stocks CSV file
#' @param folder Folder to save stock data
#' @param from Start date
#' @param to End date
download_all_wilshire_stocks <- function(wilshire_file = "Wilshire-5000-Stocks.csv",
                                          folder = "stock_data/",
                                          from = Sys.Date() - 365*5,
                                          to = Sys.Date()) {

  # Read Wilshire stocks list
  if (!file.exists(wilshire_file)) {
    stop(sprintf("Wilshire stocks file not found: %s", wilshire_file))
  }

  wilshire_stocks <- read.csv(wilshire_file, stringsAsFactors = FALSE)
  tickers <- wilshire_stocks$Ticker

  message(sprintf("Downloading %d stocks from Wilshire 5000...", length(tickers)))

  # Download and save each stock
  success_count <- 0
  fail_count <- 0

  for (i in seq_along(tickers)) {
    ticker <- tickers[i]

    if (i %% 10 == 0) {
      message(sprintf("Progress: %d/%d stocks processed", i, length(tickers)))
    }

    stock_data <- download_single_stock(ticker, from, to)

    if (!is.null(stock_data)) {
      save_stock_to_csv(stock_data, ticker, folder)
      success_count <- success_count + 1
    } else {
      fail_count <- fail_count + 1
    }
  }

  message(sprintf("\nDownload complete!"))
  message(sprintf("Successful: %d", success_count))
  message(sprintf("Failed: %d", fail_count))
}

#' Check if the market is currently open
#'
#' @return Boolean indicating if market is open
is_market_open <- function() {
  current_time <- Sys.time()
  current_day <- wday(current_time, label = TRUE)

  # Market is closed on weekends
  if (current_day %in% c("Sat", "Sun")) {
    return(FALSE)
  }

  # Get current time in Eastern Time (market hours)
  current_hour <- hour(current_time)

  # Simplified check: market hours 9:30 AM - 4:00 PM ET
  # This is a rough approximation
  if (current_hour >= 9 && current_hour < 16) {
    return(TRUE)
  }

  return(FALSE)
}

#' Update existing stock data with latest prices
#'
#' @param ticker Stock ticker symbol
#' @param folder Folder where stock data is stored
#' @return Updated xts object
update_stock_data <- function(ticker, folder = "stock_data/") {
  # Load existing data
  existing_data <- load_stock_from_csv(ticker, folder)

  if (is.null(existing_data)) {
    message(sprintf("No existing data for %s, downloading fresh data", ticker))
    new_data <- download_single_stock(ticker,
                                      from = Sys.Date() - 365*5,
                                      to = Sys.Date())
  } else {
    # Get the last date in existing data
    last_date <- index(existing_data)[nrow(existing_data)]

    # Download new data from last date to today
    if (last_date < Sys.Date()) {
      new_data <- download_single_stock(ticker,
                                        from = last_date + 1,
                                        to = Sys.Date())

      if (!is.null(new_data) && nrow(new_data) > 0) {
        # Merge with existing data
        updated_data <- rbind(existing_data, new_data)
        updated_data <- updated_data[!duplicated(index(updated_data)), ]
        new_data <- updated_data
      } else {
        message(sprintf("No new data available for %s", ticker))
        new_data <- existing_data
      }
    } else {
      message(sprintf("Data for %s is already up to date", ticker))
      new_data <- existing_data
    }
  }

  # Save updated data
  if (!is.null(new_data)) {
    save_stock_to_csv(new_data, ticker, folder)
  }

  return(new_data)
}

#' Get list of available stocks from saved data
#'
#' @param folder Folder where stock data is stored
#' @return Vector of ticker symbols
get_available_stocks <- function(folder = "stock_data/") {
  if (!dir.exists(folder)) {
    return(character(0))
  }

  files <- list.files(folder, pattern = "\\.csv$")
  tickers <- gsub("\\.csv$", "", files)

  return(tickers)
}
