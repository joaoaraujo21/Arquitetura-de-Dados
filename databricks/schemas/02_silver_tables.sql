-- Tabelas Silver: dados limpos, tipados e validados
--Camada intermediária com qualidade de dados garantida

USE CATALOG openrouter_catalog;
USE SCHEMA silver;

-- Tabela de eventos limpos
CREATE TABLE IF NOT EXISTS clean_events (
    event_id STRING NOT NULL COMMENT 'ID único do evento',
    user_id STRING NOT NULL COMMENT 'ID do usuário',
    event_type STRING NOT NULL COMMENT 'Tipo do evento',
    model STRING NOT NULL COMMENT 'Modelo de IA',
    provider STRING COMMENT 'Provedor do modelo',
    tokens_used INT COMMENT 'Tokens consumidos',
    cost_usd DECIMAL(18,6) COMMENT 'Custo em USD',
    latency_ms INT COMMENT 'Latência em ms',
    event_timestamp TIMESTAMP NOT NULL COMMENT 'Timestamp do evento',
    event_date DATE NOT NULL COMMENT 'Data do evento',
    user_key BIGINT COMMENT 'Chave surrogada do usuário',
    _ingest_timestamp TIMESTAMP COMMENT 'Timestamp original da ingestão',
    _silver_timestamp TIMESTAMP NOT NULL COMMENT 'Timestamp de transformação silver',
    _source_table STRING COMMENT 'Tabela de origem bronze'
)
USING DELTA
PARTITIONED BY (event_date)
COMMENT 'Eventos limpos e validados'
TBLPROPERTIES (
    'quality' = 'silver',
    'layer' = 'silver'
)
-- Constraints
CONSTRAINT valid_event_type CHECK (event_type IN ('request', 'response', 'error')),
CONSTRAINT positive_tokens CHECK (tokens_used >= 0),
CONSTRAINT positive_cost CHECK (cost_usd >= 0),
CONSTRAINT positive_latency CHECK (latency_ms >= 0);

-- Tabela de usuários limpos
CREATE TABLE IF NOT EXISTS clean_users (
    user_id STRING NOT NULL COMMENT 'ID único do usuário',
    user_key BIGINT COMMENT 'Chave surrogada',
    first_name STRING COMMENT 'Primeiro nome',
    last_name STRING COMMENT 'Sobrenome',
    email STRING NOT NULL COMMENT 'Email (único)',
    email_hash STRING COMMENT 'Hash do email para join',
    phone STRING COMMENT 'Telefone',
    age INT COMMENT 'Idade',
    country STRING COMMENT 'País',
    signup_date DATE COMMENT 'Data de cadastro',
    _ingest_timestamp TIMESTAMP,
    _silver_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Usuários limpos e deduplicados'
TBLPROPERTIES ('quality' = 'silver')
CONSTRAINT unique_email UNIQUE (email);

-- Tabela de dimensões de modelos
CREATE TABLE IF NOT EXISTS dim_models (
    model_key BIGINT NOT NULL COMMENT 'Chave surrogada',
    model_id STRING NOT NULL COMMENT 'ID do modelo',
    model_name STRING NOT NULL COMMENT 'Nome do modelo',
    provider STRING NOT NULL COMMENT 'Provedor',
    model_family STRING COMMENT 'Família do modelo',
    context_window INT COMMENT 'Janela de contexto',
    input_cost_per_1k DECIMAL(18,8) COMMENT 'Custo input por 1K tokens',
    output_cost_per_1k DECIMAL(18,8) COMMENT 'Custo output por 1K tokens',
    is_active BOOLEAN COMMENT 'Se está ativo',
    _silver_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Dimensão de modelos de IA'
TBLPROPERTIES ('quality' = 'silver');

-- Tabela de dimensões de data
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INT NOT NULL COMMENT 'Chave da data (YYYYMMDD)',
    date_value DATE NOT NULL COMMENT 'Data',
    year INT NOT NULL COMMENT 'Ano',
    quarter INT NOT NULL COMMENT 'Trimestre',
    month INT NOT NULL COMMENT 'Mês',
    month_name STRING NOT NULL COMMENT 'Nome do mês',
    week_of_year INT NOT NULL COMMENT 'Semana do ano',
    day_of_week INT NOT NULL COMMENT 'Dia da semana (1=Dom)',
    day_name STRING NOT NULL COMMENT 'Nome do dia',
    is_weekend BOOLEAN NOT NULL COMMENT 'É fim de semana',
    is_month_start BOOLEAN NOT NULL COMMENT 'É início do mês',
    is_month_end BOOLEAN NOT NULL COMMENT 'É fim do mês',
    fiscal_quarter STRING COMMENT 'Trimestre fiscal'
)
USING DELTA
COMMENT 'Dimensão de data'
TBLPROPERTIES ('quality' = 'silver');

-- Adiciona tags
ALTER TABLE clean_events SET TAGS ('layer' = 'silver', 'domain' = 'analytics', 'pii' = 'false');
ALTER TABLE clean_users SET TAGS ('layer' = 'silver', 'domain' => 'users', 'pii' = 'true');
ALTER TABLE dim_models SET TAGS ('layer' = 'silver', 'domain' = 'reference', 'pii' = 'false');
ALTER TABLE dim_date SET TAGS ('layer' => 'silver', 'domain' = 'reference', 'pii' = 'false');