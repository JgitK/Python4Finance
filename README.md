# 📊 Portfolio Strategy Framework

**Systematic Long-Term Investment Strategy with R and Python Implementations**

This repository contains complete implementations of a portfolio optimization framework in both **R** (primary) and **Python** (alternative).

---

## 📁 Repository Structure

```
Python4Finance/
├── R Workflow (Primary - Use This!)
│   ├── 01_download_stock_data.R
│   ├── 02_technical_analysis_screening.R
│   ├── 03_correlation_analysis.R
│   ├── 04_ichimoku_validation.R
│   ├── 05_portfolio_optimization.R
│   ├── 06_backtest_validation.R
│   ├── utils_data_loader.R
│   ├── diagnose_backtest.R
│   └── MODULE_*_README.md (documentation)
│
├── python_implementation/ (Alternative Implementation)
│   ├── module_*.py (Python modules)
│   ├── run_complete_strategy.py
│   ├── app.py (Streamlit UI)
│   ├── validation_framework.py
│   └── requirements.txt
│
└── Data Files
    ├── Wilshire-5000-Stocks.csv
    ├── stock_sectors.csv
    └── Various exchange data files
```

---

## 🎯 Quick Start with R

### 1. Install R Packages

```R
install.packages(c(
  "quantmod",      # Stock data download
  "TTR",           # Technical indicators
  "tidyverse",     # Data manipulation
  "PerformanceAnalytics",  # Portfolio metrics
  "PortfolioAnalytics",    # Optimization
  "ROI",           # Optimization engine
  "ROI.plugin.glpk"  # Solver
))
```

### 2. Run the Workflow

Execute the modules in sequence:

```bash
# 1. Download stock data (creates stocks/ directory)
Rscript 01_download_stock_data.R

# 2. Screen stocks using technical analysis
Rscript 02_technical_analysis_screening.R

# 3. Select low-correlation stocks
Rscript 03_correlation_analysis.R

# 4. Validate with Ichimoku signals
Rscript 04_ichimoku_validation.R

# 5. Optimize portfolio weights
Rscript 05_portfolio_optimization.R

# 6. Backtest the results
Rscript 06_backtest_validation.R
```

### 3. Check Results

Results are saved in the `analysis/` directory:
- `technical_candidates.rds` - Stocks passing technical screening
- `low_correlation_candidates.rds` - Diversified stock selection
- `ichimoku_validated.rds` - Final validated candidates
- `final_portfolio.rds` - **Your optimized portfolio!**
- Backtest results and performance metrics

---

## 📖 R Workflow Overview

### Module 1: Download Stock Data
- Loads Wilshire 5000 universe
- Downloads 2 years of historical data using `quantmod`
- Caches data locally for performance
- **Output:** `stocks/*.rds` files

### Module 2: Technical Screening
- Calculates RSI, MACD, Ichimoku indicators
- Filters for bullish signals
- Removes weak momentum stocks
- **Output:** ~50-200 candidates

### Module 3: Correlation Analysis
- Calculates correlation matrix
- Selects low-correlation stocks (diversification)
- Greedy algorithm for optimal selection
- **Output:** ~10-20 stocks

### Module 4: Ichimoku Validation
- Validates bullish Ichimoku cloud signals
- Checks price above cloud, TK cross, cloud color
- **Output:** ~10-15 validated stocks

### Module 5: Portfolio Optimization
- Calculates optimal weights using Modern Portfolio Theory
- Maximizes Sharpe ratio
- Generates efficient frontier
- **Output:** Optimized portfolio with weights

### Module 6: Backtest Validation
- Tests portfolio on historical data
- Calculates Sharpe ratio, returns, drawdown
- Compares to S&P 500 benchmark
- **Output:** Performance metrics and validation

---

## 📚 Documentation

Each R module has detailed documentation:

| File | Description |
|------|-------------|
| `MODULE_1_README.md` | Stock data acquisition system |
| `MODULE_2_README.md` | Technical analysis screening |
| `MODULE_3_README.md` | Correlation analysis & diversification |
| `MODULE_4_README.md` | Ichimoku technical validation |
| `MODULE_5_README.md` | Portfolio optimization |
| `MODULE_6_README.md` | Backtesting & validation |
| `PORTFOLIO_OPTIMIZATION_README.md` | Comprehensive MPT guide |

---

## 🐍 Python Implementation (Optional)

If you prefer Python, there's a complete alternative implementation in `python_implementation/`:

```bash
cd python_implementation/
pip install -r requirements.txt
python run_complete_strategy.py
```

Features:
- Same workflow as R version
- Modern Streamlit UI (`streamlit run app.py`)
- Comprehensive validation framework
- Multi-timeframe, walk-forward, Monte Carlo testing

See `python_implementation/README.md` for details.

---

## 🔧 Utility Scripts

### R Utilities
- `utils_data_loader.R` - Helper functions for loading stock data
- `diagnose_backtest.R` - Diagnostic tool for data availability
- `load_wilshire_data.R` - Wilshire 5000 index loader
- `add_sector_data.R` - Sector classification enrichment

---

## 📊 Expected Results

Based on typical runs with S&P 500 universe:

| Metric | Expected Range |
|--------|----------------|
| Sharpe Ratio | 0.8 - 1.5 |
| Annual Return | 10% - 20% |
| Max Drawdown | -15% to -30% |
| Stocks Selected | 8 - 12 |
| Correlation (avg) | < 0.4 |

---

## ⚙️ Customization

### Adjust Parameters in Each Module

**Module 2 (Technical Screening):**
```R
rsi_period <- 14
rsi_threshold <- 30
macd_fast <- 12
macd_slow <- 26
```

**Module 3 (Correlation):**
```R
correlation_threshold <- 0.4
target_portfolio_size <- 10
```

**Module 5 (Optimization):**
```R
risk_free_rate <- 0.02
target_return <- 0.12
max_position_size <- 0.25
```

---

## 🚨 Troubleshooting

### Issue: Stock downloads fail
**Solution:** Check internet connection, wait for rate limiting

### Issue: Not enough candidates after screening
**Solution:** Lower RSI threshold or extend lookback period

### Issue: Optimization fails
**Solution:** Ensure at least 5-8 stocks, check for NA values in data

### Issue: Missing packages
**Solution:** Run `install.packages()` for required packages

---

## 📅 Workflow Timeline

- **First Run:** ~30-60 minutes (includes data download)
- **Subsequent Runs:** ~5-10 minutes (uses cached data)
- **Monthly Rebalancing:** ~5 minutes (update data + reoptimize)

---

## 🎓 Learning Resources

### R-Specific
- [quantmod documentation](https://www.quantmod.com/)
- [PerformanceAnalytics guide](https://cran.r-project.org/web/packages/PerformanceAnalytics/)
- [Modern Portfolio Theory tutorial](https://bookdown.org/)

### General Finance
- Modern Portfolio Theory (MPT)
- Sharpe Ratio optimization
- Technical analysis basics
- Risk-adjusted returns

---

## ⚠️ Important Notes

### When to Rerun

1. **Monthly:** Reoptimize portfolio weights
2. **Quarterly:** Full workflow from scratch
3. **After major market events:** Revalidate strategy
4. **Annual:** Review and adjust parameters

### Limitations

- Past performance ≠ future results
- Transaction costs not included in backtests
- Assumes liquid markets (may not work for small caps)
- Technical indicators are backward-looking

### Best Practices

1. Paper trade before going live
2. Start with small capital (10-25% of total)
3. Monitor vs S&P 500 benchmark
4. Set stop-loss limits
5. Rebalance quarterly

---

## 🤝 Recommended Approach

**For R Users (Recommended):**
1. Use the R workflow at the root level
2. Ignore `python_implementation/` folder
3. Follow the module documentation

**For Python Users:**
1. Use `python_implementation/` folder
2. Requires yfinance, pandas, numpy, scipy
3. Optional Streamlit UI available

**For Both:**
- Study the MODULE_README files to understand the methodology
- Customize parameters to your risk tolerance
- Validate before live trading

---

## 📝 Version History

- **v1.0** - Complete R workflow (6 modules)
- **v1.1** - Added Python implementation
- **v1.2** - Organized into separate folders

---

## 📄 License

Educational purposes only. Use at your own risk.

---

**Built with R and Python**

**Last Updated:** January 2026
