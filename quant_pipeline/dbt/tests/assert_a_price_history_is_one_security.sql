-- Singular test: the close of a ticker must not span a factor of
-- price_span_limit over the history.
--
-- No listed share rises or falls by a factor of 1000 in four years. Such a
-- span means that the price file mixes two price regimes of the ticker: the
-- prices before a split and the prices after it, with no adjustment. The
-- daily returns of such a history are not returns. Add the ticker to the
-- price_data_exclusions seed. See decision D15.
--
-- The test warns, so a new download does not stop a build.

{{ config(severity='warn') }}

select
    ticker,
    min(close) as lowest_close,
    max(close) as highest_close,
    max(close) / min(close) as span
from {{ ref('stg_prices') }}
group by ticker
having max(close) / min(close) >= {{ var('price_span_limit') }}
