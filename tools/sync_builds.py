#!/usr/bin/env python3
"""Synchronise canonical documents across all Искра builds.

This script copies the canonical files stored in the `canon` directory at
the root of the repository into the `canon/` subdirectory of each build
(GitHub, Projects, Custom GPT).  It also ensures that the MANTRA file is
consistent by copying it from the GitHub build into other builds if they
lack one.

Run this script after modifying any file in `canon/` to propagate changes
into the individual build folders.  The script prints a summary of its
actions and can be integrated into CI pipelines.

Example:

    python tools/sync_builds.py
"""

import os
import shutil
from pathlib import Path


def sync_builds(repo_root: Path) -> None:
    canon_dir = repo_root / 'canon'
    builds_dir = repo_root / 'builds'
    if not builds_dir.exists():
        raise FileNotFoundError(f"Builds directory not found: {builds_dir}")

    # Determine canonical files to copy
    canonical_files = [p for p in canon_dir.iterdir() if p.is_file()]
    builds = [d for d in builds_dir.iterdir() if d.is_dir()]
    print(f"Found canonical files: {[p.name for p in canonical_files]}")
    for build in builds:
        dest_canon = build / 'canon'
        dest_canon.mkdir(exist_ok=True)
        for src in canonical_files:
            dest = dest_canon / src.name
            shutil.copy2(src, dest)
        # Synchronise MANTRA.md if present in GitHub build. Skip copying
        # when updating the GitHub build itself to avoid SameFileError.
        mantra_src = (builds_dir / 'github' / 'memory' / 'MANTRA.md')
        if mantra_src.exists() and build.name != 'github':
            target_mantra = build / 'memory' / 'MANTRA.md'
            target_mantra.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mantra_src, target_mantra)
        print(f"Updated {build.name}: copied {len(canonical_files)} files")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sync_builds(repo_root)


if __name__ == '__main__':
    main()
