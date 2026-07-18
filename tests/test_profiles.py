"""Unit tests for calculations and input validation that do not require OpenDSS."""

from math import isclose

import pandas as pd
import pytest

from maez.profiles import Profiles, corresponding_pf_column, validate_profiles
from maez.simulation import kw_pf_to_kvar


def _valid_profiles() -> Profiles:
    timestamps = pd.Series(pd.to_datetime(["1998-01-01 00:00:00"]))
    active = pd.DataFrame({"Datetime": timestamps, **{f"Building{i}KW": [10.0] for i in range(7)}})
    power_factor = pd.DataFrame(
        {"Datetime": timestamps, **{f"Building{i}PF": [0.8] for i in range(7)}}
    )
    return Profiles(active_power=active, power_factor=power_factor)


def test_kw_pf_to_kvar_uses_power_triangle() -> None:
    # At PF=0.8, cos(theta)=0.8 and tan(theta)=0.75, so 100 kW -> 75 kvar.
    assert isclose(kw_pf_to_kvar(100.0, 0.8), 75.0)


def test_kw_pf_to_kvar_rejects_invalid_pf() -> None:
    with pytest.raises(ValueError, match="Power factor"):
        kw_pf_to_kvar(100.0, 0.0)


def test_corresponding_pf_column() -> None:
    assert corresponding_pf_column("SuperMarketKW") == "SuperMarketPF"


def test_valid_profiles_are_accepted() -> None:
    validate_profiles(_valid_profiles())


def test_mismatched_timestamps_are_rejected() -> None:
    profiles = _valid_profiles()
    profiles.power_factor.loc[0, "Datetime"] = pd.Timestamp("1998-01-01 00:30:00")
    with pytest.raises(ValueError, match="timestamps"):
        validate_profiles(profiles)
