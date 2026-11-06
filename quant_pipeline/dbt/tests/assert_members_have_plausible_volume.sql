-- Singular test: an S&P 500 member trades many shares each day. A median
-- volume under 1,000 shares while the stock is in the index shows that the
-- price history belongs to a different security. Add such a ticker to the
-- price_data_exclusions seed. The test passes with zero rows.

{{ config(severity='warn') }}

select p.ticker, median(p.volume) as median_volume
from {{ ref('stg_prices') }} as p
join {{ ref('stg_membership') }} as mb
    on mb.ticker = p.ticker
    and {{ is_member_on('mb', 'p.price_date') }}
group by p.ticker
having median(p.volume) < 1000
