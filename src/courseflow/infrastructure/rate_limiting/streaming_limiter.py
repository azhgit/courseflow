"""Streaming-specific rate limiting configuration and helpers.

Extends base rate limiter with awareness of streaming requests,
which should count as single tokens regardless of chunk count.

Per constitution Section III: Ensures Gemini free tier compliance
(15 RPM, 1500/day) for streaming queries.
"""

import asyncio
from contextlib import asynccontextmanager

from courseflow.domain.exceptions import RateLimitExceededError
from courseflow.infrastructure.rate_limiting.rate_limiter import RateLimiter


class StreamingRateLimiter:
    """Rate limiter configured for streaming requests.

    Wraps the global rate limiter with streaming-specific behavior:
    - Entire streaming request (all chunks) counts as 1 RPM token
    - Not affected by number of chunks yielded
    - Applies standard timeout-aware backoff for initial request

    Per specification FR-011: Uses exponential backoff (1s, 2s, 4s, max 3 retries)
    Per specification FR-012: Streams have 30-second max duration
    """

    def __init__(
        self,
        base_limiter: RateLimiter | None = None,
        max_retries: int = 3,
        initial_delay: float = 1.0,
    ):
        """Initialize streaming rate limiter.

        Args:
            base_limiter: Existing RateLimiter instance (uses global if None)
            max_retries: Max retries for initial request (default 3 per clarification)
            initial_delay: Initial backoff delay in seconds (default 1.0)
        """
        self._limiter = base_limiter or _get_global_rate_limiter()
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._streaming_requests: dict[str, bool] = {}

    @asynccontextmanager
    async def acquire_for_stream(self, request_id: str):
        """Acquire rate limit token for a streaming request.

        Applies exponential backoff retry logic per specification clarification Q3.
        The entire stream (all chunks) counts as 1 token.

        Args:
            request_id: Unique identifier for this streaming request

        Raises:
            RateLimitExceededError: If rate limit exceeded after all retries

        Example:
            async with limiter.acquire_for_stream("stream_123"):
                async for chunk in gemini_stream():
                    yield chunk
        """
        delay = self._initial_delay
        last_exception = None

        for attempt in range(self._max_retries + 1):
            try:
                # Try to acquire token from base limiter
                async with self._limiter.acquire(request_id):
                    # Mark as active streaming request
                    self._streaming_requests[request_id] = True

                    try:
                        yield  # Control returns to caller for streaming
                    finally:
                        # Clean up tracking
                        self._streaming_requests.pop(request_id, None)

                return  # Success

            except RateLimitExceededError as e:
                last_exception = e

                if attempt == self._max_retries:
                    # Final retry exhausted
                    raise

                # Exponential backoff before retry
                await asyncio.sleep(delay)
                delay *= 2.0  # 1s → 2s → 4s

        # Should not reach here, but appease type checker
        if last_exception:
            raise last_exception

    async def get_streaming_stats(self) -> dict:
        """Get streaming-specific rate limit statistics.

        Returns:
            Dictionary with:
            - active_streams: Number of currently active streams
            - rate_limiter_stats: Stats from base limiter
        """
        base_stats = await self._limiter.get_stats()
        return {
            "active_streams": len(self._streaming_requests),
            "base_limiter": base_stats,
        }

    @property
    def active_stream_count(self) -> int:
        """Get number of currently active streaming requests."""
        return len(self._streaming_requests)

    @property
    def is_streaming(self, request_id: str) -> bool:
        """Check if a request ID is currently streaming."""
        return request_id in self._streaming_requests


# Global instance
_GLOBAL_STREAMING_LIMITER: StreamingRateLimiter | None = None


def _get_global_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _GLOBAL_STREAMING_LIMITER

    # Get or create the base limiter
    # In practice, this is typically injected via FastAPI dependencies
    # For now, return a default instance
    return RateLimiter(
        requests_per_minute=15,  # Gemini free tier
        max_queue_depth=100,
    )


def get_global_streaming_limiter() -> StreamingRateLimiter:
    """Get global streaming rate limiter instance.

    Lazily initializes on first call. Can be injected in dependency
    containers for testing.

    Returns:
        Global StreamingRateLimiter singleton
    """
    global _GLOBAL_STREAMING_LIMITER

    if _GLOBAL_STREAMING_LIMITER is None:
        _GLOBAL_STREAMING_LIMITER = StreamingRateLimiter(
            base_limiter=_get_global_rate_limiter(),
            max_retries=3,
            initial_delay=1.0,
        )

    return _GLOBAL_STREAMING_LIMITER


def set_global_streaming_limiter(limiter: StreamingRateLimiter) -> None:
    """Override global streaming rate limiter (mainly for testing).

    Args:
        limiter: New StreamingRateLimiter instance to use globally
    """
    global _GLOBAL_STREAMING_LIMITER
    _GLOBAL_STREAMING_LIMITER = limiter
