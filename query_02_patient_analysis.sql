SELECT
  patient_id,
  MIN(timestamp) AS first_event,
  MAX(timestamp) AS last_event,
  TIMESTAMP_DIFF(
    MAX(timestamp),
    MIN(timestamp),
    MINUTE
  ) AS total_minutes
FROM `care-flow-123456.care.raw_ehr_events`
GROUP BY patient_id
ORDER BY total_minutes DESC
LIMIT 10;
