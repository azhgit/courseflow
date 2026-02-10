"""Health check endpoint for monitoring system status.

Provides status checks for ChromaDB, SQLite, and Gemini API connectivity.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from courseflow.api.dependencies import get_query_repository, get_vector_store
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    vector_store: ChromaAdapter = Depends(get_vector_store),
    query_repo: SQLiteQueryRepository = Depends(get_query_repository)
) -> Dict[str, Any]:
    """Health check endpoint.
    
    Checks connectivity to:
    - ChromaDB vector store
    - SQLite database
    
    Returns:
        Health status with service checks
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
    
    # NOTE: Gemini API check would require making an actual API call
    # which consumes quota, so we'll skip it in health checks
    
    return health_status
