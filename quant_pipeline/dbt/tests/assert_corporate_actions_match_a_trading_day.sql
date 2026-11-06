-- Singular test: each row of the corporate_actions seed must match a day
-- with a price. Without a match, stg_prices does not adjust anything and
-- does not show an error. The test passes when this query returns zero rows.

select ca.ticker, ca.date
from {{ ref('corporate_actions') }} as ca
left join {{ source('raw', 'prices') }} as p
    on p.ticker = ca.ticker and p.date = ca.date
where p.ticker is null
