"""Unit tests for scraper RateLimiter."""

import time

import pytest

from courseflow.infrastructure.scrapers.rate_limiter import RateLimiter


class TestRateLimiterInit:
    """Test RateLimiter initialization."""

    def test_valid_rate(self) -> None:
        rl = RateLimiter(rate=1.0)
        assert rl.rate == 1.0
        assert rl.get_rate() == 1.0

    def test_custom_rate(self) -> None:
        rl = RateLimiter(rate=5.0)
        assert rl.get_interval() == pytest.approx(0.2)

    def test_min_rate(self) -> None:
        rl = RateLimiter(rate=0.1)
        assert rl.get_interval() == pytest.approx(10.0)

    def test_max_rate(self) -> None:
        rl = RateLimiter(rate=10.0)
        assert rl.get_interval() == pytest.approx(0.1)

    def test_rate_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="Rate must be between"):
            RateLimiter(rate=0.05)

    def test_rate_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="Rate must be between"):
            RateLimiter(rate=11.0)


class TestRateLimiterContextManager:
    """Test async context manager behavior."""

    @pytest.mark.asyncio
    async def test_first_request_no_wait(self) -> None:
        rl = RateLimiter(rate=10.0)
        start = time.monotonic()
        async with rl:
            pass
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_rate_limits_consecutive_requests(self) -> None:
        rl = RateLimiter(rate=10.0)  # 0.1s interval
        async with rl:
            pass
        start = time.monotonic()
        async with rl:
            pass
        elapsed = time.monotonic() - start
        # Should wait ~0.1s
        assert elapsed >= 0.05


class TestRateLimiterAcquire:
    """Test acquire method."""

    @pytest.mark.asyncio
    async def test_acquire_works(self) -> None:
        rl = RateLimiter(rate=10.0)
        await rl.acquire()
        # Should not raise

    @pytest.mark.asyncio
    async def test_aexit_does_nothing(self) -> None:
        rl = RateLimiter(rate=10.0)
        await rl.__aexit__(None, None, None)
        # Should not raise
