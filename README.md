# 📊 Portfolio Strategy Framework

**Systematic Long-Term Investment Strategy with Comprehensive Validation**

A complete end-to-end portfolio optimization framework that combines technical analysis, correlation-based diversification, Modern Portfolio Theory, and robust validation techniques.

---

## 🎯 What This Framework Does

This framework helps you:

1. **Screen stocks** using technical indicators (RSI, MACD, Ichimoku)
2. **Diversify** by selecting low-correlation stocks
3. **Optimize** portfolio weights to maximize Sharpe ratio
4. **Backtest** on historical data
5. **Validate** your strategy's robustness across multiple dimensions

The key insight: It tests if your **PROCESS** is robust, not just one lucky portfolio.

---

## 📦 Components

### Core Modules

| Module | Description |
|--------|-------------|
| `module_1_data_collection.py` | Downloads historical stock data (yfinance) |
| `module_2_technical_screening.py` | Filters stocks using RSI, MACD, Ichimoku |
| `module_3_correlation_analysis.py` | Selects low-correlation stocks for diversification |
| `module_5_portfolio_optimization.py` | Optimizes weights using Modern Portfolio Theory |
| `module_6_backtest_engine.py` | Backtests portfolios with realistic assumptions |

### Validation & Testing

| File | Description |
|------|-------------|
| `validation_framework.py` | Multi-timeframe, walk-forward, Monte Carlo validation |
| `run_complete_strategy.py` | Integrates all modules, runs full validation |
| `test_strategy_synthetic.py` | Tests workflow with synthetic data (no API needed) |
| `demo_validation.py` | Demonstration of validation framework |

### User Interface

| File | Description |
|------|-------------|
| `app.py` | Modern Streamlit dashboard with interactive charts |
| `STREAMLIT_GUIDE.md` | User guide for the UI |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- pandas
- numpy
- scipy
- scikit-learn
- yfinance
- streamlit
- plotly

### 2. Test the Workflow (No Internet Required)

```bash
python test_strategy_synthetic.py
```

This runs the complete workflow with synthetic data to verify everything works.

### 3. Run with Real Data

```bash
# Single strategy instance
python run_complete_strategy.py

# Full validation (multi-timeframe, walk-forward, Monte Carlo)
python run_complete_strategy.py --validate
```

### 4. Launch the UI

```bash
streamlit run app.py
```

Then navigate to the **🔬 Robustness Testing** page to see validation results.

---

## 🔬 Validation Methodology

This framework validates your strategy across **three critical dimensions**:

### 1. Multi-Timeframe Analysis
Tests if the strategy works across different time periods:
- 6 months
- 1 year
- 2 years
- 5 years
- 10 years

**Purpose:** Detect if strategy is overfitted to recent market conditions.

### 2. Walk-Forward Validation
The gold standard for testing robustness:

```
Window 1: Train 2020-2021 → Test 2022 → Sharpe 1.2
Window 2: Train 2021-2022 → Test 2023 → Sharpe 0.9
Window 3: Train 2022-2023 → Test 2024 → Sharpe 1.1
```

**Purpose:** Prove the PROCESS consistently works, not just one portfolio instance.

### 3. Monte Carlo Parameter Sensitivity
Runs 50-500 simulations with randomized parameters:
- RSI threshold: 60-80
- Correlation cutoff: 0.3-0.5
- Number of stocks: 8-12

**Purpose:** Ensure strategy isn't overfitted to "magic number" parameters.

### Robustness Score (0-100)

The framework combines all three tests into a single score:

- **70-100**: STRONG - Ready for live trading
- **50-70**: MODERATE - Needs refinement
- **30-50**: WEAK - Significant improvement needed
- **0-30**: FAIL - Reconsider approach

---

## 📖 Workflow Overview

### Complete Strategy Pipeline

```
1. Data Collection
   ├─ Load stock universe (Wilshire 5000 / S&P 500)
   └─ Download 2 years of historical data

2. Technical Screening
   ├─ Calculate RSI, MACD, Ichimoku
   ├─ Filter bullish signals
   └─ ~50-200 candidates pass

3. Correlation Analysis
   ├─ Calculate correlation matrix
   ├─ Select low-correlation stocks
   └─ ~10-15 stocks selected

4. Portfolio Optimization
   ├─ Calculate expected returns & covariance
   ├─ Maximize Sharpe ratio
   └─ Optimal weights calculated

5. Backtesting
   ├─ Test on 6mo, 1yr, 2yr, 5yr, 10yr
   ├─ Calculate Sharpe, returns, drawdown
   └─ Compare to benchmark (S&P 500)

6. Validation
   ├─ Multi-timeframe consistency check
   ├─ Walk-forward analysis
   ├─ Monte Carlo parameter sensitivity
   └─ Generate robustness score
```

---

## 🎨 Streamlit UI Features

The interactive dashboard includes:

- **📊 Multi-Timeframe Comparison**: Visual comparison across time periods
- **🔄 Walk-Forward Results**: Performance across rolling windows
- **🎲 Monte Carlo Distribution**: Histogram of parameter sensitivity
- **📈 Interactive Charts**: Plotly charts with zoom, pan, export
- **🎯 Robustness Gauge**: 0-100 score with color-coded assessment
- **📄 Export Reports**: Download full validation reports

---

## 📋 Example Output

```
======================================================================
PORTFOLIO STRATEGY VALIDATION REPORT
======================================================================

🎯 ROBUSTNESS SCORE: 78.5/100
📊 RECOMMENDATION: STRONG - Ready for live trading

----------------------------------------------------------------------
MULTI-TIMEFRAME ANALYSIS
----------------------------------------------------------------------
6mo        | Sharpe:   1.45 | Return:   8.2% | MaxDD:  -12.3%
1yr        | Sharpe:   1.32 | Return:  14.5% | MaxDD:  -18.5%
2yr        | Sharpe:   1.28 | Return:  28.7% | MaxDD:  -22.1%
5yr        | Sharpe:   1.41 | Return:  82.4% | MaxDD:  -28.4%

----------------------------------------------------------------------
WALK-FORWARD ANALYSIS
----------------------------------------------------------------------
WF_Window_1     | Sharpe:   1.25 | Return:   12.3%
WF_Window_2     | Sharpe:   1.08 | Return:    9.7%
WF_Window_3     | Sharpe:   1.35 | Return:   15.2%
WF_Window_4     | Sharpe:   1.42 | Return:   16.8%

Average Walk-Forward Sharpe: 1.28

----------------------------------------------------------------------
MONTE CARLO ANALYSIS
----------------------------------------------------------------------
Simulations run:        100
Profitable:             86.0%
Positive Sharpe:        84.0%
Average Sharpe:         1.15
Sharpe 25th-75th %ile:  0.89 to 1.42
```

---

## 🎓 Key Concepts

### Why Multi-Timeframe Analysis?

Different time ranges capture different market dynamics:

| Timeframe | What It Captures |
|-----------|------------------|
| 6 months | Recent momentum, current regime |
| 1-2 years | Business cycles, seasonal patterns |
| 5-10 years | Full market cycles, long-term trends |

**Robust strategies work across ALL timeframes.**

### Why Walk-Forward Validation?

Traditional backtesting tests your portfolio on the same data used to create it (look-ahead bias).

Walk-forward validation:
- Trains on historical data
- Tests on unseen future data
- Rolls forward through time
- **Tests the PROCESS, not just one instance**

### Why Monte Carlo?

If your strategy only works with very specific parameters (e.g., RSI=35 but fails at RSI=36), it's overfitted.

Monte Carlo tests 100s of parameter combinations to ensure robustness.

---

## 🛠️ Customization

### Adjust Strategy Parameters

Edit `run_complete_strategy.py`:

```python
params = {
    'universe': 'sp500',  # or 'wilshire5000'
    'rsi_threshold': 70,  # RSI overbought threshold
    'correlation_threshold': 0.4,  # Max allowed correlation
    'target_stocks': 10,  # Number of stocks in portfolio
    'risk_free_rate': 0.02  # Risk-free rate for Sharpe
}
```

### Modify Validation Settings

Edit `run_complete_strategy.py` in `run_full_validation()`:

```python
# Multi-timeframe periods
timeframes = {
    '6mo': 180,
    '1yr': 365,
    '2yr': 730,
    '5yr': 1825
}

# Walk-forward configuration
train_period_days = 365  # 1 year training
test_period_days = 90    # 3 months testing
step_size_days = 90      # Roll forward 3 months

# Monte Carlo simulations
num_simulations = 100
parameter_ranges = {
    'rsi_threshold': (60, 80),
    'target_stocks': (8, 12),
    'correlation_threshold': (0.3, 0.5)
}
```

---

## 📊 Performance Benchmarks

Based on S&P 500 universe (2020-2025):

| Metric | Expected Range |
|--------|----------------|
| Sharpe Ratio | 0.8 - 1.5 |
| Annual Return | 10% - 20% |
| Max Drawdown | -15% to -30% |
| Win Rate | 45% - 65% |
| Stocks Selected | 8 - 12 |

---

## ⚠️ Important Notes

### When to Use This Framework

✅ **Good for:**
- Long-term investing (months to years)
- Systematic portfolio construction
- Data-driven decision making
- Testing strategy robustness

❌ **Not designed for:**
- Day trading or scalping
- Manual chart reading
- High-frequency trading
- Options/derivatives strategies

### Limitations

1. **Past performance ≠ future results**: Validation reduces overfitting but doesn't guarantee future success
2. **Market regime changes**: Strategy may need revalidation after major market shifts
3. **Transaction costs**: Backtests don't include commissions/slippage
4. **Data quality**: Results depend on data accuracy

### Recommended Usage

1. **Validate thoroughly ONCE** (5+ years of data)
2. **Use the process** to select current portfolios
3. **Revalidate** quarterly or after major market events
4. **Paper trade** 2-3 months before going live
5. **Start small** (10-25% of intended capital)

---

## 🤝 Next Steps

1. **Test with synthetic data**: `python test_strategy_synthetic.py`
2. **Run on real data**: `python run_complete_strategy.py`
3. **Full validation**: `python run_complete_strategy.py --validate`
4. **Explore UI**: `streamlit run app.py`
5. **Paper trade** if robustness score > 70
6. **Go live** with small capital after 2-3 months

---

## 📚 Additional Resources

- `STREAMLIT_GUIDE.md` - UI user guide
- `MODULE_*_README.md` - Individual module documentation (R versions)
- `PORTFOLIO_OPTIMIZATION_README.md` - MPT theory background

---

## 📝 License

This framework is for educational purposes. Use at your own risk.

---

**Built with:** Python 3.11+ | pandas | numpy | scipy | streamlit | plotly

**Version:** 1.0.0

**Last Updated:** January 2026
