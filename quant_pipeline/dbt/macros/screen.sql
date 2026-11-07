-- Shared rules for the screen. The latest screen and the screen history use
-- these macros, so the two screens always apply the same rules.

{% macro ichimoku_score() %}
    (
        case when close > span_a then 1 else 0 end
        + case when close > span_b then 1 else 0 end
        + case when conversion_line > base_line then 1 else 0 end
        + case when span_a > span_b then 1 else 0 end
        + case when close > base_line then 1 else 0 end
    )
{% endmacro %}

{% macro passes_screen() %}
    (
        total_trading_days >= {{ var('min_trading_days') }}
        and avg_volume >= {{ var('min_avg_volume') }}
        and daily_volatility <= {{ var('max_daily_volatility') }}
        and ichimoku_score >= {{ var('min_ichimoku_score') }}
    )
{% endmacro %}

{#
    The column that ranks the stocks inside each sector. The latest screen
    and the screen history use this macro, so the two screens always rank
    on the same measure. An unknown value stops the build, because a
    silent default would give a screen that nobody asked for.
#}
{% macro rank_column() %}
    {%- set metric = var('rank_metric') -%}
    {%- if metric == 'cum_return' -%}
        cum_return_window
    {%- elif metric == 'sharpe' -%}
        sharpe_ratio
    {%- else -%}
        {{ exceptions.raise_compiler_error(
            "rank_metric must be 'cum_return' or 'sharpe', not '" ~ metric ~ "'") }}
    {%- endif -%}
{% endmacro %}
