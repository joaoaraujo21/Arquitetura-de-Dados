-- Model: stg_users
-- Camada Silver: Usuários limpos e deduplicados

{{ config(
    materialized = "incremental",
    unique_key = "user_id",
    incremental_strategy = "append"
) }}

with source as (

    select * from {{ source('raw', 'users') }}

),

deduplicated as (

    -- Remove duplicatas mantendo o registro mais recente
    select
        user_id,
        first_name,
        last_name,
        email,
        phone,
        age,
        country,
        created_at,
        updated_at,
        _ingest_timestamp
    from (
        select
            *,
            row_number() over (
                partition by user_id
                order by coalesce(updated_at, created_at) desc,
                         _ingest_timestamp desc
            ) as rn
        from source
    )
    where rn = 1

),

cleaned as (

    select
        user_id,
        initcap(trim(first_name)) as first_name,
        initcap(trim(last_name)) as last_name,
        lower(trim(email)) as email,
        regexp_replace(phone, '[^0-9]', '') as phone,
        cast(age as integer) as age,
        initcap(trim(country)) as country,
        cast(created_at as timestamp) as created_at,
        cast(updated_at as timestamp) as updated_at,
        _ingest_timestamp,
        current_timestamp() as _silver_timestamp
    from deduplicated

)

select * from cleaned