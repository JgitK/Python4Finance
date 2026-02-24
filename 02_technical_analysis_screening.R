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

# Risk metrics parameters
CVAR_ALPHA <- 0.05            # CVaR at 5% level (worst 5% of days)
RISK_FREE_RATE <- 0.045       # Annual risk-free rate for Sortino calculation

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

# Scan stocks/ directory for actual .rds files (more robust than relying on download log)
stock_files <- list.files("stocks", pattern = "\\.rds$", full.names = FALSE)
available_tickers <- gsub("\\.rds$", "", stock_files)

cat(sprintf("  Found %d stock files in stocks/ directory\n", length(available_tickers)))

# Load filtered_tickers.csv for sector information
filtered_tickers <- read.csv("metadata/filtered_tickers.csv", stringsAsFactors = FALSE)

# Build successful_stocks from actual files + sector info
successful_stocks <- data.frame(
  ticker = available_tickers,
  stringsAsFactors = FALSE
) %>%
  left_join(
    filtered_tickers %>% select(ticker, sector),
    by = "ticker"
  ) %>%
  mutate(sector = ifelse(is.na(sector), "Unknown", sector))

# Get row counts by loading each file (or estimate from file size)
# For speed, we'll check file existence and assume valid data
successful_stocks$rows <- sapply(successful_stocks$ticker, function(t) {
  tryCatch({
    nrow(readRDS(file.path("stocks", paste0(t, ".rds"))))
  }, error = function(e) 0)
})

cat(sprintf("  Successfully loaded metadata: %d stocks\n", nrow(successful_stocks)))
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

    # === STRATEGY-SPECIFIC METRICS ===

    # Annualized variance (for Min Variance strategy)
    annual_variance <- var(stock_data$daily_return, na.rm = TRUE) * 252

    # Downside deviation (for Sortino strategy)
    # Only considers returns below the risk-free rate
    daily_rf <- RISK_FREE_RATE / 252
    downside_returns <- stock_data$daily_return[!is.na(stock_data$daily_return)]
    downside_returns <- downside_returns - daily_rf
    downside_returns <- pmin(downside_returns, 0)  # Keep only negative deviations
    downside_deviation <- sqrt(mean(downside_returns^2)) * sqrt(252)  # Annualized

    # Sortino ratio
    annual_return <- mean(stock_data$daily_return, na.rm = TRUE) * 252
    sortino_ratio <- if (downside_deviation > 0) {
      (annual_return - RISK_FREE_RATE) / downside_deviation
    } else {
      NA
    }

    # CVaR / Expected Shortfall (for Min CVaR strategy)
    # Average return in the worst CVAR_ALPHA% of days
    sorted_returns <- sort(stock_data$daily_return[!is.na(stock_data$daily_return)])
    cutoff_idx <- floor(length(sorted_returns) * CVAR_ALPHA)
    if (cutoff_idx > 0) {
      cvar_daily <- mean(sorted_returns[1:cutoff_idx])
      cvar_annual <- cvar_daily * sqrt(252)  # Approximate annualization
    } else {
      cvar_annual <- NA
    }

    # Return summary metrics with all strategy-specific columns
    return(data.frame(
      ticker = ticker,
      sector = sector,
      cumulative_return_1y = cumulative_return,
      return_6m = return_6m,
      return_3m = return_3m,
      daily_volatility = daily_volatility,
      annual_variance = annual_variance,
      sharpe_ratio = sharpe_ratio,
      sortino_ratio = sortino_ratio,
      downside_deviation = downside_deviation,
      cvar = cvar_annual,
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
# STEP 2.5: CALCULATE ICHIMOKU SCORES
# ============================================================================

cat("\nStep 2.5: Calculating Ichimoku Cloud scores...\n")

# Ichimoku parameters (standard settings)
ICHIMOKU_TENKAN <- 9     # Conversion line period
ICHIMOKU_KIJUN <- 26     # Base line period
ICHIMOKU_SENKOU_B <- 52  # Senkou Span B period
ICHIMOKU_SHIFT <- 26     # Cloud shift / Chikou shift

# Function to calculate Ichimoku score for a stock
calculate_ichimoku_score <- function(ticker) {

  stock_data <- load_stock(ticker)

  if (is.null(stock_data) || nrow(stock_data) < ICHIMOKU_SENKOU_B + ICHIMOKU_SHIFT) {
    return(data.frame(ticker = ticker, ichimoku_score = NA, stringsAsFactors = FALSE))
  }

  tryCatch({
    # Sort by date
    stock_data <- stock_data %>% arrange(date)
    n <- nrow(stock_data)

    # Calculate rolling highs and lows using runMax/runMin from TTR
    high_9 <- runMax(stock_data$high, n = ICHIMOKU_TENKAN)
    low_9 <- runMin(stock_data$low, n = ICHIMOKU_TENKAN)
    high_26 <- runMax(stock_data$high, n = ICHIMOKU_KIJUN)
    low_26 <- runMin(stock_data$low, n = ICHIMOKU_KIJUN)
    high_52 <- runMax(stock_data$high, n = ICHIMOKU_SENKOU_B)
    low_52 <- runMin(stock_data$low, n = ICHIMOKU_SENKOU_B)

    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    tenkan <- (high_9 + low_9) / 2

    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    kijun <- (high_26 + low_26) / 2

    # Senkou Span A: (Tenkan + Kijun) / 2
    senkou_a <- (tenkan + kijun) / 2

    # Senkou Span B: (52-period high + 52-period low) / 2
    senkou_b <- (high_52 + low_52) / 2

    # Current values (latest complete day)
    current_price <- stock_data$adjusted[n]
    current_tenkan <- tenkan[n]
    current_kijun <- kijun[n]

    # Cloud values at current position (shifted 26 periods ago for current cloud)
    # Senkou Span A/B are calculated today but represent cloud 26 days ahead
    # So current cloud was calculated 26 days ago
    cloud_idx <- n - ICHIMOKU_SHIFT
    if (cloud_idx > 0) {
      current_senkou_a <- senkou_a[cloud_idx]
      current_senkou_b <- senkou_b[cloud_idx]
    } else {
      # Not enough history for cloud
      return(data.frame(ticker = ticker, ichimoku_score = NA, stringsAsFactors = FALSE))
    }

    # Future cloud (today's calculation = cloud 26 days from now)
    future_senkou_a <- senkou_a[n]
    future_senkou_b <- senkou_b[n]

    # Historical price for Chikou comparison (26 days ago)
    chikou_compare_idx <- n - ICHIMOKU_SHIFT
    historical_price <- if (chikou_compare_idx > 0) stock_data$adjusted[chikou_compare_idx] else NA

    # Cloud expansion check - compare width now vs width 5 days ago
    cloud_width_now <- abs(current_senkou_a - current_senkou_b)
    cloud_idx_5d_ago <- cloud_idx - 5
    if (cloud_idx_5d_ago > 0) {
      cloud_width_5d_ago <- abs(senkou_a[cloud_idx_5d_ago] - senkou_b[cloud_idx_5d_ago])
      cloud_expanding <- cloud_width_now > cloud_width_5d_ago
    } else {
      cloud_expanding <- FALSE
    }

    # === CALCULATE 5-POINT SCORE ===
    score <- 0

    # 1. Price above cloud (+1)
    cloud_top <- max(current_senkou_a, current_senkou_b)
    if (!is.na(cloud_top) && current_price > cloud_top) {
      score <- score + 1
    }

    # 2. TK bullish: Tenkan > Kijun (+1)
    if (!is.na(current_tenkan) && !is.na(current_kijun) && current_tenkan > current_kijun) {
      score <- score + 1
    }

    # 3. Green cloud: Span A > Span B (+1)
    if (!is.na(current_senkou_a) && !is.na(current_senkou_b) && current_senkou_a > current_senkou_b) {
      score <- score + 1
    }

    # 4. Chikou above historical price (+1)
    if (!is.na(historical_price) && current_price > historical_price) {
      score <- score + 1
    }

    # 5. Cloud expanding OR future cloud is green (+1)
    future_cloud_green <- !is.na(future_senkou_a) && !is.na(future_senkou_b) && future_senkou_a > future_senkou_b
    if (cloud_expanding || future_cloud_green) {
      score <- score + 1
    }

    return(data.frame(
      ticker = ticker,
      ichimoku_score = score,
      stringsAsFactors = FALSE
    ))

  }, error = function(e) {
    warning(sprintf("Ichimoku error for %s: %s", ticker, e$message))
    return(data.frame(ticker = ticker, ichimoku_score = NA, stringsAsFactors = FALSE))
  })
}

# Calculate Ichimoku scores for all analyzed stocks
ichimoku_scores <- bind_rows(lapply(performance_data$ticker, calculate_ichimoku_score))

# Merge Ichimoku scores into performance data
performance_data <- performance_data %>%
  left_join(ichimoku_scores, by = "ticker")

# Report distribution
score_dist <- table(performance_data$ichimoku_score, useNA = "ifany")
cat("  Ichimoku score distribution:\n")
for (i in seq_along(score_dist)) {
  score_val <- names(score_dist)[i]
  score_label <- if (is.na(score_val) || score_val == "NA") "N/A" else score_val
  cat(sprintf("    Score %s: %d stocks\n", score_label, score_dist[i]))
}

avg_score <- mean(performance_data$ichimoku_score, na.rm = TRUE)
cat(sprintf("  Average Ichimoku score: %.2f\n", avg_score))

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
cat(sprintf("    Avg Ichimoku score: %.2f/5\n",
            mean(top_performers$ichimoku_score, na.rm = TRUE)))

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
