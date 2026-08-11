#!/usr/bin/env python3
"""Standalone entry point for a vendored copy of flowlint.

Two ways to run this tool, and both must keep working:

    pip install flowlint && flowlint render ...        # console script -> flowlint.cli:main
    python3 flowlint/scripts/flowlint.py render ...    # vendored, nothing installed

This file serves the second. It puts `scripts/` on the import path so that
`flowlint_lib` -- the same directory that ships to PyPI as the `flowlint` package --
can be imported without an install step, then hands over to the real CLI.

Keep it thin. All logic lives in flowlint_lib/cli.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flowlint_lib.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
