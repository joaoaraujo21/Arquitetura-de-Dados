-- Tabelas Gold: dados agregados para consumo analítico
-- Camada final otimizada para consultas e relatórios

USE CATALOG openrouter_catalog;
USE SCHEMA gold;

-- Tabela fato: métricas diárias de uso
CREATE TABLE IF NOT EXISTS fact_daily_usage (
    date_key INT NOT NULL COMMENT 'FK para dim_date',
    model_key BIGINT NOT NULL COMMENT 'FK para dim_models',
    user_key BIGINT COMMENT 'FK para dim_users',
    tenant_id STRING COMMENT 'ID do tenant',

    -- Measures
    total_requests BIGINT COMMENT 'Total de requisições',
    total_tokens_input BIGINT COMMENT 'Tokens de input',
    total_tokens_output BIGINT COMMENT 'Tokens de output',
    total_tokens BIGINT COMMENT 'Total de tokens',
    total_cost_usd DECIMAL(18,6) COMMENT 'Custo total em USD',

    -- Métricas de latência
    avg_latency_ms DECIMAL(18,6) COMMENT 'Latência média em ms',
    p50_latency_ms DECIMAL(18,6) COMMENT 'Latência p50 em ms',
    p95_latency_ms DECIMAL(18,6) COMMENT 'Latência p95 em ms',
    p99_latency_ms DECIMAL(18,6) COMMENT 'Latência p99 em ms',
    max_latency_ms INT COMMENT 'Latência máxima em ms',

    -- Métricas de usuários
    unique_users INT COMMENT 'Usuários únicos',
    new_users INT COMMENT 'Novos usuários',
    returning_users INT COMMENT 'Usuários retornantes',

    -- Metadados
    _gold_timestamp TIMESTAMP NOT NULL COMMENT 'Timestamp de criação'
)
USING DELTA
COMMENT 'Fato de métricas diárias de uso'
TBLPROPERTIES ('quality' = 'gold')
-- Clustering otimizado para queries por data e modelo
CLUSTER BY (date_key, model_key);

-- Tabela fato: métricas por sessão
CREATE TABLE IF NOT EXISTS fact_sessions (
    session_key BIGINT NOT NULL COMMENT 'Chave da sessão',
    session_id STRING NOT NULL COMMENT 'ID único da sessão',
    user_key BIGINT NOT NULL COMMENT 'FK para dim_users',
    date_key INT NOT NULL COMMENT 'FK para dim_date',

    session_start TIMESTAMP COMMENT 'Início da sessão',
    session_end TIMESTAMP COMMENT 'Fim da sessão',
    session_duration_minutes DECIMAL(18,6) COMMENT 'Duração em minutos',

    requests_in_session INT COMMENT 'Requisições na sessão',
    tokens_in_session BIGINT COMMENT 'Tokens na sessão',
    cost_in_session_usd DECIMAL(18,6) COMMENT 'Custo da sessão',

    models_used ARRAY<STRING> COMMENT 'Modelos utilizados',
    error_count INT COMMENT 'Quantidade de erros',

    _gold_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Fato de métricas por sessão'
CLUSTER BY (date_key, user_key)
TBLPROPERTIES ('quality' = 'gold');

-- Dimensão: usuário agregada
CREATE TABLE IF NOT EXISTS dim_user_360 (
    user_key BIGINT NOT NULL COMMENT 'Chave do usuário',
    user_id STRING NOT NULL COMMENT 'ID do usuário',
    email STRING COMMENT 'Email',
    first_name STRING COMMENT 'Primeiro nome',
    last_name STRING COMMENT 'Sobrenome',
    country STRING COMMENT 'País',

    -- Métricas de lifetime
    signup_date DATE COMMENT 'Data de cadastro',
    days_since_signup INT COMMENT 'Dias desde cadastro',
    lifetime_requests BIGINT COMMENT 'Requisições totais',
    lifetime_tokens BIGINT COMMENT 'Tokens totais',
    lifetime_cost_usd DECIMAL(18,6) COMMENT 'Custo total',

    -- Métricas recentes
    last_activity_date DATE COMMENT 'Última atividade',
    days_since_last_activity INT COMMENT 'Dias desde última atividade',
    last_30d_requests INT COMMENT 'Requisições últimos 30 dias',
    last_30d_cost_usd DECIMAL(18,6) COMMENT 'Custo últimos 30 dias',

    -- Segmentação
    user_segment STRING COMMENT 'Segmento (active/recent/dormant/inactive)',
    user_tier STRING COMMENT 'Tier (free/pro/business/enterprise)',
    risk_score DECIMAL(18,6) COMMENT 'Score de risco de churn',

    _gold_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Dimensão usuário 360'
CLUSTER BY (user_key)
TBLPROPERTIES ('quality' = 'gold');

-- Agregação: métricas por hora
CREATE TABLE IF NOT EXISTS agg_hourly_metrics (
    hour_key INT NOT NULL COMMENT 'Chave da hora (YYYYMMDDHH)',
    date_key INT NOT NULL COMMENT 'FK para dim_date',
    model_key BIGINT NOT NULL COMMENT 'FK para dim_models',

    total_requests BIGINT,
    total_tokens BIGINT,
    total_cost_usd DECIMAL(18,6),
    avg_latency_ms DECIMAL(18,6),
    p95_latency_ms DECIMAL(18,6),
    unique_users INT,
    error_rate DECIMAL(18,6),

    _gold_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Agregação hourly de métricas'
CLUSTER BY (hour_key)
TBLPROPERTIES ('quality' = 'gold');

-- Adiciona tags às tabelas gold
ALTER TABLE fact_daily_usage SET TAGS ('layer' = 'gold', 'domain' = 'analytics', 'aggregation' = 'daily');
ALTER TABLE fact_sessions SET TAGS ('layer' = 'gold', 'domain' = 'analytics', 'aggregation' = 'session');
ALTER TABLE dim_user_360 SET TAGS ('layer' = 'gold', 'domain' => 'users', 'pii' = 'true');
ALTER TABLE agg_hourly_metrics SET TAGS ('layer' = 'gold', 'domain' = 'analytics', 'aggregation' = 'hourly');

-- Análise de estatísticas para otimização de queries
ANALYZE TABLE fact_daily_usage COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE fact_sessions COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE dim_user_360 COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE agg_hourly_metrics COMPUTE STATISTICS FOR ALL COLUMNS;