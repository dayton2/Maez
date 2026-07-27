"""Input adapters that normalize external datasets for the solver."""

from maez.inputs.load_profiles import load_phase_profiles
from maez.inputs.pv_profiles import load_pv_profiles

__all__ = ["load_phase_profiles", "load_pv_profiles"]
