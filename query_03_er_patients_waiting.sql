WITH patient_times AS (
  SELECT
    patient_id,
    MIN(IF(
      event_name = 'Patient Arrived',
      timestamp, NULL
    )) AS arrival_time,
    MIN(IF(
      event_name = 'Triage Completed',
      timestamp, NULL
    )) AS triage_time
  FROM `care-flow-123456.care.raw_ehr_events`
  GROUP BY patient_id
)
SELECT
  patient_id,
  arrival_time,
  triage_time,
  TIMESTAMP_DIFF(
    triage_time,
    arrival_time,
    MINUTE
  ) AS waiting_minutes
FROM patient_times
WHERE arrival_time IS NOT NULL
  AND triage_time IS NOT NULL
  AND triage_time >= arrival_time
ORDER BY waiting_minutes DESC;
