"""Server-Sent Events (SSE) formatting and utilities.

Provides helper functions for formatting and streaming SSE events.
Per constitution section III (AI Engineering Standards): supports immediate
chunk emission with proper event sequence (chunk* → sources → done | error).
"""

from collections.abc import AsyncGenerator

from courseflow.domain.models import SSEEvent


async def stream_sse_events(
    event_generator: AsyncGenerator[SSEEvent, None],
) -> AsyncGenerator[str, None]:
    """Convert domain SSEEvent objects to SSE-formatted strings.

    Yields each event as a properly formatted SSE string with double newline
    terminator, maintaining stream semantics and proper ordering.

    Args:
        event_generator: Async generator yielding SSEEvent objects

    Yields:
        SSE-formatted event strings (ready to write to StreamingResponse)

    Example:
        async for sse_str in stream_sse_events(chunk_generator):
            yield sse_str  # Each event formatted and ready to send
    """
    async for event in event_generator:
        yield event.to_sse()


async def emit_chunk(content: str) -> SSEEvent:
    """Factory for chunk events (convenience wrapper).

    Args:
        content: Text chunk from LLM streaming response

    Returns:
        SSEEvent configured for chunk delivery
    """
    return SSEEvent.chunk(content)


async def emit_sources(
    sources: list[str],
    retrieval_count: int,
) -> SSEEvent:
    """Factory for sources event (convenience wrapper).

    Args:
        sources: List of document filenames retrieved
        retrieval_count: Total chunks used in generation

    Returns:
        SSEEvent configured for sources reporting
    """
    return SSEEvent.with_sources(sources, retrieval_count)


async def emit_completion(
    conversation_id: str,
    token_count: int,
) -> SSEEvent:
    """Factory for done event (convenience wrapper).

    Args:
        conversation_id: UUID of conversation (new or existing)
        token_count: Total tokens in complete response

    Returns:
        SSEEvent configured for completion notification
    """
    return SSEEvent.done(conversation_id, token_count)


async def emit_error(error: str, message: str) -> SSEEvent:
    """Factory for error event (convenience wrapper).

    Args:
        error: Error code (e.g., "rate_limit_exceeded", "no_relevant_documents")
        message: Human-readable error description

    Returns:
        SSEEvent configured for error reporting
    """
    return SSEEvent.failure(error, message)


class SSEEventBuffer:
    """Buffer for collecting SSE events before streaming.

    Used during streaming response generation to track all events
    for logging/monitoring before they're sent to client.

    Immutable after creation - append-only via collect().
    """

    def __init__(self) -> None:
        """Initialize empty event buffer."""
        self._events: list[SSEEvent] = []
        self._chunks: list[str] = []
        self._sources_event: SSEEvent | None = None
        self._done_event: SSEEvent | None = None
        self._error_event: SSEEvent | None = None

    def collect(self, event: SSEEvent) -> None:
        """Collect event for tracking.

        Args:
            event: SSEEvent to track (called after event.to_sse() is sent)

        Raises:
            ValueError: If trying to add events in wrong order or duplicates
        """
        self._events.append(event)

        if event.type == "chunk":
            if event.content:
                self._chunks.append(event.content)
        elif event.type == "sources":
            if self._sources_event is not None:
                raise ValueError("Multiple sources events not allowed")
            self._sources_event = event
        elif event.type == "done":
            if self._done_event is not None:
                raise ValueError("Multiple done events not allowed")
            self._done_event = event
        elif event.type == "error":
            if self._error_event is not None:
                raise ValueError("Multiple error events not allowed")
            self._error_event = event

    @property
    def all_events(self) -> tuple[SSEEvent, ...]:
        """Get all collected events in order."""
        return tuple(self._events)

    @property
    def chunk_content(self) -> str:
        """Reconstruct full response from chunk events."""
        return "".join(self._chunks)

    @property
    def sources_list(self) -> list[str]:
        """Get list of source documents."""
        if self._sources_event is None:
            return []
        return self._sources_event.sources or []

    @property
    def token_count(self) -> int:
        """Get total token count from done event."""
        if self._done_event is None:
            return 0
        return self._done_event.token_count or 0

    @property
    def has_error(self) -> bool:
        """Check if stream ended with error."""
        return self._error_event is not None

    @property
    def error_code(self) -> str | None:
        """Get error code if any."""
        return self._error_event.error if self._error_event else None

    @property
    def error_message(self) -> str | None:
        """Get error message if any."""
        return self._error_event.message if self._error_event else None
