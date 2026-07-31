"""Resolve human-readable DSS names to reusable classic-API indices."""

from __future__ import annotations

from dataclasses import dataclass

from dss.ICircuit import ICircuit

from maez.models.circuit import StudySpec


@dataclass(frozen=True)
class EngineBindings:
    """
    Cached indices and names used repeatedly in the time-step loop.
    
    Attributes:
        load_indices: all load indices mapped to the building load elements.
        pv_indices: all indices mapped to the pv system load elements.
        measured_element_names: all element names needed to be measured.
        utility_line_name: the utility line element's name in the circuit.
        bus_names: all bus names provided in the circuit.
    """

    load_indices: tuple[int, ...]
    pv_indices: tuple[int, ...]
    measured_element_names: tuple[str, ...]
    utility_line_name: str
    bus_names: tuple[str, ...]


def build_bindings(circuit: ICircuit, study: StudySpec) -> EngineBindings:
    """Cache indices once instead of repeatedly selecting elements by text."""

    load_index = {name.casefold(): index for index, name in enumerate(circuit.Loads.AllNames, 1)}
    pv_index = {name.casefold(): index for index, name in enumerate(circuit.PVSystems.AllNames, 1)}

    return EngineBindings(
        load_indices=tuple(load_index[load.dss_name.casefold()] for load in study.loads),
        pv_indices=tuple(pv_index[pv.dss_name.casefold()] for pv in study.pv_systems),
        measured_element_names=tuple(
            [load.full_name for load in study.loads] + [pv.full_name for pv in study.pv_systems]
        ),
        utility_line_name=study.measurements.utility_line_full_name,
        bus_names=study.measurements.buses,
    )
