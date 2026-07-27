"""Adapter for PV irradiance, temperature, ratings, and operating PF data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from maez.models.circuit import StudySpec
from maez.models.profiles import PVProfileData

REQUIRED_COLUMNS = {
    "Datetime",
    "PVSystem",
    "Irradiance_kW_m2",
    "Temperature_C",
    "Pmpp_kW",
    "kVA",
    "PF",
}


def load_pv_profiles(path: Path, study: StudySpec) -> PVProfileData:
    """Read PV inputs and verify ratings remain constant through the dataset."""

    if not path.is_file():
        raise FileNotFoundError(f"PV profile file not found: {path}")
    table = pd.read_csv(path, parse_dates=["Datetime"])
    missing = REQUIRED_COLUMNS - set(table.columns)
    if missing:
        raise ValueError(f"PV profile is missing columns: {sorted(missing)}")
    if table.empty or table["Datetime"].isna().any():
        raise ValueError("PV profile must contain valid timestamped rows.")

    table["PVSystem"] = table["PVSystem"].astype(str)
    expected_names = tuple(pv.dss_name for pv in study.pv_systems)
    if set(table["PVSystem"]) != set(expected_names):
        raise ValueError("PVSystem names in the input do not match StudySpec.")
    if table.duplicated(["Datetime", "PVSystem"]).any():
        raise ValueError("PV profile has duplicate Datetime/PVSystem rows.")

    numeric_columns = REQUIRED_COLUMNS - {"Datetime", "PVSystem"}
    for column in numeric_columns:
        table[column] = pd.to_numeric(table[column], errors="coerce")
    if (
        table[list(numeric_columns)].isna().any().any()
        or not np.isfinite(table[list(numeric_columns)].to_numpy(dtype=float)).all()
    ):
        raise ValueError("PV numeric values must be finite.")
    if (table["Irradiance_kW_m2"] < 0).any():
        raise ValueError("PV irradiance cannot be negative.")
    if (table[["Pmpp_kW", "kVA"]] <= 0).any().any():
        raise ValueError("PV Pmpp_kW and kVA ratings must be positive.")
    if ((table["PF"].abs() <= 0) | (table["PF"].abs() > 1)).any():
        raise ValueError("PV PF magnitude must be in (0, 1].")

    static_columns = ["Pmpp_kW", "kVA", "PF"]
    if (table.groupby("PVSystem")[static_columns].nunique() > 1).any().any():
        raise ValueError("PV ratings and PF must remain constant for each PVSystem.")
    timestamps = pd.DatetimeIndex(sorted(table["Datetime"].unique()))
    if len(table) != len(timestamps) * len(expected_names):
        raise ValueError("Every timestamp must provide one row for every configured PVSystem.")

    def dynamic_matrix(column: str) -> np.ndarray:
        matrix = table.pivot(index="Datetime", columns="PVSystem", values=column).reindex(
            index=timestamps, columns=expected_names
        )
        if matrix.isna().any().any():
            raise ValueError(f"PV profile grid for {column} is incomplete.")
        return matrix.to_numpy(dtype=float)

    static = table.drop_duplicates("PVSystem").set_index("PVSystem").reindex(expected_names)
    return PVProfileData(
        timestamps=timestamps,
        pv_names=expected_names,
        irradiance_kw_m2=dynamic_matrix("Irradiance_kW_m2"),
        temperature_c=dynamic_matrix("Temperature_C"),
        pmpp_kw=static["Pmpp_kW"].to_numpy(dtype=float),
        kva=static["kVA"].to_numpy(dtype=float),
        power_factor=static["PF"].to_numpy(dtype=float),
    )
