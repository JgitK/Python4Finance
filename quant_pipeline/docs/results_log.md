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

The Caps column holds the three caps of the exposure, in the order
`top_n_per_sector/target_size/max_per_sector`. The first cap is the count
of candidates that each sector keeps in the screen. The second is the count
of stocks in the portfolio. The third is the count of portfolio stocks that
one sector can hold. The flags `--top-n-per-sector`, `--target-size` and
`--max-per-sector` set the three. Every row before D20 used `10/12/3`,
which is the default of `dbt_project.yml` and of `PortfolioParams`. See D20.

The rows before 2026-11-06 18:00 come from the work notes of that day. The
pipeline did not add them.

| Run date | Commit | Universe | Caps | Candidates | Live Sharpe (in-sample) | Window 1: portfolio vs SPY | Window 2 | Window 3 | Walk-forward, many windows | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-06 | c324453 | 43 stocks | 10/12/3 | 32 | 2.90 | 2026-02-11: +13.9% vs +11.2% | 2025-08-12: +2.8% vs +11.8% | 2025-02-10: +1.3% vs +13.6% |  | Look-ahead bias: the stock list came from today's screen. Do not use. |
| 2026-11-06 | 0208699 | 43 stocks | 10/12/3 | 32 | 2.90 | 2026-02-11: +5.8% vs +11.2% | 2025-08-12: +4.3% vs +11.8% | 2025-02-10: +6.6% vs +13.6% |  | D5: point-in-time screen. |
| 2026-11-06 | 9bc2d8c | 43 stocks | 10/12/3 | 32 | 2.90 | 2026-02-11: +6.3% vs +11.2% | 2025-08-12: +8.2% vs +11.8% | 2025-02-10: +9.8% vs +13.6% |  | D6: same 252-day window in the live run and the backtest. |
| 2026-11-06 | 9c2addd | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D7: S&P 500 on each date. |
| 2026-11-06 | 4cfa116 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D11: real large moves stay. No change to the backtest. |
| 2026-11-06 | f0509e1 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D12: first row from the pipeline. Same results as 4cfa116. |
| 2026-11-06 | 5a2ddc3 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | Baseline of the universe comparison. The universe switch did not change the sp500 results. |
| 2026-11-06 | 23102b3 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | D13: the baseline of the universe comparison. The price file grew to 2,123 symbols, and the sp500 results did not change. |
| 2026-11-06 | 23102b3 | nasdaq | 10/12/3 | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  | D13. PROVISIONAL: 601 large moves are not reviewed, and 34 of the affected tickers pass the screen. Do not trust this row. |
| 2026-11-06 | 23102b3 | both | 10/12/3 | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  | D13. PROVISIONAL: same data problem as the nasdaq row. Do not trust this row. |
| 2026-11-06 | 0c14836 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 0c14836 | nasdaq | 10/12/3 | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 0c14836 | both | 10/12/3 | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  | Same results as the 23102b3 row, after the merge b1a5be4 replaced the price file with the file of a parallel download. Two independent downloads give the same results. |
| 2026-11-06 | 81e83c3 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% |  |D14 and D15. The data quality checks all pass now. The results are the same as the 0c14836 row, so the volume rule changed no sp500 number. HON is the only S&P 500 member with a corporate action, and its row was already in the seed. |
| 2026-11-06 | 81e83c3 | nasdaq | 10/12/3 | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% |  |D14 and D15. NOT PROVISIONAL. Every large move holds a review, and 10 tickers with a broken price history are gone. The results are the same as the 0c14836 row: none of those tickers passed the screen. |
| 2026-11-06 | 81e83c3 | both | 10/12/3 | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% |  |D14 and D15. NOT PROVISIONAL. Same results as the 0c14836 row, for the same reason as the nasdaq row. |
| 2026-11-06 | 06862e6 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | 85 windows: 48.2% on return, 45.9% on Sharpe, mean excess +1.1%, median -0.3% |D16: the first row with the many-window measure. The median excess return is negative on every step that I tried (3, 5, 10 and 21 days), and the mean changes its sign. Read the median. The 3-window cells are the same as the 1bac23e row. |
| 2026-11-06 | 06862e6 | nasdaq | 10/12/3 | 103 | 5.72 | 2026-02-11: +29.2% vs +11.2% | 2025-08-12: -2.0% vs +11.8% | 2025-02-10: +0.8% vs +13.6% | 85 windows: 56.5% on return, 49.4% on Sharpe, mean excess +4.7%, median +4.6% |D16. A run on the price data before D14 and D15, with the same 85 dates, gives the same measure to every decimal. The two data quality decisions changed no number, on 3 windows and on 85 windows. |
| 2026-11-06 | 06862e6 | both | 10/12/3 | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% | 85 windows: 45.9% on return, 37.6% on Sharpe, mean excess +4.6%, median -0.7% |D16. The mean excess return is +4.6% and the median is -0.7%. A few large wins make the mean. This universe beats SPY in fewer windows than sp500, on both measures. |
| 2026-11-06 | 9ad5e17 | sp500 | 10/12/3 | 110 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | 85 windows: 48.2% on return, 45.9% on Sharpe, mean excess +1.1%, median -0.3% | D20: the baseline of the cap measurement. Same numbers as the 06862e6 row. |
| 2026-11-06 | 9ad5e17 | sp500 | 25/12/3 | 243 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | 85 windows: 48.2% on return, 45.9% on Sharpe, mean excess +1.1%, median -0.3% | D20: a 2.2 times larger candidate pool. Every number is the same as the 10/12/3 row. The screen cap is slack: the selection takes at most 3 names of a sector, so it never looks below the third name. |
| 2026-11-06 | 9ad5e17 | sp500 | 100000/12/3 | 359 | 4.66 | 2026-02-11: +12.7% vs +11.2% | 2025-08-12: +5.3% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | 85 windows: 48.2% on return, 45.9% on Sharpe, mean excess +1.1%, median -0.3% | D20: the screen cap is removed, so the 359 stocks that pass the four gates are all candidates. Every number is still the same as the 10/12/3 row. |
| 2026-11-06 | 9ad5e17 | sp500 | 10/24/6 | 110 | 5.01 | 2026-02-11: +0.5% vs +11.2% | 2025-08-12: +2.5% vs +11.8% | 2025-02-10: +3.7% vs +13.6% | 85 windows: 62.4% on return, 56.5% on Sharpe, mean excess +2.1%, median +2.5% | D20: 24 stocks instead of 12. The median window goes from -0.27% to +2.46%, and the mean Sharpe ratio from 0.68 to 0.82 against 0.80 for SPY. The portfolio cap holds the exposure, not the screen cap. |
| 2026-11-06 | 9ad5e17 | sp500 | 25/24/6 | 243 | 5.01 | 2026-02-11: +0.5% vs +11.2% | 2025-08-12: +2.5% vs +11.8% | 2025-02-10: +3.7% vs +13.6% | 85 windows: 62.4% on return, 56.5% on Sharpe, mean excess +2.1%, median +2.5% | D20: same numbers as the 10/24/6 row. The screen cap is slack again. |
| 2026-11-06 | 9ad5e17 | sp500 | 100000/24/6 | 359 | 5.01 | 2026-02-11: +0.5% vs +11.2% | 2025-08-12: +2.5% vs +11.8% | 2025-02-10: +3.7% vs +13.6% | 85 windows: 62.4% on return, 56.5% on Sharpe, mean excess +2.1%, median +2.5% | D20: same numbers as the 10/24/6 row, with 359 candidates instead of 110. |
| 2026-11-06 | 9ad5e17 | sp500 | 100000/40/10 | 359 | 4.64 | 2026-02-11: +4.9% vs +11.2% | 2025-08-12: +8.8% vs +11.8% | 2025-02-10: +14.9% vs +13.6% | 85 windows: 64.7% on return, 61.2% on Sharpe, mean excess +2.2%, median +3.7% | D20: the best setting of the project. It beats SPY on the median window (+3.68%), on the share of the windows (64.7%), and on the mean Sharpe ratio (0.82 against 0.80) at the same time. But $10,000 of whole shares drops 11 of the 40 stocks, which is 9.5% of the target weight. A plan that holds every weight needs $916,335. |
| 2026-11-06 | 9ad5e17 | sp500 | 10/40/10 | 110 | 4.88 | 2026-02-11: +1.9% vs +11.2% | 2025-08-12: +8.8% vs +11.8% | 2025-02-10: +14.9% vs +13.6% | 85 windows: 64.7% on return, 61.2% on Sharpe, mean excess +2.3%, median +3.7% | D20: 40 stocks from the capped pool. The 85-window measure is the same as the 100000/40/10 row, and the live portfolio is not: a sector of 10 names can run out, so the screen cap binds a little here. |
| 2026-11-06 | 9ad5e17 | sp500 | 100000/60/15 | 359 | 4.75 | 2026-02-11: +4.5% vs +11.2% | 2025-08-12: +7.7% vs +11.8% | 2025-02-10: +8.1% vs +13.6% | 85 windows: 61.2% on return, 56.5% on Sharpe, mean excess +1.4%, median +3.4% | D20: 60 stocks is past the best setting. The measure falls back to 61.2% and a median of +3.43%. $10,000 drops 19 of the 60 stocks. |
| 2026-11-06 | 9ad5e17 | both | 10/12/3 | 110 | 6.01 | 2026-02-11: +24.5% vs +11.2% | 2025-08-12: -5.1% vs +11.8% | 2025-02-10: +4.7% vs +13.6% | 85 windows: 45.9% on return, 37.6% on Sharpe, mean excess +4.6%, median -0.7% | D20: the baseline of the cap measurement for both. Same numbers as the 06862e6 row. |
| 2026-11-06 | 9ad5e17 | both | 10/24/6 | 110 | 6.42 | 2026-02-11: +23.5% vs +11.2% | 2025-08-12: +12.7% vs +11.8% | 2025-02-10: -3.0% vs +13.6% | 85 windows: 57.6% on return, 49.4% on Sharpe, mean excess +4.1%, median +2.6% | D20: the portfolio size gives the same gain in the larger universe. The median goes from -0.72% to +2.61%. |
| 2026-11-06 | 9ad5e17 | both | 10/40/10 | 110 | 6.64 | 2026-02-11: +15.0% vs +11.2% | 2025-08-12: +10.6% vs +11.8% | 2025-02-10: -0.5% vs +13.6% | 85 windows: 61.2% on return, 54.1% on Sharpe, mean excess +4.4%, median +3.5% | D20: 40 stocks from the capped pool of both. |
| 2026-11-06 | 9ad5e17 | both | 100000/40/10 | 755 | 6.64 | 2026-02-11: +15.7% vs +11.2% | 2025-08-12: +10.6% vs +11.8% | 2025-02-10: -0.5% vs +13.6% | 85 windows: 61.2% on return, 55.3% on Sharpe, mean excess +4.5%, median +3.5% | D20: 755 candidates instead of 110, and the same 40 stocks and the same median of +3.52%. sp500 at the same caps measures better (+3.68%), and it carries 2 to 3 times less survivorship bias (D19). The larger universe is not the way to more exposure. |
| 2026-11-06 | 9ad5e17 | both | 100000/60/15 | 755 | 6.75 | 2026-02-11: +16.1% vs +11.2% | 2025-08-12: +15.0% vs +11.8% | 2025-02-10: +5.0% vs +13.6% | 85 windows: 63.5% on return, 56.5% on Sharpe, mean excess +4.3%, median +3.7% | D20: the best both setting, and it is still below sp500 at 40 stocks on the share of the windows (63.5% against 64.7%) and on the Sharpe share (56.5% against 61.2%). |
| 2026-11-06 | 47a61be | sp500 | 10/10/3 | 110 | 4.47 | 2026-02-11: +11.9% vs +11.2% | 2025-08-12: +9.0% vs +11.8% | 2025-02-10: +1.4% vs +13.6% | 85 windows: 47.1% on return, 42.4% on Sharpe, mean excess +1.7%, median -1.4% |  |
| 2026-11-06 | 47a61be | sp500 | 10/10/2 | 110 | 4.58 | 2026-02-11: +9.9% vs +11.2% | 2025-08-12: +7.9% vs +11.8% | 2025-02-10: +1.4% vs +13.6% | 85 windows: 50.6% on return, 45.9% on Sharpe, mean excess +0.6%, median +0.1% |  |
| 2026-11-06 | 47a61be | sp500 | 10/12/2 | 110 | 4.66 | 2026-02-11: +9.9% vs +11.2% | 2025-08-12: +10.6% vs +11.8% | 2025-02-10: -2.1% vs +13.6% | 85 windows: 47.1% on return, 38.8% on Sharpe, mean excess +0.1%, median -1.1% |  |
| 2026-11-06 | 47a61be | sp500 | 10/10/4 | 110 | 4.41 | 2026-02-11: +10.4% vs +11.2% | 2025-08-12: +10.9% vs +11.8% | 2025-02-10: +1.4% vs +13.6% | 85 windows: 49.4% on return, 44.7% on Sharpe, mean excess +2.3%, median -0.9% |  |
| 2026-11-06 | 47a61be | sp500 | 10/10/5 | 110 | 4.26 | 2026-02-11: +10.4% vs +11.2% | 2025-08-12: +10.9% vs +11.8% | 2025-02-10: +1.4% vs +13.6% | 85 windows: 49.4% on return, 44.7% on Sharpe, mean excess +2.8%, median -0.9% |  |
