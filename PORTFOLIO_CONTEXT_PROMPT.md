# Portfolio Context Prompt
## Copy this entire section into a new chat to provide context

---

I'm working with a quantitative portfolio optimization system that I ran through a complete analysis pipeline. Here's the context:

## Investment Parameters
- **Investment Amount**: $4,300
- **Selected Strategy**: Risk Parity (recommended for this budget level)
- **Investment Date**: February 2026
- **Current Market Regime**: BULL_LOW_VOL (favorable conditions, 100% position sizing)

## Portfolio Analysis Background

The system ran 8 modules:
1. **Module 0**: Market Regime Detection - Identified current regime as BULL_LOW_VOL
2. **Module 1**: Downloaded 5 years of stock data
3. **Module 2**: Technical analysis screening (Bollinger Bands, momentum, volatility filters)
4. **Module 3**: Correlation analysis with z-score normalized signals
5. **Module 4**: Ichimoku Cloud validation (5-point scoring system)
6. **Module 5**: Portfolio optimization with Ledoit-Wolf shrinkage, QP optimization, resampled efficient frontier (500 bootstrap iterations)
7. **Module 6**: Walk-forward validation (4 periods, 6-month holding each)
8. **Module 7**: Factor decomposition (Fama-French 4-factor model)

## Key Validation Results

**Walk-Forward Testing (Unbiased, Out-of-Sample)**:
- Average Return: +25.5% per 6-month period
- Average Sharpe Ratio: 2.01 (realistic expectation)
- Win Rate: 100% (all 4 test periods profitable)
- Average Alpha vs SPY: +17.6%
- Beat Rate vs SPY: 75%

**Factor Decomposition (Module 7)**:
- Annualized Alpha: +172.18% (p < 0.0001, statistically significant)
- Market Beta: 1.20x (moderate market exposure)
- Momentum Exposure: 1.24x (strong)
- Size Exposure: 0.62x (modest small-cap tilt)
- R-squared: 45.1% (55% is genuine stock-picking skill)
- **Conclusion**: Strategy VALIDATED - shows genuine alpha beyond factor exposures

## Strategy Comparison at $4,300

| Strategy | Stocks | Invested | Efficiency | Expected Return | Risk | Sharpe |
|----------|--------|----------|------------|-----------------|------|--------|
| **Risk Parity** ⭐ | 11 | $3,631 | 84.5% | 133% | 37.1% | 3.48 |
| Max Sharpe | 7 | $3,433 | 79.8% | 190% | 44.8% | 4.15 |
| Min CVaR | 11 | $3,506 | 81.5% | 79% | 20.6% | 3.62 |
| Min Variance | 10 | $3,354 | 78.0% | 53% | 14.1% | 3.47 |

**Why Risk Parity was recommended**:
- Best efficiency at my budget level (84.5%)
- 11 stocks vs only 7 in Max Sharpe
- Better sector diversification (7 sectors)
- Lower concentration risk (equal risk contribution)
- More practical allocation with less idle cash

## My Selected Portfolio: Risk Parity Strategy

**Total Invested**: $3,631.25 (84.5% efficiency)
**Cash Remaining**: $668.75

### Complete Allocation (11 Stocks):

```
Ticker | Shares | Price    | Cost      | Sector                | Weight | Signal
-------|--------|----------|-----------|----------------------|--------|--------
WDC    | 3      | $269.41  | $808.23   | Technology           | 21.0%  | BULLISH
AU     | 6      | $100.87  | $605.22   | Basic Materials      | 14.5%  | BULLISH
MU     | 1      | $379.40  | $379.40   | Technology           | 13.8%  | BULLISH
AGX    | 1      | $354.14  | $354.14   | Consumer Disc.       | 9.0%   | BULLISH
IONS   | 4      | $84.99   | $339.96   | Health Care          | 8.5%   | BULLISH
CSTM   | 12     | $24.30   | $291.60   | Industrials          | 6.9%   | BULLISH
CIEN   | 1      | $253.50  | $253.50   | Utilities            | 7.7%   | BULLISH
FIVE   | 1      | $192.93  | $192.93   | Consumer Disc.       | 4.5%   | NEUTRAL
SSL    | 24     | $7.29    | $174.96   | Energy               | 4.1%   | BULLISH
GEL    | 7      | $17.33   | $121.31   | Energy               | 3.2%   | BULLISH
COCO   | 2      | $55.00   | $110.00   | Consumer Staples     | 2.8%   | BULLISH
```

**Sector Diversification**:
- Technology: 34.8% (WDC, MU)
- Basic Materials: 14.5% (AU)
- Consumer Discretionary: 13.5% (AGX, FIVE)
- Health Care: 8.5% (IONS)
- Energy: 7.3% (SSL, GEL)
- Utilities: 7.7% (CIEN)
- Industrials: 6.9% (CSTM)
- Consumer Staples: 2.8% (COCO)

## Technical Details

**All stocks passed these filters**:
- Minimum 400 trading days of data
- Ichimoku score ≥ 2/5 (all selected stocks scored 4-5/5)
- Positive 3-month momentum
- Average volume ≥ 100,000 shares/day
- Daily volatility ≤ 5%

**Optimization Method**:
- Ledoit-Wolf covariance shrinkage (reduces estimation error 40-60%)
- Quadratic programming with weight constraints (2-25% per stock)
- Resampled efficient frontier (500 bootstrap iterations)
- Regime-aware position sizing (100% allocation in BULL_LOW_VOL)

## Risk Management Plan

1. **Stop Losses**: Consider -20% per position
2. **Rebalance**: Quarterly or when weights drift >5% from target
3. **Regime Monitoring**: If market shifts to BEAR_HIGH_VOL → reduce to 70% allocation
4. **Holding Period**: Minimum 6 months (based on walk-forward testing)
5. **Transaction Costs**: Not included in backtest, expect ~0.5-1% impact

## Alternative Strategy Considered

**Max Sharpe Portfolio** (if I wanted higher returns):
- 7 stocks: ASM, ALM, TGB, LITE, STX, LQDA, BBVA
- $3,433 invested (79.8% efficiency)
- Expected: 190% return, 44.8% risk, Sharpe 4.15
- Walk-forward validated: Sharpe 2.01
- **Trade-off**: Less diversification, 50% in Basic Materials

## Statistical Improvements Implemented

The pipeline includes these bias-reduction techniques:
- ✅ Z-score signal normalization (eliminated ad-hoc scoring bias)
- ✅ Ledoit-Wolf shrinkage (reduces covariance estimation error)
- ✅ Look-ahead bias elimination (Ichimoku calculated as-of date)
- ✅ Survivorship bias detection and correction (1% annual discount)
- ✅ Regime-aware correlation adjustments (stress multipliers)
- ✅ Factor decomposition validation
- ✅ True walk-forward testing (no in-sample optimization)

## Key Files Location

Project: `/Users/jackson/Desktop/Python4Finance`

- Pipeline script: `run_full_pipeline.R`
- Portfolio weights: `analysis/all_strategy_weights.csv`
- Walk-forward results: `analysis/backtest/walkforward_summary.txt`
- Factor analysis: `analysis/factors/factor_results.csv`
- Methodology doc: `analysis/METHODOLOGY_NARRATIVE.md` (122KB detailed documentation)
- Web app: `http://localhost:8001` (portfolio calculator)

## Questions I Might Ask

Based on this context, I may want to:
1. Monitor portfolio performance and decide when to rebalance
2. Understand how to adjust if market regime changes
3. Evaluate when to take profits or cut losses on specific positions
4. Decide how to deploy the remaining $668.75 cash
5. Determine if/when to switch strategies
6. Analyze individual stock performance vs expectations
7. Compare actual returns to walk-forward validation predictions
8. Understand tax implications and optimal holding periods

---

**Please use this context when I ask questions about my portfolio, strategy decisions, rebalancing, or performance monitoring.**
