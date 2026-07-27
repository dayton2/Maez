# Maez Phase-Resolved Distribution Study

This project uses DSS-Python to inject externally generated, phase-resolved load
and PV inputs into a 16-bus OpenDSS feeder. Each timestamp is solved as a snapshot,
then terminal power, current, voltage, source flow, bus voltage, and system power
balance are recorded. MATLAB and Windows COM are not required.

## Install and run

```powershell
uv sync
uv run maez-run
```

The repository includes two simple two-step mock datasets, so the default command
is a complete lightweight example. Limit any dataset to its first timestamp with:

```powershell
uv run maez-run --max-steps 1
```

Custom files can be supplied without modifying source code:

```powershell
uv run maez-run `
  --load-profiles data/my_load_profiles.csv `
  --pv-profiles data/my_pv_profiles.csv
```

## Input schemas

`data/mock_load_phase_profiles.csv` is long-form, with exactly one row per DSS
single-phase Load per timestamp:

```text
Datetime,Load,Phase,P_kW,Q_kvar
2026-07-01 12:00:00,load_8A,A,18,6
```

The required columns are `Datetime`, `Load`, `Phase`, and `P_kW`. Supply either:

- `Q_kvar`, which may be positive or negative; or
- `PF`, where positive means lagging and negative means leading.

Every configured load must appear at every timestamp. The explicit load/phase/bus
mapping is defined by `default_study_spec()` in `src/maez/config.py`.

`data/mock_pv_profiles.csv` has one row per PVSystem per timestamp:

```text
Datetime,PVSystem,Irradiance_kW_m2,Temperature_C,Pmpp_kW,kVA,PF
2026-07-01 12:00:00,PV_346kW,0.50,30,346,346,1.0
```

`Pmpp_kW`, `kVA`, and `PF` are equipment/operating settings and must remain
constant for a given PVSystem. Irradiance and temperature may vary each timestamp.
The load and PV timestamp sets must match exactly.

## Architecture

```text
models/       typed circuit, input, and measurement contracts
inputs/       CSV validation and conversion to dense NumPy arrays
engine/       DSS compilation, cached bindings, injection, and measurement
simulation.py time-step orchestration and system-balance calculation
results.py    CSV and Parquet persistence
cli.py        reproducible command-line entry point
```

The static circuit remains in `dss/`. It is compiled once. Load kW/kvar and PV
irradiance/temperature are then assigned directly before each solve; circuit
elements are not recreated during the time-series loop.

The source model and solution algorithm are intentionally left at their present
OpenDSS settings until the study requirements are finalized. The commented lines
in `Master.dss` show where those settings can later be made explicit.

## Results

Each table is written as readable CSV and typed Parquet:

- `element_timeseries`: phase and net load/PV terminal P and Q, plus phase
  current and node-to-ground voltage magnitude/angle.
- `bus_voltage_timeseries`: A/B/C voltage magnitude, angle, and per-unit value.
- `utility_line_timeseries`: phase and net measurements at terminal 1 of
  `Line.feeder_1_2`, with positive power entering the feeder.
- `system_timeseries`: phase and net gross load, positive PV generation, source
  import, and derived feeder loss.
- `applied_inputs`: an audit trail of every load and PV value injected.

For net element rows, current and voltage are intentionally blank: P and Q add
across phases, but phase current phasors and voltages do not have a single scalar
"net" measurement.

The balance convention is:

```text
Source import = Gross load - PV generation + Feeder loss
```

Open `notebooks/analysis_results.ipynb` after a run to inspect tables, phase source
flows, bus voltages, load/PV terminal measurements, and balance checks:

```powershell
uv run jupyter notebook notebooks/analysis_results.ipynb
```

## Verification

```powershell
uv run ruff check .
uv run pytest
```

The tests validate both input schemas and perform real DSS-Python solves using the
mock unbalanced profiles.
