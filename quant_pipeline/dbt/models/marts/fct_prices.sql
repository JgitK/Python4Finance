-- The price fact table. One row per ticker per day.
-- It joins the clean prices with every indicator. This is the wide table
-- for charts and review. The Python stats layer does not need it.

select
    p.ticker,
    p.price_date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,
    r.daily_return,
    c.cum_return,
    b.middle_band,
    b.upper_band,
    b.lower_band,
    i.conversion_line,
    i.base_line,
    i.span_a,
    i.span_b,
    i.lagging_line
from {{ ref('stg_prices') }} as p
left join {{ ref('int_daily_returns') }} as r using (ticker, price_date)
left join {{ ref('int_cumulative_returns') }} as c using (ticker, price_date)
left join {{ ref('int_bollinger') }} as b using (ticker, price_date)
left join {{ ref('int_ichimoku') }} as i using (ticker, price_date)
