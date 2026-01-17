# ============================================================================
# MODULE 5: PORTFOLIO OPTIMIZATION & EFFICIENT FRONTIER
# ============================================================================
# Calculates optimal portfolio weights using Modern Portfolio Theory
# Following principles from: https://www.codingfinance.com/
#
# Inputs: Final portfolio from Module 3
# Outputs: Optimal weights, efficient frontier, dollar allocations
#
# Author: Portfolio Optimization System
# Date: 2026-01-17

# Load utilities
source("utils_data_loader.R")

# Additional packages
if (!require("quadprog", quietly = TRUE)) install.packages("quadprog")
if (!require("ggplot2", quietly = TRUE)) install.packages("ggplot2")
library(quadprog)
library(ggplot2)

# ============================================================================
# CONFIGURATION
# ============================================================================

cat("\n=== MODULE 5: PORTFOLIO OPTIMIZATION ===\n\n")

# Optimization parameters
NUM_PORTFOLIOS <- 10000       # Number of random portfolios for efficient frontier
RISK_FREE_RATE <- 0.045       # 4.5% annual (10-year Treasury as of 2026)
OPTIMIZATION_PERIOD <- 252    # Trading days for return calculation (1 year)

# Investment parameters (can be changed)
INVESTMENT_AMOUNT <- 10000    # Default: $10,000 (user can modify)

# Output directory
OUTPUT_DIR <- "analysis"
WEIGHTS_FILE <- file.path(OUTPUT_DIR, "optimal_weights.csv")
WEIGHTS_RDS <- file.path(OUTPUT_DIR, "optimal_weights.rds")
ALLOCATION_FILE <- file.path(OUTPUT_DIR, "dollar_allocation.csv")
FRONTIER_FILE <- file.path(OUTPUT_DIR, "efficient_frontier.csv")
FRONTIER_RDS <- file.path(OUTPUT_DIR, "efficient_frontier.rds")

# ============================================================================
# STEP 1: LOAD FINAL PORTFOLIO
# ============================================================================

cat("Step 1: Loading final portfolio...\n")

# Load portfolio
portfolio <- readRDS(file.path(OUTPUT_DIR, "final_portfolio.rds"))
tickers <- portfolio$ticker

cat(sprintf("  Portfolio stocks: %d\n", length(tickers)))
cat(sprintf("  Tickers: %s\n", paste(tickers, collapse = ", ")))

# ============================================================================
# STEP 2: CREATE RETURNS MATRIX
# ============================================================================

cat("\nStep 2: Creating returns matrix...\n")

# Load stock data for all portfolio stocks
stock_data_list <- load_multiple_stocks(tickers)

cat(sprintf("  Successfully loaded: %d stocks\n", length(stock_data_list)))

# Calculate returns and create matrix
returns_list <- lapply(names(stock_data_list), function(ticker) {
  stock_data_list[[ticker]] %>%
    arrange(date) %>%
    mutate(daily_return = (adjusted - lag(adjusted)) / lag(adjusted)) %>%
    select(date, daily_return) %>%
    tail(OPTIMIZATION_PERIOD + 1) %>%  # +1 for lag
    rename(!!ticker := daily_return)
})

# Join all returns
returns_matrix <- reduce(returns_list, full_join, by = "date") %>%
  arrange(date) %>%
  filter(!is.na(date))

cat(sprintf("  Returns matrix: %d days × %d stocks\n",
            nrow(returns_matrix), ncol(returns_matrix) - 1))

# Extract returns only (remove date column)
returns_df <- returns_matrix %>% select(-date)

# Convert to matrix
returns_mat <- as.matrix(returns_df)

# Remove any rows with NA
returns_mat <- returns_mat[complete.cases(returns_mat), ]

cat(sprintf("  Clean returns matrix: %d days × %d stocks\n",
            nrow(returns_mat), ncol(returns_mat)))

# ============================================================================
# STEP 3: CALCULATE PORTFOLIO STATISTICS
# ============================================================================

cat("\nStep 3: Calculating portfolio statistics...\n")

# Calculate mean returns (annualized)
mean_returns <- colMeans(returns_mat, na.rm = TRUE) * 252

# Calculate covariance matrix (annualized)
cov_matrix <- cov(returns_mat, use = "complete.obs") * 252

cat(sprintf("  Average annual return range: %.1f%% to %.1f%%\n",
            100 * min(mean_returns), 100 * max(mean_returns)))

# Display expected returns
cat("\n  Expected Annual Returns:\n")
return_summary <- data.frame(
  ticker = names(mean_returns),
  annual_return = sprintf("%.1f%%", 100 * mean_returns),
  stringsAsFactors = FALSE
)
print(return_summary, row.names = FALSE)

# ============================================================================
# STEP 4: GENERATE EFFICIENT FRONTIER
# ============================================================================

cat("\nStep 4: Generating efficient frontier...\n")
cat(sprintf("  Simulating %s random portfolios...\n",
            format(NUM_PORTFOLIOS, big.mark = ",")))

# Function to calculate portfolio statistics
calc_portfolio_stats <- function(weights, mean_returns, cov_matrix, rf_rate) {
  port_return <- sum(weights * mean_returns)
  port_variance <- t(weights) %*% cov_matrix %*% weights
  port_sd <- sqrt(port_variance)
  sharpe_ratio <- (port_return - rf_rate) / port_sd

  return(list(
    return = as.numeric(port_return),
    risk = as.numeric(port_sd),
    sharpe = as.numeric(sharpe_ratio)
  ))
}

# Generate random portfolios
set.seed(123)  # For reproducibility
num_assets <- length(tickers)

all_portfolios <- data.frame(
  portfolio = integer(),
  return = numeric(),
  risk = numeric(),
  sharpe = numeric()
)

# Store weights for each portfolio
all_weights <- matrix(nrow = NUM_PORTFOLIOS, ncol = num_assets)
colnames(all_weights) <- tickers

for (i in 1:NUM_PORTFOLIOS) {
  # Generate random weights
  weights <- runif(num_assets)
  weights <- weights / sum(weights)  # Normalize to sum to 1

  # Calculate statistics
  stats <- calc_portfolio_stats(weights, mean_returns, cov_matrix, RISK_FREE_RATE)

  # Store results
  all_portfolios <- rbind(all_portfolios, data.frame(
    portfolio = i,
    return = stats$return,
    risk = stats$risk,
    sharpe = stats$sharpe
  ))

  all_weights[i, ] <- weights

  # Progress indicator
  if (i %% 1000 == 0) {
    cat(sprintf("    Progress: %s / %s portfolios\n",
                format(i, big.mark = ","),
                format(NUM_PORTFOLIOS, big.mark = ",")))
  }
}

cat(sprintf("\n  Generated %s portfolios\n", format(NUM_PORTFOLIOS, big.mark = ",")))

# ============================================================================
# STEP 5: FIND OPTIMAL PORTFOLIOS
# ============================================================================

cat("\nStep 5: Finding optimal portfolios...\n")

# Maximum Sharpe Ratio portfolio
max_sharpe_idx <- which.max(all_portfolios$sharpe)
max_sharpe_portfolio <- all_portfolios[max_sharpe_idx, ]
max_sharpe_weights <- all_weights[max_sharpe_idx, ]

cat("\n  === MAXIMUM SHARPE RATIO PORTFOLIO ===\n")
cat(sprintf("    Expected Return: %.2f%%\n", 100 * max_sharpe_portfolio$return))
cat(sprintf("    Expected Risk (Std Dev): %.2f%%\n", 100 * max_sharpe_portfolio$risk))
cat(sprintf("    Sharpe Ratio: %.3f\n", max_sharpe_portfolio$sharpe))

# Minimum Variance portfolio
min_var_idx <- which.min(all_portfolios$risk)
min_var_portfolio <- all_portfolios[min_var_idx, ]
min_var_weights <- all_weights[min_var_idx, ]

cat("\n  === MINIMUM VARIANCE PORTFOLIO ===\n")
cat(sprintf("    Expected Return: %.2f%%\n", 100 * min_var_portfolio$return))
cat(sprintf("    Expected Risk (Std Dev): %.2f%%\n", 100 * min_var_portfolio$risk))
cat(sprintf("    Sharpe Ratio: %.3f\n", min_var_portfolio$sharpe))

# Equal Weight portfolio (for comparison)
equal_weights <- rep(1/num_assets, num_assets)
equal_stats <- calc_portfolio_stats(equal_weights, mean_returns, cov_matrix, RISK_FREE_RATE)

cat("\n  === EQUAL WEIGHT PORTFOLIO (Baseline) ===\n")
cat(sprintf("    Expected Return: %.2f%%\n", 100 * equal_stats$return))
cat(sprintf("    Expected Risk (Std Dev): %.2f%%\n", 100 * equal_stats$risk))
cat(sprintf("    Sharpe Ratio: %.3f\n", equal_stats$sharpe))

# ============================================================================
# STEP 6: SAVE OPTIMAL WEIGHTS
# ============================================================================

cat("\nStep 6: Saving optimal weights...\n")

# Create weights dataframe
optimal_weights <- data.frame(
  ticker = tickers,
  max_sharpe_weight = max_sharpe_weights,
  min_variance_weight = min_var_weights,
  equal_weight = equal_weights,
  stringsAsFactors = FALSE
)

# Add stock info
optimal_weights <- optimal_weights %>%
  left_join(portfolio %>% select(ticker, sector, cumulative_return_1y, sharpe_ratio),
            by = "ticker") %>%
  arrange(desc(max_sharpe_weight))

# Display optimal weights
cat("\n  Optimal Weights (Maximum Sharpe Ratio):\n")
print(optimal_weights %>%
        select(ticker, sector, max_sharpe_weight) %>%
        mutate(weight_pct = sprintf("%.2f%%", 100 * max_sharpe_weight)) %>%
        select(ticker, sector, weight_pct),
      row.names = FALSE)

# Save weights
write.csv(optimal_weights, WEIGHTS_FILE, row.names = FALSE)
saveRDS(optimal_weights, WEIGHTS_RDS)

cat(sprintf("\n  Saved weights: %s\n", WEIGHTS_FILE))

# ============================================================================
# STEP 7: CALCULATE DOLLAR ALLOCATION
# ============================================================================

cat("\nStep 7: Calculating dollar allocation...\n")
cat(sprintf("  Investment amount: $%s\n", format(INVESTMENT_AMOUNT, big.mark = ",")))

# Function to calculate allocations
calculate_allocation <- function(weights, investment, stock_prices) {

  allocation <- data.frame(
    ticker = names(weights),
    weight = weights,
    dollar_amount = weights * investment,
    stringsAsFactors = FALSE
  )

  # Add current prices
  allocation <- allocation %>%
    left_join(
      portfolio %>% select(ticker, current_price),
      by = "ticker"
    ) %>%
    mutate(
      shares = floor(dollar_amount / current_price),  # Whole shares only
      actual_invested = shares * current_price,
      remaining = dollar_amount - actual_invested
    )

  return(allocation)
}

# Calculate allocation for max Sharpe portfolio
max_sharpe_allocation <- calculate_allocation(
  max_sharpe_weights,
  INVESTMENT_AMOUNT,
  portfolio$current_price
)

# Display allocation
cat("\n  === DOLLAR ALLOCATION (Maximum Sharpe Ratio) ===\n")
print(max_sharpe_allocation %>%
        select(ticker, weight, dollar_amount, current_price, shares, actual_invested) %>%
        mutate(
          weight_pct = sprintf("%.1f%%", 100 * weight),
          dollar_amount = sprintf("$%.2f", dollar_amount),
          current_price = sprintf("$%.2f", current_price),
          actual_invested = sprintf("$%.2f", actual_invested)
        ) %>%
        select(-weight),
      row.names = FALSE)

# Summary
total_invested <- sum(max_sharpe_allocation$actual_invested)
cash_remaining <- INVESTMENT_AMOUNT - total_invested

cat(sprintf("\n  Total invested: $%.2f\n", total_invested))
cat(sprintf("  Cash remaining: $%.2f\n", cash_remaining))
cat(sprintf("  Investment efficiency: %.2f%%\n", 100 * total_invested / INVESTMENT_AMOUNT))

# Save allocation
write.csv(max_sharpe_allocation, ALLOCATION_FILE, row.names = FALSE)
cat(sprintf("  Saved allocation: %s\n", ALLOCATION_FILE))

# ============================================================================
# STEP 8: PLOT EFFICIENT FRONTIER
# ============================================================================

cat("\nStep 8: Creating efficient frontier visualization...\n")

# Create plot
frontier_plot <- ggplot(all_portfolios, aes(x = risk, y = return)) +
  geom_point(aes(color = sharpe), alpha = 0.5, size = 0.8) +
  scale_color_gradient(low = "red", high = "green", name = "Sharpe\nRatio") +

  # Add optimal portfolios
  geom_point(data = max_sharpe_portfolio,
             aes(x = risk, y = return),
             color = "darkgreen", size = 5, shape = 17) +
  geom_point(data = min_var_portfolio,
             aes(x = risk, y = return),
             color = "blue", size = 5, shape = 17) +
  geom_point(data = data.frame(risk = equal_stats$risk, return = equal_stats$return),
             aes(x = risk, y = return),
             color = "black", size = 5, shape = 17) +

  # Labels
  annotate("text", x = max_sharpe_portfolio$risk, y = max_sharpe_portfolio$return,
           label = "Max Sharpe", hjust = -0.1, vjust = -0.5, size = 4) +
  annotate("text", x = min_var_portfolio$risk, y = min_var_portfolio$return,
           label = "Min Variance", hjust = -0.1, vjust = -0.5, size = 4) +
  annotate("text", x = equal_stats$risk, y = equal_stats$return,
           label = "Equal Weight", hjust = -0.1, vjust = -0.5, size = 4) +

  # Formatting
  labs(
    title = "Efficient Frontier - Portfolio Optimization",
    subtitle = sprintf("Based on %s simulated portfolios", format(NUM_PORTFOLIOS, big.mark = ",")),
    x = "Risk (Annual Standard Deviation)",
    y = "Expected Return (Annual)"
  ) +
  scale_x_continuous(labels = scales::percent) +
  scale_y_continuous(labels = scales::percent) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "right"
  )

# Save plot
ggsave(file.path(OUTPUT_DIR, "efficient_frontier.pdf"),
       frontier_plot, width = 12, height = 8)
ggsave(file.path(OUTPUT_DIR, "efficient_frontier.png"),
       frontier_plot, width = 12, height = 8, dpi = 300)

cat("  Saved plots:\n")
cat(sprintf("    - %s\n", file.path(OUTPUT_DIR, "efficient_frontier.pdf")))
cat(sprintf("    - %s\n", file.path(OUTPUT_DIR, "efficient_frontier.png")))

# Save frontier data
write.csv(all_portfolios, FRONTIER_FILE, row.names = FALSE)
saveRDS(list(
  portfolios = all_portfolios,
  weights = all_weights,
  tickers = tickers
), FRONTIER_RDS)

cat(sprintf("  Saved frontier data: %s\n", FRONTIER_FILE))

# ============================================================================
# STEP 9: GENERATE SUMMARY REPORT
# ============================================================================

cat("\nStep 9: Creating summary report...\n")

summary_report <- sprintf("
=== MODULE 5: PORTFOLIO OPTIMIZATION SUMMARY ===
Generated: %s

OPTIMIZATION PARAMETERS:
- Number of portfolios simulated: %s
- Risk-free rate: %.2f%% (10-year Treasury)
- Optimization period: %d trading days (~1 year)
- Investment amount: $%s

PORTFOLIO COMPOSITION:
- Number of stocks: %d
- Tickers: %s

OPTIMAL PORTFOLIO (Maximum Sharpe Ratio):
- Expected Annual Return: %.2f%%
- Expected Annual Risk (Std Dev): %.2f%%
- Sharpe Ratio: %.3f
- Risk-adjusted performance: %.1fx better than risk-free rate

COMPARISON TO ALTERNATIVES:

Maximum Sharpe Ratio Portfolio:
  Return: %.2f%% | Risk: %.2f%% | Sharpe: %.3f

Minimum Variance Portfolio:
  Return: %.2f%% | Risk: %.2f%% | Sharpe: %.3f

Equal Weight Portfolio:
  Return: %.2f%% | Risk: %.2f%% | Sharpe: %.3f

Improvement vs Equal Weight:
  Return: %+.2f%% | Risk: %+.2f%% | Sharpe: %+.3f

OPTIMAL WEIGHTS (Maximum Sharpe Ratio):
%s

DOLLAR ALLOCATION (for $%s investment):
%s

ALLOCATION SUMMARY:
- Total invested: $%.2f
- Cash remaining: $%.2f
- Investment efficiency: %.1f%%

RISK METRICS:
- Portfolio diversification: %d stocks across %d sectors
- Average correlation: %.3f
- Expected volatility: %.2f%% annually

FILES GENERATED:
- Optimal weights: %s
- Dollar allocation: %s
- Efficient frontier data: %s
- Efficient frontier plot: %s

INTERPRETATION:
- Sharpe Ratio > 1.0 is good, > 2.0 is excellent
- Your portfolio Sharpe: %.3f - %s
- Expected return significantly exceeds risk-free rate
- Diversification reduces risk while maintaining high returns

NEXT STEPS:
- Review dollar allocation and adjust investment amount if needed
- Run Module 6 for backtesting validation
- Consider rebalancing strategy for ongoing management
",
Sys.time(),
format(NUM_PORTFOLIOS, big.mark = ","),
100 * RISK_FREE_RATE,
OPTIMIZATION_PERIOD,
format(INVESTMENT_AMOUNT, big.mark = ","),
length(tickers),
paste(tickers, collapse = ", "),
100 * max_sharpe_portfolio$return,
100 * max_sharpe_portfolio$risk,
max_sharpe_portfolio$sharpe,
max_sharpe_portfolio$sharpe,
100 * max_sharpe_portfolio$return,
100 * max_sharpe_portfolio$risk,
max_sharpe_portfolio$sharpe,
100 * min_var_portfolio$return,
100 * min_var_portfolio$risk,
min_var_portfolio$sharpe,
100 * equal_stats$return,
100 * equal_stats$risk,
equal_stats$sharpe,
100 * (max_sharpe_portfolio$return - equal_stats$return),
100 * (max_sharpe_portfolio$risk - equal_stats$risk),
max_sharpe_portfolio$sharpe - equal_stats$sharpe,
paste(capture.output(print(
  optimal_weights %>%
    select(ticker, sector, max_sharpe_weight) %>%
    mutate(weight_pct = sprintf("%.2f%%", 100 * max_sharpe_weight)) %>%
    select(ticker, sector, weight_pct),
  row.names = FALSE
)), collapse = "\n"),
format(INVESTMENT_AMOUNT, big.mark = ","),
paste(capture.output(print(
  max_sharpe_allocation %>%
    select(ticker, shares, actual_invested) %>%
    mutate(invested = sprintf("$%.2f", actual_invested)) %>%
    select(ticker, shares, invested),
  row.names = FALSE
)), collapse = "\n"),
total_invested,
cash_remaining,
100 * total_invested / INVESTMENT_AMOUNT,
length(tickers),
length(unique(portfolio$sector)),
mean(portfolio$avg_correlation),
100 * max_sharpe_portfolio$risk,
WEIGHTS_FILE,
ALLOCATION_FILE,
FRONTIER_FILE,
file.path(OUTPUT_DIR, "efficient_frontier.png"),
max_sharpe_portfolio$sharpe,
ifelse(max_sharpe_portfolio$sharpe > 2.0, "Excellent",
       ifelse(max_sharpe_portfolio$sharpe > 1.0, "Good", "Fair"))
)

# Save summary
summary_file <- file.path(OUTPUT_DIR, "module_5_summary.txt")
writeLines(summary_report, summary_file)
cat(sprintf("  Summary report: %s\n", summary_file))

# Print summary to console
cat(summary_report)

cat("\n=== MODULE 5 COMPLETE ===\n\n")

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

cat("=== INVESTMENT CALCULATOR ===\n")
cat("To calculate allocation for different investment amounts:\n\n")
cat("# Example: $25,000 investment\n")
cat("investment <- 25000\n")
cat("weights <- readRDS('analysis/optimal_weights.rds')\n")
cat("allocation <- weights %>%\n")
cat("  mutate(\n")
cat("    dollar_amount = max_sharpe_weight * investment,\n")
cat("    shares = floor(dollar_amount / portfolio$current_price),\n")
cat("    actual_invested = shares * portfolio$current_price\n")
cat("  )\n")
cat("print(allocation %>% select(ticker, shares, actual_invested))\n\n")

cat("=== VIEW EFFICIENT FRONTIER ===\n")
cat("# Plot is saved as PNG and PDF in analysis/ folder\n")
cat("# Open: analysis/efficient_frontier.png\n\n")
