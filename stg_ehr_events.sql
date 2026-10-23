with source as (
    select
        trim(patient_id) as case_id,
        trim(activity) as activity_raw,
        event_time,
        resource,
        department
    from {{ source('careflow', 'raw_ehr_events') }}
    where patient_id is not null and event_time is not null
),
cleaned as (
    select
        case_id,
        initcap(activity_raw) as activity_name,
        cast(event_time as timestamp) as event_ts,
        resource,
        department
    from source
)
select *
from cleaned
qualify row_number() over (
    partition by case_id, lower(activity_name), event_ts
    order by event_ts
) = 1
