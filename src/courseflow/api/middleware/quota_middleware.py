"""Quota enforcement middleware for FastAPI.

Intercepts requests to query endpoints and enforces quota limits.
Provides rate limit and cache hit headers in responses.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from courseflow.application.quota_service import QuotaService
from courseflow.domain.exceptions import (
    DailyQuotaExceededError,
    IPLimitExceededError,
    QuotaStorageError,
)


class QuotaMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce quota on query endpoints.

    Applies to:
    - POST /api/v1/query
    - POST /api/v1/query/stream

    Enforces per-IP hourly limit and global daily budget.
    Skips quota for cache hits (indicated by X-Cache-Hit header).
    """

    def __init__(self, app, quota_service: QuotaService):
        """Initialize middleware.

        Args:
            app: FastAPI application
            quota_service: QuotaService instance
        """
        super().__init__(app)
        self.quota_service = quota_service

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request through middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            Response with quota headers or error response
        """
        # Only enforce quota on query endpoints
        if not (
            request.url.path.startswith("/api/v1/query")
            or request.url.path.startswith("/api/v1/query/stream")
        ):
            return await call_next(request)

        # Extract client IP
        try:
            ip = self._get_client_ip(request)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "IPAddressUnavailable",
                    "message": "Unable to determine client IP address",
                    "timestamp": self._get_timestamp(),
                    "path": request.url.path,
                },
            )

        # Check quota (except for cache hits which will bypass)
        try:
            await self.quota_service.check_and_enforce_quota(ip)
        except IPLimitExceededError as e:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(e.retry_after_seconds),
                    "X-RateLimit-Limit": str(self.quota_service.hourly_limit),
                    "X-RateLimit-Remaining": "0",
                },
                content={
                    "error": "IPLimitExceeded",
                    "message": str(e),
                    "details": {
                        "ip": e.ip,
                        "limit": e.limit,
                        "retry_after_seconds": e.retry_after_seconds,
                    },
                    "timestamp": self._get_timestamp(),
                    "path": request.url.path,
                },
            )
        except DailyQuotaExceededError as e:
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": "86400",  # 24 hours
                },
                content={
                    "error": "DailyQuotaExceeded",
                    "message": str(e),
                    "details": {
                        "used": e.used,
                        "limit": e.limit,
                        "reset_at": e.reset_at,
                    },
                    "timestamp": self._get_timestamp(),
                    "path": request.url.path,
                },
            )
        except QuotaStorageError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "QuotaStorageUnavailable",
                    "message": "Quota storage is temporarily unavailable",
                    "timestamp": self._get_timestamp(),
                    "path": request.url.path,
                },
            )

        # Call next handler
        response = await call_next(request)

        # Add rate limit headers
        ip_count_after = self.quota_service.get_ip_request_count(ip)
        remaining = max(0, self.quota_service.hourly_limit - ip_count_after)

        response.headers["X-RateLimit-Limit"] = str(self.quota_service.hourly_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request, checking proxy headers.

        Args:
            request: HTTP request

        Returns:
            Client IP address

        Raises:
            ValueError: If IP cannot be determined
        """
        # Check X-Forwarded-For header (proxy-aware)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP in list (original client)
            return forwarded_for.split(",")[0].strip()

        # Check direct connection
        if request.client and request.client.host:
            return request.client.host

        # Unable to determine IP
        raise ValueError("Unable to determine client IP address")

    @staticmethod
    def _get_timestamp() -> str:
        """Get ISO 8601 timestamp.

        Returns:
            Current timestamp in ISO 8601 format
        """
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()
