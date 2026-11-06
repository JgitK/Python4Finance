-- The membership rule. A stock is in the index on a date when the date is
-- on or after the start date and before the end date. The end date is the
-- first day out of the index. A null end date means that the stock is
-- still in the index.

{% macro is_member_on(membership, date_expr) %}
    ({{ date_expr }} >= {{ membership }}.start_date
     and ({{ membership }}.end_date is null
          or {{ date_expr }} < {{ membership }}.end_date))
{% endmacro %}
