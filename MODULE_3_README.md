# Module 3: Correlation Analysis & Portfolio Selection

## Overview

This module takes your ~130 high-performing candidates from Module 2 and selects the final 12 stocks for your portfolio using correlation analysis and a greedy selection algorithm. It ensures maximum diversification while maintaining high returns.

## What It Does

1. **Loads Candidate Stocks** from Module 2
2. **Creates Returns Matrix** for all candidates (1 year of daily returns)
3. **Calculates Correlation Matrix** (Pearson correlation)
4. **Applies Greedy Selection Algorithm:**
   - Stage 1: Select top performer from each major sector (ensures diversity)
   - Stage 2: Add remaining stocks with lowest correlation and highest Sharpe ratio
5. **Enforces Constraints:**
   - Maximum 3 stocks from any single sector
   - Minimum 6 different sectors represented
   - Average correlation < 0.5
6. **Generates Outputs:**
   - Final 12-stock portfolio
   - Correlation matrix and heatmap
   - Detailed analysis report

## Configuration Used

Based on your approval of recommended defaults:

```r
TARGET_PORTFOLIO_SIZE <- 12       # 12 stocks
MAX_CORRELATION <- 0.5            # Moderate correlation threshold
MIN_SECTORS <- 6                  # Minimum sector diversity
MAX_PER_SECTOR <- 3               # Prevent sector concentration
USE_SHARPE_WEIGHTING <- TRUE      # Weight by risk-adjusted returns
EXCLUDE_UNKNOWN_SECTOR <- FALSE   # Flag but don't exclude Unknown sector
CORRELATION_PERIOD <- 252         # 1 year of data
```

## Files

- **`03_correlation_analysis.R`** - Main correlation & selection script
- **`MODULE_3_README.md`** - This file

## Prerequisites

### Completed Module 2
Requires `analysis/candidate_stocks.rds` from Module 2

### R Packages
Auto-installed by script:
```r
install.packages(c("corrplot", "reshape2"))
```

## Usage

### Run the Analysis

```r
source("03_correlation_analysis.R")
```

**Expected runtime:** 3-8 minutes for 130 candidates

### What Happens

The script will:
1. Load your 130 candidates
2. Download returns data for all candidates
3. Calculate 130×130 correlation matrix
4. Run two-stage greedy selection algorithm
5. Select final 12 stocks with optimal diversification
6. Generate correlation heatmap
7. Save portfolio and analysis reports

### Output Files

All outputs in `analysis/` directory:

```
analysis/
├── final_portfolio.csv            # Your 12 selected stocks (main output)
├── final_portfolio.rds            # Same in RDS format
├── correlation_matrix.csv         # Full correlation matrix
├── correlation_matrix.rds         # Same in RDS format
├── portfolio_correlation_heatmap.pdf  # Visual correlation map
├── portfolio_correlation_heatmap.rds  # Heatmap data
└── module_3_summary.txt           # Analysis summary
```

## Selection Algorithm Explained

### Stage 1: Sector Diversity (Stocks 1-6)

Ensures you start with a well-diversified base:

```
For each of the 6 largest sectors:
  - Select the stock with highest Sharpe ratio
  - Add to portfolio
```

This guarantees you won't end up with all stocks from one or two sectors.

### Stage 2: Greedy Optimization (Stocks 7-12)

Fills remaining slots with best available stocks:

```
While portfolio < 12 stocks:
  For each remaining candidate:
    - Calculate average correlation with already-selected stocks
    - Calculate selection score = Sharpe ratio × (1 - avg_correlation)
    - Check sector constraint (max 3 per sector)

  Select highest-scoring stock that doesn't violate constraints
  Add to portfolio
```

**Why this works:**
- Balances performance (Sharpe ratio) with diversification (low correlation)
- Sector constraints prevent over-concentration
- Greedy approach is interpretable and fast

## Output Format

### Final Portfolio (`final_portfolio.csv`)

| Column               | Description                              |
|----------------------|------------------------------------------|
| ticker               | Stock ticker symbol                      |
| sector               | Industry sector                          |
| cumulative_return_1y | 1-year cumulative return                 |
| return_6m            | 6-month return                           |
| return_3m            | 3-month return                           |
| daily_volatility     | Daily return standard deviation          |
| sharpe_ratio         | Risk-adjusted return metric              |
| avg_volume           | Average daily trading volume             |
| bb_position          | Bollinger Band position                  |
| current_price        | Latest price                             |
| latest_date          | Most recent data date                    |
| sector_rank          | Original rank within sector              |
| sector_size          | Number in sector                         |
| avg_correlation      | Average correlation with other portfolio stocks |

## Understanding Correlation

### What is Correlation?

Correlation measures how two stocks move together:
- **+1.0:** Perfect positive correlation (move identically)
- **0.0:** No correlation (move independently)
- **-1.0:** Perfect negative correlation (move oppositely)

### Correlation Thresholds

- **< 0.3:** Low correlation - Excellent diversification
- **0.3 - 0.5:** Moderate correlation - Good diversification
- **0.5 - 0.7:** High correlation - Limited diversification benefit
- **> 0.7:** Very high correlation - Similar to holding same stock

### Why Low Correlation Matters

**Example with 2 stocks:**
- Stock A and B both have 20% annual return, 15% volatility
- If correlation = 1.0: Portfolio has 15% volatility
- If correlation = 0.5: Portfolio has 12% volatility
- If correlation = 0.0: Portfolio has 10.6% volatility

**Lower correlation = same return with less risk!**

## Loading and Analyzing Results

### Load Final Portfolio

```r
# Load the portfolio
portfolio <- readRDS("analysis/final_portfolio.rds")

# View it
print(portfolio)

# Summary stats
summary(portfolio$sharpe_ratio)
summary(portfolio$avg_correlation)

# Sector distribution
table(portfolio$sector)
```

### View Correlation Matrix

```r
library(corrplot)

# Load correlation data
portfolio_corr <- readRDS("analysis/portfolio_correlation_heatmap.rds")

# Create interactive heatmap
corrplot(portfolio_corr,
         method = "color",
         type = "upper",
         addCoef.col = "black",  # Show correlation values
         tl.col = "black",       # Ticker label color
         tl.srt = 45,            # Rotate labels
         title = "Portfolio Correlation Matrix")
```

### Analyze Pairwise Correlations

```r
# Get upper triangle (unique pairs)
corr_values <- portfolio_corr[upper.tri(portfolio_corr)]

# Statistics
mean(corr_values)      # Average correlation
median(corr_values)    # Median correlation
range(corr_values)     # Min and max

# Histogram
hist(corr_values, breaks = 20,
     main = "Distribution of Pairwise Correlations",
     xlab = "Correlation")
abline(v = 0.5, col = "red", lty = 2)  # Your threshold
```

### Find Highest/Lowest Correlation Pairs

```r
# Convert to data frame
corr_df <- as.data.frame(as.table(portfolio_corr))
names(corr_df) <- c("Stock1", "Stock2", "Correlation")

# Remove diagonal and duplicates
corr_df <- corr_df %>%
  filter(Stock1 != Stock2) %>%
  filter(as.character(Stock1) < as.character(Stock2))

# Highest correlations
corr_df %>%
  arrange(desc(Correlation)) %>%
  head(5)

# Lowest correlations
corr_df %>%
  arrange(Correlation) %>%
  head(5)
```

## Expected Results

Based on your 130 candidates with 140% average return:

### Portfolio Metrics (Expected)

- **Total stocks:** 12
- **Sectors:** 6-8 different sectors
- **Average 1-year return:** 150-200% (slightly higher than overall average)
- **Average Sharpe ratio:** 1.3-1.8 (top performers tend to have higher Sharpe)
- **Average correlation:** 0.25-0.40 (well-diversified)

### Typical Sector Distribution

- Technology: 2-3 stocks
- Industrials: 1-2 stocks
- Basic Materials: 1-2 stocks
- Healthcare: 1-2 stocks
- Consumer Discretionary: 1-2 stocks
- Other sectors: 3-4 stocks

## Interpreting Your Results

### Good Portfolio Characteristics

✅ **Average correlation < 0.4** - Excellent diversification

✅ **6+ different sectors** - Industry diversification

✅ **No sector > 25% of portfolio** - No concentration risk

✅ **Mix of low and moderate correlations** - Some pairs can be higher if offset by low pairs

✅ **High Sharpe ratios** - Risk-adjusted performance

### Warning Signs

⚠️ **Average correlation > 0.6** - May need to adjust selection

⚠️ **Only 3-4 sectors** - Insufficient diversification

⚠️ **One sector has 4+ stocks** - Over-concentration

⚠️ **Many stocks from "Unknown" sector** - Review sector classifications

## Troubleshooting

### Issue: Portfolio has high average correlation (>0.5)

**Possible causes:**
- Market conditions (all stocks moving together)
- Candidates from related industries
- Recent market trends affecting correlations

**Solutions:**
- Decrease `MAX_CORRELATION` to 0.4 or 0.3
- Increase `MIN_SECTORS` to 7 or 8
- Manually exclude highly correlated sectors

### Issue: Can't reach target portfolio size (12 stocks)

**Possible causes:**
- Sector constraints too strict
- Correlation threshold too low
- Insufficient candidates

**Solutions:**
- Increase `MAX_PER_SECTOR` to 4
- Relax `MAX_CORRELATION` to 0.6
- Reduce `TARGET_PORTFOLIO_SIZE` to 10

### Issue: "Unknown" sector stocks selected

**This is flagged but allowed:**
- Review the stocks manually
- Check if you can identify their sectors
- Decision is yours whether to keep them

**To exclude automatically:**
- Set `EXCLUDE_UNKNOWN_SECTOR <- TRUE` in script
- Re-run Module 3

### Issue: Portfolio heavily weighted to one sector

**Normal if that sector has many high performers:**
- MAX_PER_SECTOR is set to 3 (25% of portfolio)
- This is reasonable sector concentration
- If uncomfortable, reduce to 2

## Customization Examples

### More Aggressive (Higher Returns, Less Diversification)

```r
TARGET_PORTFOLIO_SIZE <- 10       # Fewer stocks
MAX_CORRELATION <- 0.6            # Allow higher correlation
MIN_SECTORS <- 5                  # Fewer sectors required
MAX_PER_SECTOR <- 4               # Allow more concentration
```

### More Conservative (Maximum Diversification)

```r
TARGET_PORTFOLIO_SIZE <- 15       # More stocks
MAX_CORRELATION <- 0.3            # Stricter correlation
MIN_SECTORS <- 8                  # More sectors required
MAX_PER_SECTOR <- 2               # Less concentration
```

### Pure Correlation (Ignore Returns)

```r
USE_SHARPE_WEIGHTING <- FALSE     # Don't weight by Sharpe ratio
```

This will pick stocks purely on low correlation, regardless of performance.

## Next Steps

After Module 3, you'll have your final 12 stocks ready for:

**Module 4: Ichimoku Technical Validation**
- Calculate Ichimoku Cloud indicators
- Validate bullish/bearish signals
- Confirm technical strength
- Flag any concerning technical patterns

**Module 5: Portfolio Optimization**
- Calculate efficient frontier
- Find optimal weights
- Maximize Sharpe ratio
- Generate dollar allocations

**Module 6: Backtesting**
- Test historical performance
- Compare to benchmarks
- Validate strategy

## Advanced Analysis

### Compare Your Portfolio to Alternatives

```r
# Load all candidates
all_candidates <- readRDS("analysis/candidate_stocks.rds")

# Your portfolio
portfolio <- readRDS("analysis/final_portfolio.rds")

# Alternative: Top 12 by return only
top_12_return <- all_candidates %>%
  arrange(desc(cumulative_return_1y)) %>%
  head(12)

# Compare average correlations
# (Need to calculate correlation for top_12_return stocks)

# Compare average Sharpe ratios
cat("Your portfolio avg Sharpe:", mean(portfolio$sharpe_ratio), "\n")
cat("Top 12 by return avg Sharpe:", mean(top_12_return$sharpe_ratio), "\n")
```

### Sensitivity Analysis

Test how portfolio changes with different parameters:

```r
# Save current portfolio
portfolio_moderate <- readRDS("analysis/final_portfolio.rds")

# Modify script to use MAX_CORRELATION <- 0.3
# Re-run
portfolio_strict <- readRDS("analysis/final_portfolio.rds")

# Compare
setdiff(portfolio_strict$ticker, portfolio_moderate$ticker)  # Different stocks
```

## Support

Check these files for diagnostics:
- `analysis/module_3_summary.txt` - Overall results
- `analysis/final_portfolio.csv` - Your selected stocks
- `analysis/portfolio_correlation_heatmap.pdf` - Visual correlation
- R console warnings - Any issues during selection

---

**Module 3 Complete!** You now have a mathematically optimized, well-diversified portfolio of 12 stocks ready for technical validation and portfolio optimization.
