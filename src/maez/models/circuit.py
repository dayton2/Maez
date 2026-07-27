"""Typed descriptions of the OpenDSS elements used by the study."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Phase = Literal["A", "B", "C"]
PHASE_TO_NODE: dict[Phase, int] = {"A": 1, "B": 2, "C": 3}
NODE_TO_PHASE: dict[int, Phase] = {node: phase for phase, node in PHASE_TO_NODE.items()}


@dataclass(frozen=True)
class LoadPhaseSpec:
    """One single-phase DSS Load and its physical location."""

    dss_name: str
    building: str
    bus: str
    phase: Phase

    @property
    def node(self) -> int:
        return PHASE_TO_NODE[self.phase]

    @property
    def full_name(self) -> str:
        return f"Load.{self.dss_name}"


@dataclass(frozen=True)
class PVSystemSpec:
    """Static identity and connection of one balanced three-phase PV system."""

    dss_name: str
    bus: str
    phases: tuple[Phase, ...] = ("A", "B", "C")

    @property
    def full_name(self) -> str:
        return f"PVSystem.{self.dss_name}"


@dataclass(frozen=True)
class MeasurementSpec:
    """Elements and buses whose solved values are retained at every step."""

    utility_line: str
    buses: tuple[str, ...]

    @property
    def utility_line_full_name(self) -> str:
        return f"Line.{self.utility_line}"


@dataclass(frozen=True)
class StudySpec:
    """Complete static mapping required by the time-series study."""

    loads: tuple[LoadPhaseSpec, ...]
    pv_systems: tuple[PVSystemSpec, ...]
    measurements: MeasurementSpec

    def __post_init__(self) -> None:
        load_names = [load.dss_name.casefold() for load in self.loads]
        pv_names = [pv.dss_name.casefold() for pv in self.pv_systems]
        if len(load_names) != len(set(load_names)):
            raise ValueError("Load names in StudySpec must be unique.")
        if len(pv_names) != len(set(pv_names)):
            raise ValueError("PVSystem names in StudySpec must be unique.")
