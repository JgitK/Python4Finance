-- Singular test: on the last day of each stock, the daily risk metrics must
-- equal int_risk_metrics. The test passes with zero rows.

with daily as (
    select *
    from {{ ref('int_risk_metrics_daily') }}
    qualify row_number() over (partition by ticker order by as_of_date desc) = 1
)

select d.ticker
from daily as d
full join {{ ref('int_risk_metrics') }} as m using (ticker)
where d.ticker is null
    or m.ticker is null
    or d.total_trading_days <> m.total_trading_days
    or abs(d.avg_volume - m.avg_volume) > 1e-6
    or abs(d.daily_volatility - m.daily_volatility) > 1e-12
    or abs(d.annual_return - m.annual_return) > 1e-12
    or abs(d.sharpe_ratio - m.sharpe_ratio) > 1e-12
    -- The screen ranks on this column, so a point-in-time version of it
    -- must equal the latest version on the last day of each stock.
    or abs(d.cum_return_window - m.cum_return_window) > 1e-12
