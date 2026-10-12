# CareFlow --- Clinical Pathway Process Mining

## Project overview

CareFlow is a healthcare operations and process-analytics project. It
aims to help identify delays and repeated steps in Emergency Room (ER)
patient journeys by analysing timestamped hospital event logs.

**Current stage:** Week 1 setup and synthetic-data preparation. The CSV
sample has been prepared for testing. BigQuery upload and successful
execution of the local simulator must be confirmed separately.

## Work completed on 12 October 2026

-   Opened the `CAREFLOW` project folder in Visual Studio Code (VS
    Code).
-   Reviewed the project folder structure in the integrated terminal.
-   Identified the main project folders reported in the workspace:
    `airflow`, `dbt`, `data`, `simulator`, and `src`.
-   Identified project support files: `.gitignore`, `README.md`, and
    `requirements.txt`.
-   Checked the available Python command. `python3 --version` returned
    Python 3.14.2, while the `python`/`py` commands were not
    consistently recognised in the terminal.
-   Investigated running Python syntax checks and the simulator.
    Execution was blocked by a script-path / file-not-found error, so
    successful local generation has **not yet been confirmed**.
-   Prepared a separate synthetic sample file named `raw_ehr_events.csv`
    containing 753 event records for initial BigQuery and SQL practice.
-   Planned the next step: place the sample CSV in `data/` and upload it
    to BigQuery Sandbox, then continue with SQL analysis.
-   Identified that the Python simulator still needs to be verified and
    made runnable from the project folder.

## Project structure

The following folders and files were reported in the VS Code workspace.
Check the Explorer before committing to ensure the current files match
this list.

``` text
CAREFLOW/
├── airflow/
├── dbt/
├── data/
├── simulator/
├── src/
├── .gitignore
├── README.md
└── requirements.txt
```

Expected files to verify before running the simulator:

``` text
simulator/
├── simulate_ehr.py
└── load_to_bigquery.py
```

These two scripts should only be described as complete after confirming
that they exist and work in the local workspace.

## Sample data

`raw_ehr_events.csv` is synthetic demonstration data prepared separately
for this project. It contains 753 records with these columns:

-   `patient_id`
-   `event_name`
-   `timestamp`
-   `department`

The sample includes simulated repeated tests and returns to earlier
departments. It does not contain real patient data.

**Important:** The prepared sample CSV is not automatically stored in
this repository. Copy it into `data/raw_ehr_events.csv` before
committing it, if your team's repository rules allow committing
generated sample data. Confirm the file is present first.

## Next steps

1.  Confirm the files inside `simulator/` and fix the local Python
    command/path issue.
2.  Copy `raw_ehr_events.csv` into the project's `data/` folder.
3.  Upload the CSV to the `careflow` dataset in BigQuery Sandbox (if the
    dataset exists); do not enable billing just for this task.
4.  Verify the BigQuery table and run a simple row-count query.
5.  Continue SQL analysis of patient journeys, delays, repeated tests,
    and department loop-backs.
6.  Update this README as each step is actually completed.
7.  Commit and push the verified work to the agreed team repository.

## Git progress note

This README documents today's setup and troubleshooting work. A file
save is not the same as a Git commit, and a commit is not the same as a
push. Only record a task as completed after verifying it. Follow the
team's repository and review rules, and do not create multiple
repositories if the team has agreed to use one shared repository.

Suggested commit message:

``` text
docs: document CareFlow Week 1 setup and data preparation
```

## Privacy and safety

All hospital events used for development must be synthetic or properly
de-identified. Never commit real patient information, credentials, API
keys, service-account JSON files, or other secrets.
