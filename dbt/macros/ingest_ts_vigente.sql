{#
  Devolve o ingest_ts da versão VIGENTE de um mês, lido de controle.manifesto_vigente (Fase 2, D5 e D6).

  Por que uma macro: a projection da Bronze (ingest_ts do tipo injected) só aceita o valor ESCRITO
  no SQL ("static equality"), nunca uma subconsulta. Então o dbt pergunta ao manifesto ANTES e
  escreve a resposta no texto da consulta.

  Uso no model:  and ingest_ts = '{{ ingest_ts_vigente('tlc_hvfhv', var('source_month')) }}'

  Sem versão vigente para o mês: erro de compilação, antes de qualquer leitura de dados
  (falhar alto: sem isso, a consulta leria zero linhas sem reclamar).
#}
{% macro ingest_ts_vigente(fonte, mes) %}
    {#- Na fase de leitura do projeto (parse) o dbt não conversa com o banco: devolve vazio -#}
    {%- if not execute -%}
        {{ return('') }}
    {%- endif -%}

    {%- set consulta -%}
        select ingest_ts
        from {{ source('controle', 'manifesto_vigente') }}
        where source = '{{ fonte }}'
          and source_month = '{{ mes }}'
    {%- endset -%}

    {%- set linhas = run_query(consulta).rows -%}
    {%- if linhas | length != 1 -%}
        {{ exceptions.raise_compiler_error(
            "Manifesto: esperada 1 versão vigente de " ~ fonte ~ " " ~ mes ~ ", encontradas "
            ~ (linhas | length) ~ ". O mês já foi ingerido e aceito?"
        ) }}
    {%- endif -%}

    {{ return(linhas[0][0]) }}
{% endmacro %}
