-- Singular test: a stock appears at most one time on each date.
-- The test passes when this query returns zero rows.

select as_of_date, ticker, count(*) as row_count
from {{ ref('mart_screen_history') }}
group by as_of_date, ticker
having count(*) > 1
