library(dplyr)                                                                                    
                                                                                                    
  # === INPUTS ===                                                                                  
  investment <- 3500                                                                               
  risk_tolerance <- 0.7  # 0 = conservative, 1 = aggressive                                         
                                                                                                    
  # === LOAD DATA ===                                                                               
  weights <- read.csv("analysis/optimal_weights.csv")                                               
                                                                                                    
  # === CALCULATE BLENDED WEIGHTS ===                                                               
  portfolio <- weights %>%                                                                          
    mutate(                                                                                         
      blended_weight = risk_tolerance * max_sharpe_weight +                                         
                       (1 - risk_tolerance) * min_variance_weight,                                  
      dollar_amount = investment * blended_weight                                                   
    )                                                                                               
                                                                                                    
  # === GET CURRENT PRICES (from saved stock data) ===                                              
  portfolio$current_price <- sapply(portfolio$ticker, function(t) {                                 
    stock <- readRDS(paste0("stocks/", t, ".rds"))                                                  
    tail(stock$adjusted, 1)                                                                         
  })                                                                                                
                                                                                                    
  # === CALCULATE SHARES ===                                                                        
  portfolio <- portfolio %>%                                                                        
    mutate(                                                                                         
      shares = floor(dollar_amount / current_price),                                                
      actual_invested = shares * current_price,                                                     
      cash_leftover = dollar_amount - actual_invested                                               
    )                                                                                               
                                                                                                    
  # === SUMMARY ===                                                                                 
  cat("Investment:", scales::dollar(investment), "\n")                                              
  cat("Risk Tolerance:", risk_tolerance, "\n\n")                                                    
                                                                                                    
  portfolio %>%                                                                                     
    select(ticker, sector, blended_weight, dollar_amount,                                           
           current_price, shares, actual_invested) %>%                                              
    mutate(                                                                                         
      blended_weight = scales::percent(blended_weight, 0.1),                                        
      dollar_amount = scales::dollar(dollar_amount),                                                
      current_price = scales::dollar(current_price),                                                
      actual_invested = scales::dollar(actual_invested)                                             
    ) %>%                                                                                           
    print()                                                                                         
                                                                                                    
  cat("\nTotal Invested:", scales::dollar(sum(portfolio$actual_invested)))                          
  cat("\nCash Remaining:", scales::dollar(sum(portfolio$cash_leftover))) 