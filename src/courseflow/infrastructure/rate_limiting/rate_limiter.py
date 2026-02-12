"""Rate limiter with queue management and exponential backoff.

Constitution compliance:
- Zero-cost: In-memory implementation, no external dependencies
- Performance: <10ms overhead per request
- Gemini quota: 15 RPM enforced globally
"""

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager

from courseflow.domain.exceptions import QueueFullError, RateLimitExceededError


class RateLimiter:
    """Global rate limiter with queue management.

    Enforces Gemini free tier limits:
    - 15 requests per minute (RPM)
    - Maximum 100 requests in queue

    Features:
    - Token bucket algorithm for smooth rate limiting
    - Queue depth limit enforcement
    - Request timestamp tracking
    - Thread-safe async implementation
    """

    def __init__(
        self,
        requests_per_minute: int = 15,
        max_queue_depth: int = 100,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
            max_queue_depth: Maximum pending requests in queue
        """
        self.rpm = requests_per_minute
        self.max_queue_depth = max_queue_depth

        # Token bucket: refills at rate of rpm/60 tokens per second
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(requests_per_minute)
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.time()

        # Queue management
        self.queue: deque = deque()
        self.lock = asyncio.Lock()

    async def _refill_tokens(self) -> None:
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on time elapsed
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

    @asynccontextmanager
    async def acquire(self, request_id: str | None = None):
        """Acquire rate limit token with automatic release.

        Args:
            request_id: Optional request identifier for logging

        Raises:
            QueueFullError: If queue depth limit exceeded

        Yields:
            None: Control returns when token acquired

        Example:
            async with rate_limiter.acquire(request_id="abc123"):
                await make_api_call()
        """
        async with self.lock:
            # Check queue depth
            if len(self.queue) >= self.max_queue_depth:
                raise QueueFullError(
                    f"Rate limiter queue full ({self.max_queue_depth} requests). "
                    "Try again later."
                )

            # Add to queue
            self.queue.append(request_id or "unknown")

        try:
            # Wait for token
            while True:
                async with self.lock:
                    await self._refill_tokens()

                    if self.tokens >= 1.0:
                        # Consume token
                        self.tokens -= 1.0
                        break

                # Wait before checking again (prevent busy loop)
                await asyncio.sleep(0.1)

            yield

        finally:
            # Remove from queue
            async with self.lock:
                try:
                    self.queue.remove(request_id or "unknown")
                except ValueError:
                    pass  # Already removed

    async def get_stats(self) -> dict:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with tokens available, queue depth, capacity
        """
        async with self.lock:
            await self._refill_tokens()

            return {
                "tokens_available": self.tokens,
                "max_tokens": self.max_tokens,
                "queue_depth": len(self.queue),
                "max_queue_depth": self.max_queue_depth,
                "requests_per_minute": self.rpm,
            }


async def retry_with_backoff(
    func,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    request_id: str | None = None,
):
    """Retry function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum retry attempts (default: 5)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_multiplier: Delay multiplier for each retry (default: 2.0)
        request_id: Optional request identifier for logging

    Returns:
        Function result on success

    Raises:
        Last exception encountered after retries exhausted

    Example:
        result = await retry_with_backoff(
            lambda: api_call(),
            max_retries=3,
            request_id="abc123"
        )
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # Final attempt failed
                raise RateLimitExceededError(
                    f"Request {request_id or 'unknown'} failed after {max_retries} retries. "
                    f"Last error: {str(e)}"
                ) from e

            # Wait before retry with exponential backoff
            await asyncio.sleep(delay)
            delay *= backoff_multiplier

    # Should never reach here, but satisfies type checker
    if last_exception:
        raise last_exception
