-- Show the top stocks in each sector by one-year return.
-- This mart mirrors the "top by sector" view from the original project.
-- It ranks every stock, so it does not apply the screen gates.

{% set leaders_n = var('sector_leaders_n') %}

with ranked as (
    select
        m.ticker,
        d.sector,
        m.cum_return_window as one_year_return,
        m.sharpe_ratio,
        row_number() over (
            partition by d.sector
            order by m.cum_return_window desc
        ) as sector_rank
    from {{ ref('int_risk_metrics') }} as m
    join {{ ref('dim_ticker') }} as d using (ticker)
)

select
    ticker,
    sector,
    one_year_return,
    sharpe_ratio,
    sector_rank
from ranked
where sector_rank <= {{ leaders_n }}
