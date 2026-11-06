-- Singular test: on the latest date, the screen history must select the
-- same stocks as mart_screen_candidates. The test passes with zero rows.

with latest as (
    select ticker
    from {{ ref('mart_screen_history') }}
    where as_of_date = (select max(as_of_date) from {{ ref('mart_screen_history') }})
),

current_screen as (
    select ticker from {{ ref('mart_screen_candidates') }}
)

(select ticker, 'only in history' as problem from latest
 except select ticker, 'only in history' from current_screen)
union all
(select ticker, 'only in candidates' from current_screen
 except select ticker, 'only in candidates' from latest)
