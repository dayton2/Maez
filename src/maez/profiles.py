"""Loading and validation for paired active-power and power-factor profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Profiles:
    """Validated time-aligned profile tables used by the simulation."""

    active_power: pd.DataFrame
    power_factor: pd.DataFrame

    @property
    def timestamps(self) -> pd.Series:
        return self.active_power["Datetime"]

    @property
    def profile_columns(self) -> list[str]:
        return [column for column in self.active_power.columns if column != "Datetime"]

    def limited(self, max_steps: int | None) -> Profiles:
        """Return the first ``max_steps`` rows, primarily for quick smoke runs."""

        if max_steps is None:
            return self
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1 when supplied.")
        return Profiles(
            active_power=self.active_power.iloc[:max_steps].reset_index(drop=True),
            power_factor=self.power_factor.iloc[:max_steps].reset_index(drop=True),
        )


def load_profiles(active_power_path: Path, power_factor_path: Path) -> Profiles:
    """Read the two CSV files, parse their timestamps, and validate their pairing."""

    for path in (active_power_path, power_factor_path):
        if not path.is_file():
            raise FileNotFoundError(f"Profile file not found: {path}")

    # Explicit timestamp parsing prevents pandas from treating Datetime as plain text.
    active_power = pd.read_csv(active_power_path, parse_dates=["Datetime"])
    power_factor = pd.read_csv(power_factor_path, parse_dates=["Datetime"])
    profiles = Profiles(active_power=active_power, power_factor=power_factor)
    validate_profiles(profiles)
    return profiles


def validate_profiles(profiles: Profiles) -> None:
    """Fail before starting OpenDSS if the paired input files are inconsistent."""

    active = profiles.active_power
    power_factor = profiles.power_factor

    if active.empty:
        raise ValueError("Active-power profiles contain no time steps.")
    if len(active) != len(power_factor):
        raise ValueError("Active-power and power-factor files must have the same row count.")
    if list(active.columns) != list(power_factor.columns):
        # The two files use KW and PF suffixes, so compare their normalized names below.
        active_names = [name.removesuffix("KW") for name in active.columns]
        pf_names = [name.removesuffix("PF") for name in power_factor.columns]
        if active_names != pf_names:
            raise ValueError("Active-power and power-factor profile columns do not correspond.")
    if not active["Datetime"].equals(power_factor["Datetime"]):
        raise ValueError("Active-power and power-factor timestamps do not match.")
    if len(profiles.profile_columns) < 7:
        raise ValueError("At least seven building profiles are required by the DSS model.")

    active_values = active.drop(columns="Datetime").to_numpy(dtype=float)
    pf_values = power_factor.drop(columns="Datetime").to_numpy(dtype=float)
    if not np.isfinite(active_values).all() or not np.isfinite(pf_values).all():
        raise ValueError("Profile values must be finite numbers without missing values.")
    if np.any(active_values < 0):
        raise ValueError("Active-power profiles cannot contain negative demand.")
    if np.any((pf_values <= 0) | (pf_values > 1)):
        raise ValueError("Every power-factor value must be in the interval (0, 1].")


def corresponding_pf_column(active_power_column: str) -> str:
    """Translate a column such as ``SuperMarketKW`` to ``SuperMarketPF``."""

    if not active_power_column.endswith("KW"):
        raise ValueError(f"Active-power column must end with 'KW': {active_power_column}")
    return f"{active_power_column.removesuffix('KW')}PF"
