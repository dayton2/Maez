"""Time-series OpenDSS solution loop and result collection."""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, tan
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from maez.config import LoadGroup
from maez.opendss_engine import compile_circuit
from maez.profiles import Profiles, corresponding_pf_column


@dataclass(frozen=True)
class SimulationResults:
    """The three normalized tables produced by a time-series analysis."""

    bus_power: pd.DataFrame
    system_power: pd.DataFrame
    applied_loads: pd.DataFrame


def kw_pf_to_kvar(kw: float, power_factor: float) -> float:
    """Convert real power and lagging power factor to reactive-power magnitude."""

    if not 0 < power_factor <= 1:
        raise ValueError(f"Power factor must be in (0, 1]; received {power_factor}.")
    return kw * tan(acos(power_factor))


def run_time_series(
    master_file: Path,
    profiles: Profiles,
    load_groups: Sequence[LoadGroup],
) -> SimulationResults:
    """Apply each profile row, solve a snapshot, and collect circuit results.

    The CSV data already represents 30-minute samples, so each row is solved as
    an independent static snapshot. OpenDSS controls are allowed to settle within
    each solve according to the settings in ``Master.dss``.
    """

    dss = compile_circuit(master_file)
    circuit = dss.ActiveCircuit
    solution = circuit.Solution
    dss.Text.Command = "set mode=snapshot"

    bus_names = list(circuit.AllBusNames)
    bus_rows: list[dict[str, object]] = []
    system_rows: list[dict[str, object]] = []
    applied_rows: list[dict[str, object]] = []

    for step_index, timestamp in enumerate(profiles.timestamps):
        for group in load_groups:
            total_kw = float(profiles.active_power.at[step_index, group.profile_column])
            pf_column = corresponding_pf_column(group.profile_column)
            total_kvar = kw_pf_to_kvar(
                total_kw, float(profiles.power_factor.at[step_index, pf_column])
            )

            # Three single-phase elements model one balanced building demand.
            phase_kw = total_kw / len(group.load_names)
            phase_kvar = total_kvar / len(group.load_names)
            for load_name in group.load_names:
                dss.Text.Command = (
                    f"edit load.{load_name} kW={phase_kw:.12f} kvar={phase_kvar:.12f}"
                )

            applied_rows.append(
                {
                    "Datetime": timestamp,
                    "BuildingProfile": group.profile_column,
                    "Bus": group.bus,
                    "AssignedKW": total_kw,
                    "AssignedKvar": total_kvar,
                }
            )

        solution.Solve()
        if not solution.Converged:
            raise RuntimeError(
                f"OpenDSS did not converge at time step {step_index + 1} ({timestamp})."
            )

        bus_p, bus_q = _collect_bus_pc_element_powers(circuit, bus_names)
        bus_rows.extend(
            {
                "Datetime": timestamp,
                "Bus": bus_name,
                "P_kW": bus_p[bus_index],
                "Q_kvar": bus_q[bus_index],
            }
            for bus_index, bus_name in enumerate(bus_names)
        )

        # TotalPower uses the source-delivery sign convention. Negating it makes
        # positive values represent net circuit demand, matching the MATLAB export.
        total_power = circuit.TotalPower
        system_rows.append(
            {
                "Datetime": timestamp,
                "TotalKW": -float(total_power[0]),
                "TotalKvar": -float(total_power[1]),
            }
        )

    return SimulationResults(
        bus_power=pd.DataFrame(bus_rows),
        system_power=pd.DataFrame(system_rows),
        applied_loads=pd.DataFrame(applied_rows),
    )


def _collect_bus_pc_element_powers(
    circuit: Any, bus_names: Sequence[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Sum load and PV powers onto the first terminal's normalized bus name."""

    bus_p = np.zeros(len(bus_names), dtype=float)
    bus_q = np.zeros(len(bus_names), dtype=float)
    bus_lookup = {name.casefold(): index for index, name in enumerate(bus_names)}

    for element_name in circuit.AllElementNames:
        if not element_name.casefold().startswith(("load.", "pvsystem.")):
            continue

        circuit.SetActiveElement(element_name)
        element = circuit.ActiveCktElement
        element_buses = element.BusNames
        if not element_buses:
            continue

        # Remove node suffixes (for example, con_8.1) to match AllBusNames.
        bus_name = element_buses[0].split(".", maxsplit=1)[0]
        bus_index = bus_lookup.get(bus_name.casefold())
        if bus_index is None:
            continue

        powers = np.asarray(element.Powers, dtype=float)
        bus_p[bus_index] += powers[0::2].sum()
        bus_q[bus_index] += powers[1::2].sum()

    return bus_p, bus_q
