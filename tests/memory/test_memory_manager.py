"""Tests for the MemoryManager class.

These tests cover basic validation, automatic ID and next_review assignment,
and simple search functionality.  They use temporary files under a
workspace-specific directory so as not to interfere with real memory data.
"""

import json
from pathlib import Path

import pytest

from iskra_core.memory_manager import MemoryManager


@pytest.fixture()
def temp_memory_files(tmp_path):
    # Create temporary archive and shadow files in a fresh directory
    archive = tmp_path / 'archive.jsonl'
    shadow = tmp_path / 'shadow.jsonl'
    return str(archive), str(shadow)


def test_append_archive_assigns_id_and_review(temp_memory_files):
    archive_path, shadow_path = temp_memory_files
    mm = MemoryManager(archive_path, shadow_path)
    entry = {
        'title': 'Тестовое решение',
        'type': 'решение',
        'content': 'Проверка автоназначения id и next_review',
        'confidence': 'сред',
    }
    res = mm.append_archive(entry)
    # ID и next_review должны быть добавлены
    assert 'id' in res
    assert res['id'].startswith('ARC_')
    assert 'next_review' in res
    # Файл должен содержать одну запись
    with open(archive_path, encoding='utf-8') as f:
        lines = f.readlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved['title'] == entry['title']


def test_search_archive_filters_by_tag_and_confidence(temp_memory_files):
    archive_path, shadow_path = temp_memory_files
    mm = MemoryManager(archive_path, shadow_path)
    # Добавим несколько записей с разными тегами и уровнями уверенности
    mm.append_archive({
        'title': 'Факт 1',
        'type': 'факт',
        'content': '...',
        'confidence': 'высок',
        'tags': ['§test'],
    })
    mm.append_archive({
        'title': 'Факт 2',
        'type': 'факт',
        'content': '...',
        'confidence': 'сред',
        'tags': ['§other'],
    })
    mm.append_archive({
        'title': 'Решение 3',
        'type': 'решение',
        'content': '...',
        'confidence': 'высок',
        'tags': ['§test'],
    })
    # Фильтруем по тегу и уверенности
    result = mm.search_archive(tag='§test', confidence='высок')
    assert len(result) == 2
    for rec in result:
        assert '§test' in rec['tags']
        assert rec['confidence'] == 'высок'


def test_append_shadow_assigns_defaults(temp_memory_files):
    archive_path, shadow_path = temp_memory_files
    mm = MemoryManager(archive_path, shadow_path)
    entry = {
        'signal': '⚠️',
        'pattern': 'тестовый паттерн',
        'hypothesis': '...',
        'counter': '...',
        'confidence': 'низк',
    }
    res = mm.append_shadow(entry)
    assert res['id'].startswith('SHD_')
    assert 'review_after' in res


def test_stitch_generates_insight_and_shadow(temp_memory_files):
    archive_path, shadow_path = temp_memory_files
    mm = MemoryManager(archive_path, shadow_path)

    # Create a mixture of questions and decisions to trigger both entries
    for idx in range(2):
        mm.append_archive({
            'title': f'Вопрос {idx}',
            'type': 'вопрос',
            'content': 'Что улучшить?',
            'confidence': 'сред',
            'tags': ['§stitch-test'],
        })
    mm.append_archive({
        'title': 'Принятое решение',
        'type': 'решение',
        'content': 'Протестировать stitch()',
        'confidence': 'высок',
        'tags': ['§stitch-test'],
    })

    summary = mm.stitch()

    assert summary['insights'], "Ожидали появление новой записи-инсайта"
    assert summary['insight_entry']['type'] == 'инсайт'
    assert 'shadow_entry' in summary

    with open(archive_path, encoding='utf-8') as f:
        lines = f.readlines()
    # Последняя запись должна относиться к инсайту stitch()
    stitched = json.loads(lines[-1])
    assert stitched['type'] == 'инсайт'
    assert '§stitch' in stitched['tags']


def test_sync_creates_snapshot_file(temp_memory_files):
    archive_path, shadow_path = temp_memory_files
    mm = MemoryManager(archive_path, shadow_path)

    mm.append_archive({
        'title': 'Факт',
        'type': 'факт',
        'content': 'Синхронизация создаёт снапшот.',
        'confidence': 'сред',
    })

    result = mm.sync()
    snapshot_path = Path(result['snapshot_path'])
    assert snapshot_path.exists()

    with snapshot_path.open(encoding='utf-8') as f:
        data = json.load(f)
    assert data['archive'], "Экспорт должен содержать записи архива"
