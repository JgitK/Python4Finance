-- The membership of the selected universe. Each row is one stint.
-- The end_date is the first day out. A null end_date means "still in".
--
-- The var universe selects the lists:
--   sp500   the S&P 500 (the default).
--   nasdaq  the Nasdaq universe: listed operating companies with a market
--           cap of at least $1B in each monthly snapshot.
--   both    the two lists together.
-- A stock can have stints in the two lists that overlap or touch. This
-- model merges such stints into one, so a screen counts the stock one time.

{% set universe = var('universe') %}
{% if universe not in ['sp500', 'nasdaq', 'both'] %}
    {{ exceptions.raise_compiler_error(
        "The var universe must be sp500, nasdaq, or both. It is: " ~ universe) }}
{% endif %}

with stints as (
    {% if universe in ['sp500', 'both'] %}
    select ticker, start_date, end_date from {{ ref('sp500_membership') }}
    {% endif %}
    {% if universe == 'both' %}
    union all
    {% endif %}
    {% if universe in ['nasdaq', 'both'] %}
    select ticker, start_date, end_date from {{ ref('nasdaq_membership') }}
    {% endif %}
),

-- Use a far date for an open stint, so the merge can compare the dates.
dated as (
    select ticker, start_date, coalesce(end_date, date '9999-12-31') as end_date
    from stints
),

-- A stint starts a new group when it starts after every earlier stint of
-- the same stock has ended. Otherwise it joins the group before it.
flagged as (
    select
        *,
        case
            when start_date <= max(end_date) over (
                partition by ticker order by start_date, end_date
                rows between unbounded preceding and 1 preceding
            ) then 0
            else 1
        end as new_group
    from dated
),

grouped as (
    select
        *,
        sum(new_group) over (
            partition by ticker order by start_date, end_date
            rows between unbounded preceding and current row
        ) as group_id
    from flagged
)

select
    ticker,
    min(start_date) as start_date,
    nullif(max(end_date), date '9999-12-31') as end_date
from grouped
group by ticker, group_id
