# ============================================================================
# MODULE 2: TECHNICAL ANALYSIS & STOCK SCREENING
# ============================================================================
# Calculates technical indicators and screens for top performers by sector
# Following principles from: https://www.codingfinance.com/
#
# Inputs: Downloaded stock data from Module 1
# Outputs: Screened candidate stocks for portfolio optimization
#
# Author: Portfolio Optimization System
# Date: 2026-01-17

# Load utilities
source("utils_data_loader.R")

# Additional packages for technical analysis
if (!require("TTR", quietly = TRUE)) install.packages("TTR")
library(TTR)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 2: TECHNICAL ANALYSIS & STOCK SCREENING ===\n\n")

# Screening parameters
ANALYSIS_PERIOD <- 252        # 1 year of trading days for performance ranking
MIN_TRADING_DAYS <- 400       # Minimum data requirement (~2 years with buffer)
TOP_N_PER_SECTOR <- 10        # Top N performers per sector
MIN_AVG_VOLUME <- 100000      # Minimum average daily volume
MAX_VOLATILITY <- 0.05        # Maximum daily volatility (5%)

# Bollinger Bands parameters
BB_PERIOD <- 20               # 20-day moving average
BB_SD <- 2                    # Standard deviations

# Output files
OUTPUT_DIR <- "analysis"
CANDIDATES_FILE <- file.path(OUTPUT_DIR, "candidate_stocks.csv")
CANDIDATES_RDS <- file.path(OUTPUT_DIR, "candidate_stocks.rds")
PERFORMANCE_FILE <- file.path(OUTPUT_DIR, "performance_summary.csv")

# Create output directory
if (!dir.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR, recursive = TRUE)
  cat("Created output directory: analysis/\n\n")
}

# ============================================================================
# STEP 1: LOAD METADATA & FILTER AVAILABLE STOCKS
# ============================================================================

cat("Step 1: Loading stock metadata...\n")

# Load download log to get sector information
download_log <- read.csv("metadata/download_log.csv", stringsAsFactors = FALSE)

# Filter to successful downloads only
successful_stocks <- download_log %>%
  filter(success == TRUE) %>%
  select(ticker, sector, rows)

cat(sprintf("  Successfully downloaded stocks: %d\n", nrow(successful_stocks)))
cat(sprintf("  Sectors represented: %d\n", length(unique(successful_stocks$sector))))

# Filter by minimum data requirement
valid_stocks <- successful_stocks %>%
  filter(rows >= MIN_TRADING_DAYS)

cat(sprintf("  After minimum data filter (>%d days): %d stocks\n",
            MIN_TRADING_DAYS, nrow(valid_stocks)))

# ============================================================================
# STEP 2: CALCULATE TECHNICAL INDICATORS
# ============================================================================

cat("\nStep 2: Calculating technical indicators...\n")
cat("This may take a few minutes for large datasets...\n\n")

# Function to calculate all technical indicators for a stock
calculate_technical_indicators <- function(ticker, sector) {

  # Load stock data
  stock_data <- load_stock(ticker)

  if (is.null(stock_data) || nrow(stock_data) < MIN_TRADING_DAYS) {
    return(NULL)
  }

  tryCatch({

    # Sort by date
    stock_data <- stock_data %>% arrange(date)

    # Calculate returns
    stock_data <- stock_data %>%
      mutate(
        daily_return = (adjusted - lag(adjusted)) / lag(adjusted),
        log_return = log(adjusted / lag(adjusted))
      )

    # Cumulative returns (using last ANALYSIS_PERIOD days)
    recent_data <- stock_data %>%
      tail(ANALYSIS_PERIOD + 1)  # +1 for lag calculation

    if (nrow(recent_data) < ANALYSIS_PERIOD) {
      return(NULL)
    }

    cumulative_return <- prod(1 + recent_data$daily_return, na.rm = TRUE) - 1

    # Bollinger Bands
    bb <- BBands(stock_data$adjusted, n = BB_PERIOD, sd = BB_SD)
    stock_data <- cbind(stock_data, bb)

    # Current position relative to Bollinger Bands
    latest <- tail(stock_data, 1)
    bb_position <- (latest$adjusted - latest$dn) / (latest$up - latest$dn)

    # Performance metrics
    avg_volume <- mean(stock_data$volume, na.rm = TRUE)
    daily_volatility <- sd(stock_data$daily_return, na.rm = TRUE)
    sharpe_ratio <- mean(stock_data$daily_return, na.rm = TRUE) / daily_volatility * sqrt(252)

    # Momentum indicators
    return_6m <- prod(1 + tail(stock_data$daily_return, 126), na.rm = TRUE) - 1  # 6 months
    return_3m <- prod(1 + tail(stock_data$daily_return, 63), na.rm = TRUE) - 1   # 3 months

    # Return summary metrics
    return(data.frame(
      ticker = ticker,
      sector = sector,
      cumulative_return_1y = cumulative_return,
      return_6m = return_6m,
      return_3m = return_3m,
      daily_volatility = daily_volatility,
      sharpe_ratio = sharpe_ratio,
      avg_volume = avg_volume,
      bb_position = bb_position,
      current_price = latest$adjusted,
      latest_date = latest$date,
      stringsAsFactors = FALSE
    ))

  }, error = function(e) {
    warning(sprintf("Error processing %s: %s", ticker, e$message))
    return(NULL)
  })
}

# Calculate indicators for all valid stocks
# Process in batches with progress updates
all_metrics <- list()
total_stocks <- nrow(valid_stocks)
batch_size <- 50

for (i in 1:nrow(valid_stocks)) {

  ticker <- valid_stocks$ticker[i]
  sector <- valid_stocks$sector[i]

  metrics <- calculate_technical_indicators(ticker, sector)

  if (!is.null(metrics)) {
    all_metrics[[ticker]] <- metrics
  }

  # Progress indicator
  if (i %% batch_size == 0) {
    cat(sprintf("  Progress: %d/%d stocks processed (%.1f%%)\n",
                i, total_stocks, 100 * i / total_stocks))
  }
}

# Combine all metrics into single dataframe
performance_data <- bind_rows(all_metrics)

cat(sprintf("\n  Successfully analyzed: %d stocks\n", nrow(performance_data)))

# ============================================================================
# STEP 3: APPLY SCREENING FILTERS
# ============================================================================

cat("\nStep 3: Applying screening filters...\n")

initial_count <- nrow(performance_data)

# Filter by volume
performance_data <- performance_data %>%
  filter(avg_volume >= MIN_AVG_VOLUME)

cat(sprintf("  After volume filter (>%s): %d stocks\n",
            format(MIN_AVG_VOLUME, big.mark = ","),
            nrow(performance_data)))

# Filter by volatility (not too volatile)
performance_data <- performance_data %>%
  filter(daily_volatility <= MAX_VOLATILITY)

cat(sprintf("  After volatility filter (<%.1f%%): %d stocks\n",
            100 * MAX_VOLATILITY,
            nrow(performance_data)))

# Filter by positive returns (at least positive 3-month return)
performance_data <- performance_data %>%
  filter(return_3m > 0)

cat(sprintf("  After positive momentum filter: %d stocks\n",
            nrow(performance_data)))

cat(sprintf("  Total filtered: %d → %d (%.1f%% pass rate)\n",
            initial_count, nrow(performance_data),
            100 * nrow(performance_data) / initial_count))

# ============================================================================
# STEP 4: RANK BY SECTOR
# ============================================================================

cat("\nStep 4: Ranking stocks by sector...\n")

# Rank within each sector by cumulative return
sector_rankings <- performance_data %>%
  group_by(sector) %>%
  mutate(
    sector_rank = rank(-cumulative_return_1y, ties.method = "first"),
    sector_size = n()
  ) %>%
  ungroup()

# Select top N per sector
top_performers <- sector_rankings %>%
  filter(sector_rank <= TOP_N_PER_SECTOR) %>%
  arrange(sector, sector_rank)

cat(sprintf("  Selected top %d stocks per sector\n", TOP_N_PER_SECTOR))
cat(sprintf("  Total candidates: %d stocks\n", nrow(top_performers)))

# Show breakdown by sector
sector_summary <- top_performers %>%
  group_by(sector) %>%
  summarise(
    count = n(),
    avg_return = mean(cumulative_return_1y),
    min_return = min(cumulative_return_1y),
    max_return = max(cumulative_return_1y),
    .groups = "drop"
  ) %>%
  arrange(desc(avg_return))

cat("\n  Candidates by sector:\n")
print(as.data.frame(sector_summary), row.names = FALSE)

# ============================================================================
# STEP 5: SAVE CANDIDATE LIST
# ============================================================================

cat("\nStep 5: Saving candidate stocks...\n")

# Save to CSV
write.csv(top_performers, CANDIDATES_FILE, row.names = FALSE)
cat(sprintf("  Saved CSV: %s\n", CANDIDATES_FILE))

# Save to RDS
saveRDS(top_performers, CANDIDATES_RDS)
cat(sprintf("  Saved RDS: %s\n", CANDIDATES_RDS))

# Save full performance data
write.csv(performance_data, PERFORMANCE_FILE, row.names = FALSE)
cat(sprintf("  Saved full performance: %s\n", PERFORMANCE_FILE))

# ============================================================================
# STEP 6: GENERATE SUMMARY VISUALIZATIONS
# ============================================================================

cat("\nStep 6: Generating summary statistics...\n")

# Top 20 overall performers
top_20_overall <- performance_data %>%
  arrange(desc(cumulative_return_1y)) %>%
  head(20)

cat("\n  Top 20 Performers (All Sectors):\n")
top_20_display <- top_20_overall %>%
  select(ticker, sector, cumulative_return_1y, sharpe_ratio, daily_volatility) %>%
  mutate(cumulative_return_1y = sprintf("%.2f%%", 100 * cumulative_return_1y))
print(as.data.frame(top_20_display), row.names = FALSE)

# Summary statistics for candidates
cat("\n  Candidate Portfolio Statistics:\n")
cat(sprintf("    Total candidates: %d\n", nrow(top_performers)))
cat(sprintf("    Sectors represented: %d\n", length(unique(top_performers$sector))))
cat(sprintf("    Avg 1-year return: %.2f%%\n",
            100 * mean(top_performers$cumulative_return_1y)))
cat(sprintf("    Avg Sharpe ratio: %.2f\n",
            mean(top_performers$sharpe_ratio, na.rm = TRUE)))
cat(sprintf("    Avg daily volatility: %.2f%%\n",
            100 * mean(top_performers$daily_volatility)))

# Return distribution
return_quantiles <- quantile(top_performers$cumulative_return_1y,
                              probs = c(0.25, 0.5, 0.75))
cat("\n  Return Distribution (1-year):\n")
cat(sprintf("    25th percentile: %.2f%%\n", 100 * return_quantiles[1]))
cat(sprintf("    Median: %.2f%%\n", 100 * return_quantiles[2]))
cat(sprintf("    75th percentile: %.2f%%\n", 100 * return_quantiles[3]))

# ============================================================================
# STEP 7: PREPARE BOLLINGER BANDS DATA FOR TOP CANDIDATES
# ============================================================================

cat("\nStep 7: Calculating Bollinger Bands for top candidates...\n")

# Function to get stock data with Bollinger Bands
get_stock_with_bb <- function(ticker) {

  stock_data <- load_stock(ticker)

  if (is.null(stock_data)) return(NULL)

  stock_data <- stock_data %>%
    arrange(date) %>%
    calculate_returns()

  # Add Bollinger Bands
  bb <- BBands(stock_data$adjusted, n = BB_PERIOD, sd = BB_SD)
  stock_data <- cbind(stock_data, bb)

  stock_data$ticker <- ticker
  return(stock_data)
}

# Get BB data for top 10 overall performers for plotting
top_10_tickers <- head(top_20_overall$ticker, 10)
bb_data_list <- lapply(top_10_tickers, get_stock_with_bb)
names(bb_data_list) <- top_10_tickers

# Save BB data
bb_output <- file.path(OUTPUT_DIR, "bollinger_bands_data.rds")
saveRDS(bb_data_list, bb_output)
cat(sprintf("  Saved Bollinger Bands data: %s\n", bb_output))

# ============================================================================
# STEP 8: CREATE SUMMARY REPORT
# ============================================================================

cat("\nStep 8: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 2: TECHNICAL ANALYSIS SUMMARY ===
Generated: %s

SCREENING PARAMETERS:
- Analysis period: %d trading days (~1 year)
- Minimum data requirement: %d trading days
- Minimum average volume: %s shares/day
- Maximum daily volatility: %.1f%%
- Top performers per sector: %d

INPUT DATA:
- Total stocks downloaded: %d
- Stocks meeting minimum data: %d
- Stocks after screening: %d

CANDIDATE SELECTION:
- Total candidates: %d
- Sectors represented: %d
- Average 1-year return: %.2f%%
- Average Sharpe ratio: %.2f
- Average daily volatility: %.2f%%

SECTOR BREAKDOWN:
%s

TOP 10 PERFORMERS:
%s

FILES GENERATED:
- Candidates: %s
- Full performance data: %s
- Bollinger Bands data: %s

NEXT STEPS:
- Run Module 3 for correlation analysis
- Select 9-12 stocks with low correlation
- Apply Ichimoku analysis for validation
",
Sys.time(),
ANALYSIS_PERIOD,
MIN_TRADING_DAYS,
format(MIN_AVG_VOLUME, big.mark = ","),
100 * MAX_VOLATILITY,
TOP_N_PER_SECTOR,
nrow(successful_stocks),
nrow(valid_stocks),
nrow(performance_data),
nrow(top_performers),
length(unique(top_performers$sector)),
100 * mean(top_performers$cumulative_return_1y),
mean(top_performers$sharpe_ratio, na.rm = TRUE),
100 * mean(top_performers$daily_volatility),
paste(capture.output(print(sector_summary, row.names = FALSE)), collapse = "\n"),
paste(capture.output(print(
  head(top_20_overall %>%
         select(ticker, sector, cumulative_return_1y) %>%
         mutate(return_pct = sprintf("%.2f%%", 100 * cumulative_return_1y)) %>%
         select(-cumulative_return_1y), 10),
  row.names = FALSE
)), collapse = "\n"),
CANDIDATES_FILE,
PERFORMANCE_FILE,
bb_output
)

# Save summary
summary_file <- file.path(OUTPUT_DIR, "module_2_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 2 COMPLETE ===\n")
cat(sprintf("Next step: Run Module 3 for correlation analysis\n\n"))

# ============================================================================
# USAGE EXAMPLE FOR NEXT STEPS
# ============================================================================

cat("=== QUICK START FOR MODULE 3 ===\n")
cat("# Load candidate stocks:\n")
cat("candidates <- readRDS('analysis/candidate_stocks.rds')\n\n")
cat("# View candidates:\n")
cat("head(candidates)\n\n")
cat("# Load Bollinger Bands data for plotting:\n")
cat("bb_data <- readRDS('analysis/bollinger_bands_data.rds')\n\n")
cat("# Plot Bollinger Bands for a stock:\n")
cat("stock <- bb_data[['AAPL']]\n")
cat("plot(stock$date, stock$adjusted, type='l', main='AAPL with Bollinger Bands')\n")
cat("lines(stock$date, stock$up, col='red', lty=2)\n")
cat("lines(stock$date, stock$dn, col='red', lty=2)\n")
cat("lines(stock$date, stock$mavg, col='blue')\n\n")
