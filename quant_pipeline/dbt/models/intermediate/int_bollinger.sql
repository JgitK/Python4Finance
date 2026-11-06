-- Add Bollinger Bands for each stock.
-- The middle band is a 20-day moving average of the close.
-- The upper and lower bands sit two standard deviations away from the middle.
-- The bands need a full window, so they are null until 20 days of data exist.

{% set window = var('bollinger_window') %}
{% set num_sd = var('bollinger_sd') %}

with prices as (
    select
        ticker,
        price_date,
        close
    from {{ ref('stg_prices') }}
)

select
    ticker,
    price_date,
    close,
    case
        when count(close) over w = {{ window }}
        then avg(close) over w
    end as middle_band,
    case
        when count(close) over w = {{ window }}
        then avg(close) over w + {{ num_sd }} * stddev_samp(close) over w
    end as upper_band,
    case
        when count(close) over w = {{ window }}
        then avg(close) over w - {{ num_sd }} * stddev_samp(close) over w
    end as lower_band
from prices
window w as (
    partition by ticker
    order by price_date
    rows between {{ window - 1 }} preceding and current row
)
