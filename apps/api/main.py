# AgiAgentIskra/apps/api/main.py

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from iskra_core.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

CONFIDENCE_MAP = {
    'низк': 0.25,
    'низкий': 0.25,
    'сред': 0.5,
    'средн': 0.5,
    'высок': 0.85,
    'высокий': 0.85,
}


def _confidence_to_float(value: str) -> float:
    return CONFIDENCE_MAP.get(value.lower(), 0.6)


def _initialise_memory() -> Optional[MemoryManager]:
    """Create a MemoryManager instance, handling IO errors gracefully."""

    archive = Path("memory/ARCHIVE/main_archive.jsonl")
    shadow = Path("memory/SHADOW/main_shadow.jsonl")
    try:
        manager = MemoryManager(str(archive), str(shadow))
        return manager
    except OSError as exc:  # pragma: no cover - defensive guard
        logger.warning("Memory subsystem disabled: %s", exc)
        return None


memory_manager = _initialise_memory()


app = FastAPI(
    title="Искра Core API",
    description="Минимальный API для демонстрации памяти и оркестрации Искры.",
    version="v1.1",
)


# --- Schemas ---
class SearchRequest(BaseModel):
    query: str = Field(..., description="Текст запроса")
    limit: int = Field(5, ge=1, le=25, description="Максимальное число результатов")


class SearchResult(BaseModel):
    text: str
    source_uri: str
    confidence: float
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    citations: List[SearchResult]
    confidence: float = Field(0.6, ge=0.0, le=1.0)
    memory_record_id: Optional[str] = None


def _load_records_for_query(query: str) -> List[Dict[str, Any]]:
    if not memory_manager:
        return []
    query_normalised = query.lower().strip()
    entries = memory_manager.search_archive()
    if not query_normalised:
        return entries
    filtered = []
    for record in entries:
        haystack = " ".join(
            str(record.get(field, ""))
            for field in ("title", "content", "tags")
        ).lower()
        if query_normalised in haystack:
            filtered.append(record)
    return filtered if filtered else entries


# --- Endpoints ---


@app.get("/health")
async def health_check():
    """Return the status of the lightweight subsystems used by the demo."""

    response: Dict[str, Any] = {
        "status": "ok",
        "system": "Искра Core",
        "phase": "demo",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "memory": "ready" if memory_manager else "disabled",
        },
    }
    if memory_manager:
        stats = memory_manager.get_stats()
        response["memory"] = {
            "archive_records": stats["archive"]["total_records"],
            "shadow_records": stats["shadow"]["total_records"],
        }
    return response


@app.post("/v1/search", response_model=List[SearchResult])
async def search(request: SearchRequest):
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory subsystem unavailable")

    records = _load_records_for_query(request.query)
    results: List[SearchResult] = []
    for record in records[: request.limit]:
        results.append(
            SearchResult(
                text=str(record.get("content", record.get("title", ""))),
                source_uri=f"memory://archive/{record.get('id', 'unknown')}",
                confidence=_confidence_to_float(record.get("confidence", "")),
                metadata={
                    "title": record.get("title"),
                    "tags": record.get("tags", []),
                },
            )
        )

    if not results:
        results.append(
            SearchResult(
                text="В памяти нет подходящих записей, добавьте контент через /v1/chat.",
                source_uri="memory://empty",
                confidence=0.4,
            )
        )
    return results


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory subsystem unavailable")

    timestamp = datetime.utcnow().isoformat()
    history = memory_manager.search_archive(owner=f"session:{request.session_id}")

    summary_parts = [
        f"Запрос принят ({timestamp}).",
        f"Найдено связанных записей: {len(history)}.",
    ]
    response_text = " ".join(summary_parts) + " Ответ будет основан на доступной памяти."

    record = memory_manager.append_archive(
        {
            'title': f"Диалог сессии {request.session_id}",
            'type': 'диалог',
            'content': request.message,
            'confidence': 'сред',
            'owner': f"session:{request.session_id}",
            'tags': ['§chat', f"§session:{request.session_id}"],
        }
    )

    citations: List[SearchResult] = []
    for related in history[:3]:
        citations.append(
            SearchResult(
                text=str(related.get("content", related.get("title", ""))),
                source_uri=f"memory://archive/{related.get('id', 'unknown')}",
                confidence=_confidence_to_float(related.get("confidence", "")),
                metadata={
                    "tags": related.get("tags", []),
                    "owner": related.get("owner"),
                },
            )
        )

    if not citations:
        citations.append(
            SearchResult(
                text="История для этой сессии ещё не накоплена.",
                source_uri="memory://session/empty",
                confidence=0.5,
            )
        )

    return ChatResponse(
        response=response_text,
        citations=citations,
        confidence=0.65,
        memory_record_id=record.get('id'),
    )


# To run the app locally:
# uvicorn apps.api.main:app --reload --port 8000

