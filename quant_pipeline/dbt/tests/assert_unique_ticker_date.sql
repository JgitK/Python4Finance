-- Singular test: a ticker and a date together must be unique.
-- The test passes when this query returns zero rows.

select
    ticker,
    price_date,
    count(*) as row_count
from {{ ref('stg_prices') }}
group by ticker, price_date
having count(*) > 1
