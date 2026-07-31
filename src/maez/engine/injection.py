"""Direct DSS-Python assignments for static ratings and time-varying inputs."""

from __future__ import annotations

from dss.ICircuit import ICircuit

from maez.engine.bindings import EngineBindings
from maez.models.profiles import StudyInputs


def configure_pv_ratings(circuit: ICircuit, bindings: EngineBindings, inputs: StudyInputs) -> None:
    """Apply static PV ratings once after compiling the circuit."""

    pv_systems = circuit.PVSystems
    for profile_index, dss_index in enumerate(bindings.pv_indices):
        pv_systems.idx = dss_index
        pv_systems.Pmpp = float(inputs.pv.pmpp_kw[profile_index])
        pv_systems.kVArated = float(inputs.pv.kva[profile_index])
        pv_systems.PF = float(inputs.pv.power_factor[profile_index])


def inject_time_step(
    circuit: ICircuit,
    bindings: EngineBindings,
    inputs: StudyInputs,
    step_index: int,
) -> None:
    """Inject phase P/Q and PV weather values for one snapshot."""

    loads = circuit.Loads
    for profile_index, dss_index in enumerate(bindings.load_indices):
        loads.idx = dss_index
        loads.kW = float(inputs.loads.p_kw[step_index, profile_index])
        loads.kvar = float(inputs.loads.q_kvar[step_index, profile_index])

    pv_systems = circuit.PVSystems
    for profile_index, dss_index in enumerate(bindings.pv_indices):
        pv_systems.idx = dss_index
        pv_systems.Irradiance = float(inputs.pv.irradiance_kw_m2[step_index, profile_index])
        # Temperature is not exposed by the classic IPVSystems interface, so use
        # the generic property interface on the PV element activated by ``idx``.
        circuit.ActiveCktElement.Properties("temperature").Val = str(
            float(inputs.pv.temperature_c[step_index, profile_index])
        )
