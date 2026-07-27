"""Validated, solver-ready arrays for load and PV time-series inputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LoadProfileData:
    """Phase load P and Q arrays shaped ``(time, load element)``."""

    timestamps: pd.DatetimeIndex
    load_names: tuple[str, ...]
    p_kw: np.ndarray
    q_kvar: np.ndarray

    def __post_init__(self) -> None:
        expected = (len(self.timestamps), len(self.load_names))
        if self.p_kw.shape != expected or self.q_kvar.shape != expected:
            raise ValueError(f"Load arrays must have shape {expected}.")

    def limited(self, max_steps: int | None) -> LoadProfileData:
        if max_steps is None:
            return self
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        return LoadProfileData(
            self.timestamps[:max_steps],
            self.load_names,
            self.p_kw[:max_steps].copy(),
            self.q_kvar[:max_steps].copy(),
        )


@dataclass(frozen=True)
class PVProfileData:
    """PV weather, ratings, and operating PF data."""

    timestamps: pd.DatetimeIndex
    pv_names: tuple[str, ...]
    irradiance_kw_m2: np.ndarray
    temperature_c: np.ndarray
    pmpp_kw: np.ndarray
    kva: np.ndarray
    power_factor: np.ndarray

    def __post_init__(self) -> None:
        dynamic_shape = (len(self.timestamps), len(self.pv_names))
        if self.irradiance_kw_m2.shape != dynamic_shape:
            raise ValueError(f"PV irradiance must have shape {dynamic_shape}.")
        if self.temperature_c.shape != dynamic_shape:
            raise ValueError(f"PV temperature must have shape {dynamic_shape}.")
        for name, values in (
            ("Pmpp", self.pmpp_kw),
            ("kVA", self.kva),
            ("power factor", self.power_factor),
        ):
            if values.shape != (len(self.pv_names),):
                raise ValueError(f"PV {name} must have one value per PV system.")

    def limited(self, max_steps: int | None) -> PVProfileData:
        if max_steps is None:
            return self
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")
        return PVProfileData(
            self.timestamps[:max_steps],
            self.pv_names,
            self.irradiance_kw_m2[:max_steps].copy(),
            self.temperature_c[:max_steps].copy(),
            self.pmpp_kw.copy(),
            self.kva.copy(),
            self.power_factor.copy(),
        )


@dataclass(frozen=True)
class StudyInputs:
    """Time-aligned load and PV input datasets."""

    loads: LoadProfileData
    pv: PVProfileData

    def __post_init__(self) -> None:
        if not self.loads.timestamps.equals(self.pv.timestamps):
            raise ValueError("Load and PV timestamps must match exactly.")

    @property
    def timestamps(self) -> pd.DatetimeIndex:
        return self.loads.timestamps

    def limited(self, max_steps: int | None) -> StudyInputs:
        return StudyInputs(self.loads.limited(max_steps), self.pv.limited(max_steps))
