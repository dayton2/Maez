"""Measurement records and the normalized result-table container."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class ElementPhaseMeasurement:
    """Solved quantities for one phase conductor at one element terminal."""

    Datetime: pd.Timestamp
    ElementClass: str
    Element: str
    Terminal: int
    Bus: str
    Node: int
    Phase: str
    P_kW: float
    Q_kvar: float
    I_A: float
    I_angle_deg: float
    V_V: float
    V_angle_deg: float

    def as_record(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BusVoltageMeasurement:
    """Solved node-to-ground voltage for one phase at one bus."""

    Datetime: pd.Timestamp
    Bus: str
    Node: int
    Phase: str
    V_V: float
    V_angle_deg: float
    V_pu: float

    def as_record(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationResults:
    """All phase-resolved and derived outputs from a simulation run."""

    element_timeseries: pd.DataFrame
    bus_voltage_timeseries: pd.DataFrame
    utility_line_timeseries: pd.DataFrame
    system_timeseries: pd.DataFrame
    applied_inputs: pd.DataFrame
