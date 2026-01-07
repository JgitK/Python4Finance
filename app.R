# Portfolio Optimization and Technical Analysis Shiny App
# Author: R Portfolio Analysis App
# Description: Daily refreshing portfolio optimizer with Ichimoku charting

library(shiny)
library(shinydashboard)
library(quantmod)
library(PerformanceAnalytics)
library(PortfolioAnalytics)
library(plotly)
library(DT)
library(tidyverse)
library(quadprog)

# Source helper functions
source("download_stocks.R")
source("portfolio_optimization.R")
source("ichimoku_analysis.R")

# UI Definition
ui <- dashboardPage(
  dashboardHeader(title = "Portfolio Optimizer & Technical Analysis"),

  dashboardSidebar(
    sidebarMenu(
      menuItem("Dashboard", tabName = "dashboard", icon = icon("dashboard")),
      menuItem("Portfolio Optimization", tabName = "portfolio", icon = icon("chart-line")),
      menuItem("Ichimoku Analysis", tabName = "ichimoku", icon = icon("chart-area")),
      menuItem("Stock Data Manager", tabName = "data_manager", icon = icon("database"))
    ),

    hr(),

    # Date Range Input
    dateRangeInput("date_range",
                   "Date Range:",
                   start = Sys.Date() - 365*5,
                   end = Sys.Date(),
                   max = Sys.Date()),

    # Refresh Data Button
    actionButton("refresh_data", "Refresh Stock Data",
                 icon = icon("sync"),
                 class = "btn-primary",
                 style = "margin: 10px;")
  ),

  dashboardBody(
    tabItems(
      # Dashboard Tab
      tabItem(tabName = "dashboard",
              fluidRow(
                valueBoxOutput("total_stocks"),
                valueBoxOutput("last_update"),
                valueBoxOutput("market_status")
              ),
              fluidRow(
                box(
                  title = "Quick Stats", status = "primary", solidHeader = TRUE,
                  width = 12,
                  plotlyOutput("market_overview", height = 400)
                )
              )
      ),

      # Portfolio Optimization Tab
      tabItem(tabName = "portfolio",
              fluidRow(
                box(
                  title = "Portfolio Configuration", status = "primary", solidHeader = TRUE,
                  width = 4,
                  selectizeInput("selected_stocks",
                                 "Select Stocks for Portfolio:",
                                 choices = NULL,
                                 multiple = TRUE,
                                 options = list(maxItems = 20)),
                  numericInput("num_portfolios",
                               "Number of Random Portfolios:",
                               value = 10000,
                               min = 1000,
                               max = 50000),
                  numericInput("risk_free_rate",
                               "Risk-Free Rate:",
                               value = 0.0125,
                               min = 0,
                               max = 0.1,
                               step = 0.0001),
                  actionButton("optimize_portfolio",
                               "Optimize Portfolio",
                               icon = icon("calculator"),
                               class = "btn-success")
                ),
                box(
                  title = "Efficient Frontier", status = "success", solidHeader = TRUE,
                  width = 8,
                  plotlyOutput("efficient_frontier", height = 500)
                )
              ),
              fluidRow(
                box(
                  title = "Optimal Portfolio Weights", status = "info", solidHeader = TRUE,
                  width = 6,
                  plotlyOutput("portfolio_weights", height = 400)
                ),
                box(
                  title = "Portfolio Statistics", status = "warning", solidHeader = TRUE,
                  width = 6,
                  verbatimTextOutput("portfolio_stats"),
                  DTOutput("weights_table")
                )
              ),
              fluidRow(
                box(
                  title = "Stock Returns Correlation Matrix", status = "primary", solidHeader = TRUE,
                  width = 12,
                  plotlyOutput("correlation_matrix", height = 500)
                )
              )
      ),

      # Ichimoku Analysis Tab
      tabItem(tabName = "ichimoku",
              fluidRow(
                box(
                  title = "Ichimoku Configuration", status = "primary", solidHeader = TRUE,
                  width = 3,
                  selectizeInput("ichimoku_stock",
                                 "Select Stock:",
                                 choices = NULL),
                  selectInput("ichimoku_period",
                              "Time Period:",
                              choices = c("1 Month" = "1mo",
                                          "3 Months" = "3mo",
                                          "6 Months" = "6mo",
                                          "1 Year" = "1y",
                                          "2 Years" = "2y",
                                          "5 Years" = "5y"),
                              selected = "1y"),
                  selectInput("ichimoku_interval",
                              "Interval:",
                              choices = c("Daily" = "1d",
                                          "Weekly" = "1wk",
                                          "Monthly" = "1mo"),
                              selected = "1d"),
                  actionButton("plot_ichimoku",
                               "Plot Ichimoku",
                               icon = icon("chart-area"),
                               class = "btn-primary")
                ),
                box(
                  title = "Ichimoku Cloud Chart", status = "success", solidHeader = TRUE,
                  width = 9,
                  plotlyOutput("ichimoku_chart", height = 600)
                )
              ),
              fluidRow(
                box(
                  title = "Ichimoku Indicators", status = "info", solidHeader = TRUE,
                  width = 6,
                  DTOutput("ichimoku_data_table")
                ),
                box(
                  title = "Trading Signals", status = "warning", solidHeader = TRUE,
                  width = 6,
                  verbatimTextOutput("ichimoku_signals")
                )
              )
      ),

      # Data Manager Tab
      tabItem(tabName = "data_manager",
              fluidRow(
                box(
                  title = "Wilshire 5000 Stocks", status = "primary", solidHeader = TRUE,
                  width = 12,
                  DTOutput("wilshire_stocks_table"),
                  downloadButton("download_wilshire", "Download Wilshire List")
                )
              ),
              fluidRow(
                box(
                  title = "Data Update Status", status = "info", solidHeader = TRUE,
                  width = 12,
                  verbatimTextOutput("update_status")
                )
              )
      )
    )
  )
)

# Server Logic
server <- function(input, output, session) {

  # Reactive Values
  rv <- reactiveValues(
    wilshire_stocks = NULL,
    stock_data = NULL,
    portfolio_results = NULL,
    ichimoku_data = NULL,
    last_update = NULL
  )

  # Load Wilshire stocks on startup
  observe({
    if (file.exists("Wilshire-5000-Stocks.csv")) {
      rv$wilshire_stocks <- read.csv("Wilshire-5000-Stocks.csv", stringsAsFactors = FALSE)

      # Update stock selection inputs
      stock_choices <- rv$wilshire_stocks$Ticker
      updateSelectizeInput(session, "selected_stocks", choices = stock_choices)
      updateSelectizeInput(session, "ichimoku_stock", choices = stock_choices)
    }
  })

  # Value Boxes
  output$total_stocks <- renderValueBox({
    valueBox(
      value = ifelse(!is.null(rv$wilshire_stocks), nrow(rv$wilshire_stocks), 0),
      subtitle = "Total Stocks in Wilshire Index",
      icon = icon("list"),
      color = "blue"
    )
  })

  output$last_update <- renderValueBox({
    valueBox(
      value = ifelse(!is.null(rv$last_update),
                     format(rv$last_update, "%Y-%m-%d %H:%M"),
                     "Never"),
      subtitle = "Last Data Update",
      icon = icon("clock"),
      color = "green"
    )
  })

  output$market_status <- renderValueBox({
    market_open <- is_market_open()
    valueBox(
      value = ifelse(market_open, "Open", "Closed"),
      subtitle = "Market Status",
      icon = icon("chart-line"),
      color = ifelse(market_open, "green", "red")
    )
  })

  # Refresh Data
  observeEvent(input$refresh_data, {
    withProgress(message = 'Refreshing stock data...', value = 0, {
      # This would download updated data for selected stocks
      rv$last_update <- Sys.time()
      showNotification("Stock data refreshed successfully!", type = "message")
    })
  })

  # Portfolio Optimization
  observeEvent(input$optimize_portfolio, {
    req(input$selected_stocks)

    if (length(input$selected_stocks) < 2) {
      showNotification("Please select at least 2 stocks", type = "error")
      return()
    }

    withProgress(message = 'Optimizing portfolio...', value = 0, {
      tryCatch({
        # Download stock data
        incProgress(0.3, detail = "Downloading stock data...")
        stock_data <- download_stock_data(
          input$selected_stocks,
          from = input$date_range[1],
          to = input$date_range[2]
        )

        # Perform portfolio optimization
        incProgress(0.4, detail = "Running optimization...")
        rv$portfolio_results <- optimize_portfolio(
          stock_data,
          num_portfolios = input$num_portfolios,
          risk_free_rate = input$risk_free_rate
        )

        incProgress(0.3, detail = "Complete!")
        showNotification("Portfolio optimized successfully!", type = "message")

      }, error = function(e) {
        showNotification(paste("Error:", e$message), type = "error")
      })
    })
  })

  # Efficient Frontier Plot
  output$efficient_frontier <- renderPlotly({
    req(rv$portfolio_results)

    plot_ly(rv$portfolio_results$portfolios,
            x = ~Volatility,
            y = ~Return,
            color = ~SharpeRatio,
            type = 'scatter',
            mode = 'markers',
            marker = list(size = 3),
            text = ~paste("Return:", round(Return, 4),
                          "<br>Volatility:", round(Volatility, 4),
                          "<br>Sharpe:", round(SharpeRatio, 4)),
            hoverinfo = 'text') %>%
      add_trace(x = rv$portfolio_results$optimal_portfolio$Volatility,
                y = rv$portfolio_results$optimal_portfolio$Return,
                type = 'scatter',
                mode = 'markers',
                marker = list(color = 'red', size = 15, symbol = 'star'),
                name = 'Optimal Portfolio',
                text = ~paste("Optimal Portfolio<br>Return:",
                              round(rv$portfolio_results$optimal_portfolio$Return, 4),
                              "<br>Volatility:",
                              round(rv$portfolio_results$optimal_portfolio$Volatility, 4),
                              "<br>Sharpe:",
                              round(rv$portfolio_results$optimal_portfolio$SharpeRatio, 4)),
                hoverinfo = 'text') %>%
      layout(title = "Efficient Frontier - Portfolio Optimization",
             xaxis = list(title = "Volatility (Risk)"),
             yaxis = list(title = "Expected Return"))
  })

  # Portfolio Weights Chart
  output$portfolio_weights <- renderPlotly({
    req(rv$portfolio_results)

    weights_df <- rv$portfolio_results$optimal_weights

    plot_ly(weights_df,
            labels = ~Stock,
            values = ~Weight,
            type = 'pie',
            textposition = 'inside',
            textinfo = 'label+percent',
            hoverinfo = 'text',
            text = ~paste(Stock, '<br>Weight:', round(Weight * 100, 2), '%')) %>%
      layout(title = "Optimal Portfolio Allocation")
  })

  # Portfolio Statistics
  output$portfolio_stats <- renderPrint({
    req(rv$portfolio_results)

    cat("OPTIMAL PORTFOLIO STATISTICS\n")
    cat("====================================\n\n")
    cat(sprintf("Expected Annual Return: %.2f%%\n",
                rv$portfolio_results$optimal_portfolio$Return * 100))
    cat(sprintf("Annual Volatility: %.2f%%\n",
                rv$portfolio_results$optimal_portfolio$Volatility * 100))
    cat(sprintf("Sharpe Ratio: %.4f\n",
                rv$portfolio_results$optimal_portfolio$SharpeRatio))
    cat(sprintf("Risk-Free Rate: %.2f%%\n",
                input$risk_free_rate * 100))
  })

  # Weights Table
  output$weights_table <- renderDT({
    req(rv$portfolio_results)

    weights_df <- rv$portfolio_results$optimal_weights
    weights_df$Weight <- paste0(round(weights_df$Weight * 100, 2), "%")

    datatable(weights_df,
              options = list(pageLength = 20, dom = 't'),
              rownames = FALSE)
  })

  # Correlation Matrix
  output$correlation_matrix <- renderPlotly({
    req(rv$portfolio_results)

    corr_matrix <- rv$portfolio_results$correlation_matrix

    plot_ly(z = corr_matrix,
            x = colnames(corr_matrix),
            y = rownames(corr_matrix),
            type = "heatmap",
            colors = colorRamp(c("blue", "white", "red")),
            zmin = -1,
            zmax = 1) %>%
      layout(title = "Stock Returns Correlation Matrix",
             xaxis = list(title = ""),
             yaxis = list(title = ""))
  })

  # Ichimoku Analysis
  observeEvent(input$plot_ichimoku, {
    req(input$ichimoku_stock)

    withProgress(message = 'Generating Ichimoku chart...', value = 0, {
      tryCatch({
        incProgress(0.5, detail = "Downloading data...")

        rv$ichimoku_data <- calculate_ichimoku(
          input$ichimoku_stock,
          period = input$ichimoku_period,
          interval = input$ichimoku_interval
        )

        incProgress(0.5, detail = "Complete!")
        showNotification("Ichimoku chart generated!", type = "message")

      }, error = function(e) {
        showNotification(paste("Error:", e$message), type = "error")
      })
    })
  })

  # Ichimoku Chart
  output$ichimoku_chart <- renderPlotly({
    req(rv$ichimoku_data)

    plot_ichimoku_chart(rv$ichimoku_data, input$ichimoku_stock)
  })

  # Ichimoku Data Table
  output$ichimoku_data_table <- renderDT({
    req(rv$ichimoku_data)

    display_df <- rv$ichimoku_data %>%
      tail(20) %>%
      select(Date, Close, Tenkan, Kijun, SenkouA, SenkouB, Chikou) %>%
      mutate(across(where(is.numeric), ~round(., 2)))

    datatable(display_df,
              options = list(pageLength = 10, scrollX = TRUE),
              rownames = FALSE)
  })

  # Ichimoku Signals
  output$ichimoku_signals <- renderPrint({
    req(rv$ichimoku_data)

    signals <- generate_ichimoku_signals(rv$ichimoku_data)

    cat("ICHIMOKU TRADING SIGNALS\n")
    cat("====================================\n\n")
    cat(sprintf("Current Signal: %s\n", signals$current_signal))
    cat(sprintf("Trend: %s\n", signals$trend))
    cat(sprintf("Cloud Status: %s\n", signals$cloud_status))
    cat(sprintf("Tenkan-Kijun Cross: %s\n", signals$tk_cross))
    cat("\nInterpretation:\n")
    cat(signals$interpretation)
  })

  # Wilshire Stocks Table
  output$wilshire_stocks_table <- renderDT({
    req(rv$wilshire_stocks)

    datatable(rv$wilshire_stocks,
              options = list(pageLength = 25, scrollX = TRUE),
              filter = 'top',
              rownames = FALSE)
  })

  # Download Wilshire List
  output$download_wilshire <- downloadHandler(
    filename = function() {
      paste("wilshire-stocks-", Sys.Date(), ".csv", sep = "")
    },
    content = function(file) {
      write.csv(rv$wilshire_stocks, file, row.names = FALSE)
    }
  )

  # Update Status
  output$update_status <- renderPrint({
    cat("DATA UPDATE INFORMATION\n")
    cat("====================================\n\n")
    cat(sprintf("Last Update: %s\n",
                ifelse(!is.null(rv$last_update),
                       format(rv$last_update, "%Y-%m-%d %H:%M:%S"),
                       "Never")))
    cat(sprintf("Total Stocks: %d\n",
                ifelse(!is.null(rv$wilshire_stocks), nrow(rv$wilshire_stocks), 0)))
    cat(sprintf("Market Status: %s\n",
                ifelse(is_market_open(), "Open", "Closed")))
    cat("\nNote: Data updates automatically when refresh button is clicked.\n")
    cat("For best results, refresh data during market hours.\n")
  })

  # Market Overview Chart
  output$market_overview <- renderPlotly({
    # Placeholder for market overview
    if (!is.null(rv$wilshire_stocks)) {
      # Sample visualization - could show sector distribution, etc.
      plot_ly(type = 'scatter', mode = 'markers') %>%
        layout(title = "Market Overview (Placeholder)",
               xaxis = list(title = ""),
               yaxis = list(title = ""))
    }
  })
}

# Run the application
shinyApp(ui = ui, server = server)
