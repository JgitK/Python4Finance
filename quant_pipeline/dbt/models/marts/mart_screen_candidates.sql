-- Screen the universe. Keep the stocks that are liquid and calm.
-- Only the stocks in the S&P 500 on the last date can pass.
-- A stock must pass three gates:
--   1. It has enough history.
--   2. It trades enough volume.
--   3. Its daily moves are not too wild.
-- The Ichimoku score is information for the chart. It is not a gate (D27).
-- The model then ranks the stocks inside each sector by the rank_metric
-- variable and keeps the top names. These are the candidates for the
-- portfolio. See the rank_column macro and decision D22.

{% set top_n = var('top_n_per_sector') %}

with metrics as (
    select * from {{ ref('int_risk_metrics') }}
),

score as (
    select ticker, ichimoku_score
    from {{ ref('int_ichimoku_score') }}
),

-- The latest close is the price the allocator uses to buy shares.
latest_price as (
    select ticker, close as current_price
    from {{ ref('stg_prices') }}
    qualify row_number() over (
        partition by ticker order by price_date desc
    ) = 1
),

joined as (
    select
        m.ticker,
        d.sector,
        m.total_trading_days,
        m.avg_volume,
        m.daily_volatility,
        m.annual_return,
        m.annual_volatility,
        m.sharpe_ratio,
        m.sortino_ratio,
        m.cvar_5,
        m.cum_return_window,
        coalesce(s.ichimoku_score, 0) as ichimoku_score,
        p.current_price
    from metrics as m
    join {{ ref('dim_ticker') }} as d using (ticker)
    left join score as s using (ticker)
    left join latest_price as p using (ticker)
    -- Keep a stock only when it is in the S&P 500 on the last date.
    join {{ ref('stg_membership') }} as mb
        on mb.ticker = m.ticker
        and {{ is_member_on('mb', '(select max(price_date) from ' ~ ref('stg_prices') ~ ')') }}
),

screened as (
    select *
    from joined
    where {{ passes_screen() }}
)

select
    *,
    row_number() over (
        partition by sector
        order by {{ rank_column() }} desc
    ) as sector_rank
from screened
-- Keep the top names in each sector.
qualify sector_rank <= {{ top_n }}
