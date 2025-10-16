"""Tests for the MemoryManager class.

These tests cover basic validation, automatic ID and next_review assignment,
and simple search functionality.  They use temporary files under a
workspace-specific directory so as not to interfere with real memory data.
"""

import json
import os
import tempfile

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
