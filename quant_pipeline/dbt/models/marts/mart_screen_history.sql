-- Apply the screen on each date with only the data up to that date.
-- On each date, only the stocks in the S&P 500 on that date can pass.
-- The backtest reads this mart. On a past selection date, the backtest
-- selects only from the stocks that passed the screen on that date.
-- The rules are in the passes_screen macro. mart_screen_candidates uses the
-- same macro, so on the latest date the two marts select the same stocks.

with joined as (
    select
        m.as_of_date,
        m.ticker,
        d.sector,
        m.total_trading_days,
        m.avg_volume,
        m.daily_volatility,
        m.sharpe_ratio,
        m.cum_return_window,
        coalesce(s.ichimoku_score, 0) as ichimoku_score
    from {{ ref('int_risk_metrics_daily') }} as m
    join {{ ref('dim_ticker') }} as d using (ticker)
    left join {{ ref('int_ichimoku_score_daily') }} as s using (ticker, as_of_date)
    -- Keep a stock only on the dates when it is in the S&P 500.
    join {{ ref('stg_membership') }} as mb
        on mb.ticker = m.ticker
        and {{ is_member_on('mb', 'm.as_of_date') }}
),

screened as (
    select *
    from joined
    where {{ passes_screen() }}
)

select
    *,
    row_number() over (
        partition by as_of_date, sector
        order by {{ rank_column() }} desc
    ) as sector_rank
from screened
qualify sector_rank <= {{ var('top_n_per_sector') }}
