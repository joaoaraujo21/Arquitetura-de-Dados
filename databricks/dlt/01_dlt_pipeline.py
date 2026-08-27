# Databricks notebook source
# MAGIC %md
# MAGIC # Delta Live Tables (DLT) Pipeline
# MAGIC
# MAGIC Pipeline de ELT usando Delta Live Tables para processamento contínuo de dados.

# COMMAND ----------

import dlt
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configurações

# COMMAND ----------

CATALOG = "openrouter_catalog"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Layer - Streaming Tables

# COMMAND ----------

@dlt.table(
    name="raw_events",
    comment="Eventos brutos ingeridos de Kafka",
    table_properties={
        "quality": "bronze",
        "pipelines.autoIngest.enabled": "true"
    }
)
def raw_events():
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka.example.com:9092")
        .option("subscribe", "user-events")
        .option("startingOffsets", "earliest")
        .load()
        .selectExpr("CAST(value AS STRING) as raw_value", "timestamp as event_timestamp")
        .withColumn("_ingest_time", current_timestamp())
    )

@dlt.table(
    name="raw_api_calls",
    comment="Chamadas de API brutas",
    table_properties={"quality": "bronze"}
)
def raw_api_calls():
    return (
        spark.read
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaLocation", f"{CATALOG}.{BRONZE_SCHEMA}.schema_checkpoints_api")
        .load("/mnt/openrouter/landing/api-calls/")
        .withColumn("_ingest_time", current_timestamp())
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer - Cleaned & Validated

# COMMAND ----------

@dlt.view(
    name="parsed_events",
    comment="Eventos parseados a partir do JSON bruto"
)
@dlt.expect_or_drop("valid_json", "raw_value IS NOT NULL")
def parsed_events():
    schema = StructType([
        StructField("user_id", StringType()),
        StructField("event_type", StringType()),
        StructField("model", StringType()),
        StructField("tokens_used", IntegerType()),
        StructField("cost_usd", DoubleType()),
        StructField("latency_ms", IntegerType()),
    ])

    return (
        dlt.read_stream("raw_events")
        .select(
            from_json(col("raw_value"), schema).alias("data"),
            col("event_timestamp")
        )
        .select("data.*", "event_timestamp")
        .withColumn("processed_at", current_timestamp())
    )

@dlt.table(
    name="clean_events",
    comment="Eventos limpos e validados",
    table_properties={"quality": "silver"}
)
@dlt.expect("valid_user_id", "user_id IS NOT NULL")
@dlt.expect("valid_event_type", "event_type IN ('request', 'response', 'error')")
@dlt.expect("valid_tokens", "tokens_used >= 0")
@dlt.expect("valid_cost", "cost_usd >= 0")
def clean_events():
    return (
        dlt.read_stream("parsed_events")
        .filter(col("user_id").isNotNull())
        .filter(col("event_type").isNotNull())
        .withColumn("event_date", to_date(col("event_timestamp")))
        .dropDuplicates(["user_id", "event_timestamp"])
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer - Agregações

# COMMAND ----------

@dlt.table(
    name="daily_metrics",
    comment="Métricas agregadas diariamente",
    table_properties={"quality": "gold"}
)
def daily_metrics():
    return (
        dlt.read("clean_events")
        .groupBy(
            "event_date",
            "model"
        )
        .agg(
            count("*").alias("total_events"),
            sum("tokens_used").alias("total_tokens"),
            sum("cost_usd").alias("total_cost"),
            avg("latency_ms").alias("avg_latency"),
            countDistinct("user_id").alias("unique_users")
        )
    )

@dlt.table(
    name="user_360",
    comment="Visão 360 do usuário",
    table_properties={"quality": "gold"}
)
def user_360():
    return (
        dlt.read("clean_events")
        .groupBy("user_id")
        .agg(
            count("*").alias("total_events"),
            sum("tokens_used").alias("lifetime_tokens"),
            sum("cost_usd").alias("lifetime_cost"),
            max("event_timestamp").alias("last_activity"),
            min("event_timestamp").alias("first_activity"),
            countDistinct("model").alias("models_used")
        )
        .withColumn("days_active", datediff(col("last_activity"), col("first_activity")))
        .withColumn("is_active_30d", datediff(current_date(), col("last_activity")) <= 30)
    )
