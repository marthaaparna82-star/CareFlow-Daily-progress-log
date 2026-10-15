#!/usr/bin/env python3
"""Load the raw CareFlow CSV into Google BigQuery.

This script creates the careflow dataset if needed and loads the CSV into the
raw_ehr_events table using Application Default Credentials.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "care-flow-12345"
DATASET_ID = "careflow"
TABLE_ID = "raw_ehr_events"
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_ehr_events.csv"


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)

    dataset_ref = client.dataset(DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)

    df = pd.read_csv(CSV_PATH)
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")

    table_ref = client.dataset(DATASET_ID).table(TABLE_ID)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("patient_id", "STRING"),
            bigquery.SchemaField("activity", "STRING"),
            bigquery.SchemaField("event_time", "TIMESTAMP"),
            bigquery.SchemaField("resource", "STRING"),
            bigquery.SchemaField("department", "STRING"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()

    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows into {PROJECT_ID}.{DATASET_ID}.{TABLE_ID}")


if __name__ == "__main__":
    main()
