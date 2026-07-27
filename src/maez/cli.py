"""Command-line interface for the phase-resolved OpenDSS study."""

from __future__ import annotations

import argparse
from pathlib import Path

from maez.config import AnalysisPaths, default_study_spec
from maez.inputs import load_phase_profiles, load_pv_profiles
from maez.models.profiles import StudyInputs
from maez.results import write_results
from maez.simulation import run_time_series


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the phase-resolved Maez DSS-Python study.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing data/, dss/, and results/.",
    )
    parser.add_argument("--load-profiles", type=Path, help="Override the phase load CSV path.")
    parser.add_argument("--pv-profiles", type=Path, help="Override the PV input CSV path.")
    parser.add_argument("--max-steps", type=int, help="Solve only the first N timestamps.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = AnalysisPaths.from_project_root(args.project_root)
    study = default_study_spec()
    load_path = args.load_profiles or paths.load_profiles_csv
    pv_path = args.pv_profiles or paths.pv_profiles_csv
    inputs = StudyInputs(
        loads=load_phase_profiles(load_path, study),
        pv=load_pv_profiles(pv_path, study),
    ).limited(args.max_steps)

    print(f"Compiling {paths.master_dss}")
    print(f"Solving {len(inputs.timestamps):,} phase-resolved time steps...")
    results = run_time_series(paths.master_dss, study, inputs)
    write_results(results, paths.results_dir)
    print(f"Analysis complete. Results written to {paths.results_dir}")


if __name__ == "__main__":
    main()
