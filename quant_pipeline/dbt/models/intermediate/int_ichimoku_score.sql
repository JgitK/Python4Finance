-- Give each stock a bullish Ichimoku score from 0 to 5.
-- The score uses the most recent day of each stock.
-- Each rule adds one point when the signal is bullish.
--   1. The close is above Span A.
--   2. The close is above Span B.
--   3. The conversion line is above the base line.
--   4. Span A is above Span B, so the cloud is green.
--   5. The close is above the base line.

with latest as (
    select *
    from {{ ref('int_ichimoku') }}
    -- Keep only the newest row of each stock.
    qualify row_number() over (
        partition by ticker
        order by price_date desc
    ) = 1
)

select
    ticker,
    price_date as as_of_date,
    close,
    conversion_line,
    base_line,
    span_a,
    span_b,
    {{ ichimoku_score() }} as ichimoku_score
from latest
