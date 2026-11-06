-- Clean the raw prices from the Parquet source.
-- This model is a table, not a view. A view would keep the relative path of
-- the Parquet file, and a reader in another folder could not find the file.

{{ config(materialized='table') }}
-- Keep one row per ticker per day. Drop any row without a positive close.

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
