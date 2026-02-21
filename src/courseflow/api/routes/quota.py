"""Quota status endpoints.

Provides visibility into quota usage and health status.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request

from courseflow.application.quota_service import QuotaService
from courseflow.domain.exceptions import QuotaStorageError

router = APIRouter(prefix="/api/v1/quota", tags=["quota"])


async def get_quota_service(request: Request) -> QuotaService:
    """Dependency: Get quota service from app state.

    Args:
        request: FastAPI request object

    Returns:
        QuotaService instance

    Raises:
        HTTPException: If quota service not initialized
    """
    if not hasattr(request.app.state, "quota_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quota service not initialized",
        )
    return request.app.state.quota_service


@router.get(
    "/status",
    summary="Get Quota Status",
    description="Returns current quota usage, remaining budget, and cache hit rate.",
    responses={
        200: {
            "description": "Current quota status",
            "content": {
                "application/json": {
                    "example": {
                        "daily": {
                            "used": 245,
                            "limit": 300,
                            "remaining": 55,
                            "percentage_used": 81.67,
                            "reset_at": "2026-02-17T00:00:00Z",
                        },
                        "cache": {
                            "questions_count": 10,
                            "hit_rate": 34.5,
                        },
                        "quota_warning": True,
                        "timestamp": "2026-02-16T18:23:45Z",
                    }
                }
            },
        },
        503: {"description": "Quota storage unavailable"},
    },
)
async def get_quota_status(quota_service: QuotaService = Depends(get_quota_service)):
    """Get current quota status.

    Returns:
    - **daily**: Daily usage tracking (used, limit, remaining, percentage, reset time)
    - **cache**: Demo cache statistics (question count, hit rate)
    - **quota_warning**: True if usage >= 80%
    - **timestamp**: Current server time (ISO 8601)

    Raises:
        HTTPException: 503 if quota storage unavailable
    """
    try:
        status_obj = await quota_service.get_quota_status(cached_questions_count=10)
        return status_obj.to_dict()
    except QuotaStorageError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quota storage is temporarily unavailable",
        ) from err
