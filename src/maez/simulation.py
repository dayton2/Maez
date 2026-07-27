"""Orchestrate time-step injection, OpenDSS solving, and result collection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from maez.engine.bindings import build_bindings
from maez.engine.circuit import compile_circuit
from maez.engine.injection import configure_pv_ratings, inject_time_step
from maez.engine.measurement import collect_bus_voltages, collect_element_measurements
from maez.models.circuit import StudySpec
from maez.models.measurements import ElementPhaseMeasurement, SimulationResults
from maez.models.profiles import StudyInputs

PHASES = ("A", "B", "C")


def run_time_series(master_file: Path, study: StudySpec, inputs: StudyInputs) -> SimulationResults:
    """Run independent snapshots while retaining the previous voltage solution."""

    dss = compile_circuit(master_file, study)
    circuit = dss.ActiveCircuit
    solution = circuit.Solution
    dss.Text.Command = "set mode=snapshot"
    bindings = build_bindings(circuit, study)
    configure_pv_ratings(circuit, bindings, inputs)

    element_rows: list[dict[str, object]] = []
    bus_rows: list[dict[str, object]] = []
    utility_rows: list[dict[str, object]] = []
    system_rows: list[dict[str, object]] = []
    applied_rows: list[dict[str, object]] = []

    for step_index, timestamp in enumerate(inputs.timestamps):
        inject_time_step(circuit, bindings, inputs, step_index)
        solution.Solve()
        if not solution.Converged:
            raise RuntimeError(
                f"OpenDSS did not converge at time step {step_index + 1} ({timestamp})."
            )

        step_elements: list[ElementPhaseMeasurement] = []
        for element_name in bindings.measured_element_names:
            step_elements.extend(
                collect_element_measurements(circuit, element_name, timestamp, (1,))
            )
        element_rows.extend(record.as_record() for record in step_elements)
        element_rows.extend(_element_net_rows(step_elements))

        utility_phases = collect_element_measurements(
            circuit, bindings.utility_line_name, timestamp, (1,)
        )
        utility_rows.extend(record.as_record() for record in utility_phases)
        utility_rows.extend(_element_net_rows(utility_phases))

        bus_rows.extend(
            record.as_record()
            for record in collect_bus_voltages(circuit, bindings.bus_names, timestamp)
        )
        system_rows.extend(_system_balance_rows(timestamp, step_elements, utility_phases))
        applied_rows.extend(_applied_input_rows(timestamp, step_index, study, inputs))

    return SimulationResults(
        element_timeseries=pd.DataFrame(element_rows),
        bus_voltage_timeseries=pd.DataFrame(bus_rows),
        utility_line_timeseries=pd.DataFrame(utility_rows),
        system_timeseries=pd.DataFrame(system_rows),
        applied_inputs=pd.DataFrame(applied_rows),
    )


def _element_net_rows(records: list[ElementPhaseMeasurement]) -> list[dict[str, object]]:
    """Add P/Q totals per element terminal; current and voltage have no scalar net."""

    grouped: dict[tuple[object, ...], list[ElementPhaseMeasurement]] = {}
    for record in records:
        key = (
            record.Datetime,
            record.ElementClass,
            record.Element,
            record.Terminal,
            record.Bus,
        )
        grouped.setdefault(key, []).append(record)
    return [
        {
            "Datetime": key[0],
            "ElementClass": key[1],
            "Element": key[2],
            "Terminal": key[3],
            "Bus": key[4],
            "Node": 0,
            "Phase": "NET",
            "P_kW": sum(record.P_kW for record in phase_records),
            "Q_kvar": sum(record.Q_kvar for record in phase_records),
            "I_A": np.nan,
            "I_angle_deg": np.nan,
            "V_V": np.nan,
            "V_angle_deg": np.nan,
        }
        for key, phase_records in grouped.items()
    ]


def _system_balance_rows(
    timestamp: pd.Timestamp,
    elements: list[ElementPhaseMeasurement],
    utility: list[ElementPhaseMeasurement],
) -> list[dict[str, object]]:
    """Derive gross load, positive PV generation, source import, and losses."""

    rows: list[dict[str, object]] = []
    for phase in (*PHASES, "NET"):
        selected_elements = (
            elements if phase == "NET" else [r for r in elements if r.Phase == phase]
        )
        selected_utility = utility if phase == "NET" else [r for r in utility if r.Phase == phase]
        loads = [r for r in selected_elements if r.ElementClass.casefold() == "load"]
        pv = [r for r in selected_elements if r.ElementClass.casefold() == "pvsystem"]
        gross_p = sum(r.P_kW for r in loads)
        gross_q = sum(r.Q_kvar for r in loads)
        # Raw PV terminal power is negative when the inverter delivers to the feeder.
        pv_p = -sum(r.P_kW for r in pv)
        pv_q = -sum(r.Q_kvar for r in pv)
        source_p = sum(r.P_kW for r in selected_utility)
        source_q = sum(r.Q_kvar for r in selected_utility)
        rows.append(
            {
                "Datetime": timestamp,
                "Phase": phase,
                "GrossLoadP_kW": gross_p,
                "GrossLoadQ_kvar": gross_q,
                "PVGenerationP_kW": pv_p,
                "PVGenerationQ_kvar": pv_q,
                "SourceP_kW": source_p,
                "SourceQ_kvar": source_q,
                "LossP_kW": source_p - gross_p + pv_p,
                "LossQ_kvar": source_q - gross_q + pv_q,
            }
        )
    return rows


def _applied_input_rows(
    timestamp: pd.Timestamp,
    step_index: int,
    study: StudySpec,
    inputs: StudyInputs,
) -> list[dict[str, object]]:
    """Record exactly what was injected so each solved case is auditable."""

    rows = [
        {
            "Datetime": timestamp,
            "InputType": "Load",
            "Element": load.dss_name,
            "Phase": load.phase,
            "P_kW": inputs.loads.p_kw[step_index, index],
            "Q_kvar": inputs.loads.q_kvar[step_index, index],
            "Irradiance_kW_m2": np.nan,
            "Temperature_C": np.nan,
            "Pmpp_kW": np.nan,
            "kVA": np.nan,
            "PF": np.nan,
        }
        for index, load in enumerate(study.loads)
    ]
    rows.extend(
        {
            "Datetime": timestamp,
            "InputType": "PVSystem",
            "Element": pv.dss_name,
            "Phase": "NET",
            "P_kW": np.nan,
            "Q_kvar": np.nan,
            "Irradiance_kW_m2": inputs.pv.irradiance_kw_m2[step_index, index],
            "Temperature_C": inputs.pv.temperature_c[step_index, index],
            "Pmpp_kW": inputs.pv.pmpp_kw[index],
            "kVA": inputs.pv.kva[index],
            "PF": inputs.pv.power_factor[index],
        }
        for index, pv in enumerate(study.pv_systems)
    )
    return rows
