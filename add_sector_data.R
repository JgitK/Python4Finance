# Add Sector/Industry Classification to Wilshire Data
# Following principles from: https://www.codingfinance.com/

# Required packages
# install.packages(c("dplyr", "quantmod", "tidyr", "readr"))

library(dplyr)
library(readr)
library(tidyr)

# Optional: for fetching missing sector data from Yahoo Finance
library(quantmod)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Input file - your Wilshire data with tickers from OpenFIGI
WILSHIRE_FILE <- "wilshire_with_tickers.rds"  # or "wilshire_us_equities.rds"

# Existing sector classification files in repository
SECTOR_FILE_SMALL <- "stock_sectors.csv"      # ~505 stocks (S&P 500)
SECTOR_FILE_LARGE <- "big_stock_sectors.csv"  # ~6,100 stocks

# =============================================================================
# STEP 1: LOAD YOUR WILSHIRE DATA
# =============================================================================

cat("Step 1: Loading Wilshire data...\n")

# Load your data (adjust if using CSV instead of RDS)
if (file.exists(WILSHIRE_FILE)) {
  wilshire <- readRDS(WILSHIRE_FILE)
} else if (file.exists("wilshire_with_tickers.csv")) {
  wilshire <- read_csv("wilshire_with_tickers.csv", show_col_types = FALSE)
} else {
  stop("Wilshire data file not found. Please run load_wilshire_data.R first.")
}

cat(sprintf("Loaded %d securities\n", nrow(wilshire)))
cat(sprintf("Securities with tickers: %d\n", sum(!is.na(wilshire$ticker))))

# Filter to only securities with valid tickers
wilshire_with_tickers <- wilshire %>%
  filter(!is.na(ticker), ticker != "")

cat(sprintf("Working with %d securities that have valid tickers\n",
            nrow(wilshire_with_tickers)))

# =============================================================================
# STEP 2: LOAD EXISTING SECTOR DATA
# =============================================================================

cat("\nStep 2: Loading existing sector classification files...\n")

# Load small sector file (S&P 500)
if (file.exists(SECTOR_FILE_SMALL)) {
  sectors_small <- read_csv(SECTOR_FILE_SMALL, show_col_types = FALSE) %>%
    rename(ticker = Symbol) %>%
    select(ticker, Sector) %>%
    rename(sector_classification = Sector)

  cat(sprintf("Loaded %d tickers from %s\n",
              nrow(sectors_small), SECTOR_FILE_SMALL))
} else {
  sectors_small <- data.frame(ticker = character(),
                              sector_classification = character())
}

# Load large sector file (~6,100 stocks)
if (file.exists(SECTOR_FILE_LARGE)) {
  sectors_large <- read_csv(SECTOR_FILE_LARGE, show_col_types = FALSE) %>%
    rename(ticker = Ticker) %>%
    select(ticker, Sector) %>%
    rename(sector_classification = Sector)

  cat(sprintf("Loaded %d tickers from %s\n",
              nrow(sectors_large), SECTOR_FILE_LARGE))
} else {
  sectors_large <- data.frame(ticker = character(),
                              sector_classification = character())
}

# Combine sector files (prefer small file as it's likely more curated)
combined_sectors <- bind_rows(sectors_small, sectors_large) %>%
  distinct(ticker, .keep_all = TRUE)

cat(sprintf("Combined total: %d unique tickers with sector data\n",
            nrow(combined_sectors)))

# =============================================================================
# STEP 3: JOIN SECTOR DATA WITH WILSHIRE DATA
# =============================================================================

cat("\nStep 3: Joining sector data with Wilshire data...\n")

wilshire_with_sectors <- wilshire_with_tickers %>%
  left_join(combined_sectors, by = "ticker")

# Check coverage
matched <- sum(!is.na(wilshire_with_sectors$sector_classification))
unmatched <- sum(is.na(wilshire_with_sectors$sector_classification))

cat(sprintf("Matched: %d securities (%.1f%%)\n",
            matched, 100 * matched / nrow(wilshire_with_sectors)))
cat(sprintf("Unmatched: %d securities (%.1f%%)\n",
            unmatched, 100 * unmatched / nrow(wilshire_with_sectors)))

# =============================================================================
# STEP 4: FETCH MISSING SECTOR DATA FROM YAHOO FINANCE (OPTIONAL)
# =============================================================================

cat("\nStep 4: Fetching missing sector data from Yahoo Finance...\n")
cat("This may take a few minutes for many stocks...\n\n")

# Function to get sector from Yahoo Finance
get_yahoo_sector <- function(ticker) {
  tryCatch({
    # Fetch stock info
    stock_info <- getQuote(ticker, what = yahooQF(c("Name", "Industry")))

    # Yahoo returns industry, we'll map it to broader sectors later
    if (!is.null(stock_info) && nrow(stock_info) > 0) {
      return(stock_info$Industry[1])
    } else {
      return(NA)
    }
  }, error = function(e) {
    return(NA)
  })
}

# Get list of tickers without sector data
missing_tickers <- wilshire_with_sectors %>%
  filter(is.na(sector_classification)) %>%
  pull(ticker) %>%
  unique()

cat(sprintf("Attempting to fetch sector data for %d tickers...\n",
            length(missing_tickers)))

# Fetch sectors for missing tickers (with progress indicator)
if (length(missing_tickers) > 0) {

  # Limit to first 500 to avoid very long wait times
  # You can remove this limit or increase it
  fetch_limit <- min(500, length(missing_tickers))

  if (length(missing_tickers) > fetch_limit) {
    cat(sprintf("Limiting to first %d tickers to save time.\n", fetch_limit))
    cat("You can increase fetch_limit or remove it in the script.\n\n")
    missing_tickers <- missing_tickers[1:fetch_limit]
  }

  yahoo_sectors <- data.frame(
    ticker = character(),
    yahoo_industry = character(),
    stringsAsFactors = FALSE
  )

  for (i in seq_along(missing_tickers)) {
    ticker <- missing_tickers[i]

    # Progress indicator
    if (i %% 50 == 0) {
      cat(sprintf("Progress: %d / %d tickers...\n", i, length(missing_tickers)))
    }

    industry <- get_yahoo_sector(ticker)

    yahoo_sectors <- rbind(yahoo_sectors, data.frame(
      ticker = ticker,
      yahoo_industry = industry,
      stringsAsFactors = FALSE
    ))

    # Be polite to Yahoo - small delay
    Sys.sleep(0.2)
  }

  # Map Yahoo industries to standard sectors
  # This is a simplified mapping - you can expand it
  yahoo_sectors <- yahoo_sectors %>%
    mutate(
      sector_from_yahoo = case_when(
        grepl("Technology|Software|Semiconductor|Computer|Internet",
              yahoo_industry, ignore.case = TRUE) ~ "Information Technology",
        grepl("Health|Medical|Pharma|Biotech|Drug",
              yahoo_industry, ignore.case = TRUE) ~ "Healthcare",
        grepl("Financial|Bank|Insurance|Investment",
              yahoo_industry, ignore.case = TRUE) ~ "Financials",
        grepl("Consumer|Retail|Restaurant|Hotel|Leisure",
              yahoo_industry, ignore.case = TRUE) ~ "Consumer Discretionary",
        grepl("Staples|Food|Beverage|Tobacco|Household",
              yahoo_industry, ignore.case = TRUE) ~ "Consumer Staples",
        grepl("Energy|Oil|Gas",
              yahoo_industry, ignore.case = TRUE) ~ "Energy",
        grepl("Utility|Electric|Water",
              yahoo_industry, ignore.case = TRUE) ~ "Utilities",
        grepl("Real Estate|REIT",
              yahoo_industry, ignore.case = TRUE) ~ "Real Estate",
        grepl("Material|Chemical|Mining|Metal|Paper",
              yahoo_industry, ignore.case = TRUE) ~ "Materials",
        grepl("Industrial|Manufacturing|Aerospace|Defense|Construction",
              yahoo_industry, ignore.case = TRUE) ~ "Industrials",
        grepl("Telecom|Communication",
              yahoo_industry, ignore.case = TRUE) ~ "Communication Services",
        TRUE ~ NA_character_
      )
    )

  # Join Yahoo sector data
  wilshire_with_sectors <- wilshire_with_sectors %>%
    left_join(yahoo_sectors, by = "ticker") %>%
    mutate(
      # Use original sector if available, otherwise use Yahoo sector
      sector_classification = coalesce(sector_classification, sector_from_yahoo)
    )

  # Update statistics
  matched_after <- sum(!is.na(wilshire_with_sectors$sector_classification))
  new_matches <- matched_after - matched

  cat(sprintf("\nYahoo Finance added sector data for %d additional securities\n",
              new_matches))
  cat(sprintf("Total matched: %d securities (%.1f%%)\n",
              matched_after,
              100 * matched_after / nrow(wilshire_with_sectors)))
}

# =============================================================================
# STEP 5: STANDARDIZE SECTOR NAMES
# =============================================================================

cat("\nStep 5: Standardizing sector names...\n")

# Map various sector naming conventions to standard 11 GICS sectors
wilshire_with_sectors <- wilshire_with_sectors %>%
  mutate(
    sector_standard = case_when(
      # Handle various naming conventions
      grepl("Information Technology|IT|Technology",
            sector_classification, ignore.case = TRUE) ~ "Information Technology",
      grepl("Health ?Care|Healthcare",
            sector_classification, ignore.case = TRUE) ~ "Healthcare",
      grepl("Financial",
            sector_classification, ignore.case = TRUE) ~ "Financials",
      grepl("Consumer Discretionary|Discretionary",
            sector_classification, ignore.case = TRUE) ~ "Consumer Discretionary",
      grepl("Consumer Staples|Staples",
            sector_classification, ignore.case = TRUE) ~ "Consumer Staples",
      grepl("Energy",
            sector_classification, ignore.case = TRUE) ~ "Energy",
      grepl("Utilit",
            sector_classification, ignore.case = TRUE) ~ "Utilities",
      grepl("Real Estate",
            sector_classification, ignore.case = TRUE) ~ "Real Estate",
      grepl("Material",
            sector_classification, ignore.case = TRUE) ~ "Materials",
      grepl("Industrial",
            sector_classification, ignore.case = TRUE) ~ "Industrials",
      grepl("Communication",
            sector_classification, ignore.case = TRUE) ~ "Communication Services",
      TRUE ~ sector_classification
    )
  )

# Show sector distribution
cat("\n--- Sector Distribution ---\n")
sector_counts <- wilshire_with_sectors %>%
  count(sector_standard, sort = TRUE)
print(sector_counts)

# =============================================================================
# STEP 6: SAVE ENRICHED DATA
# =============================================================================

cat("\nStep 6: Saving enriched data...\n")

# Save to CSV
output_csv <- "wilshire_with_sectors.csv"
write_csv(wilshire_with_sectors, output_csv)
cat(sprintf("Saved to: %s\n", output_csv))

# Save to RDS for faster loading in R
output_rds <- "wilshire_with_sectors.rds"
saveRDS(wilshire_with_sectors, output_rds)
cat(sprintf("Saved to: %s\n", output_rds))

# =============================================================================
# STEP 7: CREATE SECTOR SUMMARY FOR ANALYSIS
# =============================================================================

cat("\nStep 7: Creating sector summary...\n")

# Create summary by sector
sector_summary <- wilshire_with_sectors %>%
  filter(!is.na(sector_standard)) %>%
  group_by(sector_standard) %>%
  summarise(
    count = n(),
    tickers = paste(head(ticker, 5), collapse = ", "),  # Show first 5 examples
    .groups = "drop"
  ) %>%
  arrange(desc(count))

cat("\n--- Sector Summary ---\n")
print(sector_summary, n = 20)

# Save sector summary
write_csv(sector_summary, "sector_summary.csv")
cat("\nSector summary saved to: sector_summary.csv\n")

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

cat("\n\n=== USAGE IN FUTURE R SESSIONS ===\n")
cat("# Load enriched data:\n")
cat("wilshire <- readRDS('wilshire_with_sectors.rds')\n\n")

cat("# Filter by sector:\n")
cat("tech_stocks <- wilshire %>% filter(sector_standard == 'Information Technology')\n")
cat("healthcare <- wilshire %>% filter(sector_standard == 'Healthcare')\n\n")

cat("# Get tickers by sector for portfolio analysis:\n")
cat("tech_tickers <- tech_stocks$ticker\n")
cat("energy_tickers <- wilshire %>% filter(sector_standard == 'Energy') %>% pull(ticker)\n\n")

cat("# Sector rotation analysis:\n")
cat("by_sector <- wilshire %>% \n")
cat("  filter(!is.na(sector_standard)) %>% \n")
cat("  group_by(sector_standard) %>% \n")
cat("  summarise(count = n())\n")

cat("\n\n=== SCRIPT COMPLETE ===\n")
cat(sprintf("Final dataset: %d securities with sector classifications\n",
            sum(!is.na(wilshire_with_sectors$sector_standard))))
cat(sprintf("Securities without sectors: %d\n",
            sum(is.na(wilshire_with_sectors$sector_standard))))
