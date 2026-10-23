{{ config(materialized='table') }}

with staged_events as (
    select
        case_id as `Case_ID`,
        activity_name as `Activity_Name`,
        event_ts as `Timestamp`,
        resource,
        department,
        case activity_name
            when 'Registration' then 1
            when 'Triage' then 2
            when 'Doctor Consultation' then 3
            when 'X-Ray' then 4
            when 'Discharge' then 5
            else 99
        end as activity_order
    from {{ ref('stg_ehr_events') }}
)

select
    `Case_ID`,
    `Activity_Name`,
    `Timestamp`,
    resource,
    department
from staged_events
order by `Case_ID`, `Timestamp`, activity_order
