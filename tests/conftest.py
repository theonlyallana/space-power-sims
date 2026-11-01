"""Put the repository root on the import path and silence PyBaMM telemetry.

The model is the ``lunar_power`` package. Tests import it as a package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["PYBAMM_DISABLE_TELEMETRY"] = "1"
text = str(ROOT)
if text not in sys.path:
    sys.path.insert(0, text)
