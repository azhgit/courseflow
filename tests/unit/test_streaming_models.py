"""Unit tests for streaming response models.

Tests StreamingQuery validation and SSEEvent serialization per constitution
and task requirements (T001-T002).
"""

import json

import pytest
from pydantic import ValidationError

from courseflow.domain.models import SSEEvent, StreamingQuery


class TestStreamingQueryValidation:
    """Test StreamingQuery model validation (T001)."""

    def test_valid_streaming_query_with_all_fields(self) -> None:
        """Should create StreamingQuery with query and conversation_id."""
        query = StreamingQuery(
            query="Explain photosynthesis step by step",
            conversation_id="conv_abc123",
        )
        assert query.query == "Explain photosynthesis step by step"
        assert query.conversation_id == "conv_abc123"

    def test_valid_streaming_query_with_null_conversation_id(self) -> None:
        """Should create StreamingQuery with null conversation_id (new conversation)."""
        query = StreamingQuery(
            query="What is machine learning?",
            conversation_id=None,
        )
        assert query.query == "What is machine learning?"
        assert query.conversation_id is None

    def test_invalid_streaming_query_empty_string(self) -> None:
        """Should reject empty query string."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingQuery(query="", conversation_id=None)
        errors = exc_info.value.errors()
        assert any(
            "string_too_short" in str(err.get("type", "")) or "at least" in str(err.get("msg", ""))
            for err in errors
        )

    def test_invalid_streaming_query_whitespace_only(self) -> None:
        """Should reject whitespace-only query string."""
        with pytest.raises(ValidationError) as exc_info:
            StreamingQuery(query="   \n\t  ", conversation_id=None)
        errors = exc_info.value.errors()
        assert len(errors) > 0  # Should have validation errors from field_validator

    def test_valid_streaming_query_strips_whitespace(self) -> None:
        """Should strip leading/trailing whitespace from query."""
        query = StreamingQuery(
            query="  Explain quantum computing  \n",
            conversation_id=None,
        )
        assert query.query == "Explain quantum computing"

    def test_streaming_query_dict_conversion(self) -> None:
        """Should convert StreamingQuery to dict for API serialization."""
        query = StreamingQuery(
            query="Test query",
            conversation_id="conv_123",
        )
        query_dict = query.model_dump()
        assert query_dict == {
            "query": "Test query",
            "conversation_id": "conv_123",
        }

    def test_streaming_query_json_serialization(self) -> None:
        """Should serialize StreamingQuery to JSON."""
        query = StreamingQuery(
            query="Test query",
            conversation_id=None,
        )
        json_str = query.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed == {
            "query": "Test query",
            "conversation_id": None,
        }


class TestSSEEventSerialization:
    """Test SSEEvent model serialization (T002)."""

    def test_sse_chunk_event_creation(self) -> None:
        """Should create chunk event with content."""
        event = SSEEvent.chunk("Photosynthesis is")
        assert event.type == "chunk"
        assert event.content == "Photosynthesis is"
        # Access via model_dump to avoid classmethod name conflict
        data = event.model_dump()
        assert data["sources"] is None
        assert data["error"] is None
        assert data["token_count"] is None

    def test_sse_sources_event_creation(self) -> None:
        """Should create sources event with document list."""
        event = SSEEvent.with_sources(
            sources=["biology-photosynthesis.md"],
            retrieval_count=3,
        )
        assert event.type == "sources"
        data = event.model_dump()
        assert data["sources"] == ["biology-photosynthesis.md"]
        assert data["retrieval_count"] == 3
        assert data["content"] is None

    def test_sse_sources_event_multiple_documents(self) -> None:
        """Should create sources event with multiple documents."""
        sources = ["doc1.md", "doc2.md", "doc3.md"]
        event = SSEEvent.with_sources(sources=sources, retrieval_count=5)
        data = event.model_dump()
        assert data["sources"] == sources
        assert data["retrieval_count"] == 5

    def test_sse_done_event_creation(self) -> None:
        """Should create done event with conversation_id and token_count."""
        event = SSEEvent.done(
            conversation_id="conv_abc123",
            token_count=342,
        )
        assert event.type == "done"
        data = event.model_dump()
        assert data["conversation_id"] == "conv_abc123"
        assert data["token_count"] == 342
        assert data["content"] is None

    def test_sse_error_event_creation(self) -> None:
        """Should create error event with error code and message."""
        event = SSEEvent.failure(
            error="rate_limit_exceeded",
            message="Retry after 60s",
        )
        assert event.type == "error"
        data = event.model_dump()
        assert data["error"] == "rate_limit_exceeded"
        assert data["message"] == "Retry after 60s"
        assert data["content"] is None

    def test_sse_error_event_no_relevant_documents(self) -> None:
        """Should create error event for no relevant documents."""
        event = SSEEvent.failure(
            error="no_relevant_documents",
            message="No relevant content found for your query. Try rephrasing.",
        )
        data = event.model_dump()
        assert data["error"] == "no_relevant_documents"
        assert data["message"] == "No relevant content found for your query. Try rephrasing."

    def test_all_event_types_serialize_to_sse_format(self) -> None:
        """All event types should serialize to valid SSE format (double newline terminated)."""
        events = [
            SSEEvent.chunk("test"),
            SSEEvent.with_sources(sources=["doc.md"], retrieval_count=1),
            SSEEvent.done(conversation_id="conv_123", token_count=100),
            SSEEvent.failure(error="test_error", message="test message"),
        ]

        for event in events:
            sse_str = event.to_sse()
            # Check that each event ends with double newline (SSE format requirement)
            assert sse_str.endswith("\n\n"), f"Event {event.type} not SSE-formatted"
            # Check that each event starts with "data: "
            assert sse_str.startswith("data: "), f"Event {event.type} missing data prefix"
            # Check that it's valid JSON
            json_str = sse_str.replace("data: ", "").strip()
            parsed = json.loads(json_str)
            assert "type" in parsed

    def test_sse_event_json_valid(self) -> None:
        """All event payloads should be valid JSON."""
        test_cases = [
            (SSEEvent.chunk("test"), ["type", "content"]),
            (SSEEvent.with_sources(["doc.md"], 1), ["type", "sources", "retrieval_count"]),
            (SSEEvent.done("conv_123", 100), ["type", "conversation_id", "token_count"]),
            (SSEEvent.failure("err", "msg"), ["type", "error", "message"]),
        ]

        for event, expected_keys in test_cases:
            sse_str = event.to_sse()
            json_str = sse_str.replace("data: ", "").strip()
            parsed = json.loads(json_str)

            for key in expected_keys:
                assert key in parsed, f"Missing key '{key}' in event type '{event.type}'"

    def test_sse_event_with_special_characters(self) -> None:
        """Should handle special characters in event content."""
        special_content = 'He said "Hello", then wrote: C++ & Python\'s async/await'
        event = SSEEvent.chunk(special_content)
        sse_str = event.to_sse()

        # JSON should properly escape special characters
        json_str = sse_str.replace("data: ", "").strip()
        parsed = json.loads(json_str)
        assert parsed["content"] == special_content

    def test_sse_event_with_newlines_in_content(self) -> None:
        """Should handle newlines within chunk content."""
        content_with_newlines = "Line 1\nLine 2\nLine 3"
        event = SSEEvent.chunk(content_with_newlines)
        sse_str = event.to_sse()

        json_str = sse_str.replace("data: ", "").strip()
        parsed = json.loads(json_str)
        assert parsed["content"] == content_with_newlines

    def test_sse_event_multiple_sources(self) -> None:
        """Should handle multiple sources in sources event."""
        sources = ["bio.md", "chem.md", "physics.md"]
        event = SSEEvent.with_sources(sources=sources, retrieval_count=10)
        sse_str = event.to_sse()

        json_str = sse_str.replace("data: ", "").strip()
        parsed = json.loads(json_str)
        assert parsed["sources"] == sources
        assert len(parsed["sources"]) == 3


class TestSSEEventModel:
    """Additional tests for SSEEvent model structure."""

    def test_sse_event_immutable(self) -> None:
        """SSEEvent should be immutable (frozen model)."""
        event = SSEEvent.chunk("test")
        # Attempting to modify a frozen model should raise error
        with pytest.raises((ValueError, TypeError, AttributeError)):
            event.type = "done"  # type: ignore

    def test_sse_event_default_none_fields(self) -> None:
        """Non-relevant fields should default to None."""
        event = SSEEvent.chunk("content")
        data = event.model_dump()
        assert data["sources"] is None
        assert data["retrieval_count"] is None
        assert data["error"] is None
        assert data["message"] is None
        assert data["conversation_id"] is None

    def test_sse_event_equality(self) -> None:
        """Same events should be equal."""
        event1 = SSEEvent.chunk("test")
        event2 = SSEEvent.chunk("test")
        assert event1 == event2

    def test_sse_event_different_events_not_equal(self) -> None:
        """Different events should not be equal."""
        event1 = SSEEvent.chunk("test1")
        event2 = SSEEvent.chunk("test2")
        assert event1 != event2
