-- Test: user_id não pode ser nulo
select *
from {{ ref('stg_users') }}
where user_id is null