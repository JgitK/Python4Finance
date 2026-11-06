# Results log

`run_pipeline.py` adds one row after each run. Write a short note in the
last cell of the new row. [README.md](README.md) tells what the commit column
shows.

The universe column shows the stocks that the screen could select: the
hand-picked list of 43 stocks, the S&P 500 (`sp500`), the Nasdaq universe
(`nasdaq`), or the two together (`both`).

The three windows hold the portfolio for 180 trading days after each
selection date. Each cell shows the total return of the portfolio and of
SPY in that window. The live Sharpe ratio is an in-sample fit, so it is too
high. Use the backtest to judge the method.

The rows before 2026-11-06 18:00 come from the work notes of that day. The
pipeline did not add them.

| Run date | Commit | Universe | Candidates | Live Sharpe (in-sample) | Window 1: portfolio vs SPY | Window 2 | Window 3 | Note |
|---|---|---|---|---|---|---|---|---|
| 2026-11-06 | c324453 | 43 stocks | 32 | 2.90 | 2026-02-11: +13.9% vs +11.2% | 2025-08-12: +2.8% vs +11.8% | 2025-02-10: +1.3% vs +13.6% | Look-ahead bias: the stock list came from today's screen. Do not use. |
| 2026-11-06 | 0208699 | 43 stocks | 32 | 2.90 | 2026-02-11: +5.8% vs +11.2% | 2025-08-12: +4.3% vs +11.8% | 2025-02-10: +6.6% vs +13.6% | D5: point-in-time screen. |
| 2026-11-06 | 9bc2d8c | 43 stocks | 32 | 2.90 | 2026-02-11: +6.3% vs +11.2% | 2025-08-12: +8.2% vs +11.8% | 2025-02-10: +9.8% vs +13.6% | D6: same 252-day window in the live run and the backtest. |
| 2026-11-06 | 9c2addd | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | D7: S&P 500 on each date. |
| 2026-11-06 | 4cfa116 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | D11: real large moves stay. No change to the backtest. |
| 2026-11-06 | f0509e1 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | D12: first row from the pipeline. Same results as 4cfa116. |
