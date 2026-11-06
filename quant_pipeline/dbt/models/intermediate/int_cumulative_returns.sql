-- Add the cumulative return for each stock.
-- The cumulative return compounds the daily returns from the first day.
-- It starts at 1.0. A value of 1.5 means the stock grew by 50 percent.

with returns as (
    select
        ticker,
        price_date,
        daily_return
    from {{ ref('int_daily_returns') }}
)

select
    ticker,
    price_date,
    -- Sum the log returns, then undo the log with exp. This compounds the growth.
    -- The first day has a null return, so treat it as zero growth.
    exp(sum(ln(1 + coalesce(daily_return, 0))) over (
        partition by ticker
        order by price_date
    )) as cum_return
from returns
