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

The walk-forward column holds the measure of a run with `--many-windows`.
It gives the count of the windows, the share that beats SPY on the total
return and on the Sharpe ratio, and the excess return. Three windows
cannot show that a result is not luck. The many windows overlap, so they
are not independent either: the valid dates cover approximately two
independent holding periods. Read the share as a measure, not as proof.
When the cell gives "84 of 114 windows", 30 windows hold no result,
because the portfolio held no stock. See D16.

The rows before 2026-11-06 18:00 come from the work notes of that day. The
pipeline did not add them.

| Run date | Commit | Universe | Candidates | Live Sharpe (in-sample) | Window 1: portfolio vs SPY | Window 2 | Window 3 | Walk-forward, many windows | Note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-06 | c324453 | 43 stocks | 32 | 2.90 | 2026-02-11: +13.9% vs +11.2% | 2025-08-12: +2.8% vs +11.8% | 2025-02-10: +1.3% vs +13.6% |  | Look-ahead bias: the stock list came from today's screen. Do not use. |
| 2026-11-06 | 0208699 | 43 stocks | 32 | 2.90 | 2026-02-11: +5.8% vs +11.2% | 2025-08-12: +4.3% vs +11.8% | 2025-02-10: +6.6% vs +13.6% |  | D5: point-in-time screen. |
| 2026-11-06 | 9bc2d8c | 43 stocks | 32 | 2.90 | 2026-02-11: +6.3% vs +11.2% | 2025-08-12: +8.2% vs +11.8% | 2025-02-10: +9.8% vs +13.6% |  | D6: same 252-day window in the live run and the backtest. |
| 2026-11-06 | 9c2addd | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D7: S&P 500 on each date. |
| 2026-11-06 | 4cfa116 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D11: real large moves stay. No change to the backtest. |
| 2026-11-06 | f0509e1 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D12: first row from the pipeline. Same results as 4cfa116. |
| 2026-11-06 | 5a2ddc3 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | Baseline of the universe comparison. The universe switch did not change the sp500 results. |
| 2026-11-06 | 23102b3 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D13: the baseline of the universe comparison. The price file grew to 2,123 symbols, and the sp500 results did not change. |
| 2026-11-06 | 23102b3 | nasdaq | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  | D13. PROVISIONAL: 601 large moves are not reviewed, and 34 of the affected tickers pass the screen. Do not trust this row. |
| 2026-11-06 | 23102b3 | both | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  | D13. PROVISIONAL: same data problem as the nasdaq row. Do not trust this row. |
| 2026-11-06 | 0c14836 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 0c14836 | nasdaq | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 0c14836 | both | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 81e83c3 | sp500 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  |D14 and D15. The data quality checks all pass now. The results are the same as the 0c14836 row, so the volume rule changed no sp500 number. HON is the only S&P 500 member with a corporate action, and its row was already in the seed. |
| 2026-11-06 | 81e83c3 | nasdaq | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  |D14 and D15. NOT PROVISIONAL. Every large move holds a review, and 10 tickers with a broken price history are gone. The results are the same as the 0c14836 row: none of those tickers passed the screen. |
| 2026-11-06 | 81e83c3 | both | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  |D14 and D15. NOT PROVISIONAL. Same results as the 0c14836 row, for the same reason as the nasdaq row. |
