# Databricks notebook source
# MAGIC %md
# MAGIC # Transformação Gold Layer
# MAGIC
# MAGIC Criação de dados agregados e dimensionais para consumo analítico.

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window

spark = SparkSession.builder.getOrDefault()

CATALOG = "openrouter_catalog"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de Agregação

# COMMAND ----------

def create_dimension_table(source_df, dim_name, keys, attributes):
    """
    Cria uma tabela dimensional a partir de uma fonte

    Args:
        source_df: DataFrame de origem
        dim_name: Nome da dimensão
        keys: Colunas-chave da dimensão
        attributes: Colunas adicionais da dimensão

    Returns:
        DataFrame da dimensão
    """
    df = source_df.select(keys + attributes).dropDuplicates()

    # Adiciona surrogate key
    window_spec = Window.orderBy(*keys)
    df_with_key = df.withColumn(
        f"{dim_name}_key",
        row_number().over(window_spec).cast(LongType())
    )

    # Reordena colunas
    final_cols = [f"{dim_name}_key"] + keys + attributes
    return df_with_key.select(final_cols)

def create_fact_table(source_df, dimensions):
    """
    Cria uma tabela fato a partir de uma fonte

    Args:
        source_df: DataFrame de origem
        dimensions: Dict mapeando coluna source -> dimensão key

    Returns:
        DataFrame fato
    """
    fact_df = source_df

    # Adiciona measures comum
    fact_df = fact_df.withColumn("_fact_timestamp", current_timestamp())

    # Substitui colunas dimensão pelas chaves surrogates
    for source_col, dim_key in dimensions.items():
        fact_df = fact_df.withColumnRenamed(source_col, dim_key)

    return fact_df

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exemplo: Agregações de Negócio

# COMMAND ----------

def create_daily_metrics():
    """Cria métricas diárias de uso do sistema."""
    silver_df = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.usage_events")

    daily_metrics = silver_df \
        .withColumn("event_date", to_date(col("event_timestamp"))) \
        .groupBy(
            "event_date",
            "tenant_id",
            "model",
            "provider"
        ) \
        .agg(
            count("*").alias("total_events"),
            sum(when(col("event_type") == "request", 1).otherwise(0)).alias("total_requests"),
            sum(when(col("event_type") == "response", 1).otherwise(0)).alias("total_responses"),
            sum("tokens_used").alias("total_tokens"),
            avg("latency_ms").alias("avg_latency_ms"),
            sum("cost_usd").alias("total_cost"),
            countDistinct("user_id").alias("unique_users"),
        ) \
        .withColumn("_computed_at", current_timestamp())

    return daily_metrics

def create_model_performance_metrics():
    """Cria métricas de performance por modelo."""
    silver_df = spark.table(f"{CATALOG}.{SILVER_SCHEMA}.usage_events")

    model_metrics = silver_df \
        .withColumn("hour", date_trunc("hour", col("event_timestamp"))) \
        .groupBy("model", "provider", "hour") \
        .agg(
            count("*").alias("total_calls"),
            avg("latency_ms").alias("avg_latency"),
            percentile_approx("latency_ms", 0.5).alias("p50_latency"),
            percentile_approx("latency_ms", 0.95).alias("p95_latency"),
            percentile_approx("latency_ms", 0.99).alias("p99_latency"),
            max("latency_ms").alias("max_latency"),
            sum("tokens_used").alias("total_tokens"),
            sum("cost_usd").alias("total_cost"),
        ) \
        .withColumn("_computed_at", current_timestamp())

    return model_metrics

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execução

# COMMAND ----------

# Gera as tabelas gold
# daily_metrics_df = create_daily_metrics()
# daily_metrics_df.write.mode("overwrite").format("delta").saveAsTable(
#     f"{CATALOG}.{GOLD_SCHEMA}.daily_metrics"
# )

# model_metrics_df = create_model_performance_metrics()
# model_metrics_df.write.mode("overwrite").format("delta").saveAsTable(
#     f"{CATALOG}.{GOLD_SCHEMA}.model_performance"
# )

# Otimiza tabelas gold
# spark.sql(f"OPTIMIZE {CATALOG}.{GOLD_SCHEMA}.daily_metrics ZORDER BY (event_date, tenant_id)")
# spark.sql(f"OPTIMIZE {CATALOG}.{GOLD_SCHEMA}.model_performance ZORDER BY (model, hour)")

# spark.sql(f"ANALYZE TABLE {CATALOG}.{GOLD_SCHEMA}.daily_metrics COMPUTE STATISTICS")
# spark.sql(f"ANALYZE TABLE {CATALOG}.{GOLD_SCHEMA}.model_performance COMPUTE STATISTICS")

# COMMAND ----------

dbutils.notebook.exit("Transformação Gold concluída com sucesso")