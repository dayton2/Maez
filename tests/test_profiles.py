"""Tests for phase-resolved load/PV adapters and time alignment."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from maez.config import AnalysisPaths, default_study_spec
from maez.inputs import load_phase_profiles, load_pv_profiles
from maez.models.profiles import StudyInputs

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mock_profiles_load_in_study_order() -> None:
    paths = AnalysisPaths.from_project_root(PROJECT_ROOT)
    study = default_study_spec()
    loads = load_phase_profiles(paths.load_profiles_csv, study)
    pv = load_pv_profiles(paths.pv_profiles_csv, study)
    inputs = StudyInputs(loads, pv)

    assert len(inputs.timestamps) == 49
    assert inputs.timestamps[0] == pd.Timestamp("2026-07-01 00:00:00")
    assert inputs.timestamps[-1] == pd.Timestamp("2026-07-02 00:00:00")
    assert loads.p_kw.shape == (49, 21)
    assert loads.load_names[0:3] == ("load_8A", "load_8B", "load_8C")
    assert np.all(loads.p_kw == loads.p_kw[:, :1])
    assert loads.p_kw[0, 0] == loads.p_kw[-1, 0] == 5.0
    assert loads.p_kw[28, 0] == 20.0
    assert pv.irradiance_kw_m2[0, 0] == pv.irradiance_kw_m2[-1, 0] == 0.0
    assert pv.irradiance_kw_m2[26, 0] == 1.0
    assert pv.pmpp_kw.tolist() == [346.0]


def test_pf_input_is_converted_to_signed_q(tmp_path: Path) -> None:
    """Positive PF means lagging Q; negative PF means leading Q."""

    study = default_study_spec()
    rows = []
    for index, load in enumerate(study.loads):
        rows.append(
            {
                "Datetime": "2026-01-01 00:00:00",
                "Load": load.dss_name,
                "Phase": load.phase,
                "P_kW": 4.0,
                "PF": -0.8 if index == 0 else 0.8,
            }
        )
    path = tmp_path / "loads_pf.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    profiles = load_phase_profiles(path, study)

    assert np.isclose(profiles.q_kvar[0, 0], -3.0)
    assert np.isclose(profiles.q_kvar[0, 1], 3.0)


def test_missing_phase_row_is_rejected(tmp_path: Path) -> None:
    paths = AnalysisPaths.from_project_root(PROJECT_ROOT)
    table = pd.read_csv(paths.load_profiles_csv).iloc[:-1]
    path = tmp_path / "incomplete.csv"
    table.to_csv(path, index=False)

    with pytest.raises(ValueError, match="Every timestamp"):
        load_phase_profiles(path, default_study_spec())
