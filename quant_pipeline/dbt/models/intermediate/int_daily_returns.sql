-- Add the daily return for each stock.
-- The daily return is the percent change of the close from the day before.
-- The first day of each stock has no prior day, so its return is null.

with prices as (
    select
        ticker,
        price_date,
        close
    from {{ ref('stg_prices') }}
)

select
    ticker,
    price_date,
    close,
    close / lag(close) over (
        partition by ticker
        order by price_date
    ) - 1 as daily_return
from prices
