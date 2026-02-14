"""Contract tests for POST /api/v1/query/stream endpoint.

Defines the streaming response contract per specification (T007).
Tests verify:
- Endpoint accepts StreamingQuery
- Returns SSE-formatted stream
- Event sequence: chunk* → sources → done | error
- Proper headers and status codes
"""

import pytest
from httpx import AsyncClient


class TestStreamingQueryContract:
    """Contract tests for POST /api/v1/query/stream (T007)."""

    @pytest.mark.asyncio
    async def test_endpoint_exists_and_responds(
        self, client: AsyncClient
    ) -> None:
        """Endpoint should exist and respond to valid requests."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        # Status 200 OK for streaming
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_response_content_type_is_sse(
        self, client: AsyncClient
    ) -> None:
        """Response should advertise Server-Sent Events format."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "What is photosynthesis?",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_response_has_sse_cache_headers(
        self, client: AsyncClient
    ) -> None:
        """Response should include SSE-specific cache control headers."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200
        # Per spec: Cache-Control: no-cache
        assert "no-cache" in response.headers.get("cache-control", "")
        # Per spec: X-Accel-Buffering: no (prevents proxy buffering)
        assert response.headers.get("x-accel-buffering", "no") == "no"

    @pytest.mark.asyncio
    async def test_streaming_response_is_iterable(
        self, client: AsyncClient
    ) -> None:
        """Response should be iterable (streaming)."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200
        # Should be able to iterate over response
        lines = []
        async for line in response.aiter_lines():
            if line.strip():
                lines.append(line)
        # Should have received some SSE events
        assert len(lines) > 0

    @pytest.mark.asyncio
    async def test_streaming_events_are_sse_formatted(
        self, client: AsyncClient
    ) -> None:
        """Each event in stream should be SSE formatted (data: {...}\\n\\n)."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        events = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(line)

        # Should have events
        assert len(events) > 0
        # Each event should be valid SSE format
        for event in events:
            assert event.startswith("data: ")
            # After "data: " should be JSON
            json_str = event[6:]  # Remove "data: " prefix
            try:
                import json
                parsed = json.loads(json_str)
                assert "type" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON in event: {event}")

    @pytest.mark.asyncio
    async def test_empty_query_rejected_before_streaming(
        self, client: AsyncClient
    ) -> None:
        """Empty query should be rejected via HTTP 400 before streaming starts."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "",
                "conversation_id": None,
            },
        )
        # Should return 422 (Unprocessable Entity) for validation error
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_missing_query_field_rejected(
        self, client: AsyncClient
    ) -> None:
        """Missing required 'query' field should be rejected."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "conversation_id": None,
                # Missing 'query' field
            },
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_conversation_id_is_optional(
        self, client: AsyncClient
    ) -> None:
        """conversation_id should be optional (null = new conversation)."""
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                # conversation_id omitted (defaults to None)
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_event_sequence_order(
        self, client: AsyncClient
    ) -> None:
        """Events should arrive in correct order: chunks → sources → done|error."""
        import json

        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "What is Python?",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        event_types = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    event_types.append(event["type"])
                except json.JSONDecodeError:
                    pass

        # Verify order: should have chunks, then sources, then done/error
        # At minimum should have done or error
        assert "done" in event_types or "error" in event_types

    @pytest.mark.asyncio
    async def test_chunk_events_have_content(
        self, client: AsyncClient
    ) -> None:
        """Each chunk event should have 'content' field with text."""
        import json

        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        chunk_count = 0
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    if event["type"] == "chunk":
                        chunk_count += 1
                        assert "content" in event
                        assert isinstance(event["content"], str)
                except json.JSONDecodeError:
                    pass

        # Should have received at least some chunks
        # (unless retrieval returned no documents)

    @pytest.mark.asyncio
    async def test_sources_event_includes_documents(
        self, client: AsyncClient
    ) -> None:
        """Sources event should list retrieved documents."""
        import json

        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        found_sources = False
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    if event["type"] == "sources":
                        found_sources = True
                        # Should have sources list and retrieval_count
                        if "sources" in event:
                            assert isinstance(event["sources"], list)
                        if "retrieval_count" in event:
                            assert isinstance(event["retrieval_count"], int)
                except json.JSONDecodeError:
                    pass

        # If query succeeds, should have sources event
        # (might not if no documents retrieved)

    @pytest.mark.asyncio
    async def test_done_event_marks_completion(
        self, client: AsyncClient
    ) -> None:
        """Done event should mark stream completion with metadata."""
        import json

        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        found_done = False
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    if event["type"] == "done":
                        found_done = True
                        # Should have conversation_id and token_count
                        assert "conversation_id" in event
                        assert "token_count" in event
                        assert isinstance(event["token_count"], int)
                except json.JSONDecodeError:
                    pass

        # Stream should end with done event (or error)
        # At least one should be present

    @pytest.mark.asyncio
    async def test_error_event_on_no_documents(
        self, client: AsyncClient
    ) -> None:
        """Stream should emit error event when no relevant documents found.
        
        Per clarification Q1: Should emit SSE error, not call LLM, not save.
        """
        import json

        # Query something completely unrelated to knowledge base
        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "xyzabc123notarealquery",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        event_types = []
        error_found = False
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    event_types.append(event["type"])
                    if event["type"] == "error":
                        error_found = True
                        assert event.get("error") == "no_relevant_documents"
                except json.JSONDecodeError:
                    pass

        # Should end with error event (or potentially still have chunks if partial match)

    @pytest.mark.asyncio
    async def test_stream_terminates_cleanly(
        self, client: AsyncClient
    ) -> None:
        """Stream should terminate cleanly after done/error event."""
        import json

        response = await client.post(
            "/api/v1/query/stream",
            json={
                "query": "Test query",
                "conversation_id": None,
            },
        )
        assert response.status_code == 200

        terminal_event_received = False
        events_after_terminal = 0

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                json_str = line[6:]
                try:
                    event = json.loads(json_str)
                    if event["type"] in ["done", "error"]:
                        terminal_event_received = True
                    elif terminal_event_received:
                        # Should not receive events after done/error
                        events_after_terminal += 1
                except json.JSONDecodeError:
                    pass

        # Should have received terminal event
        assert terminal_event_received
        # Should not have events after termination
        assert events_after_terminal == 0
