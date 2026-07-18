"""Creation and compilation of an isolated DSS-Python engine context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dss import DSS


def compile_circuit(master_file: Path) -> Any:
    """Create a fresh engine context and compile the project's ``Master.dss``.

    ``DSS.NewContext`` gives each run isolated OpenDSS state. This replaces the
    MATLAB ``actxserver`` call and avoids Windows COM registration entirely.
    The returned context owns the Text, ActiveCircuit, and Solution interfaces.
    """

    master_file = master_file.expanduser().resolve()
    if not master_file.is_file():
        raise FileNotFoundError(f"Master.dss not found: {master_file}")

    dss = DSS.NewContext()
    dss.Text.Command = "clear"
    # Forward slashes keep the quoted DSS command unambiguous on Windows.
    dss.Text.Command = f'compile "{master_file.as_posix()}"'

    if not dss.ActiveCircuit.Name:
        result = dss.Text.Result.strip()
        detail = f" OpenDSS reported: {result}" if result else ""
        raise RuntimeError(f"OpenDSS did not create an active circuit.{detail}")
    return dss
