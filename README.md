# CareFlow: Clinical Pathway Process Mining

This Week 1 starter project creates mock raw EHR logs and prepares the initial BigQuery and dbt staging layer for downstream process mining. The goal is to capture messy operational behavior before any modeling or dashboard work begins.

## File guide
- `requirements.txt`: Pins the minimum Python package versions required for simulation, BigQuery loading, and dbt setup.
- `simulator/simulate_ehr.py`: Generates reproducible mock patient event data with realistic delays, loop-backs, and data quality noise.
- `simulator/load_to_bigquery.py`: Creates the `careflow` dataset and loads the raw CSV into BigQuery using Application Default Credentials.
- `careflow_dbt/dbt_project.yml`: Defines the dbt project metadata and points dbt at the `careflow` profile.
- `careflow_dbt/models/sources.yml`: Declares the raw BigQuery source table for the staging layer.
- `careflow_dbt/models/staging/stg_ehr_events.sql`: Cleans the raw events, standardizes field names, and de-dups by patient and event signature.
- `careflow_dbt/models/staging/schema.yml`: Adds the validation tests for nulls and allowed activity names.
- `careflow_dbt/models/marts/event_log.sql`: Creates the five-column process-mining event log from the staging model. Timestamp ties use the expected activity order.
- `careflow_dbt/models/marts/schema.yml`: Checks required event-log values and restricts activity names to the simulator's supported activities.
- `careflow_dbt/tests/event_log_chronological.sql`: Checks case event timestamps for chronological regressions with `LAG`.
- `careflow_dbt/tests/event_log_case_boundaries.sql`: Checks that each case begins with Registration and ends with Discharge.
- `process_mining/discover_as_is.py`: Reads the BigQuery event log with ADC and discovers frequency/performance DFGs and an Inductive Miner model. It also prints case/variant/loop-back metrics and exports DFG edges.

## Assumption
The workspace root is the project root, and all commands below are run from `C:\Users\Lenovo\OneDrive\Desktop\Careflow`.

## Week 1 run order
1. `python -m venv .venv`
2. `.\.venv\Scripts\Activate.ps1`
3. `python -m pip install --upgrade pip`
4. `python -m pip install -r requirements.txt`
5. `gcloud auth application-default login`
6. `python simulator/simulate_ehr.py --patients 5000`
7. `python simulator/load_to_bigquery.py`
8. `dbt debug --project-dir careflow_dbt --profiles-dir ~/.dbt`
9. `dbt run --project-dir careflow_dbt --profiles-dir ~/.dbt`
10. `dbt test --project-dir careflow_dbt --profiles-dir ~/.dbt`

## profiles.yml location
Create the file at `~/.dbt/profiles.yml` on Windows, which usually expands to `C:\Users\<your-user>\.dbt\profiles.yml`.

```yaml
careflow:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: care-flow-12345
      dataset: careflow
      threads: 4
      timeout_seconds: 300
      location: US
      priority: interactive
```

The file is intentionally kept out of version control via `.gitignore`.

## BigQuery verification SQL
```sql
SELECT COUNT(*) AS raw_row_count FROM `care-flow-12345.careflow.raw_ehr_events`;

SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT patient_id) AS unique_patients,
  COUNT(*) - COUNT(DISTINCT patient_id) AS duplicate_risk
FROM `care-flow-12345.careflow.raw_ehr_events`;

SELECT
  COUNT(DISTINCT patient_id) AS patients_with_xray_then_triage
FROM (
  SELECT patient_id
  FROM `care-flow-12345.careflow.raw_ehr_events`
  WHERE activity IN ('X-Ray', 'Triage')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY event_time) > 0
);
```

The exact dbt staging SQL and tests are implemented in the project files under `careflow_dbt/`.

## Week 2 run order

Run these commands from the project root after Week 1 is set up. If Application Default Credentials are not already configured, run `gcloud auth application-default login` and complete the browser sign-in before running dbt or process discovery. No credentials are stored in the project.

1. `python -m pip install -r requirements.txt`
2. `dbt run --project-dir careflow_dbt --profiles-dir "$HOME\.dbt" --select path:marts`
3. `dbt test --project-dir careflow_dbt --profiles-dir "$HOME\.dbt"`
4. `python process_mining/discover_as_is.py`

The dbt model builds `careflow.event_log` in BigQuery project `care-flow-12345`. PM4Py reads it using Application Default Credentials. Graphviz's Python package is installed by `requirements.txt`; the Graphviz system application must also be installed and available on `PATH` (`dot -V` checks it).

`process_mining/discover_as_is.py` creates `outputs/as_is_dfg_frequency.png`, `outputs/as_is_dfg_performance.png`, `outputs/as_is_dfg_top_variants.png`, `outputs/as_is_inductive_miner.png`, and `outputs/dfg_edges.csv`. The loop-back rate is reported among cases with an X-Ray, matching the simulator's 40% loop-back behavior.

## Week 3: Bottleneck analysis and Power BI

The temporary Week 3 analysis script is at the project root because the `src` folder is currently a OneDrive placeholder that cannot accept new files. Run it from any folder with:

```powershell
python bottleneck_analysis.py
```

It reads `data\raw_ehr_events_timestamp_filled.csv` by default and writes five new files to `local_output\`. It uses only Python's standard library. The script sorts by patient and timestamp, calculates elapsed time only between consecutive timestamped events for the same patient, and leaves the original CSV and Week 2 reports unchanged.

| Generated file | Contents |
|---|---|
| `local_output\bottleneck_sorted_events.csv` | All source events sorted by patient and timestamp |
| `local_output\bottleneck_transitions.csv` | Within-patient transition details, elapsed minutes, and departments |
| `local_output\bottleneck_transition_summary.csv` | Transition counts and average, median, minimum, and maximum elapsed times |
| `local_output\bottleneck_department_summary.csv` | Event counts and incoming transition wait-time summaries by department |
| `local_output\bottleneck_dashboard_metrics.csv` | One-row KPI summary and data-quality counts |

### Build the Power BI report

1. In Power BI Desktop, choose **Home > Get data > Text/CSV** and load each of the five generated files.
2. Check types: elapsed-minute fields should be Decimal Number, timestamps should be Date/Time, and patient, activity, and department fields should be Text.
3. Add **Card** visuals for `total_patients`, `total_events`, `average_elapsed_minutes`, and `slowest_transition_average_minutes` from `bottleneck_dashboard_metrics`. Add a card for `slowest_transition` if desired.
4. Add a **Clustered bar chart** with `transition_name` on the Y-axis and `elapsed_minutes` on the X-axis from `bottleneck_transitions`. Change the X-axis aggregation to **Average**, sort descending by average, and optionally apply a Top N visual filter.
5. Add a department **Clustered bar chart** with `to_department` on the Y-axis and the average of `elapsed_minutes` on the X-axis. This attributes each wait to the department of the next activity.
6. Add slicers using `to_department`, `from_activity`, `to_activity`, and `to_timestamp` from `bottleneck_transitions`. Add `patient_id` for individual-case exploration.
7. Add a **Table** using `transition_name`, `transition_count`, `average_elapsed_minutes`, `median_elapsed_minutes`, and `maximum_elapsed_minutes` from `bottleneck_transition_summary`.

The KPI cards are dataset-wide values from a one-row summary and will not change with transition slicers. The transition and department charts do respond to those slicers.

### Week 2 verification checklist

Run these queries in BigQuery after the dbt run and tests:

```sql
-- No repeated case/timestamp/activity signatures.
SELECT `Case_ID`, `Timestamp`, `Activity_Name`, COUNT(*) AS row_count
FROM `care-flow-12345.careflow.event_log`
GROUP BY `Case_ID`, `Timestamp`, `Activity_Name`
HAVING COUNT(*) > 1;

-- No timestamp is earlier than the preceding event within a case.
WITH ordered AS (
  SELECT
    `Case_ID`,
    `Timestamp`,
    LAG(`Timestamp`) OVER (
      PARTITION BY `Case_ID`
      ORDER BY `Timestamp`,
        CASE `Activity_Name`
          WHEN 'Registration' THEN 1
          WHEN 'Triage' THEN 2
          WHEN 'Doctor Consultation' THEN 3
          WHEN 'X-Ray' THEN 4
          WHEN 'Discharge' THEN 5
          ELSE 99
        END
    ) AS previous_timestamp
  FROM `care-flow-12345.careflow.event_log`
)
SELECT *
FROM ordered
WHERE previous_timestamp > `Timestamp`;

-- Event-log and staging row counts should be identical.
SELECT
  (SELECT COUNT(*) FROM `care-flow-12345.careflow.event_log`) AS event_log_rows,
  (SELECT COUNT(*) FROM `care-flow-12345.careflow.stg_ehr_events`) AS staging_rows;
```

Each SQL check should return no violation rows (and the count query should return matching counts). In the PM4Py frequency DFG, look for the visible `X-Ray -> Triage` loop-back arrow; the printed rate among X-Ray cases should be close to 40% for the simulator data.

## Week 4: Conformance checking and Power BI

Week 4 reads the existing cleaned local event log at `local_output\event_log.csv`. It does not change the source data or any Week 1–3 output files. The activity names in that log differ from the original pathway labels, so the rules are stored separately in `process_mining\conformance_rules.json`:

| Journey step | Activity name in this event log |
|---|---|
| Registration | Patient Arrived |
| Triage | Triage Completed |
| Doctor Consultation | Doctor Assessment |
| Optional X-Ray | Radiology Ordered, then Radiology Result Available |
| Treatment | Medication Given |
| Discharge | Discharged |

`Lab Test Ordered` and `Lab Result Available` are allowed supporting activities. `Admitted` is unexpected under the confirmed rules. If an X-Ray is started, both radiology activities must occur in order. Treatment is represented by `Medication Given`; a patient without it is reported as missing the required Treatment step.

### Run the checker

From the project root:

```powershell
python3 -m unittest discover -s tests
python3 process_mining\conformance_check.py
```

The commands use `python3`, which is available in this Windows workspace. If you have activated a virtual environment that provides `python`, you can use that command instead. The checker uses only the Python standard library. It sorts events for each patient by timestamp and reports missing required steps, incomplete optional X-Rays, wrong order, backtracking, unexpected activities, and repeated activities. Supporting lab activities are not unexpected, but repeated lab activities are still reported as repeats.

The rules file, checker, and focused tests are `process_mining\conformance_rules.json`, `process_mining\conformance_check.py`, and `tests\test_conformance_check.py`. Two new files are written to `local_output\`:

| File | Contents |
|---|---|
| `conformance_report.csv` | One row per patient with the actual and expected journeys, compliance flag, deviation types, and reason |
| `deviations.csv` | One row per detected problem, including the activity and its position in that patient's journey |

You can change the input or destination without editing the script:

```powershell
python process_mining\conformance_check.py --input "local_output\event_log.csv" --output-dir "local_output"
```

### Build the Week 4 Power BI pages

1. In Power BI Desktop, use **Home > Get data > Text/CSV** to load `local_output\conformance_report.csv`, `local_output\deviations.csv`, and the existing `local_output\event_log.csv`. The existing event log provides the timestamped event rows for a detailed patient timeline.
2. In Model view, relate `conformance_report[patient_id]` one-to-many to `deviations[patient_id]` and to `event_log[Case_ID]`. Keep the relationships single-direction from the patient report to the detail tables.
3. Use these measures (the exported `is_compliant` values are the text `true` and `false`):

```DAX
Total Patients =
    DISTINCTCOUNT(conformance_report[patient_id])

Compliant Patients =
    CALCULATE(
        [Total Patients],
        conformance_report[is_compliant] = "true"
    )

Non-Compliant Patients =
    CALCULATE(
        [Total Patients],
        conformance_report[is_compliant] = "false"
    )

% Compliant =
    DIVIDE([Compliant Patients], [Total Patients], 0)

% Non-Compliant =
    DIVIDE([Non-Compliant Patients], [Total Patients], 0)

Deviation Rows =
    COUNTROWS(deviations)
```

Format both percentage measures as **Percentage**. Add cards for the two patient counts and percentages.

4. Add a patient ID slicer from `conformance_report[patient_id]`. Add a **Patient Journey** page with an `actual_journey` card and a table using `event_log[Timestamp]`, `event_log[Activity_Name]`, and `event_log[department]`, sorted by timestamp ascending. Add a second table using the selected patient's rows from `deviations` so the reasons are visible.
5. Add a bar chart using `deviations[deviation_type]` as the axis and **Deviation Rows** as the value. Add `deviations[activity]` as the next level in the axis hierarchy to drill from problem type into activity. Optionally apply a Top N filter to show the most frequent activities.
6. To drill through from a patient, create a detail page with `conformance_report[patient_id]` in the **Drill-through** field well. Then right-click a patient in a report visual and choose that page.
7. Use a consistent palette: green for compliant, red for non-compliant, and neutral blue/gray for context. Apply conditional formatting to compliance status, align visuals to a grid, use clear titles, and keep slicers together at the top or left.

The current Week 3 data has no age or gender fields and no dedicated doctor field, so patient-demographic and doctor slicers cannot be built from it. The current cleaned CSV also has no `resource` field. No synthetic patient or doctor details are created. The existing `.pbix` is not modified.
