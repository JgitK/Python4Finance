-- Clean the raw price seed.
-- Keep one row per ticker per day. Drop any row without a positive close.

with source as (
    select * from {{ ref('raw_prices') }}
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
        -- A ticker and date should be unique. This guards against a stray duplicate.
        row_number() over (
            partition by ticker, date
            order by volume desc
        ) as row_num
    from source
    where close > 0
)

select
    ticker,
    price_date,
    open,
    high,
    low,
    close,
    volume
from deduped
where row_num = 1
