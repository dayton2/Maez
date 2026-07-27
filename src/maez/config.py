"""Repository paths and the default 16-bus study configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maez.models.circuit import LoadPhaseSpec, MeasurementSpec, PVSystemSpec, StudySpec


@dataclass(frozen=True)
class AnalysisPaths:
    """All filesystem inputs and outputs required by one analysis run."""

    project_root: Path
    master_dss: Path
    load_profiles_csv: Path
    pv_profiles_csv: Path
    results_dir: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> AnalysisPaths:
        root = project_root.expanduser().resolve()
        return cls(
            project_root=root,
            master_dss=root / "dss" / "Master.dss",
            load_profiles_csv=root / "data" / "mock_load_phase_profiles.csv",
            pv_profiles_csv=root / "data" / "mock_pv_profiles.csv",
            results_dir=root / "results",
        )


def default_study_spec() -> StudySpec:
    """Return explicit phase-to-element mappings for the existing DSS feeder."""

    buildings = {
        8: "Building1",
        9: "Building2",
        11: "Building3",
        12: "Building4",
        13: "Building5",
        14: "HeatPlant",
        15: "ChillerPlant",
    }
    loads = tuple(
        LoadPhaseSpec(
            dss_name=f"load_{bus_number}{phase}",
            building=building,
            bus=f"con_{bus_number}",
            phase=phase,
        )
        for bus_number, building in buildings.items()
        for phase in ("A", "B", "C")
    )
    buses = ("src_1",) + tuple(f"con_{number}" for number in range(2, 17))
    return StudySpec(
        loads=loads,
        pv_systems=(PVSystemSpec(dss_name="PV_346kW", bus="con_16"),),
        measurements=MeasurementSpec(utility_line="feeder_1_2", buses=buses),
    )
