# Python Implementation

This folder contains a complete Python implementation of the portfolio strategy framework, equivalent to the R workflow in the parent directory.

## 📦 What's Here

- **Core Modules** - Python versions of all 6 R modules
- **Validation Framework** - Multi-timeframe, walk-forward, Monte Carlo testing
- **Streamlit UI** - Interactive dashboard for visualization
- **Testing Scripts** - Synthetic data tests and debugging tools

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Complete Workflow

```bash
# Single strategy instance
python run_complete_strategy.py

# Full validation (comprehensive robustness testing)
python run_complete_strategy.py --validate
```

### 3. Launch the UI

```bash
streamlit run app.py
```

## 📁 Files

| File | Description |
|------|-------------|
| `module_1_data_collection.py` | Downloads stock data via yfinance |
| `module_2_technical_screening.py` | RSI, MACD, Ichimoku screening |
| `module_3_correlation_analysis.py` | Correlation-based diversification |
| `module_5_portfolio_optimization.py` | MPT optimization (Sharpe maximization) |
| `module_6_backtest_engine.py` | Backtesting with realistic assumptions |
| `validation_framework.py` | Comprehensive validation system |
| `run_complete_strategy.py` | **Main entry point** |
| `app.py` | Streamlit dashboard |
| `test_strategy_synthetic.py` | Test with synthetic data (no API needed) |
| `debug_yfinance.py` | Troubleshooting script for yfinance |

## 🔬 Validation Features

The Python implementation includes advanced validation:

### Multi-Timeframe Analysis
Tests across 6mo, 1yr, 2yr, 5yr, 10yr periods to detect overfitting to recent conditions.

### Walk-Forward Validation
Trains on historical data, tests on unseen future data, rolls forward. **Validates the PROCESS, not just one portfolio.**

### Monte Carlo Sensitivity
Runs 50-500 simulations with randomized parameters to ensure robustness.

### Robustness Score (0-100)
- **70-100**: STRONG - Ready for live trading
- **50-70**: MODERATE - Needs refinement
- **30-50**: WEAK - Improvement needed
- **0-30**: FAIL - Reconsider approach

## 📊 Usage Examples

### Test with Synthetic Data (No Internet Required)
```bash
python test_strategy_synthetic.py
```

### Run Full Validation
```bash
python run_complete_strategy.py --validate
```

Expected output:
```
ROBUSTNESS SCORE: XX/100
RECOMMENDATION: [STRONG/MODERATE/WEAK/FAIL]

Multi-Timeframe: X% profitable
Walk-Forward: Avg Sharpe X.XX
Monte Carlo: X% parameter combinations work
```

### Troubleshoot yfinance Issues
```bash
python quick_test.py
# or
python debug_yfinance.py
```

## 🎨 Streamlit Dashboard

The interactive UI includes:
- 📊 Multi-timeframe comparison charts
- 🔄 Walk-forward visualization
- 🎲 Monte Carlo distribution plots
- 📈 Interactive Plotly charts
- 🎯 Robustness gauge (0-100)
- 📄 Report export

Navigate to the **🔬 Robustness Testing** page for the full validation workflow.

## ⚙️ Customization

Edit `run_complete_strategy.py` to adjust parameters:

```python
params = {
    'universe': 'sp500',  # or 'wilshire5000'
    'rsi_threshold': 70,
    'correlation_threshold': 0.4,
    'target_stocks': 10,
    'risk_free_rate': 0.02
}
```

## 🔧 Troubleshooting

### yfinance Installation Issues
If `pip install yfinance` fails, try:
```bash
pip install --upgrade pip
pip install yfinance --no-cache-dir
```

### Data Download Fails
Run diagnostics:
```bash
python quick_test.py
```

Common fixes:
- Install yfinance: `pip install yfinance`
- Check internet connection
- Wait a few minutes (rate limiting)
- Try with fewer stocks

### Import Errors
Install all dependencies:
```bash
pip install pandas numpy scipy scikit-learn yfinance streamlit plotly
```

## 📚 Documentation

For detailed information about the methodology, see the parent directory's documentation:
- `../MODULE_*_README.md` - Module-specific guides
- `../PORTFOLIO_OPTIMIZATION_README.md` - MPT theory
- `../README.md` - Main documentation

## 🆚 Python vs R

**Use Python if:**
- You're more comfortable with Python
- You want the Streamlit UI
- You need the advanced validation framework
- You prefer object-oriented code

**Use R if:**
- You're more comfortable with R
- You want simpler, script-based workflow
- You prefer R's financial packages
- You don't need the interactive UI

Both implementations produce equivalent results!

## 📝 Notes

- **This is an alternative implementation** - the R workflow in the parent directory is the primary version
- All Python code is self-contained in this folder
- No dependencies on R code
- Fully functional standalone

## 🚀 Next Steps

1. Test installation: `python test_strategy_synthetic.py`
2. Run with real data: `python run_complete_strategy.py`
3. Full validation: `python run_complete_strategy.py --validate`
4. Explore UI: `streamlit run app.py`
5. Review robustness score and decide next steps

---

**If you prefer R, you can safely ignore this entire folder!**

Go back to the parent directory and use the R workflow instead.
