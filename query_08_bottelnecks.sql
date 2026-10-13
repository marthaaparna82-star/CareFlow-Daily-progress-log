WITH event_gaps AS (
  SELECT
    patient_id,
    event_name,
    department,
    timestamp AS current_event_time,
    LAG(event_name) OVER (
      PARTITION BY patient_id
      ORDER BY timestamp, event_name
    ) AS previous_event,
    LAG(timestamp) OVER (
      PARTITION BY patient_id
      ORDER BY timestamp, event_name
    ) AS previous_event_time
  FROM `care-flow-123456.care.raw_ehr_events`
)
SELECT
  patient_id,
  previous_event,
  event_name AS current_event,
  department,
  previous_event_time,
  current_event_time,
  TIMESTAMP_DIFF(
    current_event_time,
    previous_event_time,
    MINUTE
  ) AS delay_minutes
FROM event_gaps
WHERE previous_event_time IS NOT NULL
ORDER BY delay_minutes DESC
LIMIT 20;
