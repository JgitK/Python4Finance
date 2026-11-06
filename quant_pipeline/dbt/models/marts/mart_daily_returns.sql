-- The daily return of every stock and the benchmark.
-- The Python stats layer reads this mart. It pivots the rows into a
-- return matrix, then runs the Markowitz optimization and the backtest.

select
    ticker,
    price_date,
    daily_return
from {{ ref('int_daily_returns') }}
where daily_return is not null
