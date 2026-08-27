-- Test: email deve ser único
select
    email,
    count(*) as duplicates
from {{ ref('stg_users') }}
where email is not null
group by email
having count(*) > 1