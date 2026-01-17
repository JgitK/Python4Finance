# Module 6: Backtesting & Validation

## Overview

This final module validates your portfolio optimization strategy by testing it on historical data. It compares your optimized portfolio to benchmarks (S&P 500 and equal-weight) to confirm the strategy works in practice.

## What It Does

1. **Loads Optimized Portfolio** from Module 5
2. **Sets Up Test Period:**
   - Training: 2 years ago to 6 months ago
   - Testing: Last 6 months to today
3. **Downloads Benchmark Data** (S&P 500)
4. **Calculates Portfolio Performance:**
   - Total return
   - Annualized return
   - Volatility (risk)
   - Sharpe ratio
   - Maximum drawdown
5. **Compares to Benchmarks:**
   - S&P 500 (market benchmark)
   - Equal-weight portfolio (naive strategy)
6. **Generates Visualizations:**
   - Performance comparison chart
   - Drawdown chart
7. **Calculates Alpha and Beta:**
   - Alpha: Outperformance vs market
   - Beta: Sensitivity to market movements

## Why Backtest?

**Backtesting validates that your strategy actually works.**

Without backtesting:
- ❌ You don't know if optimization overfitted to recent data
- ❌ Can't assess real-world risk (drawdowns, volatility)
- ❌ No benchmark comparison

With backtesting:
- ✅ Confirms strategy works on unseen data
- ✅ Shows actual risk metrics
- ✅ Proves you beat the market (or not!)
- ✅ Builds confidence before investing real money

## Walk-Forward Testing

This module uses **walk-forward testing**:

```
|---- Training Period ----|---- Test Period ----|
|  (build strategy)       |   (validate it)     |
| 2 years ago → 6mo ago  |  6mo ago → today    |
```

**Why this works:**
- Strategy built on old data (training)
- Performance measured on new data (test)
- Simulates real investing: you can't use future data!

## Files

- **`06_backtest_validation.R`** - Main backtesting script
- **`MODULE_6_README.md`** - This file

## Prerequisites

### Completed Module 5
Requires:
- `analysis/final_portfolio.rds`
- `analysis/optimal_weights.rds`

### R Packages
Auto-installed by script:
```r
install.packages(c("PerformanceAnalytics", "ggplot2"))
```

## Configuration

Default settings (in script):

```r
TRAINING_START <- Sys.Date() - 365 * 2    # 2 years ago
TRAINING_END <- Sys.Date() - 180          # 6 months ago
TEST_START <- TRAINING_END + 1            # 6 months ago
TEST_END <- Sys.Date()                    # Today
BENCHMARK_TICKER <- "^GSPC"               # S&P 500
```

**Can adjust:**
- Test period length (default: 6 months)
- Benchmark ticker
- Risk-free rate

## Usage

### Run the Backtest

```r
source("06_backtest_validation.R")
```

**Expected runtime:** 2-4 minutes (downloads S&P 500 data)

### What Happens

The script will:
1. Load your 12-stock portfolio with optimal weights
2. Download 6 months of historical data
3. Download S&P 500 benchmark data
4. Calculate daily returns
5. Compute portfolio performance
6. Compare to benchmarks
7. Generate performance charts
8. Save all results

### Output Files

```
analysis/backtest/
├── backtest_results.csv             # Daily performance data
├── backtest_results.rds
├── performance_comparison.pdf       # Performance vs benchmarks
├── performance_comparison.png       # (Open this!)
├── drawdown.pdf                     # Drawdown chart
├── drawdown.png
└── backtest_summary.txt             # Full report
```

## Output Metrics

### Total Return
Cumulative return over test period.
- Example: 45.2% over 6 months

### Annualized Return
Total return scaled to 1 year.
- Formula: (1 + Total Return)^(252/Days) - 1
- Example: 45.2% over 6 months = ~90% annualized

### Volatility (Risk)
Standard deviation of daily returns, annualized.
- Example: 28% annual volatility
- Higher = more ups and downs

### Sharpe Ratio
Risk-adjusted return metric.
- Formula: (Return - Risk-Free Rate) / Volatility
- > 1.0 = Good
- > 2.0 = Excellent
- > 3.0 = Exceptional

### Maximum Drawdown
Largest peak-to-trough decline.
- Example: -15.3%
- Shows worst-case scenario
- Important for risk management

### Alpha
Outperformance vs benchmark.
- Alpha = Your Return - Benchmark Return
- Positive alpha = Beat the market!
- Example: +25% alpha vs S&P 500

### Beta
Market sensitivity.
- Beta = 1.0: Moves with market
- Beta > 1.0: More volatile than market
- Beta < 1.0: Less volatile than market
- Example: Beta = 1.3 (30% more volatile)

## Loading and Analyzing Results

### Load Performance Data

```r
# Load backtest results
backtest <- readRDS("analysis/backtest/backtest_results.rds")

# View first few days
head(backtest)

# Total return
tail(backtest$cumulative_return, 1)

# Best day
backtest[which.max(backtest$daily_return), ]

# Worst day
backtest[which.min(backtest$daily_return), ]
```

### View Performance Charts

**Main chart:**
Open `analysis/backtest/performance_comparison.png`

Shows 3 lines:
- **Green:** Your optimized portfolio
- **Blue:** Equal-weight portfolio
- **Red:** S&P 500 benchmark

**Drawdown chart:**
Open `analysis/backtest/drawdown.png`

Shows when portfolio was below its previous peak.

### Calculate Additional Metrics

```r
backtest <- readRDS("analysis/backtest/backtest_results.rds")

# Win rate (% of positive days)
win_rate <- sum(backtest$daily_return > 0, na.rm = TRUE) /
            sum(!is.na(backtest$daily_return))
cat(sprintf("Win rate: %.1f%%\n", 100 * win_rate))

# Average winning day
avg_win <- mean(backtest$daily_return[backtest$daily_return > 0], na.rm = TRUE)
cat(sprintf("Average win: %.2f%%\n", 100 * avg_win))

# Average losing day
avg_loss <- mean(backtest$daily_return[backtest$daily_return < 0], na.rm = TRUE)
cat(sprintf("Average loss: %.2f%%\n", 100 * avg_loss))

# Profit factor (wins/losses)
total_wins <- sum(backtest$daily_return[backtest$daily_return > 0], na.rm = TRUE)
total_losses <- abs(sum(backtest$daily_return[backtest$daily_return < 0], na.rm = TRUE))
profit_factor <- total_wins / total_losses
cat(sprintf("Profit factor: %.2f\n", profit_factor))
```

## Interpreting Results

### Scenario 1: Portfolio Beats Everything

**Results:**
- Your portfolio: +50% return
- S&P 500: +10% return
- Equal weight: +40% return
- Sharpe ratio: 2.5
- Max drawdown: -12%

**Interpretation:**
✅ **Strategy validated!**
- Optimization worked
- Beat market and naive strategy
- Good risk-adjusted returns
- Ready to implement

---

### Scenario 2: Beats Equal Weight, Not S&P 500

**Results:**
- Your portfolio: +15% return
- S&P 500: +20% return (strong bull market)
- Equal weight: +12% return
- Sharpe ratio: 1.8

**Interpretation:**
✓ **Optimization working, market very strong**
- You're in volatile growth stocks
- S&P 500 had unusual run
- Still beat equal-weight (optimization helped)
- Sharpe ratio good (risk-adjusted you did well)
- **Decision:** Likely still good strategy

---

### Scenario 3: Beats S&P 500, Not Equal Weight

**Results:**
- Your portfolio: +18% return
- S&P 500: +10% return
- Equal weight: +22% return
- Sharpe ratio: 1.5

**Interpretation:**
~ **Mixed results**
- Beat market (good!)
- Optimization didn't help vs equal-weight
- Possible causes:
  - Short test period (6 months not enough)
  - Market regime change
  - Your stocks correlated differently than expected
- **Decision:** Monitor longer or re-optimize

---

### Scenario 4: Underperforms Both

**Results:**
- Your portfolio: +5% return
- S&P 500: +12% return
- Equal weight: +15% return
- Max drawdown: -25%

**Interpretation:**
⚠️ **Strategy needs review**
- Something went wrong
- Check for:
  - Data issues
  - Optimization overfitting
  - Wrong market conditions
  - Implementation errors
- **Decision:** Don't implement yet, investigate

---

## Expected Results

Given your strong candidates (140% avg return, 1.17 Sharpe):

### Likely Backtest Performance

**Over 6 months:**
- Portfolio return: 30-60%
- S&P 500 return: 5-15% (typical)
- Equal-weight: 25-55%
- Alpha vs S&P: +20-40%
- Sharpe ratio: 1.5-3.0
- Max drawdown: 10-20%

**Why so high?**
- Your stocks had 140% avg 1-year returns
- High growth, high volatility portfolio
- Small-cap growth bias
- If market cooperates = huge gains
- If market drops = bigger losses than S&P

**This is normal for growth portfolios!**

## Common Issues & Solutions

### Issue: Portfolio underperformed in test period

**Possible causes:**
1. **Short test period** (6 months not representative)
2. **Market regime change** (growth → value rotation)
3. **Overfitting** (optimized too much on training data)
4. **Bad luck** (random variation)

**Solutions:**
- Run longer backtest (extend test period)
- Test on different time periods
- Check if sector rotation occurred
- Compare to small-cap growth index (better benchmark)

### Issue: Very high volatility (>40%)

**Expected!** Your portfolio has:
- Growth stocks (high beta)
- Small/mid caps (more volatile)
- Sector concentration (less diversification)

**This is acceptable IF:**
- Sharpe ratio > 1.5 (volatility compensated by returns)
- You can handle -20% drawdowns emotionally
- You have long time horizon (3+ years)

**If too volatile:**
- Add lower-volatility stocks
- Increase diversification
- Reduce position sizes

### Issue: S&P 500 benchmark won't download

**Causes:**
- Network issues
- Yahoo Finance API limits
- Ticker symbol changed

**Solutions:**
```r
# Try different ticker
BENCHMARK_TICKER <- "SPY"  # S&P 500 ETF instead

# Or skip benchmark
# Script will still compare to equal-weight
```

### Issue: Max drawdown very large (>30%)

**Concern level depends on context:**
- -30% during COVID crash = normal
- -30% in calm market = concerning

**Check:**
- When did drawdown occur?
- How long to recover?
- Was it market-wide or portfolio-specific?

**Acceptable drawdown:**
- Growth portfolio: 20-35%
- Moderate portfolio: 15-25%
- Conservative portfolio: 10-15%

## Advanced Analysis

### Rolling Performance

Test strategy on multiple overlapping periods:

```r
# Define function to test 6-month periods
test_period <- function(start_date) {
  end_date <- start_date + 180
  # Run backtest for this period
  # Return performance metrics
}

# Test on rolling 6-month windows
periods <- seq(from = as.Date("2023-01-01"),
               to = Sys.Date() - 180,
               by = "month")

results <- lapply(periods, test_period)

# Analyze consistency
mean(sapply(results, function(x) x$return))
sd(sapply(results, function(x) x$return))
```

### Stress Testing

Test on crisis periods:

```r
# COVID crash: Feb-Mar 2020
covid_test <- backtest_period(
  start = as.Date("2020-02-01"),
  end = as.Date("2020-04-01")
)

# Tech bubble: 2000-2002
# Financial crisis: 2008-2009
# Etc.
```

### Monte Carlo Simulation

Simulate future performance:

```r
# Based on backtest statistics
mean_return <- mean(backtest$daily_return, na.rm = TRUE)
sd_return <- sd(backtest$daily_return, na.rm = TRUE)

# Simulate 1000 possible 1-year paths
simulations <- replicate(1000, {
  daily_rets <- rnorm(252, mean_return, sd_return)
  cumprod(1 + daily_rets)
})

# Analyze distribution
quantile(simulations[252, ], c(0.05, 0.25, 0.5, 0.75, 0.95))
```

## Practical Implementation

### After Successful Backtest

If your portfolio:
- Beat benchmarks ✓
- Sharpe ratio > 1.5 ✓
- Max drawdown acceptable ✓

**You're ready to invest!**

**Next steps:**
1. **Review allocation:**
   ```r
   allocation <- read.csv("analysis/dollar_allocation.csv")
   ```

2. **Place orders:**
   - Use limit orders
   - Buy during market hours
   - Track execution prices

3. **Set up monitoring:**
   - Check weekly
   - Rebalance if weights drift >10%
   - Review quarterly

4. **Plan rebalancing:**
   - Every 6-12 months
   - Or when weights drift >15%
   - Or after major market moves

### Ongoing Management

**Weekly:**
- Check portfolio value
- Note any major news on holdings

**Monthly:**
- Calculate current weights
- Compare to optimal weights
- Decide if rebalancing needed

**Quarterly:**
- Review performance vs benchmarks
- Check if stocks still meet criteria
- Consider tax-loss harvesting

**Annually:**
- Full rebalancing
- Re-run optimization (Modules 2-5)
- Update with fresh data

## Final Checklist

Before investing real money:

- [ ] Backtest shows positive alpha
- [ ] Sharpe ratio > 1.0 (preferably > 1.5)
- [ ] Max drawdown acceptable for my risk tolerance
- [ ] Understand why strategy worked (not just luck)
- [ ] Reviewed individual stock holdings
- [ ] Comfortable with volatility level
- [ ] Have 6-12 month time horizon
- [ ] This is money I can afford to lose
- [ ] Have emergency fund separate
- [ ] Understand this is high-risk growth strategy

## Support

Review these files:
- `analysis/backtest/backtest_summary.txt` - Full report
- `analysis/backtest/performance_comparison.png` - Visual results
- `analysis/backtest/backtest_results.csv` - Raw data

---

**Module 6 Complete!**

**ENTIRE PORTFOLIO OPTIMIZATION SYSTEM COMPLETE!** 🎉

You've successfully built and validated a complete systematic portfolio optimization strategy using Modern Portfolio Theory, technical analysis, and rigorous backtesting.

**You now have:**
- ✅ 12 carefully selected stocks
- ✅ Optimal weights backed by math
- ✅ Exact dollar allocations
- ✅ Validated performance on historical data
- ✅ Risk metrics and expectations

**Ready to implement with real capital!**
