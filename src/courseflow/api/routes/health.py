"""Health check endpoint for monitoring system status.

Provides status checks for ChromaDB, SQLite, and rate limiter.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from courseflow.api.dependencies import (
    get_query_repository,
    get_vector_store,
    get_rate_limiter,
)
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter
from courseflow.domain.models import RateLimitTracker

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    vector_store: ChromaAdapter = Depends(get_vector_store),
    query_repo: SQLiteQueryRepository = Depends(get_query_repository),
    rate_limiter: RateLimitTracker = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    """Health check endpoint with rate limit monitoring.
    
    Checks connectivity to:
    - ChromaDB vector store
    - SQLite database
    - Rate limiter status
    
    Returns:
        Health status with service checks and quota usage
    """
    health_status = {
        "status": "ok",
        "services": {}
    }
    
    # Check ChromaDB
    try:
        # Simple collection check
        collection_count = vector_store.collection.count()
        health_status["services"]["chromadb"] = {
            "status": "ok",
            "document_count": collection_count
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["chromadb"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check SQLite
    try:
        # Simple query count check
        query_count = await query_repo.get_recent_query_count(hours=24)
        health_status["services"]["sqlite"] = {
            "status": "ok",
            "queries_last_24h": query_count
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["sqlite"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Check rate limiter status
    try:
        from datetime import datetime, timezone, timedelta

        # Count requests in last minute
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=rate_limiter.window_seconds)
        requests_in_window = sum(
            1 for ts in rate_limiter.request_timestamps if ts >= cutoff
        )

        health_status["services"]["rate_limit"] = {
            "status": "ok",
            "requests_in_last_minute": requests_in_window,
            "max_requests_per_minute": rate_limiter.max_requests_per_minute,
            "available_requests": max(
                0, rate_limiter.max_requests_per_minute - requests_in_window
            ),
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["rate_limit"] = {"status": "error", "error": str(e)}
    
    # NOTE: Gemini API check would require making an actual API call
    # which consumes quota, so we'll skip it in health checks
    
    return health_status
