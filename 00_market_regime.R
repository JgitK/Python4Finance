# ============================================================================
# MODULE 0: MARKET REGIME DETECTION
# ============================================================================
# Classifies the current market environment before any stock selection.
# This informs which optimization strategy is most appropriate and provides
# context for interpreting backtest results across different market conditions.
#
# Regimes:
#   Bull/Low Vol  - VIX < 18, SPY above 200MA, broad participation
#   Bull/High Vol - VIX >= 18, SPY above 200MA, selective rally
#   Bear/Low Vol  - SPY below 200MA, orderly decline
#   Bear/High Vol - VIX >= 25, SPY below 200MA, panic/capitulation
#
# Inputs:  Market data (SPY, VIX, Treasury yields, credit spreads)
# Outputs: analysis/market_regime.rds, analysis/market_regime.csv
#
# Author: Portfolio Optimization System
# Date: 2026-02-08

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("quantmod", quietly = TRUE)) install.packages("quantmod")
library(quantmod)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 0: MARKET REGIME DETECTION ===\n\n")

# Regime thresholds
VIX_LOW_THRESHOLD <- 18       # Below = calm markets
VIX_HIGH_THRESHOLD <- 25      # Above = crisis/panic
BREADTH_HEALTHY <- 0.60       # 60% stocks above 200MA = healthy
BREADTH_WEAK <- 0.40          # Below 40% = deteriorating
YIELD_CURVE_FLAT <- 0.20      # 10Y-2Y spread < 20bp = flat
YIELD_CURVE_INVERTED <- 0.0   # Negative = inverted

# Technical parameters
MA_PERIOD <- 200              # 200-day moving average for trend
MOMENTUM_LOOKBACK <- 63       # 3-month momentum window
REGIME_LOOKBACK <- 252        # 1 year of context for regime history

# Output directory
OUTPUT_DIR <- "analysis"
if (!dir.exists(OUTPUT_DIR)) dir.create(OUTPUT_DIR, recursive = TRUE)

# ============================================================================
# STEP 1: DOWNLOAD MARKET INDICATORS
# ============================================================================

cat("Step 1: Downloading market regime indicators...\n")

# Define date range
end_date <- Sys.Date()
start_date <- end_date - 365 * 2  # 2 years for MA calculations

# Download market data with error handling
download_market_data <- function(symbol, src = "yahoo") {
  tryCatch({
    data <- getSymbols(symbol, src = src, from = start_date, to = end_date,
                       auto.assign = FALSE, warnings = FALSE)
    cat(sprintf("  Downloaded %s: %d observations\n", symbol, nrow(data)))
    return(data)
  }, error = function(e) {
    cat(sprintf("  WARNING: Could not download %s: %s\n", symbol, e$message))
    return(NULL)
  })
}

# Core market indicators
spy_data <- download_market_data("SPY")     # S&P 500 ETF
vix_data <- download_market_data("^VIX")    # Volatility Index

# Treasury yields for yield curve
tny_10y <- download_market_data("^TNX")     # 10-Year Treasury Yield
tny_2y  <- download_market_data("^IRX")     # 13-week T-Bill (proxy for short end)

# Credit spread proxies
hyg_data <- download_market_data("HYG")     # High Yield Corporate Bond ETF
lqd_data <- download_market_data("LQD")     # Investment Grade Corporate Bond ETF

# Broad market breadth proxy
rsp_data <- download_market_data("RSP")     # Equal-weight S&P 500

# ============================================================================
# STEP 2: CALCULATE REGIME INDICATORS
# ============================================================================

cat("\nStep 2: Calculating regime indicators...\n")

regime_indicators <- list()

# --- 2a: VIX Level and Trend ---
if (!is.null(vix_data)) {
  vix_close <- as.numeric(Cl(vix_data))
  vix_dates <- index(vix_data)

  current_vix <- tail(vix_close, 1)
  vix_20d_avg <- mean(tail(vix_close, 20), na.rm = TRUE)
  vix_50d_avg <- mean(tail(vix_close, 50), na.rm = TRUE)
  vix_trend <- ifelse(vix_20d_avg > vix_50d_avg, "RISING", "FALLING")

  regime_indicators$vix_current <- current_vix
  regime_indicators$vix_20d_avg <- vix_20d_avg
  regime_indicators$vix_trend <- vix_trend

  cat(sprintf("  VIX Current: %.1f | 20d Avg: %.1f | Trend: %s\n",
              current_vix, vix_20d_avg, vix_trend))
} else {
  # Fallback: estimate VIX from SPY realized vol
  if (!is.null(spy_data)) {
    spy_returns <- diff(log(as.numeric(Cl(spy_data))))
    realized_vol <- sd(tail(spy_returns, 20), na.rm = TRUE) * sqrt(252) * 100
    regime_indicators$vix_current <- realized_vol
    regime_indicators$vix_20d_avg <- realized_vol
    regime_indicators$vix_trend <- "ESTIMATED"
    cat(sprintf("  VIX Estimated from realized vol: %.1f\n", realized_vol))
  }
}

# --- 2b: SPY Trend (Price vs 200-day MA) ---
if (!is.null(spy_data)) {
  spy_close <- as.numeric(Cl(spy_data))
  spy_dates <- index(spy_data)
  n_spy <- length(spy_close)

  # 200-day moving average
  if (n_spy >= MA_PERIOD) {
    spy_200ma <- mean(tail(spy_close, MA_PERIOD))
  } else {
    spy_200ma <- mean(spy_close, na.rm = TRUE)
  }

  current_spy <- tail(spy_close, 1)
  spy_above_200ma <- current_spy > spy_200ma
  spy_distance_from_ma <- (current_spy - spy_200ma) / spy_200ma

  # 3-month momentum
  if (n_spy > MOMENTUM_LOOKBACK) {
    spy_momentum <- (current_spy / spy_close[n_spy - MOMENTUM_LOOKBACK]) - 1
  } else {
    spy_momentum <- 0
  }

  # 50-day MA for shorter-term trend
  spy_50ma <- mean(tail(spy_close, 50))
  spy_above_50ma <- current_spy > spy_50ma

  regime_indicators$spy_current <- current_spy
  regime_indicators$spy_200ma <- spy_200ma
  regime_indicators$spy_above_200ma <- spy_above_200ma
  regime_indicators$spy_distance_pct <- spy_distance_from_ma * 100
  regime_indicators$spy_momentum_3m <- spy_momentum
  regime_indicators$spy_above_50ma <- spy_above_50ma

  cat(sprintf("  SPY: $%.2f | 200MA: $%.2f | %s by %.1f%% | 3m Mom: %.1f%%\n",
              current_spy, spy_200ma,
              ifelse(spy_above_200ma, "ABOVE", "BELOW"),
              abs(spy_distance_from_ma) * 100,
              spy_momentum * 100))
}

# --- 2c: Market Breadth (Equal-weight vs Cap-weight divergence) ---
if (!is.null(rsp_data) && !is.null(spy_data)) {
  # RSP/SPY ratio: rising = broad participation, falling = narrow leadership
  rsp_close <- as.numeric(Cl(rsp_data))
  spy_close_aligned <- as.numeric(Cl(spy_data))

  # Align lengths
  min_len <- min(length(rsp_close), length(spy_close_aligned))
  rsp_close <- tail(rsp_close, min_len)
  spy_close_aligned <- tail(spy_close_aligned, min_len)

  breadth_ratio <- rsp_close / spy_close_aligned
  current_breadth <- tail(breadth_ratio, 1)
  breadth_50d <- mean(tail(breadth_ratio, 50))
  breadth_trend <- ifelse(current_breadth > breadth_50d, "IMPROVING", "DETERIORATING")

  # Estimate % above 200MA from breadth ratio trend
  # Use 3-month RSP performance as breadth proxy
  n_rsp <- length(rsp_close)
  if (n_rsp > MOMENTUM_LOOKBACK) {
    rsp_3m_return <- (rsp_close[n_rsp] / rsp_close[n_rsp - MOMENTUM_LOOKBACK]) - 1
    spy_3m_return <- (spy_close_aligned[n_rsp] / spy_close_aligned[n_rsp - MOMENTUM_LOOKBACK]) - 1

    # If RSP outperforms SPY, breadth is strong
    breadth_strength <- ifelse(rsp_3m_return > spy_3m_return, "BROAD", "NARROW")
  } else {
    rsp_3m_return <- 0
    breadth_strength <- "UNKNOWN"
  }

  regime_indicators$breadth_trend <- breadth_trend
  regime_indicators$breadth_strength <- breadth_strength
  regime_indicators$rsp_3m_return <- rsp_3m_return

  cat(sprintf("  Breadth: %s | Participation: %s | RSP 3m: %.1f%%\n",
              breadth_trend, breadth_strength, rsp_3m_return * 100))
}

# --- 2d: Yield Curve (10Y - short-term spread) ---
if (!is.null(tny_10y) && !is.null(tny_2y)) {
  yield_10y <- tail(as.numeric(Cl(tny_10y)), 1) / 100  # Convert from % points

yield_short <- tail(as.numeric(Cl(tny_2y)), 1) / 100

  yield_spread <- yield_10y - yield_short

  if (yield_spread < YIELD_CURVE_INVERTED) {
    yield_curve_signal <- "INVERTED"
  } else if (yield_spread < YIELD_CURVE_FLAT) {
    yield_curve_signal <- "FLAT"
  } else {
    yield_curve_signal <- "NORMAL"
  }

  regime_indicators$yield_10y <- yield_10y
  regime_indicators$yield_short <- yield_short
  regime_indicators$yield_spread <- yield_spread
  regime_indicators$yield_curve_signal <- yield_curve_signal

  cat(sprintf("  Yield Curve: 10Y=%.2f%% Short=%.2f%% Spread=%.2fbp → %s\n",
              yield_10y * 100, yield_short * 100, yield_spread * 100 * 100,
              yield_curve_signal))
} else {
  regime_indicators$yield_curve_signal <- "UNAVAILABLE"
  cat("  Yield Curve: Data unavailable\n")
}

# --- 2e: Credit Spreads (HYG/LQD ratio as proxy) ---
if (!is.null(hyg_data) && !is.null(lqd_data)) {
  hyg_close <- as.numeric(Cl(hyg_data))
  lqd_close <- as.numeric(Cl(lqd_data))

  min_len <- min(length(hyg_close), length(lqd_close))
  hyg_close <- tail(hyg_close, min_len)
  lqd_close <- tail(lqd_close, min_len)

  # HYG/LQD ratio: falling = spreads widening (risk-off)
  credit_ratio <- hyg_close / lqd_close
  current_credit <- tail(credit_ratio, 1)
  credit_50d <- mean(tail(credit_ratio, 50))
  credit_200d <- mean(tail(credit_ratio, min(200, length(credit_ratio))))

  if (current_credit > credit_200d) {
    credit_signal <- "TIGHT"  # Risk-on, spreads narrow
  } else if (current_credit < credit_50d * 0.98) {
    credit_signal <- "WIDENING"  # Risk-off, stress building
  } else {
    credit_signal <- "NEUTRAL"
  }

  regime_indicators$credit_signal <- credit_signal
  regime_indicators$credit_ratio <- current_credit

  cat(sprintf("  Credit Spreads: %s (HYG/LQD ratio: %.3f vs 200d: %.3f)\n",
              credit_signal, current_credit, credit_200d))
} else {
  regime_indicators$credit_signal <- "UNAVAILABLE"
  cat("  Credit Spreads: Data unavailable\n")
}

# ============================================================================
# STEP 3: CLASSIFY MARKET REGIME
# ============================================================================

cat("\nStep 3: Classifying market regime...\n")

# Scoring system for regime classification
bull_score <- 0
vol_score <- 0
total_signals <- 0

# VIX component
vix_val <- regime_indicators$vix_current
if (!is.null(vix_val) && !is.na(vix_val)) {
  total_signals <- total_signals + 2  # VIX is weighted double

  if (vix_val < VIX_LOW_THRESHOLD) {
    vol_score <- vol_score - 2  # Low vol
  } else if (vix_val >= VIX_HIGH_THRESHOLD) {
    vol_score <- vol_score + 2  # High vol
    bull_score <- bull_score - 1  # High VIX is bearish
  } else {
    vol_score <- vol_score + 1  # Moderate vol
  }
}

# SPY trend component
if (!is.null(regime_indicators$spy_above_200ma)) {
  total_signals <- total_signals + 2  # Trend is weighted double

  if (regime_indicators$spy_above_200ma) {
    bull_score <- bull_score + 2
  } else {
    bull_score <- bull_score - 2
  }

  # Add momentum nuance
  if (!is.null(regime_indicators$spy_momentum_3m)) {
    total_signals <- total_signals + 1
    if (regime_indicators$spy_momentum_3m > 0.05) {
      bull_score <- bull_score + 1
    } else if (regime_indicators$spy_momentum_3m < -0.05) {
      bull_score <- bull_score - 1
    }
  }
}

# Breadth component
if (!is.null(regime_indicators$breadth_strength)) {
  total_signals <- total_signals + 1
  if (regime_indicators$breadth_strength == "BROAD") {
    bull_score <- bull_score + 1
  } else if (regime_indicators$breadth_strength == "NARROW") {
    bull_score <- bull_score - 0.5  # Narrow rallies are less sustainable
  }
}

# Yield curve component
if (!is.null(regime_indicators$yield_curve_signal) &&
    regime_indicators$yield_curve_signal != "UNAVAILABLE") {
  total_signals <- total_signals + 1
  if (regime_indicators$yield_curve_signal == "INVERTED") {
    bull_score <- bull_score - 1
  } else if (regime_indicators$yield_curve_signal == "NORMAL") {
    bull_score <- bull_score + 0.5
  }
}

# Credit spread component
if (!is.null(regime_indicators$credit_signal) &&
    regime_indicators$credit_signal != "UNAVAILABLE") {
  total_signals <- total_signals + 1
  if (regime_indicators$credit_signal == "TIGHT") {
    bull_score <- bull_score + 1
  } else if (regime_indicators$credit_signal == "WIDENING") {
    bull_score <- bull_score - 1
    vol_score <- vol_score + 1
  }
}

# Normalize scores
bull_normalized <- bull_score / max(total_signals, 1)
vol_normalized <- vol_score / max(total_signals, 1)

# Classify regime
is_bull <- bull_normalized > 0
is_high_vol <- vol_normalized > 0.2

if (is_bull && !is_high_vol) {
  regime <- "BULL_LOW_VOL"
  regime_label <- "Bull Market / Low Volatility"
  regime_description <- "Strong uptrend with calm markets. Favorable for aggressive strategies."
} else if (is_bull && is_high_vol) {
  regime <- "BULL_HIGH_VOL"
  regime_label <- "Bull Market / High Volatility"
  regime_description <- "Uptrend but with elevated uncertainty. Favor risk-balanced approaches."
} else if (!is_bull && !is_high_vol) {
  regime <- "BEAR_LOW_VOL"
  regime_label <- "Bear Market / Low Volatility"
  regime_description <- "Orderly decline. Defensive positioning with minimum variance emphasis."
} else {
  regime <- "BEAR_HIGH_VOL"
  regime_label <- "Bear Market / High Volatility"
  regime_description <- "Crisis conditions. Maximum tail-risk protection needed."
}

cat(sprintf("\n  ╔══════════════════════════════════════════╗\n"))
cat(sprintf("  ║  CURRENT REGIME: %-24s║\n", regime_label))
cat(sprintf("  ╚══════════════════════════════════════════╝\n"))
cat(sprintf("  Bull Score: %.2f | Vol Score: %.2f\n", bull_normalized, vol_normalized))
cat(sprintf("  %s\n", regime_description))

# ============================================================================
# STEP 4: MAP REGIME TO STRATEGY RECOMMENDATIONS
# ============================================================================

cat("\nStep 4: Generating strategy recommendations...\n")

# Strategy recommendation mapping
strategy_map <- list(
  BULL_LOW_VOL = list(
    primary = "max_sharpe",
    secondary = "max_sortino",
    avoid = "min_variance",
    rationale = "Strong markets favor return maximization. Low vol means risk metrics are favorable."
  ),
  BULL_HIGH_VOL = list(
    primary = "risk_parity",
    secondary = "max_sortino",
    avoid = "max_sharpe",
    rationale = "Elevated vol makes equal risk contribution prudent. Downside protection matters."
  ),
  BEAR_LOW_VOL = list(
    primary = "min_variance",
    secondary = "min_cvar",
    avoid = "max_sharpe",
    rationale = "Capital preservation in orderly declines. Minimize portfolio variance."
  ),
  BEAR_HIGH_VOL = list(
    primary = "min_cvar",
    secondary = "min_variance",
    avoid = "max_sharpe",
    rationale = "Tail risk dominates. Protect against worst-case scenarios. Reduce exposure."
  )
)

recommendation <- strategy_map[[regime]]

cat(sprintf("\n  STRATEGY RECOMMENDATIONS (based on %s regime):\n", regime))
cat(sprintf("    Primary:   %s\n", toupper(recommendation$primary)))
cat(sprintf("    Secondary: %s\n", toupper(recommendation$secondary)))
cat(sprintf("    Avoid:     %s\n", toupper(recommendation$avoid)))
cat(sprintf("    Rationale: %s\n", recommendation$rationale))

# ============================================================================
# STEP 5: CALCULATE REGIME CONFIDENCE AND HISTORICAL CONTEXT
# ============================================================================

cat("\nStep 5: Calculating regime confidence...\n")

# Confidence based on agreement among indicators
confidence_signals <- c()

if (!is.null(regime_indicators$spy_above_200ma)) {
  confidence_signals <- c(confidence_signals,
                          ifelse(regime_indicators$spy_above_200ma == is_bull, 1, 0))
}
if (!is.null(regime_indicators$spy_above_50ma)) {
  confidence_signals <- c(confidence_signals,
                          ifelse(regime_indicators$spy_above_50ma == is_bull, 1, 0))
}
if (!is.null(regime_indicators$breadth_strength)) {
  confidence_signals <- c(confidence_signals,
                          ifelse((regime_indicators$breadth_strength == "BROAD") == is_bull, 1, 0))
}
if (!is.null(regime_indicators$credit_signal) &&
    regime_indicators$credit_signal != "UNAVAILABLE") {
  confidence_signals <- c(confidence_signals,
                          ifelse((regime_indicators$credit_signal == "TIGHT") == is_bull, 1, 0))
}

regime_confidence <- if (length(confidence_signals) > 0) {
  mean(confidence_signals)
} else {
  0.5  # No data = uncertain
}

confidence_label <- if (regime_confidence >= 0.8) {
  "HIGH"
} else if (regime_confidence >= 0.6) {
  "MODERATE"
} else {
  "LOW"
}

cat(sprintf("  Regime Confidence: %.0f%% (%s)\n",
            regime_confidence * 100, confidence_label))

if (confidence_label == "LOW") {
  cat("  WARNING: Indicators are conflicting. Consider using risk_parity as a hedge.\n")
}

# ============================================================================
# STEP 6: STRESSED CORRELATION ADJUSTMENT FACTORS
# ============================================================================

cat("\nStep 6: Computing stress-adjusted correlation factors...\n")

# During high vol regimes, correlations increase
# We provide a multiplier for the correlation matrix in Module 3/5
stress_correlation_multiplier <- switch(regime,
  "BULL_LOW_VOL"  = 1.0,   # Use historical correlations as-is
  "BULL_HIGH_VOL" = 1.15,  # Bump correlations up 15%
  "BEAR_LOW_VOL"  = 1.20,  # Bump correlations up 20%
  "BEAR_HIGH_VOL" = 1.35,  # Bump correlations up 35%
  1.0
)

# Position sizing adjustment (reduce exposure in risky regimes)
position_size_adjustment <- switch(regime,
  "BULL_LOW_VOL"  = 1.0,   # Full position
  "BULL_HIGH_VOL" = 0.85,  # Reduce 15%
  "BEAR_LOW_VOL"  = 0.70,  # Reduce 30%
  "BEAR_HIGH_VOL" = 0.50,  # Reduce 50%
  1.0
)

cat(sprintf("  Correlation stress multiplier: %.2fx\n", stress_correlation_multiplier))
cat(sprintf("  Position size adjustment: %.0f%% of full allocation\n",
            position_size_adjustment * 100))

# ============================================================================
# STEP 7: SAVE REGIME DATA
# ============================================================================

cat("\nStep 7: Saving regime classification...\n")

regime_result <- list(
  # Classification
  regime = regime,
  regime_label = regime_label,
  regime_description = regime_description,
  regime_confidence = regime_confidence,
  confidence_label = confidence_label,
  classification_date = Sys.Date(),

  # Scores
  bull_score = bull_normalized,
  vol_score = vol_normalized,

  # Strategy recommendations
  primary_strategy = recommendation$primary,
  secondary_strategy = recommendation$secondary,
  avoid_strategy = recommendation$avoid,
  strategy_rationale = recommendation$rationale,

  # Adjustment factors for downstream modules
  stress_correlation_multiplier = stress_correlation_multiplier,
  position_size_adjustment = position_size_adjustment,

  # Raw indicators
  indicators = regime_indicators,

  # Strategy mapping (full table for all regimes)
  strategy_map = strategy_map
)

# Save as RDS
saveRDS(regime_result, file.path(OUTPUT_DIR, "market_regime.rds"))
cat(sprintf("  Saved: %s\n", file.path(OUTPUT_DIR, "market_regime.rds")))

# Save summary as CSV
regime_csv <- data.frame(
  date = Sys.Date(),
  regime = regime,
  regime_label = regime_label,
  confidence = regime_confidence,
  confidence_label = confidence_label,
  vix = ifelse(!is.null(regime_indicators$vix_current), regime_indicators$vix_current, NA),
  spy_above_200ma = ifelse(!is.null(regime_indicators$spy_above_200ma),
                           regime_indicators$spy_above_200ma, NA),
  yield_curve = ifelse(!is.null(regime_indicators$yield_curve_signal),
                       regime_indicators$yield_curve_signal, NA),
  credit = ifelse(!is.null(regime_indicators$credit_signal),
                  regime_indicators$credit_signal, NA),
  primary_strategy = recommendation$primary,
  secondary_strategy = recommendation$secondary,
  avoid_strategy = recommendation$avoid,
  correlation_multiplier = stress_correlation_multiplier,
  position_adjustment = position_size_adjustment,
  stringsAsFactors = FALSE
)

write.csv(regime_csv, file.path(OUTPUT_DIR, "market_regime.csv"), row.names = FALSE)
cat(sprintf("  Saved: %s\n", file.path(OUTPUT_DIR, "market_regime.csv")))

# ============================================================================
# STEP 8: SUMMARY REPORT
# ============================================================================

cat("\nStep 8: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 0: MARKET REGIME DETECTION ===
Generated: %s

CURRENT REGIME: %s
Confidence: %.0f%% (%s)
%s

INDICATOR DASHBOARD:
- VIX:          %.1f (%s)
- SPY Trend:    %s 200MA by %.1f%%
- SPY Momentum: %.1f%% (3-month)
- Breadth:      %s
- Yield Curve:  %s
- Credit:       %s

SCORING:
- Bull/Bear Score: %+.2f (positive = bull)
- Volatility Score: %+.2f (positive = high vol)

STRATEGY RECOMMENDATIONS:
- Primary Strategy:   %s
- Secondary Strategy: %s
- Avoid:             %s
- Rationale: %s

RISK ADJUSTMENTS:
- Correlation stress multiplier: %.2fx
  (Multiply pairwise correlations by this factor for stress testing)
- Position size adjustment: %.0f%%
  (Reduce total portfolio allocation in risky regimes)

HOW TO USE:
1. Module 3 will use stress_correlation_multiplier to adjust its
   correlation penalty during stock selection
2. Module 5 will use position_size_adjustment to scale the
   dollar allocation
3. The primary_strategy recommendation guides which optimization
   objective to emphasize
4. Walk-forward backtest (Module 6) now classifies regime at each
   historical selection date for regime-aware testing

NEXT STEPS:
- Run Module 2 for technical screening
- Regime classification will be used by Modules 3, 5, and 6
",
Sys.time(),
regime_label,
regime_confidence * 100,
confidence_label,
regime_description,
ifelse(!is.null(regime_indicators$vix_current), regime_indicators$vix_current, NA),
ifelse(!is.null(regime_indicators$vix_trend), regime_indicators$vix_trend, "N/A"),
ifelse(!is.null(regime_indicators$spy_above_200ma),
       ifelse(regime_indicators$spy_above_200ma, "ABOVE", "BELOW"), "N/A"),
ifelse(!is.null(regime_indicators$spy_distance_pct), regime_indicators$spy_distance_pct, 0),
ifelse(!is.null(regime_indicators$spy_momentum_3m), regime_indicators$spy_momentum_3m * 100, 0),
ifelse(!is.null(regime_indicators$breadth_strength), regime_indicators$breadth_strength, "N/A"),
ifelse(!is.null(regime_indicators$yield_curve_signal), regime_indicators$yield_curve_signal, "N/A"),
ifelse(!is.null(regime_indicators$credit_signal), regime_indicators$credit_signal, "N/A"),
bull_normalized,
vol_normalized,
toupper(recommendation$primary),
toupper(recommendation$secondary),
toupper(recommendation$avoid),
recommendation$rationale,
stress_correlation_multiplier,
position_size_adjustment * 100
)

writeLines(summary_report, file.path(OUTPUT_DIR, "module_0_summary.txt"))
cat(sprintf("  Summary: %s\n", file.path(OUTPUT_DIR, "module_0_summary.txt")))
cat(summary_report)

cat("\n=== MODULE 0 COMPLETE ===\n")
cat("Next step: Run Module 2 for technical screening\n\n")
