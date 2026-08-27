# Databricks notebook source
# MAGIC %md
# MAGIC # Transformação Silver Layer
# MAGIC
# MAGIC Limpeza, validação e enriquecimento dos dados da camada bronze para silver.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configurações

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import Window
import great_expectations as ge
from great_expectations.dataset import SparkDFDataset

spark = SparkSession.builder.getOrDefault()

# Configurações
CATALOG = "openrouter_catalog"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de Qualidade de Dados

# COMMAND ----------

def validate_dataframe(df, table_name, expectations):
    """
    Valida DataFrame usando Great Expectations

    Args:
        df: DataFrame Spark
        table_name: Nome da tabela
        expectations: Lista de dicionários com expectativas

    Returns:
        ValidationResult
    """
    ge_df = SparkDFDataset(df)
    results = []

    for exp in expectations:
        exp_type = exp.get("type")
        column = exp.get("column")

        if exp_type == "not_null":
            result = ge_df.expect_column_values_to_not_be_null(column)
        elif exp_type == "unique":
            result = ge_df.expect_column_values_to_be_unique(column)
        elif exp_type == "range":
            result = ge_df.expect_column_values_to_be_between(
                column, exp.get("min"), exp.get("max")
            )
        elif exp_type == "regex":
            result = ge_df.expect_column_values_to_match_regex(
                column, exp.get("pattern")
            )
        elif exp_type == "in_set":
            result = ge_df.expect_column_values_to_be_in_set(
                column, exp.get("values")
            )
        else:
            print(f"Unknown expectation type: {exp_type}")
            continue

        results.append({
            "expectation_type": exp_type,
            "column": column,
            "success": result.success,
            "result": result.result
        })

    return results

def clean_dataframe(df, cleaning_rules):
    """
    Aplica regras de limpeza ao DataFrame

    Args:
        df: DataFrame Spark
        cleaning_rules: Lista de dicionários com regras

    Returns:
        DataFrame limpo
    """
    cleaned_df = df

    for rule in cleaning_rules:
        rule_type = rule.get("type")
        column = rule.get("column")

        if rule_type == "trim":
            cleaned_df = cleaned_df.withColumn(column, trim(col(column)))
        elif rule_type == "lower":
            cleaned_df = cleaned_df.withColumn(column, lower(col(column)))
        elif rule_type == "upper":
            cleaned_df = cleaned_df.withColumn(column, upper(col(column)))
        elif rule_type == "fillna":
            value = rule.get("value", "")
            cleaned_df = cleaned_df.fillna(value, subset=[column])
        elif rule_type == "dropna":
            cleaned_df = cleaned_df.dropna(subset=[column])
        elif rule_type == "deduplicate":
            subset = rule.get("subset", df.columns)
            cleaned_df = cleaned_df.dropDuplicates(subset)
        elif rule_type == "cast":
            target_type = rule.get("target_type", "string")
            cleaned_df = cleaned_df.withColumn(column, col(column).cast(target_type))
        elif rule_type == "regex_replace":
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            cleaned_df = cleaned_df.withColumn(
                column, regexp_replace(col(column), pattern, replacement)
            )

    return cleaned_df

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline de Transformação Bronze -> Silver

# COMMAND ----------

def transform_bronze_to_silver(source_table, target_table, cleaning_rules, validation_expectations):
    """
    Transforma dados da camada bronze para silver

    Args:
        source_table: Tabela fonte no formato catalog.schema.table
        target_table: Tabela destino no formato catalog.schema.table
        cleaning_rules: Regras de limpeza
        validation_expectations: Expectativas de validação
    """
    # Lê dados da bronze
    bronze_df = spark.table(source_table)

    # Aplica limpeza
    silver_df = clean_dataframe(bronze_df, cleaning_rules)

    # Valida qualidade
    validation_results = validate_dataframe(silver_df, target_table, validation_expectations)

    # Verifica falhas
    failed_validations = [r for r in validation_results if not r["success"]]
    if failed_validations:
        print(f"VALIDATION FAILURES for {target_table}:")
        for fv in failed_validations:
            print(f"  - {fv['expectation_type']} on {fv['column']}: {fv['result']}")

        # Em produção, decidir se falha ou apenas alerta
        # raise Exception(f"Data quality validation failed for {target_table}")

    # Adiciona metadados de transformação
    silver_df = silver_df.withColumn("_transform_timestamp", current_timestamp()) \
                        .withColumn("_source_table", lit(source_table))

    # Escreve na silver (Delta Lake com merge para upsert)
    silver_df.write.mode("overwrite").format("delta").saveAsTable(target_table)

    # Otimiza a tabela
    spark.sql(f"OPTIMIZE {target_table}")
    spark.sql(f"VACUUM {target_table} RETAIN 168 HOURS")

    print(f"Successfully transformed {bronze_df.count()} -> {silver_df.count()} records into {target_table}")
    return silver_df, validation_results

# COMMAND ----------

# MAGIC %md
# MAGIC ## Exemplo: Transformação de Usuários

# COMMAND ----------

# Regras de limpeza para usuários
USER_CLEANING_RULES = [
    {"type": "trim", "column": "email"},
    {"type": "lower", "column": "email"},
    {"type": "trim", "column": "first_name"},
    {"type": "trim", "column": "last_name"},
    {"type": "fillna", "column": "phone", "value": ""},
    {"type": "cast", "column": "age", "target_type": "int"},
    {"type": "cast", "column": "created_at", "target_type": "timestamp"},
    {"type": "deduplicate", "subset": ["email"]},
]

USER_VALIDATION_EXPECTATIONS = [
    {"type": "not_null", "column": "user_id"},
    {"type": "unique", "column": "email"},
    {"type": "not_null", "column": "email"},
    {"type": "regex", "column": "email", "pattern": r"^[^@]+@[^@]+\.[^@]+"},
    {"type": "range", "column": "age", "min": 0, "max": 120},
]

# Executa transformação
# users_silver, validation = transform_bronze_to_silver(
#     source_table=f"{CATALOG}.{BRONZE_SCHEMA}.users_raw",
#     target_table=f"{CATALOG}.{SILVER_SCHEMA}.users_clean",
#     cleaning_rules=USER_CLEANING_RULES,
#     validation_expectations=USER_VALIDATION_EXPECTATIONS
# )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Notebook Concluído

# COMMAND ----------

dbutils.notebook.exit("Transformação Silver concluída com sucesso")