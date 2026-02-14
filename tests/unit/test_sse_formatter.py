"""Unit tests for SSE formatter utilities.

Tests SSE event formatting, streaming, and event buffering per T004.
"""

import pytest

from courseflow.domain.models import SSEEvent
from courseflow.infrastructure.sse import SSEEventBuffer, emit_chunk, emit_completion, emit_error, emit_sources, stream_sse_events


class TestSSEEventFactories:
    """Test convenience factory functions for SSE events (T004)."""

    @pytest.mark.asyncio
    async def test_emit_chunk_creates_chunk_event(self) -> None:
        """Should create chunk event via factory."""
        event = await emit_chunk("test content")
        assert event.type == "chunk"
        assert event.content == "test content"

    @pytest.mark.asyncio
    async def test_emit_sources_creates_sources_event(self) -> None:
        """Should create sources event via factory."""
        event = await emit_sources(["doc1.md", "doc2.md"], 5)
        assert event.type == "sources"
        assert event.model_dump()["sources"] == ["doc1.md", "doc2.md"]
        assert event.model_dump()["retrieval_count"] == 5

    @pytest.mark.asyncio
    async def test_emit_completion_creates_done_event(self) -> None:
        """Should create done event via factory."""
        event = await emit_completion("conv_123", 256)
        assert event.type == "done"
        assert event.model_dump()["conversation_id"] == "conv_123"
        assert event.model_dump()["token_count"] == 256

    @pytest.mark.asyncio
    async def test_emit_error_creates_error_event(self) -> None:
        """Should create error event via factory."""
        event = await emit_error("timeout", "Request exceeded 30 seconds")
        assert event.type == "error"
        assert event.model_dump()["error"] == "timeout"
        assert event.model_dump()["message"] == "Request exceeded 30 seconds"


class TestStreamSSEEvents:
    """Test SSE event streaming functionality (T004)."""

    @pytest.mark.asyncio
    async def test_stream_single_chunk_event(self) -> None:
        """Should stream a single chunk event with SSE formatting."""

        async def event_gen():
            yield SSEEvent.chunk("test")

        results = []
        async for sse_str in stream_sse_events(event_gen()):
            results.append(sse_str)

        assert len(results) == 1
        assert results[0].startswith("data: ")
        assert results[0].endswith("\n\n")
        assert "chunk" in results[0]
        assert "test" in results[0]

    @pytest.mark.asyncio
    async def test_stream_multiple_chunks(self) -> None:
        """Should stream multiple chunk events in order."""

        async def event_gen():
            yield SSEEvent.chunk("Hello")
            yield SSEEvent.chunk(" ")
            yield SSEEvent.chunk("world")

        results = []
        async for sse_str in stream_sse_events(event_gen()):
            results.append(sse_str)

        assert len(results) == 3
        assert all(s.startswith("data: ") for s in results)
        assert all(s.endswith("\n\n") for s in results)

    @pytest.mark.asyncio
    async def test_stream_complete_sequence(self) -> None:
        """Should stream chunk → sources → done sequence correctly."""

        async def event_gen():
            yield SSEEvent.chunk("Photosynthesis")
            yield SSEEvent.chunk(" is")
            yield SSEEvent.chunk(" a process")
            yield SSEEvent.with_sources(["bio.md"], 3)
            yield SSEEvent.done("conv_123", 100)

        results = []
        async for sse_str in stream_sse_events(event_gen()):
            results.append(sse_str)

        assert len(results) == 5
        # Verify order
        assert "chunk" in results[0]
        assert "chunk" in results[1]
        assert "chunk" in results[2]
        assert "sources" in results[3]
        assert "done" in results[4]

    @pytest.mark.asyncio
    async def test_stream_error_sequence(self) -> None:
        """Should stream error event properly."""

        async def event_gen():
            yield SSEEvent.chunk("Partial")
            yield SSEEvent.failure("timeout", "Timeout exceeded")

        results = []
        async for sse_str in stream_sse_events(event_gen()):
            results.append(sse_str)

        assert len(results) == 2
        assert "chunk" in results[0]
        assert "error" in results[1]
        assert "timeout" in results[1]


class TestSSEEventBuffer:
    """Test SSEEventBuffer for event collection and tracking (T004)."""

    def test_buffer_creation_empty(self) -> None:
        """Should create empty buffer."""
        buf = SSEEventBuffer()
        assert len(buf.all_events) == 0
        assert buf.chunk_content == ""
        assert buf.sources_list == []
        assert buf.token_count == 0
        assert not buf.has_error

    def test_buffer_collect_chunks(self) -> None:
        """Should collect and concatenate chunk events."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("Hello"))
        buf.collect(SSEEvent.chunk(" "))
        buf.collect(SSEEvent.chunk("world"))

        assert buf.chunk_content == "Hello world"
        assert len(buf.all_events) == 3

    def test_buffer_collect_sources(self) -> None:
        """Should collect sources event."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("test"))
        buf.collect(SSEEvent.with_sources(["doc1.md", "doc2.md"], 5))

        assert buf.sources_list == ["doc1.md", "doc2.md"]
        assert len(buf.all_events) == 2

    def test_buffer_collect_done(self) -> None:
        """Should collect done event and track token count."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("test"))
        buf.collect(SSEEvent.done("conv_123", 256))

        assert buf.token_count == 256
        assert len(buf.all_events) == 2

    def test_buffer_collect_error(self) -> None:
        """Should track error event."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("partial"))
        buf.collect(SSEEvent.failure("timeout", "Exceeded 30s"))

        assert buf.has_error
        assert buf.error_code == "timeout"
        assert buf.error_message == "Exceeded 30s"

    def test_buffer_complete_successful_sequence(self) -> None:
        """Should track complete successful streaming sequence."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("Photosynthesis"))
        buf.collect(SSEEvent.chunk(" is"))
        buf.collect(SSEEvent.chunk(" a process"))
        buf.collect(SSEEvent.with_sources(["bio.md"], 3))
        buf.collect(SSEEvent.done("conv_abc", 120))

        assert buf.chunk_content == "Photosynthesis is a process"
        assert buf.sources_list == ["bio.md"]
        assert buf.token_count == 120
        assert not buf.has_error
        assert len(buf.all_events) == 5

    def test_buffer_rejects_duplicate_sources(self) -> None:
        """Should reject multiple sources events."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.with_sources(["doc1.md"], 1))

        with pytest.raises(ValueError, match="Multiple sources events"):
            buf.collect(SSEEvent.with_sources(["doc2.md"], 1))

    def test_buffer_rejects_duplicate_done(self) -> None:
        """Should reject multiple done events."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.done("conv_1", 100))

        with pytest.raises(ValueError, match="Multiple done events"):
            buf.collect(SSEEvent.done("conv_2", 200))

    def test_buffer_rejects_duplicate_error(self) -> None:
        """Should reject multiple error events."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.failure("timeout", "msg1"))

        with pytest.raises(ValueError, match="Multiple error events"):
            buf.collect(SSEEvent.failure("rate_limit", "msg2"))

    def test_buffer_empty_sources_list_when_no_sources_event(self) -> None:
        """Should return empty sources list if no sources event collected."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("test"))
        buf.collect(SSEEvent.done("conv_123", 100))

        assert buf.sources_list == []

    def test_buffer_zero_tokens_when_no_done_event(self) -> None:
        """Should return 0 tokens if no done event collected."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("test"))

        assert buf.token_count == 0

    def test_buffer_preserves_event_order(self) -> None:
        """Should preserve order of collected events."""
        buf = SSEEventBuffer()
        events = [
            SSEEvent.chunk("a"),
            SSEEvent.chunk("b"),
            SSEEvent.with_sources(["doc.md"], 2),
            SSEEvent.done("conv_123", 50),
        ]

        for event in events:
            buf.collect(event)

        all_events = buf.all_events
        assert len(all_events) == 4
        assert all_events[0].type == "chunk"
        assert all_events[1].type == "chunk"
        assert all_events[2].type == "sources"
        assert all_events[3].type == "done"

    def test_buffer_immutable_after_all_events_property(self) -> None:
        """Should return immutable tuple from all_events property."""
        buf = SSEEventBuffer()
        buf.collect(SSEEvent.chunk("test"))

        events = buf.all_events
        assert isinstance(events, tuple)
        # Tuple is immutable
        with pytest.raises(TypeError):
            events[0] = SSEEvent.chunk("other")  # type: ignore


class TestSSEFormatting:
    """Integration tests for SSE event formatting."""

    @pytest.mark.asyncio
    async def test_formatted_sse_is_valid(self) -> None:
        """Formatted SSE events should be valid for transmission."""
        import json

        async def event_gen():
            yield SSEEvent.chunk("Hello world")

        async for sse_str in stream_sse_events(event_gen()):
            # Each line should start with "data: "
            assert sse_str.startswith("data: ")
            # Should end with double newline
            assert sse_str.endswith("\n\n")
            # Should contain valid JSON after "data: "
            json_str = sse_str[6:-2]  # Remove "data: " and "\n\n"
            parsed = json.loads(json_str)
            assert "type" in parsed

    @pytest.mark.asyncio
    async def test_unicode_in_sse_streaming(self) -> None:
        """Should handle Unicode characters in streaming."""
        async def event_gen():
            yield SSEEvent.chunk("光合作用是 photosynthesis 🌱")

        results = []
        async for sse_str in stream_sse_events(event_gen()):
            results.append(sse_str)

        assert len(results) == 1
        assert "光合作用" in results[0]
        assert "🌱" in results[0]

    @pytest.mark.asyncio
    async def test_empty_chunks_handled(self) -> None:
        """Should handle empty chunk content gracefully."""
        buf = SSEEventBuffer()
        # Empty content chunk (could happen with streaming)
        buf.collect(SSEEvent.chunk(""))

        # Should not break the buffer
        assert buf.chunk_content == ""
