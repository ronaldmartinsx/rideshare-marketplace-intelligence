{#
  Decide o banco do Glue de cada model.
  Padrão do dbt: <schema do target>_<schema do model>  (ex.: dev_silver, prod_silver).
  Aqui (spec, seção 6.1):
    target dev  -> dev_silver, dev_gold
    target prod -> silver, gold
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
