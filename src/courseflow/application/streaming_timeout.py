"""Async context manager for streaming timeout handling.

Provides timeout enforcement for long-running streaming operations,
with graceful termination and error event emission per constitution
section III (AI Engineering Standards).
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, TypeVar

T = TypeVar("T")


class StreamingTimeoutError(Exception):
    """Raised when streaming operation exceeds max duration."""

    def __init__(self, max_seconds: int, elapsed_seconds: float):
        """Initialize with timeout context.

        Args:
            max_seconds: Configured timeout limit in seconds
            elapsed_seconds: Actual elapsed time before timeout
        """
        self.max_seconds = max_seconds
        self.elapsed_seconds = elapsed_seconds
        super().__init__(
            f"Stream exceeded {max_seconds}s timeout after {elapsed_seconds:.1f}s"
        )


@asynccontextmanager
async def streaming_timeout(
    max_seconds: int = 30,
) -> AsyncGenerator[None, None]:
    """Context manager for streaming response timeout enforcement.

    Ensures streaming operations don't run indefinitely. When timeout
    is exceeded, raises StreamingTimeoutError which can be caught and
    converted to SSE error event (no HTTP 500).

    Per specification FR-012: 30 second max stream duration.
    Per constitution: graceful termination without HTTP 5xx.

    Args:
        max_seconds: Maximum allowed stream duration (default 30, per spec)

    Yields:
        None (context is just for timeout enforcement)

    Raises:
        StreamingTimeoutError: If any operation in context exceeds max_seconds

    Example:
        try:
            async with streaming_timeout(max_seconds=30):
                async for chunk in gemini_stream():
                    yield chunk
        except StreamingTimeoutError as e:
            yield SSEEvent.failure("timeout", str(e))
    """
    task = asyncio.current_task()
    if task is None:
        # Not in an async task context - shouldn't happen but fallback
        yield
        return

    handle = None
    try:
        # Create timeout callback
        def _on_timeout():
            if task and not task.done():
                task.cancel()

        # Schedule timeout
        loop = asyncio.get_event_loop()
        handle = loop.call_later(max_seconds, _on_timeout)

        yield

    except asyncio.CancelledError:
        # Task was cancelled - check if it was our timeout
        elapsed = max_seconds  # Close approximation
        raise StreamingTimeoutError(max_seconds, elapsed) from None

    finally:
        # Clean up timeout callback
        if handle is not None:
            handle.cancel()


class StreamingDeadlineManager:
    """Manager for streaming operation deadlines.

    Tracks elapsed time during streaming and provides periodic
    checks to detect timeout conditions early (before OS signal).

    Useful for integrating timeout checks within streaming loop:
        deadline = StreamingDeadlineManager(max_seconds=30)
        async for chunk in stream():
            deadline.check()  # Raises if exceeded
            yield chunk
    """

    def __init__(self, max_seconds: int = 30) -> None:
        """Initialize deadline manager.

        Args:
            max_seconds: Maximum allowed duration in seconds
        """
        self.max_seconds = max_seconds
        self._start_time: float | None = None
        self._last_check_time: float | None = None

    def start(self) -> None:
        """Mark the start of streaming operation.

        Called once at streaming start to initialize timer.
        """
        import time

        self._start_time = time.monotonic()
        self._last_check_time = self._start_time

    def check(self) -> None:
        """Check if deadline has been exceeded.

        Call periodically during streaming (e.g., before each chunk yield).

        Raises:
            StreamingTimeoutError: If max_seconds has been exceeded

        Example:
            deadline = StreamingDeadlineManager(30)
            deadline.start()
            async for chunk in stream():
                deadline.check()  # Raises if exceeded
                yield chunk
        """
        if self._start_time is None:
            raise RuntimeError("call start() before check()")

        import time

        elapsed = time.monotonic() - self._start_time
        if elapsed > self.max_seconds:
            raise StreamingTimeoutError(self.max_seconds, elapsed)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since start() was called.

        Returns:
            Seconds elapsed, or 0 if not yet started

        Raises:
            RuntimeError: If start() hasn't been called
        """
        if self._start_time is None:
            raise RuntimeError("call start() before checking elapsed_seconds")

        import time

        return time.monotonic() - self._start_time

    @property
    def remaining_seconds(self) -> float:
        """Get remaining time before deadline.

        Returns:
            Seconds remaining, or 0 if deadline already passed

        Raises:
            RuntimeError: If start() hasn't been called
        """
        elapsed = self.elapsed_seconds
        remaining = self.max_seconds - elapsed
        return max(0, remaining)
