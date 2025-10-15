"""Validate Unicode→ASCII alias mapping for the GitHub build."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_ALIAS_FILE = Path(__file__).resolve().parent.parent / "aliases.json"


def load_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_aliases(alias_map: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for unicode_path, ascii_path in alias_map.items():
        if Path(ascii_path).suffix == "":
            errors.append(f"ASCII alias must include extension: {ascii_path}")
        if not Path(unicode_path).exists():
            errors.append(f"Missing canonical Unicode path: {unicode_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIAS_FILE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    alias_map = load_aliases(args.aliases)
    errors = check_aliases(alias_map)
    if args.check and errors:
        for error in errors:
            print(error)
        return 1
    if errors:
        print("Warnings:")
        for error in errors:
            print(f"- {error}")
    else:
        print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
