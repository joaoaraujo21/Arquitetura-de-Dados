-- Tabelas Bronze: dados brutos ingeridos
-- Cada tabela mantém o formato original + metadados de ingestão

USE CATALOG openrouter_catalog;
USE SCHEMA bronze;

-- Tabela de eventos brutos
CREATE TABLE IF NOT EXISTS raw_events (
    -- Colunas originais
    event_id STRING COMMENT 'ID único do evento',
    user_id STRING COMMENT 'ID do usuário',
    event_type STRING COMMENT 'Tipo do evento (request, response, error)',
    model STRING COMMENT 'Modelo de IA utilizado',
    provider STRING COMMENT 'Provedor do modelo',
    tokens_used INT COMMENT 'Tokens consumidos',
    cost_usd DECIMAL(18,6) COMMENT 'Custo em USD',
    latency_ms INT COMMENT 'Latência em milissegundos',
    event_timestamp TIMESTAMP COMMENT 'Timestamp do evento',
    payload STRING COMMENT 'Payload completo em JSON',

    -- Colunas de metadados
    _ingest_timestamp TIMESTAMP COMMENT 'Timestamp da ingestão',
    _source_file STRING COMMENT 'Arquivo/URL de origem',
    _ingestion_batch_id STRING COMMENT 'ID do batch de ingestão'
)
USING DELTA
PARTITIONED BY (event_date DATE GENERATED ALWAYS AS (DATE_TRUNC('day', event_timestamp)))
COMMENT 'Eventos brutos de uso da API'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'quality' = 'bronze',
    'layer' = 'bronze'
);

-- Tabela de usuários brutos
CREATE TABLE IF NOT EXISTS raw_users (
    user_id STRING,
    first_name STRING,
    last_name STRING,
    email STRING,
    phone STRING,
    age INT,
    country STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    _ingest_timestamp TIMESTAMP,
    _source_file STRING
)
USING DELTA
COMMENT 'Dados brutos de usuários'
TBLPROPERTIES ('quality' = 'bronze');

-- Tabela de billing/custos brutos
CREATE TABLE IF NOT EXISTS raw_billing (
    billing_id STRING,
    user_id STRING,
    subscription_id STRING,
    amount DECIMAL(18,6),
    currency STRING,
    status STRING,
    billing_period_start DATE,
    billing_period_end DATE,
    created_at TIMESTAMP,
    _ingest_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (billing_period_start)
COMMENT 'Dados brutos de billing'
TBLPROPERTIES ('quality' = 'bronze');

-- Tabela de logs de auditoria
CREATE TABLE IF NOT EXISTS raw_audit_logs (
    log_id STRING,
    user_id STRING,
    action STRING,
    resource_type STRING,
    resource_id STRING,
    ip_address STRING,
    user_agent STRING,
    status_code INT,
    response_time_ms INT,
    log_timestamp TIMESTAMP,
    _ingest_timestamp TIMESTAMP
)
USING DELTA
PARTITIONED BY (log_date DATE GENERATED ALWAYS AS (DATE_TRUNC('day', log_timestamp)))
COMMENT 'Logs de auditoria brutos'
TBLPROPERTIES ('quality' = 'bronze');

-- Adiciona tags
ALTER TABLE raw_events SET TAGS ('layer' = 'bronze', 'domain' = 'analytics', 'pii' = 'false');
ALTER TABLE raw_users SET TAGS ('layer' = 'bronze', 'domain' = 'users', 'pii' = 'true');
ALTER TABLE raw_billing SET TAGS ('layer' = 'bronze', 'domain' = 'finance', 'pii' = 'false');
ALTER TABLE raw_audit_logs SET TAGS ('layer' = 'bronze', 'domain' = 'security', 'pii' = 'false');