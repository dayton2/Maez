"""Project paths and the explicit mapping between data profiles and DSS loads.

Keeping configuration separate from the solver makes the study easier to audit:
this file answers *which data is applied where*, while ``simulation.py`` answers
*how the circuit is solved*.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadGroup:
    """One building profile and the single-phase DSS loads representing it.

    Each modeled building is a balanced three-phase load. Its total measured kW
    and calculated kvar are divided equally among the A, B, and C phase elements.
    """

    bus: str
    load_names: tuple[str, ...]
    profile_column: str


@dataclass(frozen=True)
class AnalysisPaths:
    """All filesystem inputs and outputs required by one analysis run."""

    project_root: Path
    master_dss: Path
    active_power_csv: Path
    power_factor_csv: Path
    results_dir: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> AnalysisPaths:
        """Build the conventional paths used by this repository."""

        root = project_root.expanduser().resolve()
        return cls(
            project_root=root,
            master_dss=root / "dss" / "Master.dss",
            active_power_csv=root / "data" / "abq_buildings_active_power.csv",
            power_factor_csv=root / "data" / "abq_buildings_power_factor.csv",
            results_dir=root / "results",
        )


def default_load_groups(profile_columns: list[str]) -> tuple[LoadGroup, ...]:
    """Map the first seven input profiles to the seven modeled load buses.

    This is the same mapping used by the former MATLAB implementation. Passing
    the actual CSV column names avoids duplicating building names in source code
    and raises a clear error if fewer than seven profiles are provided.
    """

    if len(profile_columns) < 7:
        raise ValueError(
            "Expected at least seven building profiles in addition to Datetime; "
            f"received {len(profile_columns)}."
        )

    buses = ("con_8", "con_9", "con_11", "con_12", "con_13", "con_14", "con_15")
    phase_labels = (
        ("load_8A", "load_8B", "load_8C"),
        ("load_9A", "load_9B", "load_9C"),
        ("load_11A", "load_11B", "load_11C"),
        ("load_12A", "load_12B", "load_12C"),
        ("load_13A", "load_13B", "load_13C"),
        ("load_14A", "load_14B", "load_14C"),
        ("load_15A", "load_15B", "load_15C"),
    )

    return tuple(
        LoadGroup(bus=bus, load_names=loads, profile_column=profile_columns[index])
        for index, (bus, loads) in enumerate(zip(buses, phase_labels, strict=True))
    )
