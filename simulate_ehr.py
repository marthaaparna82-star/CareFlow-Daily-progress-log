#!/usr/bin/env python3
"""Generate a realistic raw EHR event log for CareFlow Week 1.

This script creates a reproducible CSV of pseudo-clinical patient events with
intentional operational delays, quality issues, and a loop-back pattern for dbt
cleaning exercises.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "raw_ehr_events.csv"

WORKFLOW = [
    "Registration",
    "Triage",
    "Doctor Consultation",
    "X-Ray",
    "Doctor Consultation",
    "Discharge",
]


def sample_lognormal(mean_minutes: float, sigma: float) -> float:
    """Sample a positive delay from a log-normal distribution."""
    mu = math.log(mean_minutes) - 0.5 * sigma ** 2
    return max(1.0, float(np.random.lognormal(mu, sigma)))


def format_patient_id(index: int) -> str:
    """Format a patient id as P00001 style."""
    return f"P{index:05d}"


def generate_patient_events(patient_id: str, rng: np.random.Generator, patient_idx: int) -> list[dict]:
    """Create a single patient's clinical event timeline."""
    arrival_time = pd.Timestamp("2024-01-01") + pd.Timedelta(
        days=int(rng.integers(1, 31)),
        hours=int(rng.integers(0, 24)),
        minutes=int(rng.integers(0, 60)),
        seconds=int(rng.integers(0, 60)),
    )
    arrival_hour = arrival_time.hour

    events: list[dict] = []
    current_time = arrival_time
    departments = {
        "Registration": "Front Desk",
        "Triage": "Emergency",
        "Doctor Consultation": "Emergency",
        "X-Ray": "Radiology",
        "Discharge": "Discharge",
    }

    def add_event(activity: str, resource: str, dept: str, event_ts: pd.Timestamp):
        events.append(
            {
                "patient_id": patient_id,
                "activity": activity,
                "event_time": event_ts,
                "resource": resource,
                "department": dept,
            }
        )

    # Registration
    add_event(
        "Registration",
        f"F{rng.integers(100, 999)}",
        departments["Registration"],
        current_time,
    )
    current_time += pd.Timedelta(minutes=sample_lognormal(8.0, 0.7))

    # Triage
    add_event(
        "Triage",
        f"RN{rng.integers(10, 99)}",
        departments["Triage"],
        current_time,
    )
    triage_to_doc_mean = 40.0 if arrival_hour >= 17 else 15.0
    current_time += pd.Timedelta(minutes=sample_lognormal(triage_to_doc_mean, 0.6))

    # First consultation
    add_event(
        "Doctor Consultation",
        f"MD{rng.integers(10, 99)}",
        departments["Doctor Consultation"],
        current_time,
    )

    needs_xray = rng.random() < 0.60
    if needs_xray:
        current_time += pd.Timedelta(minutes=sample_lognormal(18.0, 0.7))
        add_event(
            "X-Ray",
            f"XR{rng.integers(100, 999)}",
            departments["X-Ray"],
            current_time,
        )

        if rng.random() < 0.40:
            # Operational inefficiency: missing paperwork sends patient back to triage.
            current_time += pd.Timedelta(minutes=sample_lognormal(22.0, 0.75))
            add_event(
                "Triage",
                f"RN{rng.integers(10, 99)}",
                departments["Triage"],
                current_time,
            )
            current_time += pd.Timedelta(minutes=sample_lognormal(16.0 if arrival_hour < 17 else 40.0, 0.6))
            add_event(
                "Doctor Consultation",
                f"MD{rng.integers(10, 99)}",
                departments["Doctor Consultation"],
                current_time,
            )
        else:
            current_time += pd.Timedelta(minutes=sample_lognormal(22.0, 0.7))
            add_event(
                "Doctor Consultation",
                f"MD{rng.integers(10, 99)}",
                departments["Doctor Consultation"],
                current_time,
            )

    current_time += pd.Timedelta(minutes=sample_lognormal(10.0, 0.7))
    add_event(
        "Discharge",
        f"DC{rng.integers(100, 999)}",
        departments["Discharge"],
        current_time,
    )

    return events


def inject_data_quality_issues(df: pd.DataFrame, duplicate_target_pct: float = 0.01, lowercase_target_pct: float = 0.03, null_time_target_pct: float = 0.005) -> tuple[pd.DataFrame, int, int, int]:
    """Add known data quality issues and return counts for the summary output."""
    rng = np.random.default_rng(SEED + 1)

    duplicate_count = max(1, int(round(len(df) * duplicate_target_pct)))
    lowercase_count = max(1, int(round(len(df) * lowercase_target_pct)))
    null_time_count = max(1, int(round(len(df) * null_time_target_pct)))

    duplicate_idx = rng.choice(len(df), size=duplicate_count, replace=False)
    duplicate_rows = df.iloc[duplicate_idx].copy()
    df = pd.concat([df, duplicate_rows], ignore_index=True)

    lowercase_idx = rng.choice(len(df), size=lowercase_count, replace=False)
    df.loc[lowercase_idx, "activity"] = df.loc[lowercase_idx, "activity"].str.lower()

    null_idx = rng.choice(len(df), size=null_time_count, replace=False)
    df.loc[null_idx, "event_time"] = pd.NaT

    return df, duplicate_count, lowercase_count, null_time_count


def calculate_loopback_rate(df: pd.DataFrame) -> float:
    """Measure the proportion of X-Ray patients who loop back through Triage."""
    patient_rows = df.copy()
    patient_rows["activity_norm"] = patient_rows["activity"].fillna("").astype(str).str.strip().str.lower()
    patient_rows["event_time"] = pd.to_datetime(patient_rows["event_time"], errors="coerce")

    xray_patients = set(
        patient_rows.loc[patient_rows["activity_norm"] == "x-ray", "patient_id"].tolist()
    )
    loopback_patients = set()

    for patient_id, patient_df in patient_rows.groupby("patient_id"):
        patient_df = patient_df.sort_values("event_time", na_position="last")
        activity_seq = patient_df["activity_norm"].fillna("").tolist()
        for idx in range(len(activity_seq) - 1):
            if activity_seq[idx] == "x-ray" and activity_seq[idx + 1] == "triage":
                loopback_patients.add(patient_id)
                break

    xray_count = len(xray_patients)
    if xray_count == 0:
        return 0.0
    return len(loopback_patients & xray_patients) / xray_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mock EHR patient flow logs for CareFlow.")
    parser.add_argument("--patients", type=int, default=5000, help="Number of patients to generate.")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)
    all_rows: list[dict] = []
    for patient_index in range(1, args.patients + 1):
        patient_id = format_patient_id(patient_index)
        patient_events = generate_patient_events(patient_id, rng, patient_index)
        all_rows.extend(patient_events)

    df = pd.DataFrame(all_rows)
    df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    df, duplicates_added, lowercase_added, nulls_added = inject_data_quality_issues(df)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    unique_patients = df["patient_id"].nunique()
    loopback_rate = calculate_loopback_rate(df)

    print(f"CSV saved to: {OUTPUT_PATH}")
    print(f"Row count: {len(df)}")
    print(f"Unique patients: {unique_patients}")
    print(f"Duplicates added: {duplicates_added}")
    print(f"Null event_time rows added: {nulls_added}")
    print(f"Actual loop-back rate: {loopback_rate:.2%}")


if __name__ == "__main__":
    main()
