"""Unit tests for streaming rate limiter configuration (T006).

Tests streaming-specific rate limiting configuration and behavior.
"""

import pytest

from courseflow.infrastructure.rate_limiting.rate_limiter import RateLimiter
from courseflow.infrastructure.rate_limiting.streaming_limiter import (
    StreamingRateLimiter,
    get_global_streaming_limiter,
    set_global_streaming_limiter,
)


class TestStreamingRateLimiter:
    """Test StreamingRateLimiter configuration (T006)."""

    def test_creation_with_default_config(self) -> None:
        """Should create with default streaming configuration."""
        limiter = StreamingRateLimiter()
        assert limiter._max_retries == 3
        assert limiter._initial_delay == 1.0

    def test_creation_with_custom_config(self) -> None:
        """Should accept custom retry configuration."""
        limiter = StreamingRateLimiter(
            max_retries=5,
            initial_delay=0.5,
        )
        assert limiter._max_retries == 5
        assert limiter._initial_delay == 0.5

    def test_creation_with_custom_base_limiter(self) -> None:
        """Should accept custom base rate limiter."""
        base = RateLimiter(requests_per_minute=10, max_queue_depth=50)
        limiter = StreamingRateLimiter(base_limiter=base)
        assert limiter._limiter is base

    def test_active_stream_count_property(self) -> None:
        """Should return count of active streams."""
        base = RateLimiter()
        limiter = StreamingRateLimiter(base_limiter=base)
        assert limiter.active_stream_count == 0
        limiter._streaming_requests["stream_1"] = True
        limiter._streaming_requests["stream_2"] = True
        assert limiter.active_stream_count == 2

    @pytest.mark.asyncio
    async def test_get_streaming_stats_structure(self) -> None:
        """Should return properly structured streaming statistics."""
        base = RateLimiter()
        limiter = StreamingRateLimiter(base_limiter=base)
        limiter._streaming_requests["stream_1"] = True
        stats = await limiter.get_streaming_stats()
        assert "active_streams" in stats
        assert "base_limiter" in stats
        assert stats["active_streams"] == 1


class TestGlobalStreamingLimiter:
    """Test global streaming limiter singleton (T006)."""

    def test_get_global_streaming_limiter_creates_singleton(self) -> None:
        """Should create and return global singleton."""
        limiter1 = get_global_streaming_limiter()
        limiter2 = get_global_streaming_limiter()
        assert limiter1 is limiter2

    def test_set_global_streaming_limiter_overrides(self) -> None:
        """Should allow overriding global limiter."""
        custom_limiter = StreamingRateLimiter()
        set_global_streaming_limiter(custom_limiter)
        retrieved = get_global_streaming_limiter()
        assert retrieved is custom_limiter

    def test_global_limiter_has_gemini_config(self) -> None:
        """Global limiter should have Gemini free tier config."""
        limiter = get_global_streaming_limiter()
        assert limiter._max_retries == 3
        assert limiter._initial_delay == 1.0
