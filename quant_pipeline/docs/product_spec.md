# Product spec: an honest Markowitz tool

Status: first draft, 2026-11-09. Decision D34 records the change of
direction. This spec says what the tool must do. It does not say how to
build each part.

## The aim

The tool builds a Markowitz portfolio and it shows how much the user can
trust that portfolio. It does not promise to beat SPY.

The old aim was "find a method that beats SPY on a risk-adjusted
measure". D22 to D33 measured that aim many times. The rank order, the
exact optimizer and the hold length do not give a risk-adjusted gain.
Only a wide pool across the sectors helps, and an equal weight of the
same pool does as well as the optimizer (D32, D33). The validation code
found this. In the new aim, that code is the main feature.

An analogy: a weather app that says "sun tomorrow" is less useful than an
app that says "70% chance of sun, and our forecast is often wrong at this
range".

## Why Markowitz fails out of sample here

Markowitz gives the best mix of a set of stocks **when the expected
returns and the covariance are known**. The tool must estimate both from
past prices. The optimizer uses the estimates as facts.

1. **The expected return is the weak input.** The standard error of an
   annual mean return is approximately the annual volatility divided by
   the square root of the years of data. For a stock with a volatility of
   30%:

   | Window | Standard error of the annual return |
   |---|---|
   | 1 month | ±104% |
   | 3 months | ±60% |
   | 6 months | ±42% |
   | 1 year | ±30% |
   | 2 years | ±21% |
   | 5 years | ±13% |

   The covariance becomes accurate much faster than the mean.
2. **Error maximisation (Michaud, 1989).** The optimizer puts the most
   weight on the stocks with the largest errors in the upward direction.
   The project shows this: the in-sample Sharpe ratio is 5.32 and the
   realized one is 0.88. The exact solver does worse than the random
   search (D29). Equal weights beat the optimizer weights on the same
   names (D33), inside the noise of the overlapping windows. DeMiguel, Garlappi and Uppal (2009) found that no
   mean-variance method of 14 beat 1/N out of sample.
3. **The same data is used two times.** The screen selects the stocks
   with the highest past return. The optimizer then uses that past return
   as the forecast. The selected stocks are partly the lucky ones, so
   their estimates are too high before the optimizer starts.
4. **SPY is a hard benchmark.** In the CAPM, the market portfolio is on
   the efficient frontier. Markowitz finds the best mix of the stocks that
   it receives. It does not promise to beat an index of 500 stocks.

Markowitz is a risk tool. The methods that work in practice use the
covariance and they trust the mean less: minimum variance, shrinkage
(Ledoit-Wolf), Black-Litterman and risk parity.

## Screen 1: pick the stocks

The user selects the stocks. The tool gives information and does not
select.

- **A ranking window that the user selects:** 1 month, 3 months, 6
  months, 1 year, 2 years or 5 years. For each window, the tool shows the
  stocks with the highest cumulative return in each sector.
- **The error range of each return.** Show the cumulative return with
  its standard error for the selected window, from the table above and
  the volatility of each stock. Example: "+18%, 95% range -12% to +48%".
- **The known effect of each window.** Show a label:

  | Window | Effect in the research | Label |
  |---|---|---|
  | 1 month | Short-term reversal (Jegadeesh, 1990) | Past winners tend to fall back |
  | 3 to 12 months | Momentum (Jegadeesh and Titman, 1993) | Past winners tend to continue |
  | 3 to 5 years | Long-term reversal (De Bondt and Thaler, 1985) | Past winners tend to fall back |

  The standard momentum signal is 12 months without the last month. D30
  found the momentum premium in the project portfolios.
- **Rank stability.** Show if a stock is in the top 3 of its sector on
  3, 6 and 12 months, or on one window only. A stock that leads on many
  windows gives a stronger signal.
- **The walk-forward result of each window.** Run the existing backtest
  for each ranking window and show them together. The user then sees
  which windows held up out of sample. This also shows the risk of data
  snooping: if the user tries six windows and keeps the best one, the
  best result is partly luck.
- **The Ichimoku chart** of each stock, as information for the timing
  (D27).
- **A sector balance meter.** The spread across the sectors is the part
  that helped (D32, D33).

## Screen 2: estimate the inputs

- **Two windows with two jobs.** The ranking window of screen 1 is the
  choice of the user. The covariance uses its own window of 1 to 2 years.
- **The estimator of the covariance:** sample, or Ledoit-Wolf shrinkage.
- **The estimator of the expected return:** the sample mean, a mean
  shrunk toward the mean of the group, or none (minimum variance).
- **Show each expected return as a range,** not as one number.

## Screen 3: the efficient frontier

- Draw the frontier from the estimates.
- **A cloud of frontiers.** Draw the frontier again on 200 bootstrap
  samples of the data. The cloud shows how unstable the optimal point
  is.
- **Portfolios with one click:** minimum variance, maximum Sharpe (with
  shrinkage), risk parity and equal weight. Plot each one on the
  frontier.
- **Weight stability.** Move the data window by one month and show how
  much each weight changes.

## Screen 4: the assumption checks

Each check is a warning light: green, amber or red.

| Check | The Markowitz assumption | Red when |
|---|---|---|
| Error of the return estimate | The means are known | The 95% range is wider than the estimate |
| Days for each stock (T/N) and the condition number | The covariance is accurate | Too few days for each stock, or the matrix is almost singular |
| Fat tails and skew | The variance holds all the risk | High kurtosis. Show the CVaR next to the volatility |
| Regime change | The future is like the past | The correlations of the two halves of the window are very different |
| Concentration | Diversification | One weight is more than 25%, or the effective count of stocks is low |
| In-sample and out-of-sample gap | The fit is not noise | The in-sample Sharpe ratio is much higher than the walk-forward one |
| Same data for the screen and the forecast | The estimates have no selection bias | The ranking window and the return window overlap |

**The honest scorecard.** Below the lights, always show the walk-forward
result of the selected portfolio next to equal weight, SPY and the
random-order null. Show it also when the result is bad.

## What exists now

- The dbt and DuckDB warehouse, the screen and the point-in-time
  universe.
- `quant/exact.py`: minimum variance, maximum Sharpe, maximum Sortino,
  minimum CVaR and equal weight, with weight bounds and the pool mode.
- The walk-forward backtest, the random-order null
  (`quant/null_benchmark.py`), the factor regressions
  (`quant/factors.py`) and the holding checkpoints (`quant/holding.py`).
- The CAPM beta and alpha (`quant/capm.py`).

## What is new

- A ranking window that the user selects, from 1 month to 5 years. The
  screen now uses one fixed lookback.
- The error range of each return, and the rank stability.
- Ledoit-Wolf shrinkage (scikit-learn has it) and a shrunk mean.
- Risk parity.
- The bootstrap frontiers and the weight stability.
- The functions of the assumption checks.
- The user interface. Streamlit is the fastest path from the Python
  code. The old R Shiny app in `webapp/` is a second option.

## What stops

More experiments that try to beat SPY. They answer a question that the
tool does not ask now.

## The first slice

Screen 4 for one portfolio: the warning lights and the honest scorecard.
It uses code that exists, and it makes the new aim visible.

## Open points for the user

- Streamlit or R Shiny.
- The thresholds of each warning light.
- If the tool keeps the whole-share plan (D21, D26) or uses fractional
  shares only.
