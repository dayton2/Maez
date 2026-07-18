"""Small integration test covering DSS compilation, solving, and result shapes."""

from pathlib import Path

from maez.config import AnalysisPaths, default_load_groups
from maez.profiles import load_profiles
from maez.simulation import run_time_series


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_two_step_time_series_runs_with_dss_python() -> None:
    paths = AnalysisPaths.from_project_root(PROJECT_ROOT)
    profiles = load_profiles(paths.active_power_csv, paths.power_factor_csv).limited(2)
    groups = default_load_groups(profiles.profile_columns)

    results = run_time_series(paths.master_dss, profiles, groups)

    assert len(results.system_power) == 2
    assert len(results.applied_loads) == 2 * len(groups)
    assert len(results.bus_power) > 2
    assert results.system_power[["TotalKW", "TotalKvar"]].notna().all().all()
