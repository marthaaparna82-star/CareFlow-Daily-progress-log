#!/usr/bin/env python3
"""Analyze patient-level activity delays and export Power BI-ready CSV files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw_ehr_events_timestamp_filled.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "local_output"
REQUIRED_COLUMNS = ("patient_id", "event_name", "timestamp", "department")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp and normalize timezone-aware values to UTC."""
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def read_events(input_path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Read the event log, retain source values, and count data-quality issues."""
    with input_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"The input CSV is empty: {input_path}")

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"The input CSV is missing required columns: {', '.join(missing_columns)}"
            )

        events: list[dict[str, Any]] = []
        quality = {
            "invalid_timestamp_events": 0,
            "missing_patient_id_events": 0,
            "missing_event_name_events": 0,
            "missing_department_events": 0,
        }

        for row_number, row in enumerate(reader, start=2):
            event: dict[str, Any] = {
                column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS
            }
            event["_row_number"] = row_number
            event["_timestamp"] = None

            if not event["patient_id"]:
                quality["missing_patient_id_events"] += 1
            if not event["event_name"]:
                quality["missing_event_name_events"] += 1
            if not event["department"]:
                quality["missing_department_events"] += 1

            if event["timestamp"]:
                try:
                    event["_timestamp"] = parse_timestamp(event["timestamp"])
                except ValueError:
                    quality["invalid_timestamp_events"] += 1
            else:
                quality["invalid_timestamp_events"] += 1

            events.append(event)

    return events, quality


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    """Write rows with a stable column order and UTF-8 encoding."""
    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze(events: list[dict[str, Any]], quality: dict[str, int]) -> dict[str, Any]:
    """Sort events and calculate gaps only between consecutive events for one patient."""
    sorted_events = sorted(
        events,
        key=lambda event: (
            event["patient_id"],
            event["_timestamp"] is None,
            event["_timestamp"] or datetime.max,
            event["_row_number"],
        ),
    )

    valid_events = [
        event
        for event in sorted_events
        if event["_timestamp"] is not None
        and event["patient_id"]
        and event["event_name"]
    ]

    events_by_patient: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in valid_events:
        events_by_patient[event["patient_id"]].append(event)

    transitions: list[dict[str, Any]] = []
    negative_duration_count = 0
    for patient_id, patient_events in events_by_patient.items():
        for previous, current in zip(patient_events, patient_events[1:]):
            elapsed_minutes = (
                current["_timestamp"] - previous["_timestamp"]
            ).total_seconds() / 60
            if elapsed_minutes < 0:
                negative_duration_count += 1
                continue

            transition_name = f"{previous['event_name']} -> {current['event_name']}"
            transitions.append(
                {
                    "patient_id": patient_id,
                    "from_activity": previous["event_name"],
                    "to_activity": current["event_name"],
                    "transition_name": transition_name,
                    "from_timestamp": previous["timestamp"],
                    "to_timestamp": current["timestamp"],
                    "elapsed_minutes": round(elapsed_minutes, 2),
                    "from_department": previous["department"],
                    "to_department": current["department"],
                }
            )

    grouped_transitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_departments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for transition in transitions:
        grouped_transitions[transition["transition_name"]].append(transition)
        if transition["to_department"]:
            grouped_departments[transition["to_department"]].append(transition)

    transition_summaries = []
    for transition_name, grouped in grouped_transitions.items():
        durations = [row["elapsed_minutes"] for row in grouped]
        transition_summaries.append(
            {
                "transition_name": transition_name,
                "from_activity": grouped[0]["from_activity"],
                "to_activity": grouped[0]["to_activity"],
                "transition_count": len(grouped),
                "patient_count": len({row["patient_id"] for row in grouped}),
                "average_elapsed_minutes": round(mean(durations), 2),
                "median_elapsed_minutes": round(median(durations), 2),
                "minimum_elapsed_minutes": round(min(durations), 2),
                "maximum_elapsed_minutes": round(max(durations), 2),
            }
        )
    transition_summaries.sort(
        key=lambda row: (
            -row["average_elapsed_minutes"],
            -row["transition_count"],
            row["transition_name"],
        )
    )
    for rank, summary in enumerate(transition_summaries, start=1):
        summary["rank_by_average_elapsed"] = rank

    event_counts_by_department: dict[str, int] = defaultdict(int)
    for event in valid_events:
        if event["department"]:
            event_counts_by_department[event["department"]] += 1

    department_summaries = []
    for department in sorted(set(event_counts_by_department) | set(grouped_departments)):
        grouped = grouped_departments[department]
        durations = [row["elapsed_minutes"] for row in grouped]
        department_summaries.append(
            {
                "department": department,
                "valid_event_count": event_counts_by_department[department],
                "incoming_transition_count": len(grouped),
                "average_incoming_elapsed_minutes": round(mean(durations), 2) if durations else "",
                "median_incoming_elapsed_minutes": round(median(durations), 2) if durations else "",
                "maximum_incoming_elapsed_minutes": round(max(durations), 2) if durations else "",
                "department_assignment": "Department of the next activity in each transition",
            }
        )

    patient_count = len({event["patient_id"] for event in events if event["patient_id"]})
    valid_timestamp_event_count = sum(event["_timestamp"] is not None for event in events)
    elapsed_values = [row["elapsed_minutes"] for row in transitions]
    slowest_transition = transition_summaries[0] if transition_summaries else None
    metrics = {
        "total_patients": patient_count,
        "total_events": len(events),
        "events_with_valid_timestamps": valid_timestamp_event_count,
        "events_used_for_transitions": len(valid_events),
        "patients_with_transitions": len(events_by_patient),
        "transition_count": len(transitions),
        "average_elapsed_minutes": round(mean(elapsed_values), 2) if elapsed_values else "",
        "median_elapsed_minutes": round(median(elapsed_values), 2) if elapsed_values else "",
        "slowest_transition": slowest_transition["transition_name"] if slowest_transition else "",
        "slowest_transition_average_minutes": (
            slowest_transition["average_elapsed_minutes"] if slowest_transition else ""
        ),
        "negative_duration_transitions_excluded": negative_duration_count,
        **quality,
    }

    sorted_event_rows = [
        {column: event[column] for column in REQUIRED_COLUMNS} for event in sorted_events
    ]
    return {
        "sorted_events": sorted_event_rows,
        "transitions": transitions,
        "transition_summaries": transition_summaries,
        "department_summaries": department_summaries,
        "metrics": metrics,
    }


def export_results(results: dict[str, Any], output_dir: Path) -> None:
    """Export new Week 3 files without changing the source CSV or older reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir / "bottleneck_sorted_events.csv",
        REQUIRED_COLUMNS,
        results["sorted_events"],
    )
    write_csv(
        output_dir / "bottleneck_transitions.csv",
        (
            "patient_id",
            "from_activity",
            "to_activity",
            "transition_name",
            "from_timestamp",
            "to_timestamp",
            "elapsed_minutes",
            "from_department",
            "to_department",
        ),
        results["transitions"],
    )
    write_csv(
        output_dir / "bottleneck_transition_summary.csv",
        (
            "rank_by_average_elapsed",
            "transition_name",
            "from_activity",
            "to_activity",
            "transition_count",
            "patient_count",
            "average_elapsed_minutes",
            "median_elapsed_minutes",
            "minimum_elapsed_minutes",
            "maximum_elapsed_minutes",
        ),
        results["transition_summaries"],
    )
    write_csv(
        output_dir / "bottleneck_department_summary.csv",
        (
            "department",
            "valid_event_count",
            "incoming_transition_count",
            "average_incoming_elapsed_minutes",
            "median_incoming_elapsed_minutes",
            "maximum_incoming_elapsed_minutes",
            "department_assignment",
        ),
        results["department_summaries"],
    )
    write_csv(
        output_dir / "bottleneck_dashboard_metrics.csv",
        tuple(results["metrics"].keys()),
        [results["metrics"]],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze CareFlow patient-level event delays and export Power BI CSVs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input event-log CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Folder for generated CSV files (default: {DEFAULT_OUTPUT_DIR})",
    )
    arguments = parser.parse_args()

    if not arguments.input.is_file():
        raise FileNotFoundError(f"Input CSV was not found: {arguments.input}")

    events, quality = read_events(arguments.input)
    if not events:
        raise ValueError(f"The input CSV contains no event rows: {arguments.input}")

    results = analyze(events, quality)
    export_results(results, arguments.output_dir)

    metrics = results["metrics"]
    print(f"Input: {arguments.input}")
    print(f"Output folder: {arguments.output_dir}")
    print(f"Total patients: {metrics['total_patients']}")
    print(f"Total events: {metrics['total_events']}")
    print(f"Valid timestamp events: {metrics['events_with_valid_timestamps']}")
    print(f"Transitions analyzed: {metrics['transition_count']}")
    print(f"Average elapsed time: {metrics['average_elapsed_minutes']} minutes")
    print(
        "Slowest transition by average: "
        f"{metrics['slowest_transition']} "
        f"({metrics['slowest_transition_average_minutes']} minutes)"
    )
    print(
        "Data-quality exclusions: "
        f"{metrics['invalid_timestamp_events']} invalid timestamps, "
        f"{metrics['missing_patient_id_events']} missing patient IDs, "
        f"{metrics['missing_event_name_events']} missing event names, "
        f"{metrics['missing_department_events']} missing departments"
    )
    print("Created 5 Power BI-ready CSV files.")


if __name__ == "__main__":
    main()
