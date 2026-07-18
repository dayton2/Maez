"""Compatibility entry point for running the analysis from the repository root.

The installed ``maez-run`` command is preferred, but keeping this small wrapper
means ``uv run python main.py`` also works for someone exploring the repository.
All real behavior lives in the importable package so it can be tested and reused.
"""

from maez.cli import main


if __name__ == "__main__":
    main()
