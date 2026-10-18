SELECT
  COUNT(*) AS total_events,
  COUNT(DISTINCT patient_id) AS total_patients,
  COUNTIF(timestamp IS NULL) AS missing_timestamps
FROM `care-flow-123456.care.raw_ehr_events`;
