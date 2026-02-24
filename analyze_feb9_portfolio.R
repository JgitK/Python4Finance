# ============================================================================
# FEB 9 PORTFOLIO PERFORMANCE ANALYSIS
# Downloads fresh data for the Feb 9 holdings and calculates P&L
# ============================================================================

suppressPackageStartupMessages({
  library(quantmod)
  library(dplyr)
  library(lubridate)
})

# Feb 9 portfolio (Risk Parity strategy)
feb9_portfolio <- tribble(
  ~ticker, ~shares, ~buy_price, ~cost,       ~sector,
  "WDC",    3,       269.41,     808.23,      "Technology",
  "AU",     6,       100.87,     605.22,      "Basic Materials",
  "MU",     1,       379.40,     379.40,      "Technology",
  "AGX",    1,       354.14,     354.14,      "Consumer Disc",
  "IONS",   4,        84.99,     339.96,      "Health Care",
  "CSTM",  12,        24.30,     291.60,      "Industrials",
  "CIEN",   1,       253.50,     253.50,      "Utilities",
  "FIVE",   1,       192.93,     192.93,      "Consumer Disc",
  "SSL",   24,         7.29,     174.96,      "Energy",
  "GEL",    7,        17.33,     121.31,      "Energy",
  "COCO",   2,        55.00,     110.00,      "Consumer Staples"
)

total_cost <- sum(feb9_portfolio$cost)  # $3,631.25

cat("=== FEB 9 PORTFOLIO PERFORMANCE ANALYSIS ===\n")
cat(sprintf("Purchase Date : Feb 9, 2026\n"))
cat(sprintf("Analysis Date : %s\n", Sys.Date()))
cat(sprintf("Total Invested: $%.2f\n\n", total_cost))

# Download fresh data for each holding
buy_date   <- as.Date("2026-02-09")
today_date <- Sys.Date()
start_dl   <- buy_date - days(5)   # a few days before for context

results <- list()

for (i in seq_len(nrow(feb9_portfolio))) {
  ticker     <- feb9_portfolio$ticker[i]
  shares     <- feb9_portfolio$shares[i]
  buy_price  <- feb9_portfolio$buy_price[i]
  cost_basis <- feb9_portfolio$cost[i]

  tryCatch({
    env <- new.env()
    getSymbols(ticker, src = "yahoo",
               from = start_dl, to = today_date,
               env = env, auto.assign = TRUE, warnings = FALSE)

    raw <- get(ticker, envir = env)
    df  <- data.frame(
      date  = index(raw),
      close = as.numeric(Ad(raw))   # adjusted close
    )

    # Price on/just after Feb 9
    on_date <- df %>% filter(date >= buy_date) %>% slice(1)
    latest  <- df %>% slice(n())

    current_price  <- latest$close
    actual_buy     <- on_date$close   # what the adjusted price was on Feb 9

    current_value  <- shares * current_price
    pnl            <- current_value - cost_basis
    pct_return     <- (current_price - buy_price) / buy_price * 100

    results[[ticker]] <- data.frame(
      ticker         = ticker,
      sector         = feb9_portfolio$sector[i],
      shares         = shares,
      buy_price      = buy_price,
      current_price  = round(current_price, 2),
      cost_basis     = cost_basis,
      current_value  = round(current_value, 2),
      pnl            = round(pnl, 2),
      pct_return     = round(pct_return, 2),
      latest_date    = latest$date,
      stringsAsFactors = FALSE
    )

    cat(sprintf("  %-6s  buy=$%7.2f  now=$%7.2f  P&L=%+7.2f  (%+.1f%%)\n",
                ticker, buy_price, current_price, pnl, pct_return))

  }, error = function(e) {
    cat(sprintf("  %-6s  FAILED: %s\n", ticker, conditionMessage(e)))
  })
}

# Combine results
df_results <- bind_rows(results)

if (nrow(df_results) == 0) {
  cat("\nNo data retrieved — check network / Yahoo Finance availability.\n")
  quit(status = 1)
}

# --- Portfolio-level summary ---
total_current  <- sum(df_results$current_value)
total_pnl      <- total_current - total_cost
portfolio_pct  <- (total_current - total_cost) / total_cost * 100

# --- SPY benchmark over same period ---
spy_env <- new.env()
tryCatch({
  getSymbols("SPY", src = "yahoo",
             from = start_dl, to = today_date,
             env = spy_env, auto.assign = TRUE, warnings = FALSE)
  spy_raw  <- get("SPY", envir = spy_env)
  spy_df   <- data.frame(date = index(spy_raw), close = as.numeric(Ad(spy_raw)))
  spy_buy  <- spy_df %>% filter(date >= buy_date) %>% slice(1) %>% pull(close)
  spy_now  <- spy_df %>% slice(n()) %>% pull(close)
  spy_pct  <- (spy_now - spy_buy) / spy_buy * 100
  spy_ok   <- TRUE
}, error = function(e) {
  spy_pct <<- NA
  spy_ok  <<- FALSE
})

cat("\n")
cat(rep("=", 65), "\n", sep = "")
cat("PORTFOLIO SUMMARY (Feb 9 → ", format(today_date), ")\n", sep = "")
cat(rep("=", 65), "\n", sep = "")
cat(sprintf("  Total Cost Basis   : $%8.2f\n", total_cost))
cat(sprintf("  Current Value      : $%8.2f\n", total_current))
cat(sprintf("  Total P&L          : %+.2f\n", total_pnl))
cat(sprintf("  Portfolio Return   : %+.2f%%\n", portfolio_pct))
if (!is.na(spy_pct)) {
  cat(sprintf("  SPY Return (same)  : %+.2f%%\n", spy_pct))
  cat(sprintf("  Alpha vs SPY       : %+.2f%%\n", portfolio_pct - spy_pct))
}

# Winners and losers
cat("\n--- WINNERS ---\n")
winners <- df_results %>% arrange(desc(pct_return)) %>% filter(pct_return > 0)
if (nrow(winners) > 0) {
  for (i in seq_len(nrow(winners))) {
    r <- winners[i, ]
    cat(sprintf("  %-6s  %+.1f%%  (P&L: %+.2f)  [%s]\n",
                r$ticker, r$pct_return, r$pnl, r$sector))
  }
} else cat("  (none)\n")

cat("\n--- LOSERS ---\n")
losers <- df_results %>% arrange(pct_return) %>% filter(pct_return <= 0)
if (nrow(losers) > 0) {
  for (i in seq_len(nrow(losers))) {
    r <- losers[i, ]
    cat(sprintf("  %-6s  %+.1f%%  (P&L: %+.2f)  [%s]\n",
                r$ticker, r$pct_return, r$pnl, r$sector))
  }
} else cat("  (none)\n")

cat("\n--- FULL POSITION TABLE ---\n")
cat(sprintf("%-6s  %-22s  %3s  Buy($)   Now($)  Value($)   P&L($)   Ret(%%)\n",
            "Ticker", "Sector", "Sh."))
cat(rep("-", 80), "\n", sep = "")
for (i in seq_len(nrow(df_results))) {
  r <- df_results[i, ]
  cat(sprintf("%-6s  %-22s  %3d  %7.2f  %7.2f  %8.2f  %+7.2f  %+6.1f%%\n",
              r$ticker, r$sector, r$shares,
              r$buy_price, r$current_price,
              r$current_value, r$pnl, r$pct_return))
}
cat(rep("-", 80), "\n", sep = "")
cat(sprintf("%-6s  %-22s  %3d  %7.2f          %8.2f  %+7.2f  %+6.1f%%\n",
            "TOTAL", "", as.integer(sum(df_results$shares)),
            total_cost / sum(df_results$shares),
            total_current, total_pnl, portfolio_pct))

# Save results
write.csv(df_results, "analysis/feb9_portfolio_performance.csv", row.names = FALSE)
cat(sprintf("\nResults saved: analysis/feb9_portfolio_performance.csv\n"))
cat(sprintf("Data as of: %s\n", max(df_results$latest_date)))
