"""Rate limiting implementation using token bucket algorithm.

This module provides an async context manager for rate limiting HTTP requests
to respect Wikipedia's API guidelines (default 1 req/sec).
"""

import asyncio
import time
from typing import AsyncIterator


class RateLimiter:
    """Token bucket rate limiter for async operations.

    Implements precise rate limiting with configurable requests per second.
    Uses asyncio.sleep() for accurate timing with ±50ms tolerance.

    Attributes:
        rate: Requests per second (0.1-10.0)
        _interval: Minimum seconds between requests
        _last_request_time: Timestamp of last request
        _lock: Async lock for thread safety
    """

    def __init__(self, rate: float = 1.0) -> None:
        """Initialize rate limiter.

        Args:
            rate: Requests per second (default: 1.0)

        Raises:
            ValueError: If rate is not between 0.1 and 10.0
        """
        if not 0.1 <= rate <= 10.0:
            raise ValueError(f"Rate must be between 0.1 and 10.0, got {rate}")

        self.rate = rate
        self._interval = 1.0 / rate
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "RateLimiter":
        """Enter rate-limited context."""
        async with self._lock:
            current_time = time.monotonic()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self._interval:
                # Need to wait before next request
                sleep_time = self._interval - time_since_last
                await asyncio.sleep(sleep_time)

            self._last_request_time = time.monotonic()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit rate-limited context."""
        # No cleanup needed
        pass

    def get_interval(self) -> float:
        """Get the minimum interval between requests in seconds.

        Returns:
            Interval in seconds between consecutive requests
        """
        return self._interval

    def get_rate(self) -> float:
        """Get the configured rate in requests per second.

        Returns:
            Rate in requests per second
        """
        return self.rate

    async def acquire(self) -> None:
        """Acquire rate limit token (wait if necessary).

        This method can be used as an alternative to the context manager.
        """
        async with self:
            pass
