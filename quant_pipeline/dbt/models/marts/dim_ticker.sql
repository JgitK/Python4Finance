-- The ticker dimension. One row per stock in the universe.
-- It holds the sector and the span of available history.
-- The benchmark SPY has no sector, so the inner join removes it.

with history as (
    select
        ticker,
        min(price_date) as first_date,
        max(price_date) as last_date,
        count(*) as total_trading_days
    from {{ ref('stg_prices') }}
    group by ticker
)

select
    s.ticker,
    s.sector,
    h.first_date,
    h.last_date,
    h.total_trading_days
from {{ ref('stg_sectors') }} as s
join history as h using (ticker)
