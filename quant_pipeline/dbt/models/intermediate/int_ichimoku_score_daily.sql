-- Give each stock a bullish Ichimoku score from 0 to 5 on each day.
-- The rules are in the ichimoku_score macro. int_ichimoku uses only past
-- data for the score inputs, so each score uses only data up to its date.

select
    ticker,
    price_date as as_of_date,
    {{ ichimoku_score() }} as ichimoku_score
from {{ ref('int_ichimoku') }}
