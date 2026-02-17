"""
Rate limit middleware for Zeabur deployment.

Enforces 20 requests per hour per IP address to protect Gemini API quota.
Uses SQLite persistence to survive container restarts.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from courseflow.infrastructure.repositories.rate_limit_repo import SQLiteRateLimitRepository


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce IP-based rate limiting.

    Applies to all endpoints except /health.
    Enforces 20 requests per hour per IP (configurable via QUOTA_HOURLY_LIMIT).
    Persists state in SQLite for container restart resilience.
    """

    def __init__(self, app: object, db_path: str, hourly_limit: int = 20) -> None:
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            db_path: Path to SQLite database
            hourly_limit: Maximum requests per hour per IP
        """
        super().__init__(app)
        self.repo = SQLiteRateLimitRepository(db_path)
        self.hourly_limit = hourly_limit
        self.window_seconds = 3600  # 1 hour

    async def dispatch(self, request: Request, call_next: Callable[[Request], object]) -> Response:
        """
        Process request through rate limit middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response (429 if rate limited, otherwise pass through)
        """
        # Skip rate limiting for health check endpoint
        if request.url.path.endswith("/health"):
            response_obj = await call_next(request)
            return response_obj if isinstance(response_obj, Response) else Response()

        # Extract client IP
        ip_address = self._get_client_ip(request)

        # Check rate limit
        try:
            is_allowed, retry_after = await self._check_rate_limit(ip_address)

            if not is_allowed:
                # Rate limit exceeded - return 429
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "type": "rate_limit_exceeded",
                            "message": f"Rate limit exceeded. Maximum {self.hourly_limit} requests per hour.",
                            "retry_after_seconds": retry_after,
                        }
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.hourly_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(retry_after)),
                    },
                )

            # Rate limit OK - proceed with request
            response_obj = await call_next(request)
            response = response_obj if isinstance(response_obj, Response) else Response()

            # Add rate limit headers to response
            remaining = await self._get_remaining_requests(ip_address)
            response.headers["X-RateLimit-Limit"] = str(self.hourly_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        except Exception as e:
            # Rate limit check failed - log error but allow request through
            # (fail open to avoid blocking all traffic on database errors)
            print(f"Rate limit middleware error: {e}")
            response_obj = await call_next(request)
            return response_obj if isinstance(response_obj, Response) else Response()

    async def _check_rate_limit(self, ip_address: str) -> tuple[bool, int]:
        """
        Check if IP is within rate limit.

        Args:
            ip_address: Client IP address

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        entry = await self.repo.get_by_ip(ip_address)
        now = datetime.now(UTC)

        if entry is None:
            # First request - create entry
            await self.repo.create_entry(ip_address)
            return (True, 0)

        # Check if window expired
        window_age = (now - entry.window_start).total_seconds()

        if window_age >= self.window_seconds:
            # Window expired - reset
            await self.repo.reset_window(ip_address)
            return (True, 0)

        # Check if at limit
        if entry.request_count >= self.hourly_limit:
            # Rate limited
            retry_after = int(self.window_seconds - window_age)
            return (False, retry_after)

        # Within limit - increment counter
        await self.repo.increment_counter(ip_address)
        return (True, 0)

    async def _get_remaining_requests(self, ip_address: str) -> int:
        """
        Get remaining requests for IP in current window.

        Args:
            ip_address: Client IP address

        Returns:
            Number of remaining requests
        """
        entry = await self.repo.get_by_ip(ip_address)

        if entry is None:
            return self.hourly_limit

        remaining = max(0, self.hourly_limit - entry.request_count)
        return remaining

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Checks X-Forwarded-For header first (for proxies/load balancers),
        falls back to direct connection IP.

        Args:
            request: FastAPI request

        Returns:
            Client IP address string
        """
        # Check X-Forwarded-For header (Zeabur/proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP if comma-separated list
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header (alternative proxy header)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        if request.client and request.client.host:
            return request.client.host

        # Default fallback (shouldn't happen)
        return "unknown"
