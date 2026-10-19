"""Assets: os dados que as DAGs produzem e dos quais outras DAGs dependem (Aula 5).

Ficam num arquivo comum para uma DAG não precisar importar o arquivo de outra DAG.
A URI é só um nome: o Airflow não confere o S3, confia na task que declara o Asset em outlets.
"""

from airflow.sdk import Asset

from include.ingestao.bronze import BUCKET_LAKE

# Produzido pela tlc_ingest; dispara a weather_ingest (e o dbt_build, na Fase 3)
BRONZE_TLC = Asset(f"s3://{BUCKET_LAKE}/bronze/tlc_hvfhv")

# Produzido pela weather_ingest
BRONZE_CLIMA = Asset(f"s3://{BUCKET_LAKE}/bronze/open_meteo")
