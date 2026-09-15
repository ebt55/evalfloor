"""Shared test setup.

Puts ``tests/`` on the import path so ``fixtures.loose_eval`` resolves, and
imports the fixture module once so its tasks land in the Inspect registry and
can be addressed by name the same way any other task is.
"""

from __future__ import annotations

import pathlib
import sys

TESTS_DIR = pathlib.Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from fixtures import loose_eval as _loose_eval  # noqa: E402,F401  (registers tasks)
