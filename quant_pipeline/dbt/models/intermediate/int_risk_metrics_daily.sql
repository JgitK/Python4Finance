-- Measure the risk and return of each stock on each day.
-- Each row uses only the last N returns up to its own date. N is the
-- analysis window. A future return cannot change an earlier row.
-- On the last day of each stock, the values equal int_risk_metrics.
-- A test in the tests folder makes sure of this.

{% set window = var('analysis_window') %}
{% set rf = var('risk_free_rate') %}
{% set tdays = var('trading_days_per_year') %}

-- Count the history of each stock up to each date.
with history as (
    select
        ticker,
        price_date,
        volume,
        count(*) over (
            partition by ticker order by price_date
            rows between unbounded preceding and current row
        ) as total_trading_days
    from {{ ref('stg_prices') }}
),

returns as (
    select
        r.ticker,
        r.price_date,
        r.daily_return,
        h.volume,
        h.total_trading_days
    from {{ ref('int_daily_returns') }} as r
    join history as h using (ticker, price_date)
    where r.daily_return is not null
),

metrics as (
    select
        ticker,
        price_date as as_of_date,
        total_trading_days,
        avg(volume) over w as avg_volume,
        stddev_samp(daily_return) over w as daily_volatility,
        avg(daily_return) over w * {{ tdays }} as annual_return,
        stddev_samp(daily_return) over w * sqrt({{ tdays }}) as annual_volatility,
        -- The compound return of the window. The screen can rank on this
        -- column. int_risk_metrics has the same expression without the
        -- window, and a test compares the two on the last day.
        exp(sum(ln(1 + daily_return)) over w) - 1 as cum_return_window
    from returns
    window w as (
        partition by ticker
        order by price_date
        rows between {{ window - 1 }} preceding and current row
    )
)

select
    *,
    (annual_return - {{ rf }}) / nullif(annual_volatility, 0) as sharpe_ratio
from metrics
