# Databricks notebook source
# MAGIC %md
# MAGIC # Ingestão via Kafka / Event Hubs
# MAGIC
# MAGIC Conecta ao Kafka ou Azure Event Hubs para ingestção streaming de eventos em tempo real.

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder.getOrCreate()

# Configurações
KAFKA_BOOTSTRAP_SERVERS = "kafka.bootstrap.servers"  # ou event hubs namespace
EVENT_HUBS_CONNECTION_STRING = dbutils.secrets.get("openrouter", "event_hubs_connection")

CATALOG = "openrouter_catalog"
BRONZE_SCHEMA = "bronze"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Schema dos Eventos

# COMMAND ----------

event_schema = StructType([
    StructField("event_id", StringType(), False),
    StructField("user_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("model", StringType(), True),
    StructField("provider", StringType(), True),
    StructField("tokens_used", IntegerType(), True),
    StructField("cost_usd", DoubleType(), True),
    StructField("latency_ms", IntegerType(), True),
    StructField("session_id", StringType(), True),
    StructField("tenant_id", StringType(), True),
    StructField("timestamp", StringType(), True),
])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Leitura Streaming do Kafka

# COMMAND ----------

def create_kafka_stream(batch_id="default"):
    """Cria um streaming DataFrame do Kafka."""
    return (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", "kafka.example.com:9092")
        .option("subscribe", "user-events,api-calls,billing-events")
        .option("startingOffsets", "earliest")
        .option("kafka.security.protocol", "SASL_SSL")
        .option("kafka.sasl.mechanism", "PLAIN")
        .option("kafka.sasl.jaas.config",
                f'kafka.security.authenticator.credentials="{{{{\"username\": \"$ConnectionString\", \"password\": \"{EVENT_HUBS_CONNECTION_STRING}\"}}}}')
        .load()
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Processamento e escrita Bronze

# COMMAND ----------

# Processa eventos do Kafka
kafka_df = create_kafka_stream()

processed_df = (
    kafka_df
    .select(
        from_json(col("value").cast("string"), event_schema).alias("data"),
        col("timestamp").alias("kafka_timestamp"),
        col("topic"),
        col("partition"),
        col("offset")
    )
    .select("data.*", "kafka_timestamp", "topic", "partition", "offset")
    .withColumn("_ingest_timestamp", current_timestamp())
    .withColumn("event_timestamp", to_timestamp(col("timestamp")))
    .withColumn("event_date", to_date(col("event_timestamp")))
)

# Escreve para Delta (bronze)
query = (
    processed_df.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", f"/mnt/openrouter/checkpoints/kafka_bronze_{batch_id}")
    .option("mergeSchema", "true")
    .trigger(processingTime="30 seconds")
    .toTable(f"{CATALOG}.{BRONZE_SCHEMA}.raw_events_streaming")
)

print(f"Streaming query started: {query.name}")
print(f"Writing to: {CATALOG}.{BRONZE_SCHEMA}.raw_events_streaming")

dbutils.notebook.exit("Kafka ingestion pipeline started")