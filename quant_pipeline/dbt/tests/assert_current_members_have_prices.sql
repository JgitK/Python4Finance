-- Singular test: a member of the universe on the last trading day must
-- have prices on that day.
--
-- The price source serves the symbols that trade now. For a company that
-- left the market, it answers "Symbol not exists.", and the pipeline has
-- no prices for that company. Such a gap is not repairable, and
-- data/missing_symbols.csv records it. See decision D19.
--
-- A member of the universe today is a different case. The company still
-- trades, so the source must have it. A row here is therefore a problem
-- that a person can repair: a ticker with punctuation that the API writes
-- in another way (BF.B), a company in the middle of an acquisition, or a
-- new ticker after a name change.
--
-- The test warns, so a new download does not stop a build.

{{ config(severity='warn') }}

with last_day as (
    select max(as_of_date) as as_of_date from {{ ref('mart_universe_coverage') }}
)

select c.ticker, c.as_of_date
from {{ ref('mart_universe_coverage') }} as c
join last_day as l using (as_of_date)
where not c.has_prices
