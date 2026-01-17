# Module 2: Technical Analysis & Stock Screening

## Overview

This module analyzes all downloaded stocks, calculates technical indicators, and screens for top performers by sector. It prepares a high-quality candidate list for portfolio optimization.

## What It Does

1. **Calculates Technical Indicators:**
   - Cumulative returns (1-year, 6-month, 3-month)
   - Daily volatility
   - Sharpe ratio
   - Bollinger Bands (20-day, ±2 SD)
   - Average volume

2. **Applies Screening Filters:**
   - Minimum data requirement (400+ trading days)
   - Minimum average volume (100K shares/day)
   - Maximum volatility (5% daily)
   - Positive 3-month momentum

3. **Ranks by Sector:**
   - Selects top 10 performers per sector
   - Ensures sector diversification
   - Balances performance with risk

4. **Generates Outputs:**
   - Candidate stock list for correlation analysis
   - Performance metrics for all stocks
   - Bollinger Bands data for top performers
   - Summary statistics and reports

## Files

- **`02_technical_analysis_screening.R`** - Main analysis script
- **`MODULE_2_README.md`** - This file

## Prerequisites

### Completed Module 1
You must have successfully downloaded stock data using Module 1.

Required files from Module 1:
- `stocks/` directory with downloaded RDS files
- `metadata/download_log.csv`

### R Packages

Auto-installed by script, but you can install manually:
```r
install.packages(c("dplyr", "tidyr", "TTR", "purrr", "lubridate"))
```

## Configuration

You can adjust these parameters in `02_technical_analysis_screening.R`:

```r
# Screening parameters
ANALYSIS_PERIOD <- 252        # Days for performance ranking (1 year)
MIN_TRADING_DAYS <- 400       # Minimum data requirement
TOP_N_PER_SECTOR <- 10        # Top performers per sector
MIN_AVG_VOLUME <- 100000      # Minimum daily volume
MAX_VOLATILITY <- 0.05        # Maximum daily volatility (5%)

# Bollinger Bands parameters
BB_PERIOD <- 20               # Moving average period
BB_SD <- 2                    # Standard deviations
```

## Usage

### Run the Analysis

```r
source("02_technical_analysis_screening.R")
```

**Expected runtime:** 5-15 minutes for 2,000+ stocks

### What Happens

The script will:
1. Load stock metadata from Module 1
2. Calculate technical indicators for all valid stocks
3. Apply screening filters
4. Rank by sector and select top performers
5. Generate Bollinger Bands data
6. Save candidate list and reports

### Output Files

All outputs are saved in the `analysis/` directory:

```
analysis/
├── candidate_stocks.csv           # Top performers by sector (main output)
├── candidate_stocks.rds           # Same data in RDS format
├── performance_summary.csv        # All stocks with metrics
├── bollinger_bands_data.rds       # BB data for top 10 stocks
└── module_2_summary.txt           # Summary report
```

## Output Format

### Candidate Stocks (`candidate_stocks.csv`)

| Column               | Description                          |
|----------------------|--------------------------------------|
| ticker               | Stock ticker symbol                  |
| sector               | Industry sector                      |
| cumulative_return_1y | 1-year cumulative return             |
| return_6m            | 6-month return                       |
| return_3m            | 3-month return                       |
| daily_volatility     | Standard deviation of daily returns  |
| sharpe_ratio         | Risk-adjusted return metric          |
| avg_volume           | Average daily trading volume         |
| bb_position          | Position within Bollinger Bands (0-1)|
| current_price        | Latest adjusted close price          |
| latest_date          | Most recent data date                |
| sector_rank          | Rank within sector (by 1-yr return)  |
| sector_size          | Number of stocks in sector           |

## Screening Logic

### Step-by-Step Filtering

1. **Data Quality Filter:**
   - Require minimum 400 trading days (~2 years)
   - Ensures sufficient data for reliable metrics

2. **Liquidity Filter:**
   - Average daily volume ≥ 100,000 shares
   - Ensures tradability and price stability

3. **Risk Filter:**
   - Daily volatility ≤ 5%
   - Removes extremely volatile/risky stocks

4. **Momentum Filter:**
   - 3-month return > 0%
   - Focuses on stocks with recent positive momentum

5. **Sector Ranking:**
   - Rank all remaining stocks within their sector
   - Select top 10 per sector by 1-year cumulative return

### Why Screen by Sector?

✅ **Ensures diversification** - Won't end up with all tech stocks

✅ **Reduces correlation** - Stocks from different sectors are less correlated

✅ **Balanced risk** - Mix of growth and defensive sectors

✅ **Aligns with Modern Portfolio Theory** - Diversification is key

## Loading Results

### Load Candidate Stocks

```r
# From RDS (faster)
candidates <- readRDS("analysis/candidate_stocks.rds")

# From CSV (portable)
candidates <- read.csv("analysis/candidate_stocks.csv")

# View
head(candidates)
summary(candidates)
```

### View by Sector

```r
library(dplyr)

# See count by sector
candidates %>%
  count(sector, sort = TRUE)

# Get specific sector
tech_candidates <- candidates %>%
  filter(sector == "Technology")

# Top performers across all sectors
top_overall <- candidates %>%
  arrange(desc(cumulative_return_1y)) %>%
  head(20)

print(top_overall)
```

### Load Bollinger Bands Data

```r
# Load BB data for top performers
bb_data <- readRDS("analysis/bollinger_bands_data.rds")

# List available stocks
names(bb_data)

# Get data for specific stock
aapl_bb <- bb_data[["AAPL"]]

# Plot Bollinger Bands
plot(aapl_bb$date, aapl_bb$adjusted, type = "l",
     main = "AAPL with Bollinger Bands",
     xlab = "Date", ylab = "Price")
lines(aapl_bb$date, aapl_bb$up, col = "red", lty = 2)    # Upper band
lines(aapl_bb$date, aapl_bb$dn, col = "red", lty = 2)    # Lower band
lines(aapl_bb$date, aapl_bb$mavg, col = "blue")          # Moving average
legend("topleft", legend = c("Price", "Upper BB", "Lower BB", "MA"),
       col = c("black", "red", "red", "blue"),
       lty = c(1, 2, 2, 1))
```

### Analyze Performance Distribution

```r
# Return statistics
summary(candidates$cumulative_return_1y)

# Histogram of returns
hist(candidates$cumulative_return_1y,
     breaks = 30,
     main = "Distribution of 1-Year Returns",
     xlab = "Cumulative Return")

# Sharpe ratio distribution
boxplot(sharpe_ratio ~ sector, data = candidates,
        main = "Sharpe Ratio by Sector",
        las = 2)  # Rotate labels
```

## Understanding the Metrics

### Cumulative Return
- **What:** Total return over the period
- **Example:** 0.25 = 25% gain
- **Use:** Primary performance metric

### Sharpe Ratio
- **What:** Return per unit of risk
- **Higher is better:** >1 is good, >2 is excellent
- **Use:** Risk-adjusted performance comparison

### Daily Volatility
- **What:** Standard deviation of daily returns
- **Example:** 0.02 = 2% daily volatility
- **Use:** Risk assessment

### Bollinger Bands Position
- **What:** Where price sits within bands (0 to 1)
- **0.5:** Middle of bands (on moving average)
- **<0.3:** Near lower band (potentially oversold)
- **>0.7:** Near upper band (potentially overbought)
- **Use:** Entry/exit timing indicator

## Typical Results

Based on your download of **2,725 stocks**:

**Expected Candidates:** 80-130 stocks
- ~10 per sector across 13 sectors
- Some sectors may have fewer than 10 qualifying stocks

**Expected Performance Range:**
- Average 1-year return: 15-30%
- Average Sharpe ratio: 0.8-1.5
- Average daily volatility: 2-3%

## Troubleshooting

### Issue: "No stocks pass screening"

**Possible causes:**
1. Filters too strict for current market conditions
2. Downloaded data doesn't cover full time period

**Solutions:**
- Reduce `MIN_AVG_VOLUME` (try 50,000)
- Increase `MAX_VOLATILITY` (try 0.07 or 7%)
- Reduce `MIN_TRADING_DAYS` (try 300)

### Issue: "Error in calculation for specific stocks"

**Normal:** Some stocks may have data issues
- Script will skip them and continue
- Check warnings for details

### Issue: "Too few candidates in some sectors"

**Expected:** Some sectors naturally have fewer qualifying stocks
- Unknown sector often has <10 stocks
- Utilities, Energy may have fewer high-growth candidates
- This is normal and reflects market reality

### Issue: "Script runs very slowly"

**Expected for large datasets**
- 2,000+ stocks may take 10-15 minutes
- Progress updates every 50 stocks
- Can't be easily parallelized due to memory constraints

**To speed up:**
- Close other R sessions
- Run on a faster machine
- Process in smaller batches (modify script)

## Next Steps

After Module 2, you'll have a curated list of high-quality candidates.

**Module 3 will:**
- Calculate correlation matrix for candidates
- Select 9-12 least-correlated stocks
- Ensure sector diversity
- Prepare for Ichimoku validation

**Preview of Module 3:**
```r
# Load candidates
candidates <- readRDS("analysis/candidate_stocks.rds")

# Module 3 will create returns matrix
# Calculate correlation
# Apply greedy selection algorithm
# Output: Final portfolio stocks for optimization
```

## Advanced Usage

### Custom Sector Selection

```r
# Modify after loading candidates
# Select only specific sectors
target_sectors <- c("Technology", "Health Care", "Finance",
                    "Consumer Discretionary", "Industrials")

custom_candidates <- candidates %>%
  filter(sector %in% target_sectors)

# Re-rank within selected sectors
custom_candidates <- custom_candidates %>%
  group_by(sector) %>%
  mutate(sector_rank = rank(-cumulative_return_1y)) %>%
  filter(sector_rank <= 10) %>%
  ungroup()
```

### Adjust Screening Criteria

```r
# More aggressive screening (higher returns, higher risk)
aggressive <- performance_data %>%
  filter(
    avg_volume >= 50000,          # Lower volume OK
    daily_volatility <= 0.08,     # Allow more volatility
    return_6m > 0.15              # Require strong 6-month return
  )

# Conservative screening (lower risk)
conservative <- performance_data %>%
  filter(
    avg_volume >= 500000,         # High liquidity only
    daily_volatility <= 0.03,     # Low volatility
    sharpe_ratio > 1.0,           # Strong risk-adjusted returns
    return_1y > 0, return_6m > 0  # Consistent positive returns
  )
```

### Export for Excel Analysis

```r
# Load candidates
candidates <- readRDS("analysis/candidate_stocks.rds")

# Format for Excel
excel_export <- candidates %>%
  mutate(
    return_1y_pct = sprintf("%.2f%%", 100 * cumulative_return_1y),
    return_6m_pct = sprintf("%.2f%%", 100 * return_6m),
    return_3m_pct = sprintf("%.2f%%", 100 * return_3m),
    volatility_pct = sprintf("%.2f%%", 100 * daily_volatility),
    sharpe = sprintf("%.2f", sharpe_ratio)
  ) %>%
  select(ticker, sector, return_1y_pct, return_6m_pct, return_3m_pct,
         volatility_pct, sharpe, avg_volume, current_price)

write.csv(excel_export, "analysis/candidates_for_excel.csv", row.names = FALSE)
```

## Support

Check these files for diagnostics:
- `analysis/module_2_summary.txt` - Overall summary
- `analysis/performance_summary.csv` - All analyzed stocks
- Warnings in R console - Individual stock issues

---

**Module 2 Complete!** You now have a screened list of top-performing stocks ready for correlation analysis and portfolio optimization.
