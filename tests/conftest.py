"""Put the repository and the November folder on the import path.

``01-lunar-night-battery`` is not a Python package name, because the folder
is named so a reader can find it from the series table. Tests import its
modules as top-level modules the same way ``run_all.py`` does.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVEMBER = ROOT / "01-lunar-night-battery"
os.environ["PYBAMM_DISABLE_TELEMETRY"] = "1"
for path in (ROOT, NOVEMBER):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
