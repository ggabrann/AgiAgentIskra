"""Memory management for AgiAgent Искра.

This module provides a `MemoryManager` class implementing the core operations
described in the `ISKRA_MEMORY_CORE` specification.  The goal is to
encapsulate reading and writing of the Архив и Shadow Core, validate
entries according to the JSONL schema and automate assignment of IDs and
review dates.  It also exposes helper methods to search/filter records.

Usage:

    mm = MemoryManager('memory/ARCHIVE/main_archive.jsonl',
                       'memory/SHADOW/main_shadow.jsonl')
    mm.append_archive({
        'title': 'Введён ∆DΩΛ как обязательный хвост',
        'type': 'решение',
        'content': 'каждый ответ заканчивается ∆DΩΛ',
        'confidence': 'высок',
        'owner': 'user',
        'tags': ['§ritual']
    })
    entries = mm.search_archive(tag='§ritual', confidence='высок')

This implementation is intentionally minimal: it does not yet integrate
connectors or implement Rule‑8/Rule‑88 logic, but provides extension
points for those features.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional


class MemoryManager:
    """Manages Архив and Shadow records stored in JSONL files.

    Each record appended via this manager is validated and automatically
    assigned an `id` and `next_review`/`review_after` field if missing.
    """

    def __init__(self, archive_path: str, shadow_path: str) -> None:
        self.archive_path = archive_path
        self.shadow_path = shadow_path
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.archive_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.shadow_path), exist_ok=True)

    # ------------------------------------------------------------------
    # Validation helpers
    @staticmethod
    def _generate_id(prefix: str) -> str:
        now = datetime.datetime.utcnow()
        return f"{prefix}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _default_next_review(days: int = 7) -> str:
        return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    def _validate_archive_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize an archive entry.

        Adds missing required fields and performs basic type checks.
        """
        data = entry.copy()
        # Required fields: title, type, content, confidence
        for field in ('title', 'type', 'content', 'confidence'):
            if field not in data or not isinstance(data[field], str) or not data[field]:
                raise ValueError(f"Archive entry requires non-empty '{field}'")
        # Optional fields with defaults
        data.setdefault('evidence', [])
        data.setdefault('owner', 'user')
        data.setdefault('tags', [])
        # Assign ID if missing
        if 'id' not in data:
            data['id'] = self._generate_id('ARC')
        # Assign next_review if missing
        data.setdefault('next_review', self._default_next_review())
        return data

    def _validate_shadow_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize a shadow entry.
        """
        data = entry.copy()
        for field in ('signal', 'pattern', 'hypothesis', 'counter', 'confidence'):
            if field not in data or not isinstance(data[field], str) or not data[field]:
                raise ValueError(f"Shadow entry requires non-empty '{field}'")
        if 'id' not in data:
            data['id'] = self._generate_id('SHD')
        data.setdefault('review_after', self._default_next_review())
        return data

    # ------------------------------------------------------------------
    # I/O helpers
    def _append_jsonl(self, path: str, record: Dict[str, Any]) -> None:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _load_jsonl(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]

    # ------------------------------------------------------------------
    # Public methods
    def append_archive(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new archive entry after validation.

        Returns the normalized entry that was written.
        """
        data = self._validate_archive_entry(entry)
        self._append_jsonl(self.archive_path, data)
        return data

    def append_shadow(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Append a new shadow entry after validation.

        Returns the normalized entry that was written.
        """
        data = self._validate_shadow_entry(entry)
        self._append_jsonl(self.shadow_path, data)
        return data

    def search_archive(
        self,
        *,
        tag: Optional[str] = None,
        confidence: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search archive records by tag, confidence or owner.

        Parameters are optional and combined with logical AND.
        """
        records = self._load_jsonl(self.archive_path)
        result = []
        for rec in records:
            if tag and tag not in rec.get('tags', []):
                continue
            if confidence and rec.get('confidence') != confidence:
                continue
            if owner and rec.get('owner') != owner:
                continue
            result.append(rec)
        return result

    def search_shadow(
        self,
        *,
        signal: Optional[str] = None,
        confidence: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search shadow records by signal or confidence level.
        """
        records = self._load_jsonl(self.shadow_path)
        result = []
        for rec in records:
            if signal and rec.get('signal') != signal:
                continue
            if confidence and rec.get('confidence') != confidence:
                continue
            result.append(rec)
        return result

    # Placeholder for future integration
    def stitch(self, rule88: bool = False) -> None:
        """Perform a Rule‑8 or Rule‑88 insight stitching.

        This is a stub. In a full implementation, this method would read the
        latest 100 or 88 messages, extract open questions and decisions, and
        append insights to the archive and shadow.  It is left as an
        extension point for future work.
        """
        raise NotImplementedError("stitch() is not yet implemented")

    def sync(self) -> None:
        """Synchronise memory with external connectors.

        Placeholder for future integration. This function should push and
        fetch memory records from configured connectors (e.g. GitHub, Drive).
        """
        raise NotImplementedError("sync() is not yet implemented")

    def export(self, dest_path: str) -> None:
        """Export archive and shadow to a single JSON file.

        The exported file contains two top-level keys: `archive` and
        `shadow`, each a list of entries.  Useful for backups or
        migration.
        """
        data = {
            'archive': self._load_jsonl(self.archive_path),
            'shadow': self._load_jsonl(self.shadow_path),
        }
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
