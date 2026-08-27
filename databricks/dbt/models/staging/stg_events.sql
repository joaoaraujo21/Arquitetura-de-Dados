-- Model: stg_events
-- Camada Silver: Eventos limpos e enriquecidos

{{ config(
    materialized = "incremental",
    unique_key = "event_id",
    incremental_strategy = "append",
    partition_by = "event_date"
) }}

with source as (

    select * from {{ source('raw', 'events') }}

),

deduplicated as (

    select
        event_id,
        user_id,
        event_type,
        model,
        provider,
        tokens_used,
        cost_usd,
        latency_ms,
        cast(event_timestamp as timestamp) as event_timestamp,
        to_date(event_timestamp) as event_date,
        _ingest_timestamp
    from (
        select
            *,
            row_number() over (
                partition by event_id
                order by _ingest_timestamp desc
            ) as rn
        from source
    )
    where rn = 1

),

validated as (

    select
        event_id,
        user_id,
        event_type,
        model,
        provider,
        cast(tokens_used as integer) as tokens_used,
        cast(cost_usd as decimal(18,6)) as cost_usd,
        cast(latency_ms as integer) as latency_ms,
        event_timestamp,
        event_date,
        _ingest_timestamp,
        current_timestamp() as _silver_timestamp
    from deduplicated
    where user_id is not null
      and event_type in ('request', 'response', 'error')
      and tokens_used >= 0
      and cost_usd >= 0
      and latency_ms >= 0

)

select * from validated

{% if is_incremental() %}
    where event_timestamp > (select max(event_timestamp) from {{ this }})
{% endif %}