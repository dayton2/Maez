"""Persistence helpers for all normalized simulation result tables."""

from __future__ import annotations

from pathlib import Path

from maez.models.measurements import SimulationResults


def write_results(results: SimulationResults, results_dir: Path) -> None:
    """Write CSV for inspection and typed Parquet for efficient analysis."""

    results_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "element_timeseries": results.element_timeseries,
        "bus_voltage_timeseries": results.bus_voltage_timeseries,
        "utility_line_timeseries": results.utility_line_timeseries,
        "system_timeseries": results.system_timeseries,
        "applied_inputs": results.applied_inputs,
    }
    for stem, table in tables.items():
        table.to_csv(results_dir / f"{stem}.csv", index=False)
        table.to_parquet(results_dir / f"{stem}.parquet", index=False)
