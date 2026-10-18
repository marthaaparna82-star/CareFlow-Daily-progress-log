SELECT
  patient_id,
  event_name,
  department,
  COUNT(*) AS repeat_count,
  MIN(timestamp) AS first_occurrence,
  MAX(timestamp) AS last_occurrence
FROM `care-flow-123456.care.raw_ehr_events`
GROUP BY
  patient_id,
  event_name,
  department
HAVING COUNT(*) > 1
ORDER BY repeat_count DESC, patient_id;
