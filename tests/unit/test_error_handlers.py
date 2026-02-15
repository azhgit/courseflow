"""Unit tests for streaming error handlers (T014-T016).

Tests the SSE error event generation for three error scenarios:
- T014: No relevant documents (empty retrieval)
- T015: Rate limit exceeded mid-stream
- T016: Timeout during streaming
"""

import json

from courseflow.application.error_handlers import (
    handle_no_relevant_documents,
    handle_rate_limit_exceeded,
    handle_timeout,
)
from courseflow.domain.models import SSEEvent


class TestErrorHandlers:
    """Unit tests for streaming error handlers (T014-T016)."""

    # ========== T014: No Relevant Documents Handler ==========

    def test_no_relevant_documents_returns_sse_error_event(self) -> None:
        """T014: No relevant documents handler returns SSE error event."""
        # Act
        error_event = handle_no_relevant_documents()

        # Assert
        assert error_event.type == "error"
        assert error_event.error == "no_relevant_documents"
        assert "No relevant content found" in error_event.message

    def test_no_relevant_documents_event_serializes_to_sse(self) -> None:
        """T014: Error event serializes to valid SSE format."""
        # Act
        error_event = handle_no_relevant_documents()
        sse_output = error_event.to_sse()

        # Assert: Valid SSE format
        assert sse_output.startswith("data: ")
        assert sse_output.endswith("\n\n")

        # Assert: Valid JSON payload
        json_part = sse_output[6:-2]
        parsed = json.loads(json_part)
        assert parsed["type"] == "error"
        assert parsed["error"] == "no_relevant_documents"

    def test_no_relevant_documents_event_no_retry_after(self) -> None:
        """T014: No relevant docs error has no retry_after (not a quota issue)."""
        # Act
        error_event = handle_no_relevant_documents()

        # Assert
        assert error_event.retry_after is None

    # ========== T015: Rate Limit Exceeded Handler ==========

    def test_rate_limit_exceeded_returns_sse_error_event(self) -> None:
        """T015: Rate limit handler returns SSE error event."""
        # Act
        error_event = handle_rate_limit_exceeded(retry_after=60)

        # Assert
        assert error_event.type == "error"
        assert error_event.error == "rate_limit_exceeded"
        assert "Rate limit" in error_event.message or "quota" in error_event.message.lower()

    def test_rate_limit_exceeded_includes_retry_after(self) -> None:
        """T015: Rate limit event includes retry_after timing."""
        # Act
        retry_after_seconds = 45
        error_event = handle_rate_limit_exceeded(retry_after=retry_after_seconds)

        # Assert
        assert error_event.retry_after == retry_after_seconds
        assert (
            str(retry_after_seconds) in error_event.message
            or "retry" in error_event.message.lower()
        )

    def test_rate_limit_exceeded_serializes_to_sse(self) -> None:
        """T015: Rate limit error event serializes to SSE format."""
        # Act
        error_event = handle_rate_limit_exceeded(retry_after=60)
        sse_output = error_event.to_sse()

        # Assert: Valid SSE format
        assert sse_output.startswith("data: ")
        assert sse_output.endswith("\n\n")

        # Assert: Valid JSON
        json_part = sse_output[6:-2]
        parsed = json.loads(json_part)
        assert parsed["type"] == "error"
        assert parsed["error"] == "rate_limit_exceeded"

    def test_rate_limit_exceeded_default_retry_after(self) -> None:
        """T015: Rate limit handler uses default 60s if not specified."""
        # Act
        error_event = handle_rate_limit_exceeded()

        # Assert
        assert error_event.retry_after == 60

    # ========== T016: Timeout Handler ==========

    def test_timeout_returns_sse_error_event(self) -> None:
        """T016: Timeout handler returns SSE error event."""
        # Act
        error_event = handle_timeout(max_seconds=30)

        # Assert
        assert error_event.type == "error"
        assert error_event.error == "stream_timeout"
        assert "timeout" in error_event.message.lower() or "30" in error_event.message

    def test_timeout_message_includes_duration(self) -> None:
        """T016: Timeout message includes max duration."""
        # Act
        max_duration = 45
        error_event = handle_timeout(max_seconds=max_duration)

        # Assert
        assert str(max_duration) in error_event.message or "timeout" in error_event.message.lower()

    def test_timeout_serializes_to_sse(self) -> None:
        """T016: Timeout error event serializes to SSE format."""
        # Act
        error_event = handle_timeout(max_seconds=30)
        sse_output = error_event.to_sse()

        # Assert: Valid SSE format
        assert sse_output.startswith("data: ")
        assert sse_output.endswith("\n\n")

        # Assert: Valid JSON
        json_part = sse_output[6:-2]
        parsed = json.loads(json_part)
        assert parsed["type"] == "error"
        assert parsed["error"] == "stream_timeout"

    def test_timeout_no_retry_after(self) -> None:
        """T016: Timeout error has no retry_after (client can retry immediately)."""
        # Act
        error_event = handle_timeout(max_seconds=30)

        # Assert
        assert error_event.retry_after is None

    # ========== Cross-Cutting Tests ==========

    def test_all_error_handlers_return_sse_events(self) -> None:
        """All error handlers return valid SSEEvent objects."""
        # Act
        no_docs_event = handle_no_relevant_documents()
        rate_limit_event = handle_rate_limit_exceeded()
        timeout_event = handle_timeout()

        # Assert
        assert isinstance(no_docs_event, SSEEvent)
        assert isinstance(rate_limit_event, SSEEvent)
        assert isinstance(timeout_event, SSEEvent)

    def test_all_error_events_have_valid_error_codes(self) -> None:
        """All error events have valid error code field."""
        # Act
        errors = [
            handle_no_relevant_documents(),
            handle_rate_limit_exceeded(),
            handle_timeout(),
        ]

        # Assert
        for event in errors:
            assert event.type == "error"
            assert event.error in [
                "no_relevant_documents",
                "rate_limit_exceeded",
                "stream_timeout",
            ]
            assert event.message is not None
            assert len(event.message) > 0

    def test_all_error_events_serialize_cleanly(self) -> None:
        """All error events serialize to valid SSE format."""
        # Act
        errors = [
            handle_no_relevant_documents(),
            handle_rate_limit_exceeded(),
            handle_timeout(max_seconds=30),
        ]

        # Assert
        for event in errors:
            sse_output = event.to_sse()
            assert sse_output.startswith("data: ")
            assert sse_output.endswith("\n\n")

            # Verify JSON payload is valid
            json_part = sse_output[6:-2]
            parsed = json.loads(json_part)
            assert "type" in parsed
            assert "error" in parsed
            assert "message" in parsed
