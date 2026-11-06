-- Clean the sector seed. Each stock maps to one GICS sector.

select
    ticker,
    sector
from {{ ref('stock_sectors') }}
