#!/usr/bin/env python3
"""Standalone entry point for a vendored copy of uxflow.

Two ways to run this tool, and both must keep working:

    pip install uxflow && uxflow render ...        # console script -> uxflow.cli:main
    python3 uxflow/scripts/uxflow.py render ...    # vendored, nothing installed

This file serves the second. It puts `scripts/` on the import path so that
`uxflow_lib` -- the same directory that ships to PyPI as the `uxflow` package --
can be imported without an install step, then hands over to the real CLI.

Keep it thin. All logic lives in uxflow_lib/cli.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uxflow_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
