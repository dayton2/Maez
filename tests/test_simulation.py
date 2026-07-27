"""Integration tests for injection, solving, measurements, and power balance."""

from pathlib import Path

import numpy as np

from maez.config import AnalysisPaths, default_study_spec
from maez.inputs import load_phase_profiles, load_pv_profiles
from maez.models.profiles import StudyInputs
from maez.results import write_results
from maez.simulation import run_time_series

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_mock_study():
    paths = AnalysisPaths.from_project_root(PROJECT_ROOT)
    study = default_study_spec()
    inputs = StudyInputs(
        load_phase_profiles(paths.load_profiles_csv, study),
        load_pv_profiles(paths.pv_profiles_csv, study),
    )
    return run_time_series(paths.master_dss, study, inputs), study, inputs


def test_mock_time_series_is_phase_resolved_and_balanced() -> None:
    results, study, inputs = _run_mock_study()

    assert len(results.system_timeseries) == len(inputs.timestamps) * 4
    assert set(results.system_timeseries["Phase"]) == {"A", "B", "C", "NET"}
    assert set(results.bus_voltage_timeseries["Bus"]) == set(study.measurements.buses)
    assert results.bus_voltage_timeseries["V_pu"].between(0.9, 1.1).all()
    assert set(results.utility_line_timeseries["Phase"]) == {"A", "B", "C", "NET"}

    net = results.system_timeseries.query("Phase == 'NET'")
    assert net["PVGenerationP_kW"].iloc[1] > net["PVGenerationP_kW"].iloc[0]
    reconstructed_source = net["GrossLoadP_kW"] - net["PVGenerationP_kW"] + net["LossP_kW"]
    assert np.allclose(reconstructed_source, net["SourceP_kW"], atol=1e-8)

    load_a = results.element_timeseries.query(
        "ElementClass == 'Load' and Element == 'load_8A' and Phase == 'A'"
    )
    assert np.allclose(load_a["P_kW"], inputs.loads.p_kw[:, 0], atol=1e-5)


def test_result_writer_creates_every_table(tmp_path: Path) -> None:
    results, _, _ = _run_mock_study()
    write_results(results, tmp_path)

    stems = {
        "element_timeseries",
        "bus_voltage_timeseries",
        "utility_line_timeseries",
        "system_timeseries",
        "applied_inputs",
    }
    assert {path.stem for path in tmp_path.glob("*.csv")} == stems
    assert {path.stem for path in tmp_path.glob("*.parquet")} == stems
