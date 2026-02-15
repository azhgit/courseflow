"""Unit tests for streaming timeout functionality (T005).

Tests timeout context manager and deadline tracking.
"""

import asyncio

import pytest

from courseflow.application.streaming_timeout import (
    StreamingDeadlineManager,
    StreamingTimeoutError,
    streaming_timeout,
)


class TestStreamingTimeoutContextManager:
    """Test streaming_timeout context manager (T005)."""

    @pytest.mark.asyncio
    async def test_normal_completion_within_timeout(self) -> None:
        """Should allow normal operation when under timeout."""
        async with streaming_timeout(max_seconds=1):
            await asyncio.sleep(0.1)
        # Should complete without exception

    @pytest.mark.asyncio
    async def test_timeout_exceeded_raises_error(self) -> None:
        """Should raise StreamingTimeoutError when timeout is exceeded."""
        with pytest.raises(StreamingTimeoutError):
            async with streaming_timeout(max_seconds=0.1):
                await asyncio.sleep(0.5)

    @pytest.mark.asyncio
    async def test_timeout_error_contains_context(self) -> None:
        """StreamingTimeoutError should contain useful context."""
        try:
            async with streaming_timeout(max_seconds=0.1):
                await asyncio.sleep(0.3)
        except StreamingTimeoutError as e:
            assert e.max_seconds == 0.1
            assert e.elapsed_seconds > 0
            assert "timeout" in str(e).lower()
        else:
            pytest.fail("Expected StreamingTimeoutError")

    @pytest.mark.asyncio
    async def test_very_short_timeout(self) -> None:
        """Should handle very short timeouts (microseconds)."""
        with pytest.raises(StreamingTimeoutError):
            async with streaming_timeout(max_seconds=0.001):
                await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_long_timeout_doesnt_interfere(self) -> None:
        """Should not interfere with operations shorter than timeout."""
        result = []
        async with streaming_timeout(max_seconds=10):
            for i in range(5):
                result.append(i)
                await asyncio.sleep(0.01)

        assert result == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_timeout_cleanup_on_success(self) -> None:
        """Should clean up timeout callback on normal exit."""
        async with streaming_timeout(max_seconds=1):
            await asyncio.sleep(0.05)
        # If cleanup failed, might have dangling callbacks
        # This test mainly documents expected behavior

    @pytest.mark.asyncio
    async def test_timeout_cleanup_on_error(self) -> None:
        """Should clean up timeout callback even on exception."""
        try:
            async with streaming_timeout(max_seconds=10):
                raise ValueError("test error")
        except ValueError:
            pass
        # Timeout callback should be cleaned up


class TestStreamingDeadlineManager:
    """Test StreamingDeadlineManager for deadline tracking (T005)."""

    def test_manager_creation(self) -> None:
        """Should create deadline manager with timeout."""
        manager = StreamingDeadlineManager(max_seconds=30)
        assert manager.max_seconds == 30

    def test_default_timeout(self) -> None:
        """Should use 30 second default timeout."""
        manager = StreamingDeadlineManager()
        assert manager.max_seconds == 30

    def test_start_initializes_time(self) -> None:
        """Should record start time."""
        manager = StreamingDeadlineManager(max_seconds=10)
        manager.start()
        # Should not raise
        assert manager.elapsed_seconds >= 0

    def test_check_without_start_raises(self) -> None:
        """Should raise if check() called before start()."""
        manager = StreamingDeadlineManager()
        with pytest.raises(RuntimeError, match="start"):
            manager.check()

    def test_elapsed_seconds_increases(self) -> None:
        """elapsed_seconds should increase over time."""
        import time

        manager = StreamingDeadlineManager()
        manager.start()

        elapsed1 = manager.elapsed_seconds
        time.sleep(0.05)
        elapsed2 = manager.elapsed_seconds

        assert elapsed2 > elapsed1

    def test_elapsed_seconds_before_start(self) -> None:
        """Should raise if checking elapsed before start()."""
        manager = StreamingDeadlineManager()
        with pytest.raises(RuntimeError, match="start"):
            _ = manager.elapsed_seconds

    def test_remaining_seconds(self) -> None:
        """remaining_seconds should decrease over time."""
        import time

        manager = StreamingDeadlineManager(max_seconds=10)
        manager.start()

        remaining1 = manager.remaining_seconds
        time.sleep(0.05)
        remaining2 = manager.remaining_seconds

        assert remaining2 < remaining1
        assert remaining1 > 9.9  # Just started

    def test_remaining_seconds_accurate(self) -> None:
        """remaining_seconds should be approximately max - elapsed."""
        import time

        manager = StreamingDeadlineManager(max_seconds=10)
        manager.start()
        time.sleep(0.1)

        remaining = manager.remaining_seconds
        assert 9.8 < remaining < 10.0  # ~9.9 seconds left

    def test_check_passes_under_deadline(self) -> None:
        """check() should pass when under deadline."""
        import time

        manager = StreamingDeadlineManager(max_seconds=10)
        manager.start()
        time.sleep(0.05)

        manager.check()  # Should not raise

    def test_check_fails_over_deadline(self) -> None:
        """check() should raise when over deadline."""
        manager = StreamingDeadlineManager(max_seconds=0.05)
        manager.start()

        import time

        time.sleep(0.1)

        with pytest.raises(StreamingTimeoutError):
            manager.check()

    def test_remaining_seconds_at_deadline(self) -> None:
        """remaining_seconds should be 0 or negative at deadline."""
        manager = StreamingDeadlineManager(max_seconds=0.05)
        manager.start()

        import time

        time.sleep(0.1)

        remaining = manager.remaining_seconds
        assert remaining <= 0

    def test_multiple_checks_work(self) -> None:
        """Should support multiple check() calls."""
        import time

        manager = StreamingDeadlineManager(max_seconds=1)
        manager.start()

        for _ in range(10):
            manager.check()  # All should pass
            time.sleep(0.01)

    def test_deadline_manager_loop_simulation(self) -> None:
        """Should work in a simulated streaming loop."""
        import time

        manager = StreamingDeadlineManager(max_seconds=1)
        manager.start()

        chunks_processed = 0
        try:
            for _ in range(100):
                manager.check()
                time.sleep(0.005)
                chunks_processed += 1
        except StreamingTimeoutError:
            pass

        # Should have processed many chunks before timeout
        assert chunks_processed > 10


class TestTimeoutIntegration:
    """Integration tests for timeout functionality."""

    @pytest.mark.asyncio
    async def test_deadline_manager_with_async_operations(self) -> None:
        """Should track time across async operations."""

        manager = StreamingDeadlineManager(max_seconds=1)
        manager.start()

        operations = 0
        try:
            for _ in range(100):
                await asyncio.sleep(0.01)
                manager.check()
                operations += 1
        except StreamingTimeoutError:
            pass

        assert operations > 10

    @pytest.mark.asyncio
    async def test_streaming_timeout_with_generator(self) -> None:
        """Should work with async generators."""

        async def slow_generator():
            async with streaming_timeout(max_seconds=0.5):
                for i in range(100):
                    await asyncio.sleep(0.01)
                    yield i

        count = 0
        try:
            async for _ in slow_generator():
                count += 1
        except StreamingTimeoutError:
            pass

        assert count > 0  # Got some items before timeout
        assert count < 100  # But not all

    @pytest.mark.asyncio
    async def test_nested_timeout_context(self) -> None:
        """Outer timeout should apply to nested context."""
        # Outer timeout of 0.2s, inner operation takes longer
        with pytest.raises(StreamingTimeoutError):
            async with streaming_timeout(max_seconds=0.2):
                async with streaming_timeout(max_seconds=10):
                    await asyncio.sleep(0.3)
