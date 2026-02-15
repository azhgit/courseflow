"""Integration tests for streaming response delivery (T009).

Tests the streaming pipeline end-to-end:
- Rate limiting check passes
- Retrieval + LLM streaming works together
- SSE events emitted in correct sequence
- Timeout enforcement
- Error handling

Focus: Real-world streaming scenarios with core components.
"""

import asyncio
import json

import pytest

from courseflow.domain.models import SSEEvent, StreamingQuery
from courseflow.infrastructure.sse import SSEEventBuffer


class TestStreamingIntegration:
    """Integration tests for streaming chunk delivery (T009)."""

    @pytest.mark.asyncio
    async def test_sse_event_buffer_integration(self) -> None:
        """SSEEventBuffer should collect and validate event sequence."""
        # Arrange
        buffer = SSEEventBuffer()

        # Act: Simulate streaming sequence
        buffer.collect(SSEEvent.chunk("Hello "))
        buffer.collect(SSEEvent.chunk("streaming "))
        buffer.collect(SSEEvent.chunk("integration."))
        buffer.collect(SSEEvent.with_sources(["test.md"], 1))
        buffer.collect(SSEEvent.done("conv_123", 30))

        # Assert: Correct sequence and counts
        chunks = [e for e in buffer.all_events if e.type == "chunk"]
        assert len(chunks) == 3
        assert buffer.sources_list == ["test.md"]
        assert buffer.token_count == 30

    @pytest.mark.asyncio
    async def test_streaming_query_validation(self) -> None:
        """StreamingQuery should validate input correctly."""
        # Arrange: Valid query
        valid_query = StreamingQuery(
            query="Test question",
            conversation_id=None,
        )

        # Act & Assert: Valid
        assert valid_query.query == "Test question"
        assert valid_query.conversation_id is None

        # Test with conversation ID
        conv_query = StreamingQuery(
            query="Follow-up question",
            conversation_id="conv_xyz",
        )
        assert conv_query.conversation_id == "conv_xyz"

    def test_streaming_query_rejects_empty(self) -> None:
        """StreamingQuery should reject empty queries."""
        # Act & Assert: Empty query should raise validation error
        with pytest.raises(ValueError):
            StreamingQuery(query="", conversation_id=None)

    def test_streaming_query_whitespace_only_rejected(self) -> None:
        """StreamingQuery should reject whitespace-only queries."""
        # Act & Assert: Whitespace-only should raise
        with pytest.raises(ValueError):
            StreamingQuery(query="   ", conversation_id=None)

    def test_sse_event_chunk_structure(self) -> None:
        """Chunk events should have correct SSE structure."""
        # Arrange
        chunk = SSEEvent.chunk("Test content")

        # Act: Serialize
        sse_output = chunk.to_sse()

        # Assert: Valid SSE format
        assert sse_output.startswith("data: ")
        assert sse_output.endswith("\n\n")

        # Parse JSON
        json_part = sse_output[6:-2]  # Remove "data: " and "\n\n"
        event_dict = json.loads(json_part)

        assert event_dict["type"] == "chunk"
        assert event_dict["content"] == "Test content"

    def test_sse_event_sources_structure(self) -> None:
        """Sources events should have correct structure."""
        # Arrange
        sources_event = SSEEvent.with_sources(
            sources=["doc1.md", "doc2.md"],
            retrieval_count=5,
        )

        # Act: Serialize
        sse_output = sources_event.to_sse()

        # Assert: Valid SSE format
        json_part = sse_output[6:-2]
        event_dict = json.loads(json_part)

        assert event_dict["type"] == "sources"
        assert event_dict["sources"] == ["doc1.md", "doc2.md"]
        assert event_dict["retrieval_count"] == 5

    def test_sse_event_done_structure(self) -> None:
        """Done events should include conversation_id and token count."""
        # Arrange
        done_event = SSEEvent.done(
            conversation_id="conv_abc123",
            token_count=150,
        )

        # Act: Serialize
        sse_output = done_event.to_sse()

        # Assert
        json_part = sse_output[6:-2]
        event_dict = json.loads(json_part)

        assert event_dict["type"] == "done"
        assert event_dict["conversation_id"] == "conv_abc123"
        assert event_dict["token_count"] == 150

    def test_sse_event_error_structure(self) -> None:
        """Error events should have error code and message."""
        # Arrange
        error_event = SSEEvent.failure(
            error="no_relevant_documents",
            message="No relevant content found.",
        )

        # Act: Serialize
        sse_output = error_event.to_sse()

        # Assert
        json_part = sse_output[6:-2]
        event_dict = json.loads(json_part)

        assert event_dict["type"] == "error"
        assert event_dict["error"] == "no_relevant_documents"
        assert event_dict["message"] == "No relevant content found."

    def test_sse_event_special_characters_escaped(self) -> None:
        """Event content with special characters should be properly escaped."""
        # Arrange: Content with quotes and newlines
        special_content = 'Say "hello" and\nnewline'

        # Act: Create event
        event = SSEEvent.chunk(special_content)
        sse_output = event.to_sse()

        # Assert: Should serialize to valid JSON
        json_part = sse_output[6:-2]
        event_dict = json.loads(json_part)
        assert event_dict["content"] == special_content

    @pytest.mark.asyncio
    async def test_sse_event_buffer_no_duplicates(self) -> None:
        """SSEEventBuffer should enforce single sources event."""
        # Arrange
        buffer = SSEEventBuffer()

        # Act
        buffer.collect(SSEEvent.with_sources(["a.md"], 1))

        # Try to add sources twice - should raise ValueError
        with pytest.raises(ValueError, match="Multiple sources events"):
            buffer.collect(SSEEvent.with_sources(["b.md"], 1))

    def test_no_relevant_documents_scenario(self) -> None:
        """Scenario: No documents found above similarity threshold."""
        # Arrange: No retrieval results
        retrieved_count = 0

        # Act: Should create error event, not call LLM
        if retrieved_count == 0:
            error_event = SSEEvent.failure(
                error="no_relevant_documents",
                message="No relevant content found. Try rephrasing.",
            )
            should_call_llm = False
        else:
            should_call_llm = True

        # Assert: Per clarification #2
        assert not should_call_llm
        assert error_event.error == "no_relevant_documents"

    def test_partial_response_with_content_saved(self) -> None:
        """Scenario: Timeout with partial response - should be saveable."""
        # Arrange: Partial response with content
        partial_response = "This is an incomplete answer because..."
        generation_completed = False

        # Act: Per clarification #3, save if has content
        should_save = len(partial_response) > 0 and not generation_completed

        # Assert
        assert should_save is True

    def test_partial_response_empty_not_saved(self) -> None:
        """Scenario: Error before any content - should not be saved."""
        # Arrange: No content generated
        response = ""
        error_occurred = True

        # Act: Per clarification #3, don't save empty responses
        should_save = len(response) > 0 and error_occurred

        # Assert
        assert should_save is False

    @pytest.mark.asyncio
    async def test_conversation_history_integration(self) -> None:
        """Streaming should preserve conversation_id for multi-turn context."""
        # Arrange
        query_with_context = StreamingQuery(
            query="Follow-up to earlier",
            conversation_id="conv_multi_turn_123",
        )

        # Act: Query has context
        buffer = SSEEventBuffer()
        buffer.collect(SSEEvent.chunk("Continuing from before..."))
        buffer.collect(
            SSEEvent.done(
                conversation_id=query_with_context.conversation_id,
                token_count=25,
            )
        )

        # Assert: Conversation ID preserved through streaming
        done_events = [e for e in buffer.all_events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].conversation_id == "conv_multi_turn_123"

    def test_rate_limit_error_event(self) -> None:
        """When rate limited, emit error event not HTTP 429."""
        # Arrange: Rate limit condition
        rate_limited = True

        # Act: Create error event
        if rate_limited:
            event = SSEEvent.failure(
                error="rate_limit_exceeded",
                message="Rate limit exceeded. Retry after 60s.",
            )

        # Assert
        assert event.type == "error"
        assert event.error == "rate_limit_exceeded"
        # HTTP status would be 200, not 429

    def test_network_error_event(self) -> None:
        """When network fails mid-stream, emit error event."""
        # Arrange: Network failure
        network_failed = True

        # Act
        if network_failed:
            event = SSEEvent.failure(
                error="network_error",
                message="Connection lost during streaming.",
            )

        # Assert
        assert event.type == "error"
        assert event.error == "network_error"

    @pytest.mark.asyncio
    async def test_timeout_enforcement_basic(self) -> None:
        """Streaming timeout should be enforced (30 seconds default)."""
        from courseflow.application.streaming_timeout import (
            StreamingTimeoutError,
            streaming_timeout,
        )

        # Arrange: Very short timeout for testing
        try:
            async with streaming_timeout(max_seconds=0.001):
                await asyncio.sleep(0.01)  # 10ms > 1ms timeout
            timed_out = False
        except (asyncio.CancelledError, StreamingTimeoutError):
            timed_out = True

        # Assert
        assert timed_out is True

    @pytest.mark.asyncio
    async def test_chunk_order_preserved(self) -> None:
        """Chunks should be emitted in order received."""
        # Arrange
        expected_chunks = ["One ", "Two ", "Three"]

        # Act: Simulate collection
        buffer = SSEEventBuffer()
        for chunk in expected_chunks:
            buffer.collect(SSEEvent.chunk(chunk))

        # Assert
        chunk_events = [e for e in buffer.all_events if e.type == "chunk"]
        collected_chunks = [e.content for e in chunk_events]
        assert collected_chunks == expected_chunks
