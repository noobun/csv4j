"""Pytest configuration helpers for local development.

This file ensures the repository root is on `sys.path` so tests that
import `src.<package>` (as in the test suite) can resolve the `src`
package without needing an editable install or external PYTHONPATH.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
