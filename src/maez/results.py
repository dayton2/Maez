"""Persistence helpers for simulation result tables."""

from __future__ import annotations

from pathlib import Path

from maez.simulation import SimulationResults


def write_results(results: SimulationResults, results_dir: Path) -> None:
    """Write human-readable CSV and efficient Parquet copies of every table.

    CSV preserves compatibility with the former MATLAB outputs. Parquet retains
    timestamps and numeric types and is usually much faster for notebook analysis.
    """

    results_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "bus_power_timeseries": results.bus_power,
        "system_power_timeseries": results.system_power,
        "applied_load_profiles": results.applied_loads,
    }
    for stem, table in tables.items():
        table.to_csv(results_dir / f"{stem}.csv", index=False)
        table.to_parquet(results_dir / f"{stem}.parquet", index=False)
