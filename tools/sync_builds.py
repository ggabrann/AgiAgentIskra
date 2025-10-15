#!/usr/bin/env python3
"""Synchronise canonical documents across Искра build surfaces.

This script copies the canonical files stored in ``Iskra/Canon`` into the
``canon/`` subdirectory of each primary build surface (GitHub, Projects,
Custom GPT).  It also keeps the MANTRA memory file aligned by using the
GitHub build as the source of truth.

Run this script after modifying any file in ``Iskra/Canon`` to propagate
changes into the individual build folders.  The script prints a summary of
its actions and can be integrated into CI pipelines.

Example::

    python tools/sync_builds.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

BUILD_SURFACES = {
    "GitHub": Path("Iskra/GitHub/builds"),
    "Projects": Path("Iskra/Projects/builds"),
    "CustomGPT": Path("Iskra/CustomGPT/builds"),
}


def sync_builds(repo_root: Path) -> None:
    canon_dir = repo_root / "Iskra" / "Canon"
    canonical_files = [p for p in canon_dir.iterdir() if p.is_file()]
    if not canonical_files:
        print("No canonical files found, skipping sync.")
        return

    github_memory = repo_root / "Iskra" / "GitHub" / "builds" / "memory" / "MANTRA.md"

    for name, rel_build_path in BUILD_SURFACES.items():
        build_dir = repo_root / rel_build_path
        if not build_dir.exists():
            print(f"Skipping {name}: {build_dir} does not exist")
            continue

        dest_canon = build_dir / "canon"
        dest_canon.mkdir(parents=True, exist_ok=True)

        for src in canonical_files:
            dest = dest_canon / src.name
            shutil.copy2(src, dest)

        if github_memory.exists() and name != "GitHub":
            target_mantra = build_dir / "memory" / "MANTRA.md"
            target_mantra.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(github_memory, target_mantra)

        print(f"Updated {name}: copied {len(canonical_files)} canonical files")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sync_builds(repo_root)


if __name__ == "__main__":
    main()
