-- Measure the risk and return of each stock over the analysis window.
-- The window is the last 252 trading days, which is about one year.
-- These metrics drive the screen and the Max Sharpe choice.

{% set window = var('analysis_window') %}
{% set rf = var('risk_free_rate') %}
{% set tdays = var('trading_days_per_year') %}

with returns as (
    select
        r.ticker,
        r.price_date,
        r.daily_return,
        p.volume
    from {{ ref('int_daily_returns') }} as r
    join {{ ref('stg_prices') }} as p
        using (ticker, price_date)
    where r.daily_return is not null
),

-- Count the full history of each stock. The screen uses this count.
history as (
    select
        ticker,
        count(*) as total_trading_days
    from {{ ref('stg_prices') }}
    group by ticker
),

-- Keep the last 252 trading days of each stock.
recent as (
    select *
    from returns
    qualify row_number() over (
        partition by ticker
        order by price_date desc
    ) <= {{ window }}
),

-- Find the 5th percentile return of each stock. This is the Value at Risk point.
var_threshold as (
    select
        ticker,
        quantile_cont(daily_return, 0.05) as var_5
    from recent
    group by ticker
),

-- Average the returns that fall at or below the Value at Risk point.
-- This is the Conditional Value at Risk. It measures the worst days.
cvar as (
    select
        r.ticker,
        avg(r.daily_return) as cvar_5
    from recent as r
    join var_threshold as v using (ticker)
    where r.daily_return <= v.var_5
    group by r.ticker
),

metrics as (
    select
        ticker,
        avg(volume) as avg_volume,
        stddev_samp(daily_return) as daily_volatility,
        avg(daily_return) * {{ tdays }} as annual_return,
        stddev_samp(daily_return) * sqrt({{ tdays }}) as annual_volatility,
        -- Downside deviation only counts the days with a loss.
        sqrt(avg(
            case when daily_return < 0 then daily_return * daily_return else 0 end
        )) * sqrt({{ tdays }}) as downside_deviation,
        -- Compound the window returns to get the one-year return.
        exp(sum(ln(1 + daily_return))) - 1 as cum_return_window
    from recent
    group by ticker
)

select
    m.ticker,
    h.total_trading_days,
    m.avg_volume,
    m.daily_volatility,
    m.annual_return,
    m.annual_volatility,
    m.downside_deviation,
    m.cum_return_window,
    c.cvar_5,
    -- The Sharpe ratio is the excess return per unit of total risk.
    (m.annual_return - {{ rf }}) / nullif(m.annual_volatility, 0) as sharpe_ratio,
    -- The Sortino ratio is the excess return per unit of downside risk.
    (m.annual_return - {{ rf }}) / nullif(m.downside_deviation, 0) as sortino_ratio
from metrics as m
join history as h using (ticker)
left join cvar as c using (ticker)
