-- Model: daily_metrics
-- Camada Gold: Métricas agregadas diárias

{{ config(
    materialized = "table",
    partition_by = "event_date",
    cluster_by = ["model", "tenant_id"],
    post_hook = [
        "CALL spark_catalog.system.compute_table_stats(TABLE {{ this }}, FALSE)",
        "OPTIMIZE {{ this }} ZORDER BY (event_date, model)"
    ]
) }}

with source_events as (
    select * from {{ ref('stg_events') }}
    where event_type = 'request'
),

metrics as (
    select
        event_date,
        tenant_id,
        model,
        provider,
        count(*) as total_requests,
        sum(when(event_type = 'request', 1, 0)) as total_requests_count,
        sum(when(event_type = 'response', 1, 0)) as total_responses_count,
        sum(tokens_used) as total_tokens,
        avg(latency_ms) as avg_latency_ms,
        percentile_approx(latency_ms, 0.5) as p50_latency_ms,
        percentile_approx(latency_ms, 0.95) as p95_latency_ms,
        percentile_approx(latency_ms, 0.99) as p99_latency_ms,
        max(latency_ms) as max_latency_ms,
        sum(cost_usd) as total_cost_usd,
        count(distinct user_id) as unique_users,
        count(distinct session_id) as unique_sessions,
        current_timestamp() as _gold_timestamp
    from source_events
    group by
        event_date,
        tenant_id,
        model,
        provider
)

select * from metrics