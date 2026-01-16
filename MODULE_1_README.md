# Module 1: Stock Data Acquisition

## Overview

This module downloads historical stock price data for portfolio optimization analysis. It includes:
- Sector-based downloading with resume capability
- Pre-filtering for quality and liquidity
- Error handling with automatic retries
- Data validation and quality checks
- Utility functions for loading data in subsequent modules

## Files

- **`01_download_stock_data.R`** - Main download script
- **`utils_data_loader.R`** - Helper functions for loading and managing data
- **`MODULE_1_README.md`** - This file

## Prerequisites

### Required R Packages

The script will auto-install missing packages, but you can install manually:

```r
install.packages(c("dplyr", "quantmod", "readr", "lubridate", "stringr", "purrr"))
```

### Required Data Files

**Option 1: Nasdaq Stock Screener (Recommended)**

Place your Nasdaq Stock Screener CSV file at:
```
data/Nasdaq Stock Screener.csv
```

This file should contain columns like:
- `Symbol` or `Ticker` (required)
- `Name` or `Company` (optional)
- `Sector` (recommended for sector-based analysis)
- `Market Cap` (optional, for filtering)
- `Volume` (optional, for filtering)

**Option 2: Fallback Method**

If you don't have the Nasdaq Stock Screener, the script will use:
- `Nasdaq.csv` (basic ticker list)
- `big_stock_sectors.csv` (for sector classifications)

These files should already be in your repository.

## Directory Structure Created

```
Python4Finance/
├── data/                          # Input data
│   └── Nasdaq Stock Screener.csv
├── stocks/                        # Downloaded stock data (RDS files)
│   ├── AAPL.rds
│   ├── MSFT.rds
│   └── ...
├── metadata/                      # Download logs and metadata
│   ├── download_log.csv          # Success/failure tracking
│   ├── download_summary.txt      # Summary statistics
│   └── filtered_tickers.csv      # List of tickers that passed filters
└── [module scripts]
```

## Configuration

Edit these settings in `01_download_stock_data.R` if needed:

```r
# Download parameters
LOOKBACK_YEARS <- 2                # Years of historical data (default: 2)
MIN_VOLUME <- 100000              # Minimum avg daily volume (default: 100K)
MIN_MARKET_CAP <- 500e6           # Minimum market cap (default: $500M)
RETRY_ATTEMPTS <- 3               # Retry attempts for failed downloads
RETRY_DELAY <- 2                  # Seconds between retries
```

## Usage

### Step 1: Prepare Your Data

Place `Nasdaq Stock Screener.csv` in the `data/` folder, or ensure `Nasdaq.csv` exists in the root directory.

### Step 2: Run the Download Script

**In RStudio:**
```r
source("01_download_stock_data.R")
```

**From Command Line:**
```bash
Rscript 01_download_stock_data.R
```

### Step 3: Wait for Completion

The script will:
1. Create directory structure
2. Load and filter tickers
3. Download data sector by sector
4. Save progress continuously (can resume if interrupted)
5. Generate summary report

**Expected Runtime:**
- ~800-1,200 stocks: 15-30 minutes
- Full Wilshire 5000 (~2,000+ stocks): 1-2 hours

### Step 4: Review Results

Check the summary:
```r
cat(readLines("metadata/download_summary.txt"), sep = "\n")
```

Or in R:
```r
source("utils_data_loader.R")
get_download_summary()
```

## Resume Capability

If the download is interrupted:
1. Simply run `source("01_download_stock_data.R")` again
2. Already downloaded stocks will be automatically skipped
3. Downloads will resume from where they stopped

## Loading Data (For Next Modules)

Load the utility functions:
```r
source("utils_data_loader.R")
```

**Load single stock:**
```r
aapl <- load_stock("AAPL")
head(aapl)
```

**Load multiple stocks:**
```r
my_stocks <- load_multiple_stocks(c("AAPL", "MSFT", "GOOGL"))
```

**Load by sector:**
```r
tech_stocks <- load_stocks_by_sector("Information Technology")
healthcare <- load_stocks_by_sector("Healthcare")
```

**Get available tickers:**
```r
all_tickers <- get_available_tickers()
sectors <- get_available_sectors()
```

**Check data availability:**
```r
check_data_availability(c("AAPL", "MSFT", "INVALID"))
```

**Calculate returns:**
```r
aapl <- load_stock("AAPL")
aapl_with_returns <- calculate_returns(aapl)

# View cumulative return
plot(aapl_with_returns$date, aapl_with_returns$cumulative_return, type = "l")
```

**Create returns matrix (for correlation analysis):**
```r
portfolio <- load_multiple_stocks(c("AAPL", "MSFT", "GOOGL", "AMZN"))
returns_matrix <- create_returns_matrix(portfolio)
head(returns_matrix)
```

## Data Format

Each stock RDS file contains a data frame with:

| Column    | Description                           |
|-----------|---------------------------------------|
| date      | Trading date                          |
| open      | Opening price                         |
| high      | Highest price of the day              |
| low       | Lowest price of the day               |
| close     | Closing price                         |
| volume    | Number of shares traded               |
| adjusted  | Adjusted closing price (for dividends/splits) |

## Filters Applied

The script applies these filters before downloading:

1. **Basic Cleaning:**
   - Remove NA tickers
   - Remove duplicates
   - Remove likely ETFs (tickers with `^` or `-`)
   - Keep tickers ≤ 5 characters

2. **Market Cap Filter:** (if data available)
   - Minimum: $500M market cap

3. **Volume Filter:** (if data available)
   - Minimum: 100,000 shares/day average volume

4. **Data Quality Validation:**
   - Minimum 400 trading days (~2 years with some buffer)
   - No zero or negative prices
   - Less than 10% missing data

## Troubleshooting

### Issue: "Could not find ticker data"

**Solution:** Ensure either:
- `data/Nasdaq Stock Screener.csv` exists, OR
- `Nasdaq.csv` exists in the root directory

### Issue: Many failed downloads

**Possible causes:**
1. **Network issues** - Check internet connection
2. **Delisted stocks** - Normal, script will log and continue
3. **API rate limiting** - Script includes delays, but you can increase `RETRY_DELAY`

**Check the download log:**
```r
log <- read.csv("metadata/download_log.csv")
failed <- log[log$success == FALSE, ]
table(failed$error)  # See what errors occurred
```

### Issue: Out of memory

**Solution:** The script saves to disk immediately (no data held in memory). If R itself crashes:
1. Increase R memory: `memory.limit(size = 16000)` (Windows)
2. Close other applications
3. Download by sector (already implemented - script does this automatically)

### Issue: Want to re-download specific stocks

**Solution:** Delete the RDS files you want to re-download:
```r
# Delete single stock
file.remove("stocks/AAPL.rds")

# Delete multiple
lapply(c("AAPL", "MSFT"), function(t) file.remove(paste0("stocks/", t, ".rds")))

# Then re-run the download script
```

### Issue: Want to update data (refresh with latest prices)

**Solution 1: Delete all and re-download**
```r
unlink("stocks/*.rds")
source("01_download_stock_data.R")
```

**Solution 2: Create an update script** (downloads only last N days)
- This will be included in a future module

## Performance Tips

1. **Run overnight** for large downloads (1000+ stocks)
2. **Use SSD** for faster file I/O
3. **Stable internet** required (WiFi recommended over cellular)
4. **Don't interrupt mid-sector** - let each sector complete for cleaner logs

## Data Usage Statistics

Approximate disk space per stock:
- 1 year: ~5-10 KB
- 2 years: ~10-20 KB
- Total for 1,000 stocks: ~10-20 MB

This is very lightweight!

## Next Steps

After downloading data, proceed to:
- **Module 2:** Technical analysis (cumulative returns, Bollinger Bands)
- **Module 3:** Stock screening (top performers by sector)
- **Module 4:** Correlation analysis

## Support

For issues or questions:
1. Check the download log: `metadata/download_log.csv`
2. Review the summary: `metadata/download_summary.txt`
3. Test loading a few stocks manually to verify data integrity

## Example: Complete Workflow

```r
# 1. Download data
source("01_download_stock_data.R")

# 2. Load utilities
source("utils_data_loader.R")

# 3. Check what you have
get_download_summary()
available_sectors <- get_available_sectors()
print(available_sectors)

# 4. Load some stocks
tech <- load_stocks_by_sector("Information Technology")
names(tech)  # See which tech stocks downloaded

# 5. Quick analysis
aapl <- load_stock("AAPL")
aapl <- calculate_returns(aapl)

plot(aapl$date, aapl$cumulative_return, type = "l",
     main = "AAPL Cumulative Return",
     xlab = "Date", ylab = "Return")
```

---

**Module 1 Complete!** You now have a robust stock data acquisition system ready for portfolio optimization.
