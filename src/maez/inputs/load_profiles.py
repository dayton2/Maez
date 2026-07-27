"""Adapter for canonical long-form, phase-resolved load profiles."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from maez.models.circuit import StudySpec
from maez.models.profiles import LoadProfileData

REQUIRED_COLUMNS = {"Datetime", "Load", "Phase", "P_kW"}


def load_phase_profiles(path: Path, study: StudySpec) -> LoadProfileData:
    """Read and validate phase load data, returning dense solver-order arrays.

    The file must contain either ``Q_kvar`` or ``PF``. A positive PF represents
    lagging/inductive Q and a negative PF represents leading/capacitive Q.
    """

    if not path.is_file():
        raise FileNotFoundError(f"Load profile file not found: {path}")
    table = pd.read_csv(path, parse_dates=["Datetime"])
    missing = REQUIRED_COLUMNS - set(table.columns)
    if missing:
        raise ValueError(f"Load profile is missing columns: {sorted(missing)}")
    if "Q_kvar" not in table and "PF" not in table:
        raise ValueError("Load profile must contain either Q_kvar or PF.")
    if table.empty:
        raise ValueError("Load profile contains no rows.")
    if table["Datetime"].isna().any():
        raise ValueError("Load profile contains invalid Datetime values.")

    table["Load"] = table["Load"].astype(str)
    table["Phase"] = table["Phase"].astype(str).str.upper()
    expected_phase = {load.dss_name: load.phase for load in study.loads}
    expected_names = tuple(load.dss_name for load in study.loads)
    if set(table["Load"]) != set(expected_names):
        missing_loads = set(expected_names) - set(table["Load"])
        extra_loads = set(table["Load"]) - set(expected_names)
        raise ValueError(
            f"Load names differ from StudySpec; missing={missing_loads}, extra={extra_loads}."
        )
    wrong_phase = table["Phase"] != table["Load"].map(expected_phase)
    if wrong_phase.any():
        raise ValueError("At least one load row has a Phase inconsistent with StudySpec.")
    if table.duplicated(["Datetime", "Load"]).any():
        raise ValueError("Load profile has duplicate Datetime/Load rows.")

    p_kw = pd.to_numeric(table["P_kW"], errors="coerce")
    if p_kw.isna().any() or not np.isfinite(p_kw).all() or (p_kw < 0).any():
        raise ValueError("P_kW values must be finite and nonnegative.")
    if "Q_kvar" in table:
        q_kvar = pd.to_numeric(table["Q_kvar"], errors="coerce")
        if q_kvar.isna().any() or not np.isfinite(q_kvar).all():
            raise ValueError("Q_kvar values must be finite.")
    else:
        pf = pd.to_numeric(table["PF"], errors="coerce")
        if pf.isna().any() or not np.isfinite(pf).all() or ((pf.abs() <= 0) | (pf.abs() > 1)).any():
            raise ValueError("PF magnitude must be in (0, 1].")
        q_kvar = np.sign(pf) * p_kw * np.tan(np.arccos(pf.abs()))

    normalized = table.assign(P_kW=p_kw, Q_kvar=q_kvar)
    timestamps = pd.DatetimeIndex(sorted(normalized["Datetime"].unique()))
    if timestamps.has_duplicates or not timestamps.is_monotonic_increasing:
        raise ValueError("Load timestamps must be unique and increasing.")

    expected_rows = len(timestamps) * len(expected_names)
    if len(normalized) != expected_rows:
        raise ValueError("Every timestamp must provide one row for every configured load phase.")
    p_matrix = normalized.pivot(index="Datetime", columns="Load", values="P_kW").reindex(
        index=timestamps, columns=expected_names
    )
    q_matrix = normalized.pivot(index="Datetime", columns="Load", values="Q_kvar").reindex(
        index=timestamps, columns=expected_names
    )
    if p_matrix.isna().any().any() or q_matrix.isna().any().any():
        raise ValueError("Load profile grid is incomplete.")
    return LoadProfileData(
        timestamps=timestamps,
        load_names=expected_names,
        p_kw=p_matrix.to_numpy(dtype=float),
        q_kvar=q_matrix.to_numpy(dtype=float),
    )
