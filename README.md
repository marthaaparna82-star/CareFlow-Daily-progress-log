# CareFlow-Daily-progress-log
- Created a BigQuery dataset and stored 13 synthetic EHR event records.  Verified the data using SQL and downloaded it as a CSV file.  Started the initial data preparation for the CareFlow project.

Week 1: EHR Simulation and Event Log Engineering

**Date:** 10 October 2026

**Project Domain:** Healthcare Operations & Process Analytics

Today's Objective
Set up the initial synthetic Electronic Health Record (EHR) event data in BigQuery as the foundation for CareFlow's patient journey analysis.

Tasks Completed
- Created a BigQuery dataset named `careflow_dataset`.
- Created and saved the initial `ehr_events` table.
- Generated an initial sample of 13 synthetic patient event records across 3 fictional patients.
- Included patient IDs, event names, and event timestamps.
- Executed a SQL query to verify the saved records.
- Exported the event data as a CSV file for use in subsequent data processing.

Tools Used
- Google BigQuery Sandbox
- SQL
- CSV

Current Status
**In Progress** — Initial event data creation and storage completed.

Next Steps
- Expand the synthetic EHR dataset with more patient journeys and timestamped events.
- Develop the EHR event simulation.
- Prepare event logs for patient waiting-time and Emergency Department length-of-stay analysis.

**Note:** All patient records are synthetic and created for educational project development.
