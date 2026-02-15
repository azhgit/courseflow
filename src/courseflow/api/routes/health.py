"""Health check endpoint for monitoring system status."""

from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from courseflow.api.dependencies import get_query_repository, get_rate_limiter, get_vector_store
from courseflow.domain.models import RateLimitTracker
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter

router = APIRouter()
_START_TIME = perf_counter()


@router.get("/health", response_model=dict[str, Any])
async def health_check(
    vector_store: ChromaAdapter = Depends(get_vector_store),
    query_repo: SQLiteQueryRepository = Depends(get_query_repository),
    rate_limiter: RateLimitTracker = Depends(get_rate_limiter),
) -> JSONResponse:
    """Return detailed component health status."""
    status_name = "healthy"
    components: dict[str, dict[str, Any]] = {}

    chroma_start = perf_counter()
    try:
        document_count = vector_store.collection.count()
        components["chromadb"] = {
            "status": "ok",
            "document_count": document_count,
            "latency_ms": int((perf_counter() - chroma_start) * 1000),
        }
    except Exception as exc:
        status_name = "degraded"
        components["chromadb"] = {"status": "error", "message": str(exc)}

    sqlite_start = perf_counter()
    try:
        conversation_count = 0
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='conversations'"
            )
            table_exists = (await cursor.fetchone())[0] > 0
            if table_exists:
                conv_cursor = await db.execute("SELECT COUNT(*) FROM conversations")
                conversation_count = (await conv_cursor.fetchone())[0]
        components["sqlite"] = {
            "status": "ok",
            "conversation_count": conversation_count,
            "latency_ms": int((perf_counter() - sqlite_start) * 1000),
        }
    except Exception as exc:
        status_name = "degraded"
        components["sqlite"] = {"status": "error", "message": str(exc)}

    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=rate_limiter.window_seconds)
    requests_last_minute = sum(1 for ts in rate_limiter.request_timestamps if ts >= cutoff)
    if requests_last_minute >= rate_limiter.max_requests_per_minute:
        status_name = "degraded"
        components["gemini_api"] = {"status": "error", "message": "Quota exceeded"}
    else:
        components["gemini_api"] = {
            "status": "ok",
            "requests_last_minute": requests_last_minute,
            "limit_per_minute": rate_limiter.max_requests_per_minute,
        }

    payload = {
        "success": status_name == "healthy",
        "data": {
            "status": status_name,
            "components": components,
            "uptime_seconds": int(perf_counter() - _START_TIME),
        },
    }
    status_code = (
        status.HTTP_200_OK if status_name == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=payload)
