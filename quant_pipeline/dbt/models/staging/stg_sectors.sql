-- The sector of each stock. Each stock maps to one GICS sector.
-- The GICS seed comes first. A stock with no GICS sector gets its Nasdaq
-- sector. The reference step maps the Nasdaq sector to the nearest GICS name.

select ticker, sector
from {{ ref('stock_sectors') }}

union all

select n.ticker, n.sector
from {{ ref('nasdaq_sectors') }} as n
where n.ticker not in (select ticker from {{ ref('stock_sectors') }})
