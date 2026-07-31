"""Phase-aware readers for solved OpenDSS element and bus quantities."""

from __future__ import annotations

from math import atan2, degrees, hypot
from typing import Any

from dss.ICircuit import ICircuit
import numpy as np
import pandas as pd

from maez.models.circuit import NODE_TO_PHASE
from maez.models.measurements import BusVoltageMeasurement, ElementPhaseMeasurement


def _pairs(values: Any) -> np.ndarray:
    """Reshape OpenDSS alternating real/imaginary or P/Q values into pairs."""

    array = np.asarray(values, dtype=float)
    if array.size % 2:
        raise ValueError("OpenDSS returned an odd-length complex-pair array.")
    return array.reshape(-1, 2)


def _magnitude_angle(pair: np.ndarray) -> tuple[float, float]:
    return hypot(float(pair[0]), float(pair[1])), degrees(atan2(float(pair[1]), float(pair[0])))


def collect_element_measurements(
    circuit: ICircuit,
    element_name: str,
    timestamp: pd.Timestamp,
    terminal_numbers: tuple[int, ...] | None = None,
) -> list[ElementPhaseMeasurement]:
    """Read phase power, current, and voltage from selected element terminals."""

    if circuit.SetActiveElement(element_name) <= 0:
        raise ValueError(f"Unable to activate circuit element {element_name}.")
    element = circuit.ActiveCktElement
    powers = _pairs(element.Powers)
    currents = _pairs(element.Currents)
    voltages = _pairs(element.Voltages)
    node_order = np.asarray(element.NodeOrder, dtype=int)
    conductor_count = int(element.NumConductors) # number of physical connections (phase, neutral) per terminal
    terminal_count = int(element.NumTerminals) # number of buses connected to active element
    expected = conductor_count * terminal_count
    if not all(len(values) == expected for values in (powers, currents, voltages, node_order)):
        raise ValueError(f"Unexpected terminal-array dimensions for {element_name}.")

    selected = terminal_numbers or tuple(range(1, terminal_count + 1))
    element_class, short_name = element_name.split(".", maxsplit=1)
    records: list[ElementPhaseMeasurement] = []
    for terminal in selected:
        if not 1 <= terminal <= terminal_count:
            raise ValueError(f"Terminal {terminal} is invalid for {element_name}.")
        bus = element.BusNames[terminal - 1].split(".", maxsplit=1)[0]
        offset = (terminal - 1) * conductor_count
        for conductor in range(conductor_count):
            flat_index = offset + conductor
            node = int(node_order[flat_index])
            phase = NODE_TO_PHASE.get(node)
            if phase is None:
                continue
            current_magnitude, current_angle = _magnitude_angle(currents[flat_index])
            voltage_magnitude, voltage_angle = _magnitude_angle(voltages[flat_index])
            records.append(
                ElementPhaseMeasurement(
                    Datetime=timestamp,
                    ElementClass=element_class,
                    Element=short_name,
                    Terminal=terminal,
                    Bus=bus,
                    Node=node,
                    Phase=phase,
                    P_kW=float(powers[flat_index, 0]),
                    Q_kvar=float(powers[flat_index, 1]),
                    I_A=current_magnitude,
                    I_angle_deg=current_angle,
                    V_V=voltage_magnitude,
                    V_angle_deg=voltage_angle,
                )
            )
    return records


def collect_bus_voltages(
    circuit: ICircuit, bus_names: tuple[str, ...], timestamp: pd.Timestamp
) -> list[BusVoltageMeasurement]:
    """Read node-to-ground magnitude/angle and per-unit magnitude by bus phase."""

    records: list[BusVoltageMeasurement] = []
    for bus_name in bus_names:
        if circuit.SetActiveBus(bus_name) < 0:
            raise ValueError(f"Unable to activate bus {bus_name}.")
        bus = circuit.ActiveBus
        nodes = np.asarray(bus.Nodes, dtype=int)
        voltage = _pairs(bus.VMagAngle)
        voltage_pu = _pairs(bus.puVmagAngle)
        for index, node in enumerate(nodes):
            phase = NODE_TO_PHASE.get(int(node))
            if phase is None:
                continue
            records.append(
                BusVoltageMeasurement(
                    Datetime=timestamp,
                    Bus=bus_name,
                    Node=int(node),
                    Phase=phase,
                    V_V=float(voltage[index, 0]),
                    V_angle_deg=float(voltage[index, 1]),
                    V_pu=float(voltage_pu[index, 0]),
                )
            )
    return records
