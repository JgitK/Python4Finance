-- Singular test: each one-day move larger than the review limit must be in
-- the corporate_actions seed. Add the move as a corporate_action (stg_prices
-- then back-adjusts it) or as a real_move (the return stays). Put the
-- evidence in the note. The test warns, so a new move does not stop a build.

{{ config(severity='warn') }}

with moves as (
    select
        ticker,
        price_date,
        daily_return
    from {{ ref('int_daily_returns') }}
    where abs(daily_return) > {{ var('large_move_review_limit') }}
)

select m.*
from moves as m
left join {{ ref('corporate_actions') }} as ca
    on ca.ticker = m.ticker and ca.date = m.price_date
where ca.ticker is null
