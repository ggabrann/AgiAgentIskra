"""Core modules for AgiAgent Искра.

This package contains reusable components such as the MemoryManager, which
implements the operations described in the canonical document
`iskra_memory_core.md`.  By placing core logic here, other projects and
builds can import and reuse the same functionality without duplicating code.

Example:

    from iskra_core.memory_manager import MemoryManager
    mm = MemoryManager('memory/ARCHIVE/main_archive.jsonl', 'memory/SHADOW/main_shadow.jsonl')
    mm.append_archive({'title': 'Пример', 'type': 'факт', 'content': '...', 'confidence': 'сред'})
"""

from .memory_manager import MemoryManager

__all__ = ["MemoryManager"]
