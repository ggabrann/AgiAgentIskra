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

The implementation stays lightweight but now includes reference
implementations of the Rule‑8/Rule‑88 ``stitch`` workflow and a local
``sync`` routine that generates JSON snapshots for backups.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    def stitch(self, rule88: bool = False) -> Dict[str, Any]:
        """Perform a Rule‑8 or Rule‑88 stitching pass and capture insights.

        The method analyses the most recent archive entries, synthesises a
        compact insight entry and, when open questions dominate, records a
        companion shadow signal.  The generated insight is appended to the
        archive and its identifier is returned for downstream tooling.
        """

        window = 88 if rule88 else 8
        records = self._load_jsonl(self.archive_path)
        recent_records = records[-window:]

        summary: Dict[str, Any] = {
            'rule': 'rule88' if rule88 else 'rule8',
            'window': window,
            'analysed': len(recent_records),
            'insights': [],
        }

        if not recent_records:
            return summary

        decisions = [r for r in recent_records if r.get('type') == 'решение']
        questions = [r for r in recent_records if r.get('type') == 'вопрос']
        tags = sorted({tag for rec in recent_records for tag in rec.get('tags', []) if isinstance(tag, str)})

        insight_content = (
            f"Проанализировано {len(recent_records)} записей: решений — {len(decisions)}, "
            f"вопросов — {len(questions)}."
        )
        if tags:
            insight_content += f" Активные теги: {', '.join(tags[:5])}."

        insight_entry = {
            'title': 'Stitch summary',
            'type': 'инсайт',
            'content': insight_content,
            'confidence': 'сред',
            'owner': 'system.stitch',
            'tags': ['§stitch', '§rule88' if rule88 else '§rule8'],
        }

        written_insight = self.append_archive(insight_entry)
        summary['insights'].append(written_insight['id'])
        summary['insight_entry'] = written_insight

        if questions and len(questions) >= len(decisions):
            shadow_entry = {
                'signal': 'open_questions',
                'pattern': (
                    f"Количество открытых вопросов ({len(questions)}) не уступает количеству решений ({len(decisions)})."
                ),
                'hypothesis': 'Требуется дополнительная проработка выявленных вопросов.',
                'counter': 'Проверить следующую серию записей и подтвердить тренд.',
                'confidence': 'сред',
            }
            written_shadow = self.append_shadow(shadow_entry)
            summary['shadow_entry'] = written_shadow

        return summary

    def sync(self, backup_dir: Optional[str] = None) -> Dict[str, Any]:
        """Synchronise memory by creating a local JSON snapshot.

        The snapshot contains both archive and shadow records and is stored
        in the ``backups`` directory next to the archive file (or within the
        provided ``backup_dir``).
        """

        archive_base = Path(self.archive_path).resolve().parent
        # Prefer a caller-provided directory; otherwise keep snapshots close
        # to the archive to simplify ops scripts.
        target_dir = Path(backup_dir) if backup_dir else archive_base / 'backups'
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        snapshot_path = target_dir / f'memory_snapshot_{timestamp}.json'

        archive_records = self._load_jsonl(self.archive_path)
        shadow_records = self._load_jsonl(self.shadow_path)

        data = {
            'archive': archive_records,
            'shadow': shadow_records,
        }

        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {
            'snapshot_path': str(snapshot_path),
            'archive_records': len(archive_records),
            'shadow_records': len(shadow_records),
            'timestamp': timestamp,
        }

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

    def get_stats(self) -> Dict[str, Any]:
        """Return counts for archive and shadow stores."""

        archive_records = self._load_jsonl(self.archive_path)
        shadow_records = self._load_jsonl(self.shadow_path)
        return {
            'archive': {'total_records': len(archive_records)},
            'shadow': {'total_records': len(shadow_records)},
        }
