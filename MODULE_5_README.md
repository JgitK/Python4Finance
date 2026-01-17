# Module 5: Portfolio Optimization & Efficient Frontier

## Overview

This module uses **Modern Portfolio Theory (Markowitz)** to find the optimal allocation of your 12 stocks. It calculates the efficient frontier, finds the maximum Sharpe ratio portfolio, and generates exact dollar allocations for your investment.

## What It Does

1. **Loads Final Portfolio** (12 stocks from Module 3)
2. **Creates Returns Matrix** (1 year of daily returns)
3. **Calculates Portfolio Statistics:**
   - Mean returns (annualized)
   - Covariance matrix (risk relationships)
4. **Generates Efficient Frontier:**
   - Simulates 10,000 random portfolios
   - Maps risk vs. return tradeoffs
5. **Finds Optimal Portfolios:**
   - **Maximum Sharpe Ratio** - Best risk-adjusted returns
   - **Minimum Variance** - Lowest risk
   - **Equal Weight** - Baseline comparison
6. **Calculates Dollar Allocations:**
   - Converts weights to dollar amounts
   - Calculates exact number of shares
   - Accounts for whole share purchases
7. **Visualizes Efficient Frontier** (PDF & PNG charts)

## Modern Portfolio Theory Explained

### The Core Concept

**You can reduce risk without reducing returns through diversification.**

**Example:**
- Stock A: 20% return, 30% volatility
- Stock B: 20% return, 30% volatility
- If correlation = 0.5, portfolio of both: 20% return, **24% volatility**

**Less risk, same return!**

### The Efficient Frontier

The **efficient frontier** is the set of portfolios that offer:
- **Maximum return for a given level of risk**, OR
- **Minimum risk for a given level of return**

Any portfolio not on the frontier is **suboptimal** (you could get better return or lower risk).

### Sharpe Ratio

**Sharpe Ratio = (Return - Risk-Free Rate) / Risk**

Measures return per unit of risk:
- **> 1.0:** Good risk-adjusted returns
- **> 2.0:** Excellent risk-adjusted returns
- **> 3.0:** Exceptional (rare)

**Maximum Sharpe Ratio portfolio** = best risk-adjusted performance

## Files

- **`05_portfolio_optimization.R`** - Main optimization script
- **`MODULE_5_README.md`** - This file

## Prerequisites

### Completed Module 3
Requires `analysis/final_portfolio.rds` from Module 3

### R Packages
Auto-installed by script:
```r
install.packages(c("quadprog", "ggplot2", "scales"))
```

## Configuration

You can adjust these in the script:

```r
NUM_PORTFOLIOS <- 10000       # More = better frontier, slower
RISK_FREE_RATE <- 0.045       # 4.5% (10-year Treasury)
OPTIMIZATION_PERIOD <- 252    # Trading days (1 year)
INVESTMENT_AMOUNT <- 10000    # Your investment ($10,000 default)
```

**Most important:** Change `INVESTMENT_AMOUNT` to your actual investment!

## Usage

### Run the Optimization

```r
source("05_portfolio_optimization.R")
```

**Expected runtime:** 1-3 minutes for 10,000 simulations

### What Happens

The script will:
1. Load your 12 stocks
2. Calculate returns and covariance
3. Simulate 10,000 random portfolios
4. Find maximum Sharpe ratio portfolio
5. Calculate optimal weights
6. Generate dollar allocation
7. Create efficient frontier visualization
8. Save all results

### Output Files

```
analysis/
├── optimal_weights.csv              # Optimal allocation percentages
├── optimal_weights.rds
├── dollar_allocation.csv            # Exact shares to buy
├── efficient_frontier.csv           # All simulated portfolios
├── efficient_frontier.rds
├── efficient_frontier.pdf           # Visualization (RECOMMENDED)
├── efficient_frontier.png
└── module_5_summary.txt             # Summary report
```

## Output Format

### Optimal Weights (`optimal_weights.csv`)

| Column               | Description                           |
|----------------------|---------------------------------------|
| ticker               | Stock ticker                          |
| max_sharpe_weight    | Optimal weight (% of portfolio)       |
| min_variance_weight  | Minimum risk weight                   |
| equal_weight         | Equal allocation (1/12 each)          |
| sector               | Industry sector                       |
| cumulative_return_1y | Historical 1-year return              |
| sharpe_ratio         | Individual stock Sharpe               |

### Dollar Allocation (`dollar_allocation.csv`)

| Column          | Description                               |
|-----------------|-------------------------------------------|
| ticker          | Stock ticker                              |
| weight          | Portfolio weight (decimal)                |
| dollar_amount   | Target dollar allocation                  |
| current_price   | Current stock price                       |
| shares          | Number of whole shares to buy             |
| actual_invested | Actual dollars invested (shares × price)  |
| remaining       | Unspent money for this stock              |

## Loading and Analyzing Results

### Load Optimal Weights

```r
# Load weights
weights <- readRDS("analysis/optimal_weights.rds")

# View optimal allocation
weights %>%
  select(ticker, sector, max_sharpe_weight) %>%
  mutate(weight_pct = sprintf("%.1f%%", 100 * max_sharpe_weight)) %>%
  arrange(desc(max_sharpe_weight))

# Top 5 holdings
weights %>%
  arrange(desc(max_sharpe_weight)) %>%
  head(5)
```

### Load Dollar Allocation

```r
# Load allocation
allocation <- read.csv("analysis/dollar_allocation.csv")

# View what to buy
allocation %>%
  filter(shares > 0) %>%
  select(ticker, shares, current_price, actual_invested)

# Total investment
sum(allocation$actual_invested)
```

### View Efficient Frontier

**Best way:** Open the PNG file
```
analysis/efficient_frontier.png
```

Look for:
- **Green triangle:** Maximum Sharpe (your optimal portfolio)
- **Blue triangle:** Minimum variance (lowest risk)
- **Black triangle:** Equal weight (baseline)
- **Color gradient:** Green = high Sharpe, Red = low Sharpe

The curve shows all possible risk/return combinations.

### Calculate Different Investment Amounts

```r
# Example: $50,000 investment
new_investment <- 50000

weights <- readRDS("analysis/optimal_weights.rds")
portfolio <- readRDS("analysis/final_portfolio.rds")

new_allocation <- weights %>%
  mutate(
    dollar_amount = max_sharpe_weight * new_investment,
    shares = floor(dollar_amount / current_price),
    actual_invested = shares * current_price
  ) %>%
  select(ticker, shares, current_price, actual_invested)

print(new_allocation)
cat(sprintf("Total: $%.2f\n", sum(new_allocation$actual_invested)))
```

## Understanding Your Results

### Optimal Weights Interpretation

**Concentrated vs. Diversified:**
- **Concentrated:** Top stock > 20%, or top 3 stocks > 50%
- **Balanced:** Relatively even distribution
- **Diversified:** All stocks < 15%

Optimization tends toward concentration in:
- Higher Sharpe ratio stocks
- Lower correlation stocks
- Lower volatility stocks

**This is mathematically optimal but consider:**
- Personal risk tolerance
- Diversification preferences
- Concentration risk

### Expected Performance Metrics

Your results will show:

**Expected Annual Return:**
- Weighted average of stock returns
- Example: 120% (very high given your strong candidates)

**Expected Annual Risk (Std Dev):**
- Portfolio volatility
- Example: 25-35% (high but diversified)

**Sharpe Ratio:**
- Risk-adjusted performance
- Example: 2.5-4.0 (excellent given 140% avg returns)

### Comparison to Benchmarks

Your script compares to:

1. **S&P 500:** ~10% return, ~15% risk, Sharpe ~0.4
2. **Your equal-weight portfolio:** Baseline
3. **Your optimized portfolio:** Should beat both

**Typical improvement:**
- Return: Similar or higher
- Risk: 10-20% lower
- Sharpe: 20-50% higher

## Rebalancing for Different Investment Amounts

The script defaults to $10,000. To change:

### Method 1: Edit Script (Recommended)

Open `05_portfolio_optimization.R` and change line ~22:
```r
INVESTMENT_AMOUNT <- 25000    # Change to your amount
```

Then re-run:
```r
source("05_portfolio_optimization.R")
```

### Method 2: Calculate Manually

```r
# Your investment
my_investment <- 100000

# Load optimal weights
weights <- readRDS("analysis/optimal_weights.rds")
portfolio <- readRDS("analysis/final_portfolio.rds")

# Calculate allocation
my_allocation <- weights %>%
  left_join(portfolio %>% select(ticker, current_price), by = "ticker") %>%
  mutate(
    target_dollars = max_sharpe_weight * my_investment,
    shares = floor(target_dollars / current_price),
    invested = shares * current_price,
    leftover = target_dollars - invested
  ) %>%
  select(ticker, max_sharpe_weight, target_dollars, current_price, shares, invested)

# View
print(my_allocation)

# Summary
cat(sprintf("Target: $%s\n", format(my_investment, big.mark = ",")))
cat(sprintf("Invested: $%.2f\n", sum(my_allocation$invested)))
cat(sprintf("Cash left: $%.2f\n", my_investment - sum(my_allocation$invested)))
```

## Advanced Topics

### Why Not Equal Weight?

Equal weight (8.33% each for 12 stocks) is simple but **suboptimal**:

**Problems:**
- Ignores risk differences (treats volatile and stable stocks equally)
- Ignores correlations (doesn't account for stocks moving together)
- Ignores Sharpe ratios (doesn't favor efficient stocks)

**Optimization improves by:**
- Overweighting high Sharpe, low correlation stocks
- Underweighting volatile, highly correlated stocks
- Mathematically maximizing risk-adjusted returns

### Constraints in Optimization

Current optimization uses:
- **Long-only:** No short selling (weights ≥ 0)
- **Full investment:** Weights sum to 100%
- **No leverage:** No borrowing

**Could add:**
- **Position limits:** Max 20% in any stock
- **Sector limits:** Max 40% in any sector
- **Minimum positions:** At least 5% in each stock

(Requires advanced quadratic programming - not in basic script)

### Optimization Period Sensitivity

Current: 252 days (1 year)

**Shorter period (126 days / 6 months):**
- ✅ More reactive to recent trends
- ⚠️ More sensitive to short-term volatility
- ⚠️ May overfit to recent market

**Longer period (504 days / 2 years):**
- ✅ More stable estimates
- ✅ Smooths out volatility
- ⚠️ May miss recent changes

**Recommendation:** 252 days (1 year) balances both

## Troubleshooting

### Issue: Weights very concentrated (one stock > 40%)

**Causes:**
- Stock has much higher Sharpe than others
- Stock has very low correlation with others
- Optimization maximizing aggressively

**Solutions:**
- Check if that stock's metrics are realistic
- Consider manual constraints (adjust script)
- Use equal weight or hybrid approach

### Issue: Some stocks have 0% weight

**Normal!** Optimization may exclude stocks that:
- Have lower Sharpe ratios
- Are highly correlated with better stocks
- Add more risk than return

**This is mathematically optimal** but you can:
- Use a hybrid (50% optimal, 50% equal weight)
- Manually include all stocks at minimum 5%

### Issue: Negative Sharpe ratio

**Causes:**
- Expected return < risk-free rate (4.5%)
- Very low returns or very high risk

**Rare with your candidates (140% avg return)**

If it happens:
- Check if risk-free rate is too high
- Verify returns calculation
- Review stock selection

### Issue: Can't invest full amount (too much cash left)

**Causes:**
- Stock prices too high for optimal weights
- Whole share requirement creates rounding

**Solutions:**
1. **Adjust up:** Buy one extra share of a few stocks
2. **Keep cash:** Save for rebalancing
3. **Fractional shares:** Use broker that allows them
4. **Larger investment:** Reduces rounding impact

**Example:**
- $10,000 investment, $500 cash left = 5% efficiency loss
- $100,000 investment, $500 cash left = 0.5% efficiency loss

## Practical Implementation

### Step-by-Step Trading Plan

1. **Review Allocation:**
   ```r
   allocation <- read.csv("analysis/dollar_allocation.csv")
   print(allocation %>% filter(shares > 0))
   ```

2. **Place Orders:**
   - Use limit orders (not market orders)
   - Set limit price = current_price ± 1-2%
   - Place all orders on same day if possible

3. **Track Execution:**
   - Record actual prices paid
   - Note any unfilled orders
   - Calculate actual weights vs. target

4. **Leftover Cash:**
   - Keep for rebalancing
   - Or split proportionally among stocks
   - Or add to highest Sharpe stock

### Rebalancing Strategy

**When to rebalance:**
- **Time-based:** Every 6-12 months
- **Threshold-based:** When weights drift > 5% from target
- **Event-based:** After major market moves

**How to rebalance:**
1. Calculate current weights
2. Compare to optimal weights
3. Sell overweight positions
4. Buy underweight positions
5. Minimize transaction costs and taxes

### Tax Considerations

**This script doesn't account for:**
- Capital gains taxes
- Dividend taxes
- Tax-loss harvesting
- Holding period requirements

**Consult a tax advisor** for tax-efficient implementation.

## Next Steps

After Module 5, you have:
- ✅ Optimal weights for 12 stocks
- ✅ Exact share allocations
- ✅ Expected risk/return metrics
- ✅ Visual efficient frontier

**Module 6: Backtesting** will:
- Test this strategy on historical data
- Validate expected returns
- Compare to benchmarks (S&P 500)
- Calculate max drawdown and other risk metrics

---

**Module 5 Complete!** You now have a mathematically optimized portfolio ready to implement.
