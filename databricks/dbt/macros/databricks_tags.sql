-- Macro: databricks_tags
-- Aplica tags e comentários consistentes em todas as tabelas

{% macro set_table_tags(table_name, layer, owner, domain) %}
    {%- if execute -%}
        {%- set tags = {
            'layer': layer,
            'owner': owner,
            'domain': domain
        } -%}
        alter table {{ table_name }} set tags(
            'layer' = '{{ layer }}',
            'owner' = '{{ owner }}',
            'domain' = '{{ domain }}'
        );
        comment on table {{ table_name }} is
            'Layer: {{ layer }} | Owner: {{ owner }} | Domain: {{ domain }}';
    {%- endif -%}
{% endmacro %}

{% macro optimize_table(table_name, zorder_cols) %}
    {%- if execute -%}
        optimize {{ table_name }} zorder by ({{ zorder_cols | join(', ') }});
    {%- endif -%}
{% endmacro %}

{% macro vacuum_table(table_name, hours=168) %}
    {%- if execute -%}
        vacuum {{ table_name }} retain {{ hours }} hours;
    {%- endif -%}
{% endmacro %}