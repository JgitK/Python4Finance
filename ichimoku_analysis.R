# Ichimoku Kinko Hyo Technical Analysis Functions
# Purpose: Calculate and visualize Ichimoku Cloud indicator

library(quantmod)
library(tidyverse)
library(plotly)
library(xts)

#' Calculate Ichimoku Cloud components
#'
#' @param ticker Stock ticker symbol
#' @param period Time period (e.g., "1y", "2y", "5y")
#' @param interval Data interval (e.g., "1d", "1wk", "1mo")
#' @return Data frame with Ichimoku components
calculate_ichimoku <- function(ticker, period = "1y", interval = "1d") {

  message(sprintf("Calculating Ichimoku for %s...", ticker))

  # Download stock data
  stock_data <- tryCatch({
    getSymbols(ticker,
               src = "yahoo",
               period = period,
               auto.assign = FALSE,
               warnings = FALSE)
  }, error = function(e) {
    stop(sprintf("Failed to download data for %s: %s", ticker, e$message))
  })

  # Extract OHLC data
  high_col <- grep("High", colnames(stock_data), value = TRUE)
  low_col <- grep("Low", colnames(stock_data), value = TRUE)
  close_col <- grep("Close", colnames(stock_data), value = TRUE)
  open_col <- grep("Open", colnames(stock_data), value = TRUE)

  high <- stock_data[, high_col]
  low <- stock_data[, low_col]
  close <- stock_data[, close_col]
  open <- stock_data[, open_col]

  # Calculate Ichimoku components
  # Conversion Line (Tenkan-sen): (9-period high + 9-period low) / 2
  tenkan_high <- rollapply(high, width = 9, FUN = max, align = "right", fill = NA)
  tenkan_low <- rollapply(low, width = 9, FUN = min, align = "right", fill = NA)
  tenkan_sen <- (tenkan_high + tenkan_low) / 2

  # Base Line (Kijun-sen): (26-period high + 26-period low) / 2
  kijun_high <- rollapply(high, width = 26, FUN = max, align = "right", fill = NA)
  kijun_low <- rollapply(low, width = 26, FUN = min, align = "right", fill = NA)
  kijun_sen <- (kijun_high + kijun_low) / 2

  # Leading Span A (Senkou Span A): (Conversion Line + Base Line) / 2, plotted 26 periods ahead
  senkou_a <- (tenkan_sen + kijun_sen) / 2
  senkou_a_shifted <- lag(senkou_a, -26)

  # Leading Span B (Senkou Span B): (52-period high + 52-period low) / 2, plotted 26 periods ahead
  senkou_b_high <- rollapply(high, width = 52, FUN = max, align = "right", fill = NA)
  senkou_b_low <- rollapply(low, width = 52, FUN = min, align = "right", fill = NA)
  senkou_b <- (senkou_b_high + senkou_b_low) / 2
  senkou_b_shifted <- lag(senkou_b, -26)

  # Lagging Span (Chikou Span): Close price plotted 26 periods back
  chikou_span <- lag(close, 26)

  # Combine all into a data frame
  ichimoku_df <- data.frame(
    Date = index(stock_data),
    Open = as.numeric(open),
    High = as.numeric(high),
    Low = as.numeric(low),
    Close = as.numeric(close),
    Tenkan = as.numeric(tenkan_sen),
    Kijun = as.numeric(kijun_sen),
    SenkouA = as.numeric(senkou_a_shifted),
    SenkouB = as.numeric(senkou_b_shifted),
    Chikou = as.numeric(chikou_span)
  )

  # Remove rows with NA values
  ichimoku_df <- na.omit(ichimoku_df)

  message("Ichimoku calculation complete!")

  return(ichimoku_df)
}

#' Plot Ichimoku Cloud chart using Plotly
#'
#' @param ichimoku_data Data frame with Ichimoku components
#' @param ticker Stock ticker symbol for title
#' @return Plotly object
plot_ichimoku_chart <- function(ichimoku_data, ticker) {

  # Create candlestick chart
  fig <- plot_ly(ichimoku_data, x = ~Date) %>%
    add_trace(type = "candlestick",
              open = ~Open,
              high = ~High,
              low = ~Low,
              close = ~Close,
              name = "Price",
              increasing = list(line = list(color = "#00C853")),
              decreasing = list(line = list(color = "#FF1744"))) %>%

    # Add Tenkan-sen (Conversion Line)
    add_trace(y = ~Tenkan,
              type = "scatter",
              mode = "lines",
              name = "Tenkan-sen (Conversion)",
              line = list(color = "#FF6B6B", width = 1.5)) %>%

    # Add Kijun-sen (Base Line)
    add_trace(y = ~Kijun,
              type = "scatter",
              mode = "lines",
              name = "Kijun-sen (Base)",
              line = list(color = "#4ECDC4", width = 1.5)) %>%

    # Add Senkou Span A (Leading Span A)
    add_trace(y = ~SenkouA,
              type = "scatter",
              mode = "lines",
              name = "Senkou A",
              line = list(color = "#95E1D3", width = 1, dash = "dot"),
              fill = "tonexty",
              fillcolor = "rgba(149, 225, 211, 0.2)") %>%

    # Add Senkou Span B (Leading Span B)
    add_trace(y = ~SenkouB,
              type = "scatter",
              mode = "lines",
              name = "Senkou B",
              line = list(color = "#F38181", width = 1, dash = "dot"),
              fill = "tonexty",
              fillcolor = "rgba(243, 129, 129, 0.2)") %>%

    # Add Chikou Span (Lagging Span)
    add_trace(y = ~Chikou,
              type = "scatter",
              mode = "lines",
              name = "Chikou (Lagging)",
              line = list(color = "#AA96DA", width = 1, dash = "dash")) %>%

    # Layout configuration
    layout(
      title = paste("Ichimoku Cloud Chart -", ticker),
      xaxis = list(
        title = "Date",
        rangeslider = list(visible = TRUE),
        rangeselector = list(
          buttons = list(
            list(count = 1, label = "1m", step = "month", stepmode = "backward"),
            list(count = 3, label = "3m", step = "month", stepmode = "backward"),
            list(count = 6, label = "6m", step = "month", stepmode = "backward"),
            list(count = 1, label = "1y", step = "year", stepmode = "backward"),
            list(step = "all", label = "All")
          )
        )
      ),
      yaxis = list(title = "Price"),
      hovermode = "x unified",
      legend = list(orientation = "h", x = 0, y = 1.1),
      plot_bgcolor = "#F5F5F5",
      paper_bgcolor = "white"
    )

  return(fig)
}

#' Generate Ichimoku trading signals
#'
#' @param ichimoku_data Data frame with Ichimoku components
#' @return List with trading signals and interpretation
generate_ichimoku_signals <- function(ichimoku_data) {

  # Get most recent data points
  recent_data <- tail(ichimoku_data, 5)
  latest <- tail(ichimoku_data, 1)

  signals <- list()

  # 1. Tenkan-Kijun Cross
  if (nrow(recent_data) >= 2) {
    prev_tenkan <- recent_data$Tenkan[nrow(recent_data) - 1]
    prev_kijun <- recent_data$Kijun[nrow(recent_data) - 1]
    curr_tenkan <- latest$Tenkan
    curr_kijun <- latest$Kijun

    if (!is.na(prev_tenkan) && !is.na(prev_kijun) && !is.na(curr_tenkan) && !is.na(curr_kijun)) {
      if (prev_tenkan < prev_kijun && curr_tenkan > curr_kijun) {
        signals$tk_cross <- "BULLISH CROSS (Golden Cross)"
      } else if (prev_tenkan > prev_kijun && curr_tenkan < curr_kijun) {
        signals$tk_cross <- "BEARISH CROSS (Dead Cross)"
      } else if (curr_tenkan > curr_kijun) {
        signals$tk_cross <- "Tenkan above Kijun (Bullish)"
      } else {
        signals$tk_cross <- "Tenkan below Kijun (Bearish)"
      }
    } else {
      signals$tk_cross <- "Insufficient data"
    }
  }

  # 2. Price vs Cloud (Kumo)
  curr_price <- latest$Close
  curr_senkou_a <- latest$SenkouA
  curr_senkou_b <- latest$SenkouB

  if (!is.na(curr_senkou_a) && !is.na(curr_senkou_b)) {
    cloud_top <- max(curr_senkou_a, curr_senkou_b)
    cloud_bottom <- min(curr_senkou_a, curr_senkou_b)

    if (curr_price > cloud_top) {
      signals$cloud_status <- "Price ABOVE cloud (Bullish)"
      signals$trend <- "UPTREND"
    } else if (curr_price < cloud_bottom) {
      signals$cloud_status <- "Price BELOW cloud (Bearish)"
      signals$trend <- "DOWNTREND"
    } else {
      signals$cloud_status <- "Price INSIDE cloud (Neutral/Consolidation)"
      signals$trend <- "RANGING"
    }
  } else {
    signals$cloud_status <- "Insufficient data"
    signals$trend <- "UNKNOWN"
  }

  # 3. Cloud color (Senkou A vs Senkou B)
  if (!is.na(curr_senkou_a) && !is.na(curr_senkou_b)) {
    if (curr_senkou_a > curr_senkou_b) {
      signals$cloud_color <- "Bullish Cloud (Green)"
    } else {
      signals$cloud_color <- "Bearish Cloud (Red)"
    }
  } else {
    signals$cloud_color <- "Insufficient data"
  }

  # 4. Chikou Span vs Price
  if (!is.na(latest$Chikou)) {
    # Find price 26 periods ago
    if (nrow(ichimoku_data) >= 26) {
      price_26_ago <- ichimoku_data$Close[nrow(ichimoku_data) - 26]
      if (!is.na(price_26_ago)) {
        if (latest$Chikou > price_26_ago) {
          signals$chikou_status <- "Chikou above historical price (Bullish)"
        } else {
          signals$chikou_status <- "Chikou below historical price (Bearish)"
        }
      } else {
        signals$chikou_status <- "Insufficient data"
      }
    } else {
      signals$chikou_status <- "Insufficient data"
    }
  } else {
    signals$chikou_status <- "Insufficient data"
  }

  # 5. Overall signal
  bullish_count <- 0
  bearish_count <- 0

  if (grepl("Bullish|BULLISH|above", signals$tk_cross)) bullish_count <- bullish_count + 1
  if (grepl("Bearish|BEARISH|below", signals$tk_cross)) bearish_count <- bearish_count + 1

  if (signals$trend == "UPTREND") bullish_count <- bullish_count + 2
  if (signals$trend == "DOWNTREND") bearish_count <- bearish_count + 2

  if (grepl("Bullish", signals$cloud_color)) bullish_count <- bullish_count + 1
  if (grepl("Bearish", signals$cloud_color)) bearish_count <- bearish_count + 1

  if (grepl("Bullish", signals$chikou_status)) bullish_count <- bullish_count + 1
  if (grepl("Bearish", signals$chikou_status)) bearish_count <- bearish_count + 1

  if (bullish_count > bearish_count + 1) {
    signals$current_signal <- "STRONG BUY"
  } else if (bullish_count > bearish_count) {
    signals$current_signal <- "BUY"
  } else if (bearish_count > bullish_count + 1) {
    signals$current_signal <- "STRONG SELL"
  } else if (bearish_count > bullish_count) {
    signals$current_signal <- "SELL"
  } else {
    signals$current_signal <- "NEUTRAL/HOLD"
  }

  # Interpretation
  signals$interpretation <- paste0(
    "Based on the Ichimoku analysis:\n\n",
    "1. The Tenkan-Kijun relationship shows: ", signals$tk_cross, "\n",
    "2. Price position relative to cloud: ", signals$cloud_status, "\n",
    "3. Cloud color indicates: ", signals$cloud_color, "\n",
    "4. Chikou span analysis: ", signals$chikou_status, "\n\n",
    "Overall Trend: ", signals$trend, "\n",
    "Recommendation: ", signals$current_signal, "\n\n",
    "Note: Ichimoku works best for trending markets and may give false signals in ranging markets."
  )

  return(signals)
}

#' Calculate buy and sell signals based on Ichimoku
#'
#' @param ichimoku_data Data frame with Ichimoku components
#' @return Data frame with buy/sell signals
calculate_buy_sell_signals <- function(ichimoku_data) {

  ichimoku_data$Signal <- NA
  ichimoku_data$Position <- 0

  for (i in 2:nrow(ichimoku_data)) {
    # Tenkan-Kijun cross
    prev_tenkan <- ichimoku_data$Tenkan[i-1]
    prev_kijun <- ichimoku_data$Kijun[i-1]
    curr_tenkan <- ichimoku_data$Tenkan[i]
    curr_kijun <- ichimoku_data$Kijun[i]

    # Price vs Cloud
    curr_price <- ichimoku_data$Close[i]
    curr_senkou_a <- ichimoku_data$SenkouA[i]
    curr_senkou_b <- ichimoku_data$SenkouB[i]

    if (!is.na(prev_tenkan) && !is.na(prev_kijun) &&
        !is.na(curr_tenkan) && !is.na(curr_kijun) &&
        !is.na(curr_senkou_a) && !is.na(curr_senkou_b)) {

      cloud_top <- max(curr_senkou_a, curr_senkou_b)
      cloud_bottom <- min(curr_senkou_a, curr_senkou_b)

      # Buy signal: Tenkan crosses above Kijun AND price above cloud
      if (prev_tenkan < prev_kijun && curr_tenkan > curr_kijun && curr_price > cloud_top) {
        ichimoku_data$Signal[i] <- "BUY"
        ichimoku_data$Position[i] <- 1
      }
      # Sell signal: Tenkan crosses below Kijun OR price below cloud
      else if ((prev_tenkan > prev_kijun && curr_tenkan < curr_kijun) || curr_price < cloud_bottom) {
        ichimoku_data$Signal[i] <- "SELL"
        ichimoku_data$Position[i] <- -1
      }
      # Hold
      else {
        ichimoku_data$Signal[i] <- "HOLD"
        ichimoku_data$Position[i] <- ichimoku_data$Position[i-1]
      }
    }
  }

  return(ichimoku_data)
}

#' Backtest Ichimoku strategy
#'
#' @param ichimoku_data Data frame with Ichimoku components and signals
#' @param initial_capital Initial investment amount
#' @return List with backtest results
backtest_ichimoku <- function(ichimoku_data, initial_capital = 10000) {

  # Calculate buy/sell signals if not already present
  if (!"Signal" %in% colnames(ichimoku_data)) {
    ichimoku_data <- calculate_buy_sell_signals(ichimoku_data)
  }

  # Initialize portfolio
  cash <- initial_capital
  shares <- 0
  portfolio_value <- numeric(nrow(ichimoku_data))
  portfolio_value[1] <- initial_capital

  # Track trades
  trades <- data.frame()

  for (i in 2:nrow(ichimoku_data)) {
    if (!is.na(ichimoku_data$Signal[i])) {

      if (ichimoku_data$Signal[i] == "BUY" && shares == 0) {
        # Buy
        shares <- floor(cash / ichimoku_data$Close[i])
        cash <- cash - (shares * ichimoku_data$Close[i])

        trades <- rbind(trades, data.frame(
          Date = ichimoku_data$Date[i],
          Action = "BUY",
          Price = ichimoku_data$Close[i],
          Shares = shares,
          Cash = cash
        ))
      }
      else if (ichimoku_data$Signal[i] == "SELL" && shares > 0) {
        # Sell
        cash <- cash + (shares * ichimoku_data$Close[i])

        trades <- rbind(trades, data.frame(
          Date = ichimoku_data$Date[i],
          Action = "SELL",
          Price = ichimoku_data$Close[i],
          Shares = shares,
          Cash = cash
        ))

        shares <- 0
      }
    }

    # Calculate portfolio value
    portfolio_value[i] <- cash + (shares * ichimoku_data$Close[i])
  }

  # Calculate metrics
  total_return <- (portfolio_value[length(portfolio_value)] - initial_capital) / initial_capital
  buy_and_hold_return <- (ichimoku_data$Close[nrow(ichimoku_data)] - ichimoku_data$Close[1]) /
                          ichimoku_data$Close[1]

  results <- list(
    portfolio_value = portfolio_value,
    trades = trades,
    total_return = total_return,
    buy_and_hold_return = buy_and_hold_return,
    num_trades = nrow(trades),
    final_value = portfolio_value[length(portfolio_value)]
  )

  return(results)
}

#' Plot Ichimoku backtest results
#'
#' @param ichimoku_data Data frame with Ichimoku components
#' @param backtest_results Results from backtest_ichimoku
#' @return Plotly object
plot_backtest_results <- function(ichimoku_data, backtest_results) {

  plot_data <- data.frame(
    Date = ichimoku_data$Date,
    PortfolioValue = backtest_results$portfolio_value
  )

  fig <- plot_ly(plot_data, x = ~Date, y = ~PortfolioValue,
                 type = "scatter", mode = "lines",
                 name = "Portfolio Value",
                 line = list(color = "#4CAF50", width = 2)) %>%

    # Add buy signals
    add_trace(data = backtest_results$trades[backtest_results$trades$Action == "BUY", ],
              x = ~Date, y = ~Cash,
              type = "scatter", mode = "markers",
              name = "Buy Signal",
              marker = list(color = "green", size = 10, symbol = "triangle-up")) %>%

    # Add sell signals
    add_trace(data = backtest_results$trades[backtest_results$trades$Action == "SELL", ],
              x = ~Date, y = ~Cash,
              type = "scatter", mode = "markers",
              name = "Sell Signal",
              marker = list(color = "red", size = 10, symbol = "triangle-down")) %>%

    layout(
      title = "Ichimoku Strategy Backtest Results",
      xaxis = list(title = "Date"),
      yaxis = list(title = "Portfolio Value ($)"),
      hovermode = "x unified"
    )

  return(fig)
}
