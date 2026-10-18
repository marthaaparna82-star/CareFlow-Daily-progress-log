SELECT
  department,
  COUNT(*) AS total_events,
  COUNT(DISTINCT patient_id) AS unique_patients
FROM `care-flow-123456.care.raw_ehr_events`
GROUP BY department
ORDER BY total_events DESC;

