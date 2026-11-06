-- Clean the S&P 500 membership seed. Each row is one stint in the index.

select
    ticker,
    start_date,
    end_date
from {{ ref('sp500_membership') }}
