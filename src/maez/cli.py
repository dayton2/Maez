"""Command-line interface for reproducible, notebook-independent analysis runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from maez.config import AnalysisPaths, default_load_groups
from maez.profiles import load_profiles
from maez.results import write_results
from maez.simulation import run_time_series


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Maez time-series study using the DSS-Python engine."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing data/, dss/, and results/.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optionally solve only the first N rows for a quick smoke test.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    paths = AnalysisPaths.from_project_root(args.project_root)
    profiles = load_profiles(paths.active_power_csv, paths.power_factor_csv).limited(args.max_steps)
    load_groups = default_load_groups(profiles.profile_columns)

    print(f"Compiling {paths.master_dss}")
    print(f"Solving {len(profiles.timestamps):,} time steps with DSS-Python...")
    results = run_time_series(paths.master_dss, profiles, load_groups)
    write_results(results, paths.results_dir)
    print(f"Analysis complete. Results written to {paths.results_dir}")


if __name__ == "__main__":
    main()
