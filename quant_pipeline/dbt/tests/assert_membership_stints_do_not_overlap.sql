-- Singular test: the index stints of one ticker must not overlap.
-- An overlap would put a stock two times into a screen.
-- The test passes when this query returns zero rows.

select a.ticker, a.start_date, b.start_date as other_start
from {{ ref('stg_membership') }} as a
join {{ ref('stg_membership') }} as b
    on a.ticker = b.ticker
    and a.start_date < b.start_date
    and (a.end_date is null or a.end_date > b.start_date)
