-- List each S&P 500 member on each trading day. Flag the members that have
-- no price or no sector on that day. The screen cannot select such a stock.
-- This mart shows how many members the pipeline drops because it has no data.
-- The benchmark trades on each trading day, so it gives the calendar.

with calendar as (
    select distinct price_date as as_of_date
    from {{ ref('stg_prices') }}
    where ticker = 'SPY'
),

members as (
    select c.as_of_date, mb.ticker
    from calendar as c
    join {{ ref('stg_membership') }} as mb
        on {{ is_member_on('mb', 'c.as_of_date') }}
)

select
    m.as_of_date,
    m.ticker,
    p.ticker is not null as has_prices,
    s.ticker is not null as has_sector
from members as m
left join {{ ref('stg_prices') }} as p
    on p.ticker = m.ticker and p.price_date = m.as_of_date
left join {{ ref('stg_sectors') }} as s
    on s.ticker = m.ticker
