-- Add the daily return for each stock.
-- The daily return is the percent change of the close from the day before.
-- The first day of each stock has no prior day, so its return is null.
-- A move beyond the limit is a corporate action, such as a spinoff, not a
-- real return. The model nulls that day so it does not distort the metrics.

with prices as (
    select
        ticker,
        price_date,
        close
    from {{ ref('stg_prices') }}
),

raw as (
    select
        ticker,
        price_date,
        close,
        close / lag(close) over (
            partition by ticker
            order by price_date
        ) - 1 as raw_return
    from prices
)

select
    ticker,
    price_date,
    close,
    case
        when abs(raw_return) > {{ var('max_abs_daily_return') }} then null
        else raw_return
    end as daily_return
from raw
