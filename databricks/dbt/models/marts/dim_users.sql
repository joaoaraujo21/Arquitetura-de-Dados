-- Model: dim_users
-- Camada Gold: Dimensão de usuários com métricas de engajamento

{{ config(
    materialized = "table",
    post_hook = [
        "OPTIMIZE {{ this }} ZORDER BY (user_key)"
    ]
) }}

with users as (
    select * from {{ ref('stg_users') }}
),

user_events as (
    select * from {{ ref('stg_events') }}
),

user_metrics as (
    select
        u.user_id,
        u.first_name,
        u.last_name,
        u.email,
        u.country,
        u.created_at as signup_date,
        count(distinct e.event_id) as lifetime_events,
        sum(e.tokens_used) as lifetime_tokens,
        sum(e.cost_usd) as lifetime_cost,
        max(e.event_timestamp) as last_activity,
        min(e.event_timestamp) as first_activity,
        count(distinct e.model) as models_used,
        count(distinct date(e.event_timestamp)) as active_days,
        current_timestamp() as _gold_timestamp
    from users u
    left join user_events e on u.user_id = e.user_id
    group by
        u.user_id,
        u.first_name,
        u.last_name,
        u.email,
        u.country,
        u.created_at
),

with_keys as (
    select
        row_number() over (order by user_id) as user_key,
        *
    from user_metrics
),

enriched as (
    select
        user_key,
        user_id,
        first_name,
        last_name,
        email,
        country,
        signup_date,
        first_activity,
        last_activity,
        datediff(last_activity, first_activity) as days_since_signup,
        datediff(current_date(), last_activity) as days_since_last_activity,
        lifetime_events,
        lifetime_tokens,
        lifetime_cost,
        models_used,
        active_days,
        case
            when datediff(current_date(), last_activity) <= 7 then 'active'
            when datediff(current_date(), last_activity) <= 30 then 'recent'
            when datediff(current_date(), last_activity) <= 90 then 'dormant'
            else 'inactive'
        end as user_segment,
        case
            when lifetime_cost >= 1000 then 'enterprise'
            when lifetime_cost >= 100 then 'business'
            when lifetime_cost >= 10 then 'pro'
            else 'free'
        end as tier,
        _gold_timestamp
    from with_keys
)

select * from enriched