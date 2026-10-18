SELECT
  patient_id,
  event_name,
  department,
  timestamp,
  ROW_NUMBER() OVER (
    PARTITION BY patient_id
    ORDER BY timestamp
  ) AS event_sequence
FROM `care-flow-123456.care.raw_ehr_events`
ORDER BY patient_id, timestamp;
