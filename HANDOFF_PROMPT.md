# Implementation Handoff: WPN Portfolio Robustness Improvements

## Context

This is an R-based quantitative portfolio optimization system with 6 modules (01-06) plus a Python/FastAPI webapp. The pipeline downloads ~2,725 stocks, screens them technically, selects low-correlation portfolios for 6 strategies (max_sharpe, min_variance, max_sortino, min_cvar, risk_parity, equal_weight), optimizes weights via Monte Carlo, validates with Ichimoku Cloud, and backtests with walk-forward analysis.

We identified 8 critical improvements to reduce bias, noise, and overfitting. Module 0 (market regime detection) has already been written as `00_market_regime.R`. The remaining 7 need to be implemented.

## What's Already Done

- `00_market_regime.R` — COMPLETE. Downloads VIX, SPY, yield curve, credit spreads. Classifies market into 4 regimes (BULL_LOW_VOL, BULL_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL). Outputs `analysis/market_regime.rds` containing:
  - `regime` — string classification
  - `primary_strategy` / `secondary_strategy` / `avoid_strategy` — strategy recommendations
  - `stress_correlation_multiplier` — factor to inflate correlations (1.0 to 1.35)
  - `position_size_adjustment` — factor to reduce allocation (1.0 to 0.5)
  - `strategy_map` — full regime-to-strategy mapping table
  - `indicators` — raw market data (VIX, SPY trend, breadth, yield curve, credit)

## Key Files to Modify

| File | What to Change |
|------|---------------|
| `03_correlation_analysis.R` | Replace ad-hoc scoring with z-score normalized signals; add recency decay; integrate regime stress correlations |
| `05_portfolio_optimization.R` | Add Ledoit-Wolf shrinkage; replace Monte Carlo with quadprog; add weight constraints (2-25%); implement resampled efficient frontier; integrate regime position sizing |
| `06_backtest_validation.R` | Fix look-ahead bias by re-running selection+optimization at each window; add regime classification per window |
| `utils_walkforward.R` | Add Ichimoku scoring within walk-forward windows; add survivorship bias detection; add factor decomposition |
| `run_full_pipeline.R` | Add Module 0 at start; add Module 7 (factor decomposition) at end |

## New Files to Create

| File | Purpose |
|------|---------|
| `07_factor_decomposition.R` | Fama-French 3-factor + momentum decomposition of portfolio returns |
| `analysis/METHODOLOGY_NARRATIVE.md` | Comprehensive narrative document (the final deliverable) |

## Detailed Implementation Instructions

### TASK 1: Improve Signal Combination in Module 3 (`03_correlation_analysis.R`)

**Current problem:** The scoring formula `score = metric * (1 - 0.5*corr) * (1 + ichimoku/25)` uses arbitrary coefficients with no statistical basis.

**Changes needed:**

1. After loading candidates in Step 1, normalize all scoring signals to z-scores:
```r
# Z-score normalize all strategy metrics
candidates <- candidates %>%
  mutate(
    z_sharpe = (sharpe_ratio - mean(sharpe_ratio, na.rm=TRUE)) / sd(sharpe_ratio, na.rm=TRUE),
    z_sortino = (sortino_ratio - mean(sortino_ratio, na.rm=TRUE)) / sd(sortino_ratio, na.rm=TRUE),
    z_variance = -(annual_variance - mean(annual_variance, na.rm=TRUE)) / sd(annual_variance, na.rm=TRUE),  # Negative because lower is better
    z_cvar = (cvar - mean(cvar, na.rm=TRUE)) / sd(cvar, na.rm=TRUE),  # Less negative = better
    z_momentum = (return_3m - mean(return_3m, na.rm=TRUE)) / sd(return_3m, na.rm=TRUE),
    z_ichimoku = (ichimoku_score - mean(ichimoku_score, na.rm=TRUE)) / sd(ichimoku_score, na.rm=TRUE)
  )
```

2. Add recency decay to momentum signals — weight recent 1-month returns higher than 3-month:
```r
# Recency-weighted momentum (if return_1m not available, approximate from return_3m)
# decay_weight: 60% to recent month, 40% to older months
```

3. Replace `get_strategy_score()` to use z-scores per strategy:
```r
# max_sharpe uses: 0.4*z_sharpe + 0.2*z_momentum + 0.2*z_ichimoku + 0.2*(1 - corr_penalty)
# min_variance uses: 0.5*z_variance + 0.2*z_ichimoku + 0.3*(1 - corr_penalty)
# max_sortino uses: 0.4*z_sortino + 0.2*z_momentum + 0.2*z_ichimoku + 0.2*(1 - corr_penalty)
# min_cvar uses: 0.5*z_cvar + 0.2*z_ichimoku + 0.3*(1 - corr_penalty)
# risk_parity: keep existing vol-distance approach but add z_ichimoku boost
```

4. Load regime data and apply stress correlation multiplier:
```r
# At the top, after loading candidates:
regime_file <- file.path(OUTPUT_DIR, "market_regime.rds")
if (file.exists(regime_file)) {
  regime_data <- readRDS(regime_file)
  STRESS_CORR_MULT <- regime_data$stress_correlation_multiplier
  cat(sprintf("  Regime: %s | Correlation stress: %.2fx\n", regime_data$regime, STRESS_CORR_MULT))
} else {
  STRESS_CORR_MULT <- 1.0
}

# In calc_avg_correlation, multiply result by STRESS_CORR_MULT:
# avg_corr <- mean(abs(correlations)) * STRESS_CORR_MULT
# Cap at 1.0
```

### TASK 2: Add Covariance Shrinkage, Weight Constraints, and Resampled Frontier (`05_portfolio_optimization.R`)

**Current problems:**
- Raw sample covariance has huge estimation error with 252 observations and 12 assets
- Monte Carlo (10,000 random portfolios) is sparse in 11-dimensional weight space
- No weight constraints allow dangerous concentration
- Optimal weights overfit to historical noise

**Changes needed:**

1. Add Ledoit-Wolf shrinkage estimator function (no external package needed):
```r
ledoit_wolf_shrinkage <- function(returns_mat) {
  # Implements Ledoit & Wolf (2004) shrinkage toward scaled identity
  n <- nrow(returns_mat)
  p <- ncol(returns_mat)

  # Sample covariance
  sample_cov <- cov(returns_mat) * 252  # Annualized

  # Shrinkage target: scaled identity matrix
  mu <- sum(diag(sample_cov)) / p
  target <- diag(mu, p)

  # Compute optimal shrinkage intensity
  # Using the analytical formula from Ledoit & Wolf
  X <- scale(returns_mat, scale = FALSE)
  sum_sq <- 0
  for (i in 1:n) {
    xi <- X[i, , drop=FALSE]
    sum_sq <- sum_sq + sum((t(xi) %*% xi - sample_cov/252)^2)
  }

  delta <- sum_sq / (n^2)
  gamma <- sum((sample_cov - target)^2)

  shrinkage_intensity <- min(max(delta / gamma, 0), 1)

  shrunk_cov <- (1 - shrinkage_intensity) * sample_cov + shrinkage_intensity * target

  cat(sprintf("    Ledoit-Wolf shrinkage intensity: %.3f\n", shrinkage_intensity))

  return(list(cov = shrunk_cov, intensity = shrinkage_intensity))
}
```

2. Replace the Monte Carlo loop with quadratic programming using the `quadprog` package (already loaded):
```r
# For max_sharpe: solve.QP to maximize return for given risk levels, trace the frontier
# For min_variance: solve.QP to minimize w'Σw subject to sum(w)=1, w >= 0.02, w <= 0.25
# Weight constraints: MIN_WEIGHT = 0.02 (2%), MAX_WEIGHT = 0.25 (25%)

optimize_portfolio_qp <- function(mean_returns, cov_matrix, strategy,
                                    min_weight = 0.02, max_weight = 0.25) {
  n <- length(mean_returns)

  # Quadprog format: min(-d'b + 0.5*b'Db) subject to A'b >= b0
  Dmat <- 2 * cov_matrix  # Must be positive definite

  # Make sure Dmat is PD (add small ridge if needed)
  Dmat <- Dmat + diag(1e-8, n)

  # Constraints matrix:
  # 1. sum(w) = 1 (equality)
  # 2. w >= min_weight (lower bounds)
  # 3. w <= max_weight (upper bounds, as -w >= -max_weight)

  Amat <- cbind(
    rep(1, n),           # sum = 1
    diag(n),             # w >= min_weight
    -diag(n)             # w <= max_weight
  )

  bvec <- c(1, rep(min_weight, n), rep(-max_weight, n))
  meq <- 1  # First constraint is equality

  if (strategy == "min_variance") {
    dvec <- rep(0, n)
  } else {
    # For max_sharpe: use parametric approach
    # Maximize return for min_variance, then find tangency
    dvec <- mean_returns
  }

  result <- tryCatch({
    solve.QP(Dmat, dvec, Amat, bvec, meq = meq)
  }, error = function(e) {
    cat(sprintf("    QP failed: %s. Falling back to constrained random.\n", e$message))
    NULL
  })

  if (!is.null(result)) {
    weights <- result$solution
    weights <- pmax(weights, min_weight)
    weights <- weights / sum(weights)
    return(weights)
  }

  return(NULL)
}
```

3. Implement resampled efficient frontier (500 bootstrap iterations):
```r
resample_efficient_frontier <- function(returns_mat, mean_returns, cov_matrix,
                                         strategy, n_resamples = 500,
                                         min_weight = 0.02, max_weight = 0.25) {
  n_obs <- nrow(returns_mat)
  n_assets <- ncol(returns_mat)
  all_weights <- matrix(0, nrow = n_resamples, ncol = n_assets)

  for (b in 1:n_resamples) {
    # Bootstrap: resample returns with replacement
    boot_idx <- sample(1:n_obs, n_obs, replace = TRUE)
    boot_returns <- returns_mat[boot_idx, ]

    # Recalculate moments from bootstrap sample
    boot_mean <- colMeans(boot_returns) * 252
    boot_lw <- ledoit_wolf_shrinkage(boot_returns)
    boot_cov <- boot_lw$cov

    # Optimize on bootstrap sample
    w <- optimize_portfolio_qp(boot_mean, boot_cov, strategy, min_weight, max_weight)

    if (!is.null(w)) {
      all_weights[b, ] <- w
    } else {
      all_weights[b, ] <- rep(1/n_assets, n_assets)  # Fallback to equal
    }
  }

  # Average weights across all bootstrap samples
  avg_weights <- colMeans(all_weights)
  avg_weights <- avg_weights / sum(avg_weights)  # Renormalize

  return(list(weights = avg_weights, all_weights = all_weights))
}
```

4. Keep the Monte Carlo simulation for VISUALIZATION of the frontier only (not for finding optimal weights). The actual optimization should use QP + resampling.

5. Integrate regime position sizing at the dollar allocation step:
```r
# After calculating allocations, apply regime adjustment:
if (file.exists(file.path(OUTPUT_DIR, "market_regime.rds"))) {
  regime_data <- readRDS(file.path(OUTPUT_DIR, "market_regime.rds"))
  POSITION_ADJ <- regime_data$position_size_adjustment
  # Scale dollar amounts: allocated * POSITION_ADJ, remainder to cash
}
```

### TASK 3: Fix Look-Ahead Bias in Backtesting (`06_backtest_validation.R` + `utils_walkforward.R`)

**Current problem:** The walk-forward test in `utils_walkforward.R` already truncates price data at the selection date (good), but it does NOT recompute Ichimoku scores at each window. Since Module 2 pre-computes Ichimoku using all data, and Module 3 uses those scores, the backtest effectively uses future Ichimoku information.

**Changes needed to `utils_walkforward.R`:**

1. Add Ichimoku scoring function within walk-forward:
```r
calculate_ichimoku_score_asof <- function(ticker, as_of_date) {
  stock_data <- load_stock_as_of(ticker, as_of_date)
  if (is.null(stock_data) || nrow(stock_data) < 78) return(NA)  # Need 52+26

  stock_data <- stock_data %>% arrange(date)
  n <- nrow(stock_data)

  # Calculate Ichimoku components (same logic as Module 2)
  high_9 <- runMax(stock_data$high, n = 9)
  low_9 <- runMin(stock_data$low, n = 9)
  high_26 <- runMax(stock_data$high, n = 26)
  low_26 <- runMin(stock_data$low, n = 26)
  high_52 <- runMax(stock_data$high, n = 52)
  low_52 <- runMin(stock_data$low, n = 52)

  tenkan <- (high_9 + low_9) / 2
  kijun <- (high_26 + low_26) / 2
  senkou_a <- (tenkan + kijun) / 2
  senkou_b <- (high_52 + low_52) / 2

  current_price <- stock_data$adjusted[n]
  cloud_idx <- n - 26
  if (cloud_idx <= 0) return(NA)

  score <- 0
  cloud_top <- max(senkou_a[cloud_idx], senkou_b[cloud_idx])
  if (!is.na(cloud_top) && current_price > cloud_top) score <- score + 1
  if (!is.na(tenkan[n]) && !is.na(kijun[n]) && tenkan[n] > kijun[n]) score <- score + 1
  if (!is.na(senkou_a[cloud_idx]) && !is.na(senkou_b[cloud_idx]) && senkou_a[cloud_idx] > senkou_b[cloud_idx]) score <- score + 1
  if (cloud_idx > 0 && current_price > stock_data$adjusted[cloud_idx]) score <- score + 1
  future_green <- !is.na(senkou_a[n]) && !is.na(senkou_b[n]) && senkou_a[n] > senkou_b[n]
  if (future_green) score <- score + 1

  return(score)
}
```

2. Integrate Ichimoku scoring into `select_portfolio_asof()` — after calculating technical indicators, compute Ichimoku score for each candidate and use it in the greedy selection scoring.

3. Add `MIN_ICHIMOKU_SCORE` filter within the walk-forward (matching Module 3 behavior).

4. In the greedy selection (Stage 2), use the same z-score-based scoring as the improved Module 3.

**Changes needed to `06_backtest_validation.R`:**

5. Add regime classification at each historical selection date. Create a lightweight version:
```r
# Classify regime at historical date using SPY data
classify_regime_asof <- function(as_of_date) {
  spy_data <- load_stock_as_of("SPY", as_of_date)  # Need SPY in stocks/ dir
  # Or download: getSymbols("SPY", from = as_of_date - 365, to = as_of_date)
  # Calculate: above/below 200MA, realized vol, momentum
  # Return regime string
}
```

6. Add regime to walk-forward results output so you can see which regime each period tested.

### TASK 4: Add Survivorship Bias Detection

Add to `utils_walkforward.R`:

```r
detect_survivorship_bias <- function(selection_date, tickers) {
  # For each ticker selected at selection_date, check if data extends
  # to the end of the holding period. If a stock's data ends before
  # the backtest end date, it may have been delisted.

  warnings <- character()

  for (ticker in tickers) {
    stock_data <- load_stock(ticker)
    if (is.null(stock_data)) {
      warnings <- c(warnings, sprintf("%s: No data at all (possible delisting)", ticker))
      next
    }

    last_date <- max(stock_data$date)
    if (last_date < Sys.Date() - 30) {
      warnings <- c(warnings, sprintf("%s: Data ends %s (possible delisting/acquisition)",
                                       ticker, last_date))
    }
  }

  if (length(warnings) > 0) {
    cat("\n  SURVIVORSHIP BIAS WARNINGS:\n")
    for (w in warnings) cat(sprintf("    %s\n", w))
    cat(sprintf("  %d of %d stocks may have survivorship issues\n",
                length(warnings), length(tickers)))
  }

  return(list(
    n_warnings = length(warnings),
    warnings = warnings,
    bias_risk = length(warnings) / length(tickers)
  ))
}
```

Call this within `run_walkforward_test()` after portfolio selection, and include `bias_risk` in the results dataframe. Also add a survivorship bias discount to reported metrics:
```r
# Adjust reported metrics by estimated survivorship bias
# Academic estimates: survivorship bias inflates returns by 0.5-1.5% per year
SURVIVORSHIP_DISCOUNT <- 0.01  # 1% annual adjustment
```

### TASK 5: Add Factor Decomposition (`07_factor_decomposition.R`)

Create a new module that decomposes portfolio returns into Fama-French factors:

```r
# Download Fama-French factors from Ken French's website
# URL: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip
# If download fails, construct approximate factors from ETFs:
#   Market (Mkt-RF): SPY return - risk free
#   SMB: IWM (small cap) - SPY (large cap)
#   HML: IWD (value) - IWF (growth)
#   MOM: MTUM (momentum ETF) return

# Run regression: R_portfolio - RF = alpha + beta_mkt*(Mkt-RF) + beta_smb*SMB + beta_hml*HML + beta_mom*MOM + epsilon

# Report:
#   - Alpha (annualized) — is there genuine skill?
#   - Factor betas — what exposures drive returns?
#   - R-squared — how much is explained by factors?
#   - t-statistics — are factor loadings significant?
```

The key output is whether the portfolio's alpha survives after accounting for factor exposures. If alpha drops to zero, the portfolio just has momentum/size/value tilts, not genuine stock-picking skill.

### TASK 6: Wire Regime into Pipeline

**`run_full_pipeline.R`** — Add Module 0 before Module 1, add Module 7 after Module 6:
```r
# Add at the start:
source("00_market_regime.R")

# Add after Module 6:
source("07_factor_decomposition.R")
```

**`03_correlation_analysis.R`** — Already covered in Task 1 (load regime, apply stress multiplier).

**`05_portfolio_optimization.R`** — Already covered in Task 2 (load regime, apply position sizing).

### TASK 7: Write Comprehensive Narrative (`analysis/METHODOLOGY_NARRATIVE.md`)

Create a document with these sections:

1. **Executive Summary** — What this system does, who it's for
2. **The Original Pipeline** — Describe Modules 1-6 as they existed before improvements
3. **Identified Weaknesses** — For each of the 8 issues (survivorship bias, look-ahead bias, optimization overfitting, correlation instability, short backtest, no transaction costs, momentum chasing, ad-hoc signal combination), explain:
   - What the problem was
   - Why it matters (statistical/financial reasoning)
   - How we fixed it
   - What the expected impact is
4. **Market Regime Framework** — Explain the regime detection system, the 4 regimes, how they map to strategies, and why this matters
5. **The Improved Pipeline** — Walk through the enhanced system end-to-end
6. **Factor Decomposition** — Explain what factor analysis reveals about the portfolio
7. **Limitations and Future Work** — Including:
   - Fundamental analysis integration (earnings, valuations)
   - Alternative data (sentiment, options flow)
   - Machine learning for regime detection
   - Longer backtest history (ETF proxies back to 2007)
   - Transaction cost and tax-aware optimization
   - Dynamic position sizing based on Kelly criterion
   - Multi-timeframe Ichimoku (weekly + daily confirmation)
   - Sector rotation overlay
   - Drawdown-triggered rebalancing rules

## Architecture Notes

- All R files use `source("utils_data_loader.R")` for data loading
- Stock data lives in `stocks/*.rds` (OHLCV dataframes)
- Analysis outputs go to `analysis/`
- The webapp reads from `webapp/db/seed_data/` (exported by `webapp/db/export_r_data.R`)
- Packages already available: tidyverse, TTR, quantmod, quadprog, ggplot2, corrplot, reshape2
- The system expects ~2,725 stock files in `stocks/`, with `metadata/filtered_tickers.csv` and `metadata/download_log.csv` for sector mapping
- Walk-forward utils are in `utils_walkforward.R`, data loading in `utils_data_loader.R`

## Testing

After implementing, verify the pipeline runs end-to-end:
```bash
cd /Users/jackson/Desktop/Python4Finance
Rscript run_full_pipeline.R
```

Module 0 and Module 7 will need internet access to download market indicators and factor data.
