#!/usr/bin/env python3
"""Discover and export CareFlow's As-Is process from the dbt event log."""

from __future__ import annotations

import csv
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd
import pm4py
from google.cloud import bigquery

PROJECT_ID = "care-flow-12345"
DATASET_ID = "careflow"
TABLE_ID = "event_log"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"

ACTIVITY_ORDER = {
    "Registration": 1,
    "Triage": 2,
    "Doctor Consultation": 3,
    "X-Ray": 4,
    "Discharge": 5,
}


def require_graphviz() -> None:
    """Stop early with installation guidance if Graphviz's dot executable is missing."""
    if shutil.which("dot") is None:
        raise SystemExit(
            "Graphviz was not found: the 'dot' executable is required to render process maps. "
            "Install it with `winget install --id Graphviz.Graphviz -e`, then restart the "
            "terminal and confirm `dot -V` works."
        )


def order_events(
    frame: pd.DataFrame,
    case_column: str,
    activity_column: str,
    timestamp_column: str,
) -> pd.DataFrame:
    """Sort by time and apply the dbt model's deterministic activity tie-break."""
    ordered = frame.copy()
    ordered["_activity_order"] = ordered[activity_column].map(ACTIVITY_ORDER).fillna(99)
    return ordered.sort_values(
        [case_column, timestamp_column, "_activity_order"],
        kind="mergesort",
    ).drop(columns="_activity_order").reset_index(drop=True)


def get_case_variants(frame: pd.DataFrame) -> Counter[tuple[str, ...]]:
    """Return activity-sequence frequencies from an already ordered PM4Py dataframe."""
    case_variants = frame.groupby("case:concept:name", sort=False)["concept:name"].agg(tuple)
    return Counter(case_variants.tolist())


def write_dfg_edges(dfg: dict[tuple[str, str], int], output_path: Path) -> None:
    """Write frequency DFG edges in a small, spreadsheet-friendly CSV."""
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["source_activity", "target_activity", "frequency"])
        for (source, target), frequency in sorted(
            dfg.items(),
            key=lambda edge: (-edge[1], edge[0][0], edge[0][1]),
        ):
            writer.writerow([source, target, frequency])


def main() -> None:
    require_graphviz()

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        select `Case_ID`, `Activity_Name`, `Timestamp`, resource, department
        from `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        order by
            `Case_ID`,
            `Timestamp`,
            case `Activity_Name`
                when 'Registration' then 1
                when 'Triage' then 2
                when 'Doctor Consultation' then 3
                when 'X-Ray' then 4
                when 'Discharge' then 5
                else 99
            end
    """
    event_frame = client.query(query).to_dataframe()
    if event_frame.empty:
        raise ValueError(
            f"`{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` returned no events; "
            "run the dbt marts model before process discovery."
        )

    event_frame = order_events(event_frame, "Case_ID", "Activity_Name", "Timestamp")
    formatted_frame = pm4py.format_dataframe(
        event_frame,
        case_id="Case_ID",
        activity_key="Activity_Name",
        timestamp_key="Timestamp",
    )
    formatted_frame = order_events(
        formatted_frame,
        "case:concept:name",
        "concept:name",
        "time:timestamp",
    )

    case_count = formatted_frame["case:concept:name"].nunique()
    event_count = len(formatted_frame)
    variants = get_case_variants(formatted_frame)
    if not variants:
        raise ValueError("The event log contains no complete case variants.")

    print(f"Cases: {case_count}")
    print(f"Events: {event_count}")
    print(f"Distinct variants: {len(variants)}")
    print("Top 5 variants:")
    for variant, frequency in variants.most_common(5):
        print(f"  {frequency}: {' -> '.join(variant)}")

    loopback_cases = sum(
        any(
            left == "X-Ray" and right == "Triage"
            for left, right in zip(variant, variant[1:])
        )
        for variant in variants.elements()
    )
    xray_cases = sum("X-Ray" in variant for variant in variants.elements())
    if xray_cases == 0:
        raise ValueError("Cannot calculate the X-Ray-to-Triage loop-back rate: no cases contain X-Ray.")
    print(
        "Loop-back rate (among cases with X-Ray): "
        f"{loopback_cases}/{xray_cases} = {loopback_cases / xray_cases:.2%}"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    frequency_dfg, start_activities, end_activities = pm4py.discover_dfg(formatted_frame)
    performance_dfg, performance_starts, performance_ends = pm4py.discover_performance_dfg(
        formatted_frame
    )
    pm4py.save_vis_dfg(
        frequency_dfg,
        start_activities,
        end_activities,
        str(OUTPUT_DIR / "as_is_dfg_frequency.png"),
    )
    pm4py.save_vis_performance_dfg(
        performance_dfg,
        performance_starts,
        performance_ends,
        str(OUTPUT_DIR / "as_is_dfg_performance.png"),
        aggregation_measure="mean",
    )

    top_variants_frame = pm4py.filter_variants_top_k(formatted_frame, k=5)
    top_dfg, top_starts, top_ends = pm4py.discover_dfg(top_variants_frame)
    pm4py.save_vis_dfg(
        top_dfg,
        top_starts,
        top_ends,
        str(OUTPUT_DIR / "as_is_dfg_top_variants.png"),
    )

    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(formatted_frame)
    pm4py.save_vis_petri_net(
        net,
        initial_marking,
        final_marking,
        str(OUTPUT_DIR / "as_is_inductive_miner.png"),
    )

    write_dfg_edges(frequency_dfg, OUTPUT_DIR / "dfg_edges.csv")
    print(f"Process maps and DFG edges saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
