-- One row with the universe of this build. The Python layer reads it, so
-- the results log records which universe made the results.

select '{{ var("universe") }}' as universe
