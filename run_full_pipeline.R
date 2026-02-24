# ============================================================================
# FULL PIPELINE RUNNER
# Runs all 6 modules in sequence
# ============================================================================

cat("\n")
cat("╔════════════════════════════════════════════════════════════════════════╗\n")
cat("║           PORTFOLIO OPTIMIZATION - FULL PIPELINE                       ║\n")
cat("║                   (With Regime Detection & Factor Analysis)            ║\n")
cat("╚════════════════════════════════════════════════════════════════════════╝\n\n")

start_time <- Sys.time()

# Module 0: Market Regime Detection (NEW)
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 0: Market Regime Detection\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("00_market_regime.R")
cat("\n✓ Module 0 complete\n\n")

# Module 1: Download stock data
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 1: Download Stock Data\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("01_download_stock_data.R")
cat("\n✓ Module 1 complete\n\n")

# Module 2: Technical analysis
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 2: Technical Analysis & Screening\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("02_technical_analysis_screening.R")
cat("\n✓ Module 2 complete\n\n")

# Module 3: Correlation analysis
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 3: Correlation Analysis\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("03_correlation_analysis.R")
cat("\n✓ Module 3 complete\n\n")

# Module 4: Ichimoku validation
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 4: Ichimoku Validation\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("04_ichimoku_validation.R")
cat("\n✓ Module 4 complete\n\n")

# Module 5: Portfolio optimization
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 5: Portfolio Optimization\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("05_portfolio_optimization.R")
cat("\n✓ Module 5 complete\n\n")

# Module 6: Backtest validation
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 6: Backtest Validation\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("06_backtest_validation.R")
cat("\n✓ Module 6 complete\n\n")

# Module 7: Factor Decomposition (NEW)
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("STARTING MODULE 7: Factor Decomposition Analysis\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("07_factor_decomposition.R")
cat("\n✓ Module 7 complete\n\n")

# Export data for webapp
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
cat("EXPORTING DATA FOR WEB APP\n")
cat("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
source("webapp/db/export_r_data.R")
cat("\n✓ Export complete\n\n")

# Summary
end_time <- Sys.time()
duration <- difftime(end_time, start_time, units = "mins")

cat("╔════════════════════════════════════════════════════════════════════════╗\n")
cat("║                    PIPELINE COMPLETE                                   ║\n")
cat("╚════════════════════════════════════════════════════════════════════════╝\n\n")
cat(sprintf("Total runtime: %.1f minutes\n", as.numeric(duration)))
cat("Check the analysis/ folder for results.\n")
cat("Run 'python -m uvicorn webapp.api.main:app --reload' to start the webapp.\n\n")
