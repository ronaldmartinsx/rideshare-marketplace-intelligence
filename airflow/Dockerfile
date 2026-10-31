FROM astrocrpublic.azurecr.io/runtime:3.3-9

# Ambiente virtual próprio do dbt (Fase 3, decisão F7), separado do Airflow para as bibliotecas dos
# dois não brigarem. Mesmo Python (3.13) e mesmas versões do dbt/uv.lock: o dbt do Airflow é igual ao
# do terminal. O uv baixa o Python 3.13 (a imagem do Airflow usa o 3.14).
# O gcc (packages.txt) compila o mmh3, dependência do dbt sem versão pronta para Linux ARM.
ENV UV_PYTHON_INSTALL_DIR=/usr/local/airflow/.uv-python
RUN python -m venv /tmp/uv \
    && /tmp/uv/bin/pip install --no-cache-dir uv==0.9.5 \
    && /tmp/uv/bin/uv venv --python 3.13 /usr/local/airflow/dbt_venv \
    && /tmp/uv/bin/uv pip install --no-cache --python /usr/local/airflow/dbt_venv/bin/python \
         dbt-core==1.12.5 dbt-athena==1.11.1 \
    && rm -rf /tmp/uv
