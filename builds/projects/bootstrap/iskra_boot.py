"""Bootstrap loader for Iskra Projects builds.

This script loads canonical symbol definitions and exposes helper
functions that Projects automations can import.  Paths are resolved
via the `ISKRA_ROOT` environment variable which should point to the
root of the copied GitHub build.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_ROOT = Path(os.getenv("ISKRA_ROOT", ".")).resolve()
CANONICAL_PATHS = {
    "canon": [
        DEFAULT_ROOT / "canon" / "base.txt",
        DEFAULT_ROOT / "canon" / "agi_agent_искра_полная_карта_работы.md",
        DEFAULT_ROOT / "canon" / "iskra_memory_core.md",
    ],
    "memory": [
        DEFAULT_ROOT / "memory" / "MANTRA.md",
        DEFAULT_ROOT / "memory" / "ARCHIVE",
        DEFAULT_ROOT / "memory" / "SHADOW",
    ],
    "constitution": [
        DEFAULT_ROOT / "constitution" / "symbols_map.json",
        DEFAULT_ROOT / "constitution" / "formats.md",
        DEFAULT_ROOT / "constitution" / "rituals.md",
        DEFAULT_ROOT / "constitution" / "validator.md",
    ],
}


def load_symbols() -> Dict[str, Any]:
    """Return the canonical symbol map as a dictionary."""

    path = CANONICAL_PATHS["constitution"][0]
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_structure() -> None:
    """Ensure that memory directories exist within the Projects sandbox."""

    for directory in CANONICAL_PATHS["memory"][1:]:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_structure()
    symbols = load_symbols()
    print(f"Loaded {len(symbols)} symbols from {CANONICAL_PATHS['constitution'][0]}")
