-- Clean the raw prices from the Parquet source.
-- This model is a table, not a view. A view would keep the relative path of
-- the Parquet file, and a reader in another folder could not find the file.

{{ config(materialized='table') }}

-- Keep one row per ticker per day. Drop any row without a positive close.
-- Then back-adjust the prices for each corporate action in the
-- corporate_actions seed. The price source adjusts most corporate actions,
-- but not all of them. A gap that the source did not adjust is not a real
-- return.

with source as (
    select * from {{ source('raw', 'prices') }}
),

deduped as (
    select
        ticker,
        date as price_date,
        open,
        high,
        low,
        close,
        volume,
        -- A ticker and a date must be unique. This step removes a duplicate row.
        row_number() over (
            partition by ticker, date
            order by volume desc
        ) as row_num
    from source
    where close > 0
        -- Drop a ticker whose price history belongs to a different security.
        and ticker not in (select ticker from {{ ref('price_data_exclusions') }})
),

clean as (
    select ticker, price_date, open, high, low, close, volume
    from deduped
    where row_num = 1
),

-- The gap factor of each corporate action: the open on the event day
-- divided by the close of the day before.
factors as (
    select
        c.ticker,
        c.price_date as event_date,
        c.open / c.prev_close as factor
    from (
        select *, lag(close) over (partition by ticker order by price_date) as prev_close
        from clean
    ) as c
    join {{ ref('corporate_actions') }} as ca
        on ca.ticker = c.ticker
        and ca.date = c.price_date
        and ca.kind = 'corporate_action'
),

-- Each price before an event gets the product of the factors of all later
-- events. A price on or after the last event keeps a factor of 1.
adjusted as (
    select
        p.*,
        coalesce(
            (select exp(sum(ln(f.factor)))
             from factors as f
             where f.ticker = p.ticker and f.event_date > p.price_date),
            1.0
        ) as adjustment
    from clean as p
)

select
    ticker,
    price_date,
    open * adjustment as open,
    high * adjustment as high,
    low * adjustment as low,
    close * adjustment as close,
    volume
from adjusted
