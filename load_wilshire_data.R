# Load Wilshire Index Data from PDF and Fetch Tickers from OpenFIGI
# Following principles from: https://www.codingfinance.com/

# Required packages
# install.packages(c("pdftools", "httr", "jsonlite", "dplyr", "stringr", "tidyr"))

library(pdftools)
library(httr)
library(jsonlite)
library(dplyr)
library(stringr)
library(tidyr)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Set your OpenFIGI API key here (sign up at https://www.openfigi.com/)
OPENFIGI_API_KEY <- Sys.getenv("OPENFIGI_API_KEY")  # Or hardcode: "YOUR_API_KEY_HERE"

# PDF file path - UPDATE THIS to match your actual PDF filename
PDF_FILE <- "wilshire_0925.pdf"  # Change to your actual filename ending in 0925.pdf

# OpenFIGI API endpoint
OPENFIGI_API_URL <- "https://api.openfigi.com/v2/mapping"

# Batch size for API calls (max 100 per request recommended)
BATCH_SIZE <- 100

# =============================================================================
# STEP 1: EXTRACT DATA FROM PDF
# =============================================================================

cat("Step 1: Extracting data from PDF...\n")

# Read PDF file
pdf_text <- pdf_text(PDF_FILE)

# Display first page to understand structure
cat("\n--- First page preview ---\n")
cat(substr(pdf_text[1], 1, 500), "\n")
cat("...\n\n")

# CUSTOMIZE THIS SECTION based on your PDF structure
# This is a generic parser - you'll need to adjust based on actual PDF format

# Example: If PDF has tabular data with CUSIP and Security Name
parse_wilshire_pdf <- function(pdf_pages) {

  # Combine all pages
  all_text <- paste(pdf_pages, collapse = "\n")

  # Split into lines
  lines <- strsplit(all_text, "\n")[[1]]

  # Remove empty lines and trim whitespace
  lines <- str_trim(lines[lines != ""])

  # CUSTOMIZE: Extract CUSIP pattern (9-character alphanumeric)
  # Pattern for CUSIP: 6 alphanumeric + 2 alphanumeric + 1 check digit
  cusip_pattern <- "[0-9A-Z]{9}"

  # Extract lines containing CUSIPs
  data_lines <- lines[str_detect(lines, cusip_pattern)]

  # CUSTOMIZE: Parse based on your PDF structure
  # Example assuming format: "SECURITY NAME    CUSIP"
  # You may need to adjust this regex based on actual PDF layout

  parsed_data <- data.frame(
    raw_line = data_lines,
    stringsAsFactors = FALSE
  ) %>%
    mutate(
      # Extract CUSIP (9 characters)
      cusip = str_extract(raw_line, cusip_pattern),
      # Extract everything before CUSIP as security name
      security_name = str_trim(str_remove(raw_line, cusip_pattern))
    ) %>%
    filter(!is.na(cusip)) %>%
    select(security_name, cusip) %>%
    distinct()

  return(parsed_data)
}

# Parse the PDF
wilshire_data <- parse_wilshire_pdf(pdf_text)

cat(sprintf("Extracted %d securities with CUSIPs\n", nrow(wilshire_data)))
cat("\n--- Sample of extracted data ---\n")
print(head(wilshire_data, 10))

# =============================================================================
# STEP 2: QUERY OPENFIGI API TO GET TICKER SYMBOLS
# =============================================================================

cat("\n\nStep 2: Fetching ticker symbols from OpenFIGI API...\n")

# Function to query OpenFIGI API in batches
get_tickers_from_cusips <- function(cusips, api_key = NULL) {

  # Prepare results dataframe
  results <- data.frame(
    cusip = character(),
    ticker = character(),
    name = character(),
    exchange_code = character(),
    figi = character(),
    security_type = character(),
    market_sector = character(),
    stringsAsFactors = FALSE
  )

  # Split CUSIPs into batches
  num_batches <- ceiling(length(cusips) / BATCH_SIZE)

  for (batch_num in 1:num_batches) {

    cat(sprintf("Processing batch %d of %d...\n", batch_num, num_batches))

    # Get batch of CUSIPs
    start_idx <- (batch_num - 1) * BATCH_SIZE + 1
    end_idx <- min(batch_num * BATCH_SIZE, length(cusips))
    batch_cusips <- cusips[start_idx:end_idx]

    # Prepare request body (array of mapping jobs)
    request_jobs <- lapply(batch_cusips, function(cusip) {
      list(idType = "ID_CUSIP", idValue = cusip)
    })

    # Set up headers
    headers <- add_headers(
      `Content-Type` = "application/json"
    )

    # Add API key if provided
    if (!is.null(api_key) && api_key != "") {
      headers <- add_headers(
        `Content-Type` = "application/json",
        `X-OPENFIGI-APIKEY` = api_key
      )
    }

    # Make API request
    response <- POST(
      url = OPENFIGI_API_URL,
      body = toJSON(request_jobs, auto_unbox = TRUE),
      headers,
      encode = "json"
    )

    # Check for rate limiting
    if (status_code(response) == 429) {
      cat("Rate limit reached. Waiting 60 seconds...\n")
      Sys.sleep(60)
      # Retry the request
      response <- POST(
        url = OPENFIGI_API_URL,
        body = toJSON(request_jobs, auto_unbox = TRUE),
        headers,
        encode = "json"
      )
    }

    # Check response status
    if (status_code(response) != 200) {
      warning(sprintf("Batch %d failed with status code: %d", batch_num, status_code(response)))
      next
    }

    # Parse response
    response_data <- content(response, "parsed")

    # Extract results
    for (i in seq_along(response_data)) {
      cusip <- batch_cusips[i]

      # Check if we got data back
      if (!is.null(response_data[[i]]$data) && length(response_data[[i]]$data) > 0) {

        # Take first result (usually the most relevant)
        item <- response_data[[i]]$data[[1]]

        results <- rbind(results, data.frame(
          cusip = cusip,
          ticker = ifelse(!is.null(item$ticker), item$ticker, NA),
          name = ifelse(!is.null(item$name), item$name, NA),
          exchange_code = ifelse(!is.null(item$exchCode), item$exchCode, NA),
          figi = ifelse(!is.null(item$figi), item$figi, NA),
          security_type = ifelse(!is.null(item$securityType), item$securityType, NA),
          market_sector = ifelse(!is.null(item$marketSector), item$marketSector, NA),
          stringsAsFactors = FALSE
        ))
      } else {
        # No match found
        results <- rbind(results, data.frame(
          cusip = cusip,
          ticker = NA,
          name = NA,
          exchange_code = NA,
          figi = NA,
          security_type = NA,
          market_sector = NA,
          stringsAsFactors = FALSE
        ))
      }
    }

    # Be polite to API - small delay between batches
    if (batch_num < num_batches) {
      Sys.sleep(1)
    }
  }

  return(results)
}

# Only run API queries if we have an API key
if (!is.null(OPENFIGI_API_KEY) && OPENFIGI_API_KEY != "") {

  # Get tickers from OpenFIGI
  ticker_data <- get_tickers_from_cusips(wilshire_data$cusip, OPENFIGI_API_KEY)

  # Merge with original data
  wilshire_complete <- wilshire_data %>%
    left_join(ticker_data, by = "cusip")

  # Summary statistics
  cat("\n--- API Query Results ---\n")
  cat(sprintf("Total securities: %d\n", nrow(wilshire_complete)))
  cat(sprintf("Tickers found: %d\n", sum(!is.na(wilshire_complete$ticker))))
  cat(sprintf("Tickers not found: %d\n", sum(is.na(wilshire_complete$ticker))))

  # Show sample results
  cat("\n--- Sample of complete data ---\n")
  print(head(wilshire_complete %>% filter(!is.na(ticker)), 10))

} else {

  cat("\n*** API KEY NOT SET ***\n")
  cat("To fetch ticker symbols, set your OpenFIGI API key:\n")
  cat("1. Sign up at https://www.openfigi.com/\n")
  cat("2. Set environment variable: Sys.setenv(OPENFIGI_API_KEY = 'your_key_here')\n")
  cat("   OR hardcode in this script: OPENFIGI_API_KEY <- 'your_key_here'\n\n")

  wilshire_complete <- wilshire_data
}

# =============================================================================
# STEP 3: SAVE RESULTS
# =============================================================================

cat("\nStep 3: Saving results...\n")

# Save to CSV
output_file <- "wilshire_with_tickers.csv"
write.csv(wilshire_complete, output_file, row.names = FALSE)
cat(sprintf("Saved to: %s\n", output_file))

# Save to RDS for faster loading in R
output_rds <- "wilshire_with_tickers.rds"
saveRDS(wilshire_complete, output_rds)
cat(sprintf("Saved to: %s\n", output_rds))

# =============================================================================
# OPTIONAL: FILTER FOR US EQUITIES ONLY
# =============================================================================

if (exists("ticker_data")) {

  # Filter for common stock on US exchanges
  us_equities <- wilshire_complete %>%
    filter(
      !is.na(ticker),
      security_type %in% c("Common Stock", "ETP", NA),
      exchange_code %in% c("US", "UN", "UW", "UQ", NA) | is.na(exchange_code)
    ) %>%
    arrange(ticker)

  cat(sprintf("\nFiltered US equities: %d securities\n", nrow(us_equities)))

  # Save filtered version
  write.csv(us_equities, "wilshire_us_equities.csv", row.names = FALSE)
  saveRDS(us_equities, "wilshire_us_equities.rds")

  cat("\n--- Distribution by Exchange ---\n")
  print(table(us_equities$exchange_code, useNA = "ifany"))
}

# =============================================================================
# USAGE EXAMPLE: Load data in future sessions
# =============================================================================

cat("\n\n=== USAGE IN FUTURE R SESSIONS ===\n")
cat("# Quick load of processed data:\n")
cat("wilshire <- readRDS('wilshire_with_tickers.rds')\n")
cat("\n# Or from CSV:\n")
cat("wilshire <- read.csv('wilshire_with_tickers.csv', stringsAsFactors = FALSE)\n")
cat("\n# Filter for stocks with tickers:\n")
cat("valid_stocks <- wilshire %>% filter(!is.na(ticker))\n")
cat("\n# Get vector of tickers for downloading price data:\n")
cat("tickers <- valid_stocks$ticker\n")

cat("\n\n=== SCRIPT COMPLETE ===\n")
