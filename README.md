# Maez Distribution-System Analysis

This project applies building demand and power-factor time series to an OpenDSS
feeder. The simulation is controlled entirely from Python through DSS-Python;
MATLAB and the Windows COM server are not required.

## Design

The implementation deliberately separates repeatable simulation code from
interactive exploration:

- `dss/` contains the electrical model written in the native DSS language.
- `data/` contains paired 30-minute active-power and power-factor profiles.
- `src/maez/` contains the engine, validation, simulation, and export code.
- `scripts/run_analysis.py` and the `maez-run` command execute the whole study.
- `notebooks/` is reserved for preprocessing and visual analysis of saved results.
- `results/` receives both CSV and Parquet outputs and is ignored by Git.

The command-line run is the source of truth. A notebook should import functions
from `maez` or read saved results; it should not duplicate the OpenDSS solution
loop. This keeps results reproducible regardless of notebook cell execution order.

## Environment setup

The project uses `uv` and Python 3.12 or newer. Install the locked environment:

```powershell
uv sync
```

`dss-python` bundles its engine interface, so an installed or COM-registered copy
of EPRI OpenDSS is not needed.

## Running the analysis

Run all profile rows:

```powershell
uv run maez-run
```

The equivalent convenience-script command is:

```powershell
uv run python scripts/run_analysis.py
```

After generating results, open `notebooks/analysis_results.ipynb` in Jupyter to
review summary statistics, system and bus power plots, profile assignments, peak
conditions, and selected date ranges without rerunning OpenDSS.

For a quick check that compiles the model and solves only two time steps:

```powershell
uv run maez-run --max-steps 2
```

The run creates these tables in `results/`, in CSV and Parquet formats:

- `applied_load_profiles` records the building-to-bus mapping and assigned kW/kvar.
- `bus_power_timeseries` contains aggregated load and PV power at each circuit bus.
- `system_power_timeseries` contains net circuit demand at the source.

Positive system power represents net demand. At the element level, OpenDSS loads
consume positive power while the PV system normally contributes negative power.

## Code walkthrough

`config.py` defines repository paths and the mapping from the first seven CSV
building profiles to buses `con_8`, `con_9`, `con_11`, `con_12`, `con_13`,
`con_14`, and `con_15`.

`profiles.py` parses timestamps and checks row counts, column correspondence,
timestamps, finite numeric values, nonnegative demand, and power factors in
the interval `(0, 1]`. Invalid inputs therefore fail before starting a simulation.

`opendss_engine.py` creates a fresh `DSS.NewContext()` and compiles `Master.dss`.
A new context prevents state from a previous analysis from leaking into a run.

`simulation.py` converts each building's kW and power factor into kvar, divides
the balanced demand among three single-phase load objects, solves a snapshot,
checks convergence, and collects bus and circuit totals.

`results.py` writes CSV for readability and backward compatibility plus Parquet
for efficient, typed notebook analysis.

## Testing and formatting

```powershell
uv run pytest
uv run ruff check .
uv run ruff format .
```

The integration test uses a short two-step simulation, so it verifies the actual
DSS model and engine connection without running the full annual profile.
