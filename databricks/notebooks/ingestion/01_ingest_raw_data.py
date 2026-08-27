# Databricks notebook source
# MAGIC %md
# MAGIC # Ingestão de Dados Brutos
# MAGIC
# MAGIC Este notebook demonstra a ingestão de dados de várias fontes para a camada bronze no Delta Lake.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configurações

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json

# Configurações
spark = SparkSession.builder \
    .appName("OpenRouter Data Ingestion") \
    .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
    .getOrDefault()

# Configurações de caminhos
BRONZE_PATH = "/mnt/openrouter/bronze"
SILVER_PATH = "/mnt/openrouter/silver"
GOLD_PATH = "/mnt/openrouter/gold"
CHECKPOINT_PATH = "/mnt/openrouter/checkpoints"

# Configurações de Unity Catalog
CATALOG = "openrouter_catalog"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de Ingestão

# COMMAND ----------

def ingest_from_api(api_url, table_name, incremental_column=None):
    """
    Ingest data from REST API into Delta Lake bronze layer

    Args:
        api_url: URL da API
        table_name: Nome da tabela no Unity Catalog
        incremental_column: Coluna para ingestão incremental (opcional)
    """
    try:
        # Lê dados da API
        response = requests.get(api_url)
        data = response.json()

        # Converte para DataFrame
        df = spark.createDataFrame(data)

        # Adiciona metadados
        df_with_metadata = df.withColumn("_ingest_timestamp", current_timestamp()) \
                            .withColumn("_source_file", lit(api_url))

        # Escrita para Delta Lake (bronze)
        full_table_name = f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}"

        if incremental_column and spark.catalog.tableExists(full_table_name):
            # Ingestão incremental
            max_value = spark.table(full_table_name).agg(max(col(incremental_column))).collect()[0][0]
            if max_value:
                df_filtered = df_with_metadata.filter(col(incremental_column) > lit(max_value))
                df_filtered.write.mode("append").format("delta").saveAsTable(full_table_name)
            else:
                df_with_metadata.write.mode("overwrite").format("delta").saveAsTable(full_table_name)
        else:
            # Primeira carga ou sobrescrita completa
            df_with_metadata.write.mode("overwrite").format("delta").saveAsTable(full_table_name)

        print(f"Successfully ingested {df.count()} records into {full_table_name}")
        return df_with_metadata

    except Exception as e:
        print(f"Error ingesting from {api_url}: {str(e)}")
        raise

def ingest_from_s3(bucket, prefix, table_name, format="parquet"):
    """
    Ingest data from S3 into Delta Lake bronze layer

    Args:
        bucket: Nome do bucket S3
        prefix: Prefixo no bucket
        table_name: Nome da tabela no Unity Catalog
        format: Formato do arquivo (parquet, json, csv)
    """
    try:
        s3_path = f"s3a://{bucket}/{prefix}"

        # Lê dados do S3
        if format == "parquet":
            df = spark.read.parquet(s3_path)
        elif format == "json":
            df = spark.read.json(s3_path)
        elif format == "csv":
            df = spark.read.option("header", "true").csv(s3_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Adiciona metadados
        df_with_metadata = df.withColumn("_ingest_timestamp", current_timestamp()) \
                            .withColumn("_source_file", lit(s3_path))

        # Escrita para Delta Lake (bronze)
        full_table_name = f"{CATALOG}.{BRONZE_SCHEMA}.{table_name}"
        df_with_metadata.write.mode("overwrite").format("delta").saveAsTable(full_table_name)

        print(f"Successfully ingested {df.count()} records from {s3_path} into {full_table_name}")
        return df_with_metadata

    except Exception as e:
        print(f"Error ingesting from {s3_path}: {str(e)}")
        raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exemplo de Uso

# COMMAND ----------

# Exemplo: Ingestão de dados de usuários de uma API
# users_df = ingest_from_api(
#     api_url="https://api.example.com/users",
#     table_name="users_raw",
#     incremental_column="updated_at"
# )

# Exemplo: Ingestão de logs de S3
# logs_df = ingest_from_s3(
#     bucket="openrouter-logs",
#     prefix="application/logs/2024/08/27/",
#     table_name="application_logs_raw",
#     format="json"
# )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Notebook Concluído

# COMMAND ----------

dbutils.notebook.exit("Ingestão concluída com sucesso")