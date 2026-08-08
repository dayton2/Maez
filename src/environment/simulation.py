from pathlib import Path
from typing import Any

from dss import DSS
import numpy as np


def _pairs(values: Any) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.size % 2:
        raise ValueError(
            'OpenDSS returned odd-length complex-pair array.'
        )

    return array.reshape(-1, 2)

def run_simulation(master_file: Path) -> None:
    master_file = master_file.expanduser().resolve()
    if not master_file.is_file():
        raise FileNotFoundError(
            f'Master file not found: {master_file}.'
        )

    dss = DSS.NewContext()
    dss.Text.Command = 'clear'
    dss.Text.Command = f'compile "{master_file.as_posix()}"'
    dss.Text.Command = 'set mode=snapshot'

    circuit = dss.ActiveCircuit
    if not circuit.Name:
        raise RuntimeError(
            'OpenDSS did not create an active circuit.'
        )

    solution = circuit.Solution
    solution.Solve()
    if not solution.Converged:
        raise RuntimeError(
            'OpenDSS did not converge.'
        )

    # element_names = [
    #     name
    #     for name
    #     in circuit.AllElementNames
    # ]
    # print(element_names)

    # for name in element_names[:3]:
    #     if circuit.SetActiveElement(name) < 0:
    #         raise ValueError(
    #             f'Unable to activate circuit element: {name}'
    #         )
    #     element = circuit.ActiveCktElement

    #     print(name)
    #     print('-'*50)
    #     print('node_ref:', element.NodeRef)
    #     print('node_order:', element.NodeOrder)
    #     print('powers:', element.Powers)
    #     print('currents:', element.Currents)
    #     print('voltages:', element.Voltages)
    #     print('Bus Names')
    #     for bus_name in element.BusNames:
    #         print(bus_name)
    #     print()

    bus_names = [
        name
        for name
        in circuit.AllBusNames
    ]

    for bus_name in bus_names:
        if circuit.SetActiveBus(bus_name) < 0:
            raise ValueError(
                f'Unknown bus name: {bus_name}'
            )

        bus = circuit.ActiveBus

        print(bus_name)
        print('-'*50)
        print('voltages:', _pairs(bus.Voltages))
        #print('currents:', bus.CplxSeqVoltages)
        print()


root = Path.cwd()
master_dss = root / 'dss' / 'Master.dss'

run_simulation(master_dss)