-- Add the five Ichimoku Cloud lines for each stock.
-- The Ichimoku Cloud shows support, resistance, and trend.
--   conversion_line  the midpoint of the last 9 days.
--   base_line        the midpoint of the last 26 days.
--   span_a           the midpoint of the two lines, moved forward 26 days.
--   span_b           the midpoint of the last 52 days, moved forward 26 days.
--   lagging_line     the close, moved back 26 days.

{% set p_conv = var('ichimoku_conversion') %}
{% set p_base = var('ichimoku_base') %}
{% set p_spanb = var('ichimoku_span_b') %}
{% set disp = var('ichimoku_displacement') %}

with prices as (
    select
        ticker,
        price_date,
        high,
        low,
        close
    from {{ ref('stg_prices') }}
),

lines as (
    select
        ticker,
        price_date,
        close,
        -- The midpoint is the highest high plus the lowest low, divided by two.
        (max(high) over conv + min(low) over conv) / 2 as conversion_line,
        (max(high) over base + min(low) over base) / 2 as base_line,
        (max(high) over span_b_window + min(low) over span_b_window) / 2 as span_b_raw
    from prices
    window
        conv as (
            partition by ticker order by price_date
            rows between {{ p_conv - 1 }} preceding and current row
        ),
        base as (
            partition by ticker order by price_date
            rows between {{ p_base - 1 }} preceding and current row
        ),
        span_b_window as (
            partition by ticker order by price_date
            rows between {{ p_spanb - 1 }} preceding and current row
        )
)

select
    ticker,
    price_date,
    close,
    conversion_line,
    base_line,
    -- Span A and Span B move forward. Each row reads a value from 26 days back.
    lag((conversion_line + base_line) / 2, {{ disp }}) over (
        partition by ticker order by price_date
    ) as span_a,
    lag(span_b_raw, {{ disp }}) over (
        partition by ticker order by price_date
    ) as span_b,
    -- The lagging line moves back. Each row reads the close from 26 days ahead.
    lead(close, {{ disp }}) over (
        partition by ticker order by price_date
    ) as lagging_line
from lines
