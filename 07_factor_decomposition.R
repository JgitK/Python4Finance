# ============================================================================
# MODULE 7: FACTOR DECOMPOSITION ANALYSIS
# ============================================================================
# Decomposes portfolio returns into Fama-French + Momentum factors to determine
# whether alpha is genuine stock-picking skill or just factor exposure.
#
# Regression: R_portfolio - RF = alpha + β_mkt*(Mkt-RF) + β_smb*SMB + β_hml*HML + β_mom*MOM + ε
#
# Inputs:  Portfolio weights from Module 5, factor data (Fama-French or ETF proxies)
# Outputs: Alpha, factor betas, R-squared, t-statistics
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

cat("\n=== MODULE 7: FACTOR DECOMPOSITION ANALYSIS ===\n\n")

# Analysis period
ANALYSIS_PERIOD <- 252  # 1 year of daily returns

# Risk-free rate proxy
RISK_FREE_RATE_ANNUAL <- 0.045  # 4.5% annual

# Output directory
OUTPUT_DIR <- "analysis"
FACTOR_DIR <- file.path(OUTPUT_DIR, "factors")

# Create output directory
if (!dir.exists(FACTOR_DIR)) {
  dir.create(FACTOR_DIR, recursive = TRUE)
  cat("Created directory: analysis/factors/\n\n")
}

# ============================================================================
# STEP 1: LOAD PORTFOLIO AND CONSTRUCT PORTFOLIO RETURNS
# ============================================================================

cat("Step 1: Loading portfolio and calculating returns...\n")

# Load all strategy portfolios
all_portfolios <- readRDS(file.path(OUTPUT_DIR, "all_strategy_portfolios.rds"))
all_weights <- readRDS(file.path(OUTPUT_DIR, "all_strategy_weights.rds"))

# Focus on max_sharpe strategy for primary analysis
strategy <- "max_sharpe"
portfolio <- all_portfolios[[strategy]]
tickers <- portfolio$ticker

cat(sprintf("  Analyzing %s strategy: %d stocks\n", strategy, length(tickers)))
cat(sprintf("  Stocks: %s\n", paste(tickers, collapse = ", ")))

# Load stock data for portfolio
stock_data_list <- load_multiple_stocks(tickers)

cat(sprintf("  Loaded: %d/%d stocks\n", length(stock_data_list), length(tickers)))

# Get weights from optimization results
weights_file <- file.path(OUTPUT_DIR, "weights", paste0(strategy, "_weights.rds"))
if (file.exists(weights_file)) {
  weights_df <- readRDS(weights_file)
  weights <- weights_df$optimal_weight
  names(weights) <- weights_df$ticker
} else {
  # Fallback: equal weights
  weights <- rep(1/length(tickers), length(tickers))
  names(weights) <- tickers
}

# Calculate portfolio returns
returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    arrange(date) %>%
    mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted)) %>%
    select(date, daily_return) %>%
    tail(ANALYSIS_PERIOD + 1) %>%
    rename(!!ticker := daily_return)
})

returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

returns_df <- returns_matrix %>% select(-date)
returns_mat <- as.matrix(returns_df)
complete_mask <- complete.cases(returns_mat)  # Save mask before filtering
returns_mat <- returns_mat[complete_mask, ]

# Align weights with available stocks
available_stocks <- intersect(tickers, colnames(returns_mat))
weights_aligned <- weights[available_stocks]
weights_aligned <- weights_aligned / sum(weights_aligned)  # Renormalize

# Calculate portfolio daily returns
portfolio_returns <- as.numeric(returns_mat[, available_stocks] %*% weights_aligned)
dates <- returns_matrix %>% filter(!is.na(date)) %>% pull(date)
dates <- dates[complete_mask]

cat(sprintf("  Portfolio returns calculated: %d days\n", length(portfolio_returns)))

# ============================================================================
# STEP 2: DOWNLOAD OR CONSTRUCT FACTOR DATA
# ============================================================================

cat("\nStep 2: Obtaining factor data...\n")

# Try to use ETF proxies for factors (more reliable than web scraping)
# Factors: Market (SPY), Size (IWM-SPY), Value (IWD-IWF), Momentum (MTUM)

start_date <- min(dates) - 30  # Extra buffer
end_date <- max(dates) + 5

cat("  Downloading factor proxies via ETFs...\n")

# Download factor ETFs
download_factor_etf <- function(symbol, name) {
  tryCatch({
    data <- getSymbols(symbol, src = "yahoo", from = start_date, to = end_date,
                       auto.assign = FALSE, warnings = FALSE)
    cat(sprintf("    Downloaded %s (%s)\n", name, symbol))

    df <- data.frame(
      date = index(data),
      adjusted = as.numeric(Ad(data))
    ) %>%
      arrange(date) %>%
      mutate(return = (adjusted / lag(adjusted)) - 1) %>%
      filter(!is.na(return)) %>%
      select(date, return) %>%
      rename(!!symbol := return)

    return(df)
  }, error = function(e) {
    cat(sprintf("    WARNING: Could not download %s (%s): %s\n", name, symbol, e$message))
    return(NULL)
  })
}

spy_data <- download_factor_etf("SPY", "Market (S&P 500)")
iwm_data <- download_factor_etf("IWM", "Small Cap (Russell 2000)")
iwd_data <- download_factor_etf("IWD", "Value (Large Cap Value)")
iwf_data <- download_factor_etf("IWF", "Growth (Large Cap Growth)")
mtum_data <- download_factor_etf("MTUM", "Momentum Factor")

# Construct factor returns
cat("\n  Constructing factor time series...\n")

# Start with dates from portfolio
factor_data <- data.frame(date = dates, portfolio_return = portfolio_returns)

# Market factor (Mkt-RF): SPY return - risk free
if (!is.null(spy_data)) {
  factor_data <- factor_data %>%
    left_join(spy_data, by = "date") %>%
    rename(market_return = SPY)

  # Risk-free rate (daily)
  daily_rf <- RISK_FREE_RATE_ANNUAL / 252
  factor_data <- factor_data %>%
    mutate(
      mkt_rf = market_return - daily_rf,
      portfolio_excess = portfolio_return - daily_rf
    )

  cat(sprintf("    Market factor (Mkt-RF): %d observations\n", sum(!is.na(factor_data$mkt_rf))))
}

# Size factor (SMB): Small minus Big
if (!is.null(iwm_data) && !is.null(spy_data)) {
  combined <- spy_data %>%
    left_join(iwm_data, by = "date")

  combined <- combined %>%
    mutate(SMB = IWM - SPY)

  factor_data <- factor_data %>%
    left_join(combined %>% select(date, SMB), by = "date")

  cat(sprintf("    Size factor (SMB): %d observations\n", sum(!is.na(factor_data$SMB))))
}

# Value factor (HML): High minus Low book-to-market
if (!is.null(iwd_data) && !is.null(iwf_data)) {
  combined <- iwd_data %>%
    left_join(iwf_data, by = "date")

  combined <- combined %>%
    mutate(HML = IWD - IWF)

  factor_data <- factor_data %>%
    left_join(combined %>% select(date, HML), by = "date")

  cat(sprintf("    Value factor (HML): %d observations\n", sum(!is.na(factor_data$HML))))
}

# Momentum factor (MOM): MTUM return - market return
if (!is.null(mtum_data) && !is.null(spy_data)) {
  combined <- mtum_data %>%
    left_join(spy_data, by = "date")

  combined <- combined %>%
    mutate(MOM = MTUM - SPY)

  factor_data <- factor_data %>%
    left_join(combined %>% select(date, MOM), by = "date")

  cat(sprintf("    Momentum factor (MOM): %d observations\n", sum(!is.na(factor_data$MOM))))
}

# Remove rows with missing factor data
complete_factor_data <- factor_data %>%
  filter(complete.cases(.))

cat(sprintf("\n  Complete factor data: %d days (%.1f%% of portfolio returns)\n",
            nrow(complete_factor_data),
            100 * nrow(complete_factor_data) / length(portfolio_returns)))

# ============================================================================
# STEP 3: RUN FACTOR REGRESSIONS
# ============================================================================

cat("\nStep 3: Running factor regressions...\n")

# Check which factors are available
available_factors <- names(complete_factor_data)
has_mkt <- "mkt_rf" %in% available_factors
has_smb <- "SMB" %in% available_factors
has_hml <- "HML" %in% available_factors
has_mom <- "MOM" %in% available_factors

if (!has_mkt) {
  cat("  ERROR: Market factor not available. Cannot run regression.\n")
  cat("  Factor decomposition skipped.\n")
  cat("\n=== MODULE 7 INCOMPLETE ===\n")
  quit(save = "no", status = 0)
}

# Build regression formula dynamically
formula_terms <- "portfolio_excess ~ mkt_rf"
if (has_smb) formula_terms <- paste(formula_terms, "+ SMB")
if (has_hml) formula_terms <- paste(formula_terms, "+ HML")
if (has_mom) formula_terms <- paste(formula_terms, "+ MOM")

regression_formula <- as.formula(formula_terms)

cat(sprintf("  Regression formula: %s\n", formula_terms))

# Run regression
factor_model <- lm(regression_formula, data = complete_factor_data)

# Summary
model_summary <- summary(factor_model)

cat("\n  === FACTOR REGRESSION RESULTS ===\n")
print(model_summary)

# Extract key statistics
alpha <- coef(factor_model)["(Intercept)"]
alpha_annual <- alpha * 252
alpha_tstat <- model_summary$coefficients["(Intercept)", "t value"]
alpha_pvalue <- model_summary$coefficients["(Intercept)", "Pr(>|t|)"]

r_squared <- model_summary$r.squared
adj_r_squared <- model_summary$adj.r.squared

# Extract factor betas
factor_names <- c("mkt_rf", "SMB", "HML", "MOM")
betas <- list()
for (factor in factor_names) {
  if (factor %in% rownames(model_summary$coefficients)) {
    betas[[factor]] <- list(
      beta = coef(factor_model)[factor],
      tstat = model_summary$coefficients[factor, "t value"],
      pvalue = model_summary$coefficients[factor, "Pr(>|t|)"]
    )
  }
}

# ============================================================================
# STEP 4: INTERPRET RESULTS
# ============================================================================

cat("\n\n=== FACTOR DECOMPOSITION INTERPRETATION ===\n")

# Alpha interpretation
cat(sprintf("\nALPHA (Excess Return after factor adjustment):\n"))
cat(sprintf("  Daily Alpha: %.4f%% (%.2f basis points)\n", alpha * 100, alpha * 10000))
cat(sprintf("  Annualized Alpha: %.2f%%\n", alpha_annual * 100))
cat(sprintf("  t-statistic: %.2f | p-value: %.4f\n", alpha_tstat, alpha_pvalue))

if (alpha_pvalue < 0.05) {
  if (alpha_annual > 0) {
    cat(sprintf("  ✓ SIGNIFICANT POSITIVE ALPHA: Genuine stock-picking skill detected!\n"))
  } else {
    cat(sprintf("  ✗ SIGNIFICANT NEGATIVE ALPHA: Underperformance after factor adjustment\n"))
  }
} else {
  cat(sprintf("  ~ NOT STATISTICALLY SIGNIFICANT: Alpha may be due to chance\n"))
}

# Factor exposures
cat(sprintf("\nFACTOR EXPOSURES (Betas):\n"))

if ("mkt_rf" %in% names(betas)) {
  b <- betas[["mkt_rf"]]
  cat(sprintf("  Market (β_mkt): %.3f (t=%.2f, p=%.4f)\n", b$beta, b$tstat, b$pvalue))
  if (b$beta > 1) {
    cat(sprintf("    → Portfolio is %.0f%% more volatile than market\n", (b$beta - 1) * 100))
  } else if (b$beta < 1) {
    cat(sprintf("    → Portfolio is %.0f%% less volatile than market\n", (1 - b$beta) * 100))
  }
}

if ("SMB" %in% names(betas)) {
  b <- betas[["SMB"]]
  cat(sprintf("  Size (β_smb): %.3f (t=%.2f, p=%.4f)\n", b$beta, b$tstat, b$pvalue))
  if (b$beta > 0 && b$pvalue < 0.05) {
    cat(sprintf("    → SMALL CAP TILT: Portfolio overweights small stocks\n"))
  } else if (b$beta < 0 && b$pvalue < 0.05) {
    cat(sprintf("    → LARGE CAP TILT: Portfolio overweights large stocks\n"))
  }
}

if ("HML" %in% names(betas)) {
  b <- betas[["HML"]]
  cat(sprintf("  Value (β_hml): %.3f (t=%.2f, p=%.4f)\n", b$beta, b$tstat, b$pvalue))
  if (b$beta > 0 && b$pvalue < 0.05) {
    cat(sprintf("    → VALUE TILT: Portfolio overweights value stocks\n"))
  } else if (b$beta < 0 && b$pvalue < 0.05) {
    cat(sprintf("    → GROWTH TILT: Portfolio overweights growth stocks\n"))
  }
}

if ("MOM" %in% names(betas)) {
  b <- betas[["MOM"]]
  cat(sprintf("  Momentum (β_mom): %.3f (t=%.2f, p=%.4f)\n", b$beta, b$tstat, b$pvalue))
  if (b$beta > 0 && b$pvalue < 0.05) {
    cat(sprintf("    → MOMENTUM STRATEGY: Portfolio chases recent winners\n"))
  }
}

# R-squared interpretation
cat(sprintf("\nMODEL FIT:\n"))
cat(sprintf("  R-squared: %.2f%%\n", r_squared * 100))
cat(sprintf("  Adjusted R-squared: %.2f%%\n", adj_r_squared * 100))
cat(sprintf("  → %.1f%% of portfolio variance explained by factors\n", r_squared * 100))
cat(sprintf("  → %.1f%% is idiosyncratic (stock-specific)\n", (1 - r_squared) * 100))

# Overall assessment
cat(sprintf("\nOVERALL ASSESSMENT:\n"))

if (r_squared > 0.9) {
  cat(sprintf("  Portfolio returns are ALMOST ENTIRELY driven by factor exposures.\n"))
  if (alpha_pvalue >= 0.05) {
    cat(sprintf("  WARNING: No significant alpha. Consider low-cost factor ETFs instead.\n"))
  }
} else if (r_squared > 0.7) {
  cat(sprintf("  Portfolio returns are MOSTLY explained by factor exposures.\n"))
  if (alpha_pvalue < 0.05 && alpha_annual > 0.03) {
    cat(sprintf("  ✓ But significant alpha (%.2f%%) suggests some stock-picking skill.\n", alpha_annual * 100))
  }
} else {
  cat(sprintf("  Portfolio has SIGNIFICANT idiosyncratic component (stock-specific bets).\n"))
  if (alpha_pvalue < 0.05) {
    cat(sprintf("  ✓ Alpha is significant: strategy adds value beyond factors.\n"))
  } else {
    cat(sprintf("  ~ Alpha is not significant: high idiosyncratic risk without reward.\n"))
  }
}

# ============================================================================
# STEP 5: SAVE RESULTS
# ============================================================================

cat("\nStep 5: Saving factor decomposition results...\n")

# Save regression object
saveRDS(factor_model, file.path(FACTOR_DIR, "factor_model.rds"))

# Save summary table
factor_results <- data.frame(
  strategy = strategy,
  alpha_daily = alpha,
  alpha_annual = alpha_annual,
  alpha_tstat = alpha_tstat,
  alpha_pvalue = alpha_pvalue,
  r_squared = r_squared,
  adj_r_squared = adj_r_squared,
  stringsAsFactors = FALSE
)

# Add factor betas
for (factor in names(betas)) {
  factor_results[[paste0("beta_", factor)]] <- betas[[factor]]$beta
  factor_results[[paste0("tstat_", factor)]] <- betas[[factor]]$tstat
  factor_results[[paste0("pvalue_", factor)]] <- betas[[factor]]$pvalue
}

write.csv(factor_results, file.path(FACTOR_DIR, "factor_results.csv"), row.names = FALSE)
saveRDS(factor_results, file.path(FACTOR_DIR, "factor_results.rds"))

cat(sprintf("  Saved: %s\n", file.path(FACTOR_DIR, "factor_results.csv")))

# Save factor data for future analysis
write.csv(complete_factor_data, file.path(FACTOR_DIR, "factor_data.csv"), row.names = FALSE)
saveRDS(complete_factor_data, file.path(FACTOR_DIR, "factor_data.rds"))

# ============================================================================
# STEP 6: CREATE SUMMARY REPORT
# ============================================================================

cat("\nStep 6: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 7: FACTOR DECOMPOSITION ANALYSIS ===
Generated: %s

PORTFOLIO ANALYZED: %s strategy
Stocks: %s

REGRESSION MODEL:
%s

RESULTS:
─────────────────────────────────────────────────
ALPHA (Stock-Picking Skill):
  Daily Alpha:       %+.4f%% (%+.2f bps)
  Annualized Alpha:  %+.2f%%
  t-statistic:       %.2f
  p-value:           %.4f
  Significance:      %s

FACTOR EXPOSURES (Betas):
%s

MODEL FIT:
  R-squared:         %.2f%%
  Adjusted R²:       %.2f%%
  Residual Std Err:  %.4f

INTERPRETATION:
%s

CONCLUSION:
%s

FILES GENERATED:
- Factor regression model: analysis/factors/factor_model.rds
- Factor results table:    analysis/factors/factor_results.csv
- Factor time series:      analysis/factors/factor_data.csv
",
Sys.time(),
toupper(strategy),
paste(tickers, collapse = ", "),
formula_terms,
alpha * 100, alpha * 10000,
alpha_annual * 100,
alpha_tstat,
alpha_pvalue,
ifelse(alpha_pvalue < 0.05,
       ifelse(alpha > 0, "SIGNIFICANT POSITIVE", "SIGNIFICANT NEGATIVE"),
       "NOT SIGNIFICANT"),
paste(sapply(names(betas), function(f) {
  b <- betas[[f]]
  sprintf("  %s: %.3f (t=%.2f, p=%.4f) %s",
          toupper(f), b$beta, b$tstat, b$pvalue,
          ifelse(b$pvalue < 0.05, "*", ""))
}), collapse = "\n"),
r_squared * 100,
adj_r_squared * 100,
model_summary$sigma,
paste(c(
  sprintf("%.1f%% of portfolio variance explained by known risk factors", r_squared * 100),
  sprintf("%.1f%% is stock-specific (idiosyncratic risk)", (1 - r_squared) * 100),
  if (alpha_pvalue < 0.05 && alpha > 0) {
    sprintf("Significant positive alpha of %.2f%% per year suggests genuine skill", alpha_annual * 100)
  } else if (alpha_pvalue < 0.05 && alpha < 0) {
    sprintf("Significant negative alpha of %.2f%% suggests underperformance", alpha_annual * 100)
  } else {
    "Alpha is not statistically significant - returns may be factor exposure"
  }
), collapse = "\n"),
if (alpha_pvalue < 0.05 && alpha_annual > 0.02 && r_squared < 0.85) {
  "VALIDATED: Strategy shows genuine alpha beyond factor exposures.
This suggests the portfolio selection methodology has predictive power."
} else if (r_squared > 0.9 && alpha_pvalue >= 0.05) {
  "FACTOR-DRIVEN: Returns are almost entirely explained by factor exposures.
Consider replacing with low-cost factor ETFs for similar exposure."
} else {
  "MIXED RESULTS: Some stock-specific bets, but unclear if alpha is reliable.
Monitor performance and consider adjusting strategy."
}
)

writeLines(summary_report, file.path(FACTOR_DIR, "factor_summary.txt"))
cat(summary_report)

cat("\n=== MODULE 7 COMPLETE ===\n\n")
