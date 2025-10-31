"""Test configuration for AgiAgentIskra."""

import sys
from pathlib import Path

# Ensure the src/ directory is available for imports when running pytest
SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
