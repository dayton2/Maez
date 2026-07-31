"""Compile the static DSS network and verify study elements are present."""

from __future__ import annotations

from pathlib import Path

from dss import DSS
from dss.IDSS import IDSS

from maez.models.circuit import StudySpec


def compile_circuit(master_file: Path, study: StudySpec) -> IDSS:
    """Compile ``Master.dss`` in a fresh context and validate configured names."""

    master_file = master_file.expanduser().resolve()
    if not master_file.is_file():
        raise FileNotFoundError(f"Master.dss not found: {master_file}")
    dss = DSS.NewContext()
    dss.Text.Command = "clear"
    dss.Text.Command = f'compile "{master_file.as_posix()}"'
    circuit = dss.ActiveCircuit
    if not circuit.Name:
        raise RuntimeError("OpenDSS did not create an active circuit.")

    load_names = {name.casefold() for name in circuit.Loads.AllNames}
    pv_names = {name.casefold() for name in circuit.PVSystems.AllNames}
    missing_loads = [
        load.dss_name for load in study.loads if load.dss_name.casefold() not in load_names
    ]
    missing_pv = [pv.dss_name for pv in study.pv_systems if pv.dss_name.casefold() not in pv_names]
    if missing_loads or missing_pv:
        raise ValueError(
            f"Configured elements are missing; loads={missing_loads}, pv={missing_pv}."
        )
    if circuit.SetActiveElement(study.measurements.utility_line_full_name) <= 0:
        raise ValueError(f"Utility line not found: {study.measurements.utility_line_full_name}")
    missing_buses = set(study.measurements.buses) - set(circuit.AllBusNames)
    if missing_buses:
        raise ValueError(f"Configured measurement buses are missing: {sorted(missing_buses)}")
    return dss
