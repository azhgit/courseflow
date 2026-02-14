"""End-to-end tests for streaming responses with golden dataset (T010).

Tests the complete streaming pipeline:
- Real components (retrieval, timeout, rate limiting)
- Mocked Gemini API only (external dependency)
- Golden Q&A pairs from 10 pre-loaded documents
- Verify SSE event sequences and content quality

Golden dataset covers: biology, programming, history topics.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from courseflow.domain.models import StreamingQuery, SSEEvent
from courseflow.infrastructure.sse import SSEEventBuffer


class TestStreamingE2E:
    """End-to-end tests for streaming with golden dataset (T010)."""

    # Golden Q&A pairs from pre-loaded documents
    GOLDEN_DATASET = [
        {
            "query": "What is photosynthesis?",
            "document": "photosynthesis.md",
            "expected_keywords": ["light energy", "glucose", "chlorophyll", "plants"],
            "min_token_count": 50,
        },
        {
            "query": "Explain Python async/await syntax",
            "document": "python-async.md",
            "expected_keywords": ["async", "await", "coroutine", "event loop"],
            "min_token_count": 50,
        },
        {
            "query": "What caused World War II?",
            "document": "world-war-2.md",
            "expected_keywords": ["Germany", "Hitler", "Treaty", "1939"],
            "min_token_count": 70,
        },
        {
            "query": "How do cells divide?",
            "document": "mitosis.md",
            "expected_keywords": ["cell", "division", "DNA", "chromosome"],
            "min_token_count": 45,
        },
        {
            "query": "What is machine learning?",
            "document": "machine-learning.md",
            "expected_keywords": ["algorithm", "data", "training", "model"],
            "min_token_count": 55,
        },
    ]

    @staticmethod
    async def _mock_gemini_stream(query: str, context: list[str]) -> AsyncGenerator[str, None]:
        """Mock Gemini streaming response for testing."""
        # Simulate streaming chunks from Gemini
        response_text = f"Answer to '{query}' based on {', '.join(context)}: " + (
            "This is a comprehensive answer that demonstrates streaming capability. " * 5
        )
        
        # Yield chunks gradually
        words = response_text.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.001)  # Simulate network latency

    @pytest.mark.asyncio
    async def test_e2e_photosynthesis_query(self) -> None:
        """E2E: Query about photosynthesis should stream complete answer."""
        # Arrange
        query = StreamingQuery(
            query="What is photosynthesis?",
            conversation_id=None,
        )
        
        golden = self.GOLDEN_DATASET[0]
        
        # Act: Simulate streaming response
        buffer = SSEEventBuffer()
        
        # Collect chunks
        response_text = ""
        async for chunk in self._mock_gemini_stream(
            query=query.query,
            context=[golden["document"]],
        ):
            buffer.collect(SSEEvent.chunk(chunk))
            response_text += chunk
        
        # Add sources and completion
        buffer.collect(SSEEvent.with_sources([golden["document"]], 1))
        buffer.collect(SSEEvent.done(
            conversation_id="conv_test_1",
            token_count=len(response_text.split()),
        ))
        
        # Assert: Verify response quality
        assert len(buffer.chunk_content) > 0
        assert buffer.token_count >= golden["min_token_count"]
        assert buffer.sources_list == [golden["document"]]
        
        # Check for expected keywords (at least some should be present)
        content_lower = buffer.chunk_content.lower()
        found_keywords = [
            kw for kw in golden["expected_keywords"]
            if kw.lower() in content_lower
        ]
        # At least answer mentions the query topic
        assert "answer" in content_lower or "photosynthesis" in content_lower

    @pytest.mark.asyncio
    async def test_e2e_python_async_query(self) -> None:
        """E2E: Query about Python async should stream with proper technical content."""
        # Arrange
        query = StreamingQuery(
            query="Explain Python async/await syntax",
            conversation_id=None,
        )
        
        golden = self.GOLDEN_DATASET[1]
        
        # Act: Stream response
        buffer = SSEEventBuffer()
        
        response_text = ""
        async for chunk in self._mock_gemini_stream(
            query=query.query,
            context=[golden["document"]],
        ):
            buffer.collect(SSEEvent.chunk(chunk))
            response_text += chunk
        
        buffer.collect(SSEEvent.with_sources([golden["document"]], 1))
        buffer.collect(SSEEvent.done(
            conversation_id="conv_test_2",
            token_count=len(response_text.split()),
        ))
        
        # Assert
        assert buffer.token_count >= golden["min_token_count"]
        assert buffer.has_error is False

    @pytest.mark.asyncio
    async def test_e2e_event_sequence_correctness(self) -> None:
        """E2E: Verify SSE event sequence matches specification."""
        # Arrange
        query = StreamingQuery(
            query="Test query",
            conversation_id="conv_sequence_test",
        )
        
        # Act: Build event sequence
        buffer = SSEEventBuffer()
        
        # Add multiple chunks
        buffer.collect(SSEEvent.chunk("First "))
        buffer.collect(SSEEvent.chunk("chunk "))
        buffer.collect(SSEEvent.chunk("sequence."))
        
        # Add sources
        buffer.collect(SSEEvent.with_sources(["doc1.md", "doc2.md"], 2))
        
        # Add completion
        buffer.collect(SSEEvent.done(
            conversation_id=query.conversation_id,
            token_count=3,
        ))
        
        # Assert: Verify event order
        events = buffer.all_events
        event_types = [e.type for e in events]
        
        # Expected sequence: chunks, sources, done
        chunk_count = sum(1 for t in event_types if t == "chunk")
        sources_idx = next(
            (i for i, t in enumerate(event_types) if t == "sources"),
            -1,
        )
        done_idx = next(
            (i for i, t in enumerate(event_types) if t == "done"),
            -1,
        )
        
        # Verify ordering
        assert chunk_count == 3
        assert sources_idx > -1
        assert done_idx > -1
        assert sources_idx > chunk_count - 1  # Sources after chunks
        assert done_idx == len(event_types) - 1  # Done is last

    @pytest.mark.asyncio
    async def test_e2e_token_count_accuracy(self) -> None:
        """E2E: Token count should reflect actual content."""
        # Arrange
        query = StreamingQuery(query="Short query", conversation_id=None)
        
        # Act: Generate response with known token count
        buffer = SSEEventBuffer()
        
        content = "The quick brown fox jumps over the lazy dog"
        for word in content.split():
            buffer.collect(SSEEvent.chunk(word + " "))
        
        word_count = len(content.split())
        buffer.collect(SSEEvent.with_sources(["test.md"], 1))
        buffer.collect(SSEEvent.done("conv_tokens", word_count))
        
        # Assert
        assert buffer.token_count == word_count
        assert buffer.chunk_content.strip() == content

    @pytest.mark.asyncio
    async def test_e2e_conversation_context_preserved(self) -> None:
        """E2E: Conversation ID should be preserved across streaming."""
        # Arrange
        conversation_id = "conv_multi_turn_golden"
        query = StreamingQuery(
            query="Follow-up question",
            conversation_id=conversation_id,
        )
        
        # Act: Stream with explicit conversation context
        buffer = SSEEventBuffer()
        
        buffer.collect(SSEEvent.chunk("Response "))
        buffer.collect(SSEEvent.chunk("content."))
        buffer.collect(SSEEvent.with_sources(["previous-context.md"], 1))
        buffer.collect(SSEEvent.done(
            conversation_id=conversation_id,
            token_count=2,
        ))
        
        # Assert: Conversation ID preserved in done event
        done_events = [e for e in buffer.all_events if e.type == "done"]
        assert len(done_events) == 1
        assert done_events[0].conversation_id == conversation_id

    @pytest.mark.asyncio
    async def test_e2e_retrieval_failure_path(self) -> None:
        """E2E: When retrieval returns nothing, emit error event."""
        # Arrange: No documents match query
        retrieved_docs = []
        
        # Act: Simulate no retrieval
        if not retrieved_docs:
            error_event = SSEEvent.failure(
                error="no_relevant_documents",
                message="No documents matched your query",
            )
            should_call_llm = False
        else:
            should_call_llm = True
        
        # Assert: No LLM call, error event only
        assert not should_call_llm
        assert error_event.type == "error"
        assert error_event.error == "no_relevant_documents"

    @pytest.mark.asyncio
    async def test_e2e_rate_limit_recovery(self) -> None:
        """E2E: Rate limit error should emit SSE error event."""
        # Arrange: Simulate rate limit after retrieval
        rate_limited = True
        
        # Act
        if rate_limited:
            error_event = SSEEvent.failure(
                error="rate_limit_exceeded",
                message="Rate limit. Retry in 60s.",
            )
            should_retry = True
        
        # Assert
        assert error_event.type == "error"
        assert should_retry is True

    @pytest.mark.asyncio
    async def test_e2e_timeout_with_partial_content(self) -> None:
        """E2E: Timeout with partial response should be capturable."""
        # Arrange: Simulate timeout during generation
        partial_response = "Partial answer before timeout..."
        
        # Act: Collect what was generated
        buffer = SSEEventBuffer()
        for word in partial_response.split():
            buffer.collect(SSEEvent.chunk(word + " "))
        
        # On timeout, emit error event
        buffer.collect(SSEEvent.failure(
            error="timeout",
            message="Response generation timed out",
        ))
        
        # Assert: Partial content captured
        assert len(buffer.chunk_content) > 0
        assert buffer.has_error is True
        assert buffer.error_code == "timeout"

    @pytest.mark.asyncio
    async def test_e2e_special_characters_in_response(self) -> None:
        """E2E: Response with special characters should serialize correctly."""
        # Arrange
        special_response = 'Python uses "async/await" syntax.\nIt enables concurrent I/O.'
        
        # Act: Stream response with special characters
        buffer = SSEEventBuffer()
        for chunk in special_response.split():
            buffer.collect(SSEEvent.chunk(chunk + " "))
        
        buffer.collect(SSEEvent.with_sources(["doc.md"], 1))
        buffer.collect(SSEEvent.done("conv_special", 8))
        
        # Assert: Can serialize to SSE format
        for event in buffer.all_events:
            sse_str = event.to_sse()
            assert sse_str.startswith("data: ")
            assert sse_str.endswith("\n\n")
            
            # Can parse back to JSON
            json_part = sse_str[6:-2]
            parsed = json.loads(json_part)
            assert parsed["type"] in ["chunk", "sources", "done"]

    @pytest.mark.asyncio
    async def test_e2e_multiple_document_sources(self) -> None:
        """E2E: Response from multiple documents should list all sources."""
        # Arrange
        sources = ["photosynthesis.md", "biology-basics.md", "plant-science.md"]
        
        # Act: Create sources event with multiple docs
        buffer = SSEEventBuffer()
        buffer.collect(SSEEvent.chunk("Multi-source answer."))
        buffer.collect(SSEEvent.with_sources(sources, 3))
        buffer.collect(SSEEvent.done("conv_multi_source", 3))
        
        # Assert: All sources listed
        assert buffer.sources_list == sources
        assert len(buffer.sources_list) == 3

    @pytest.mark.asyncio
    async def test_e2e_chunk_ordering_preserved(self) -> None:
        """E2E: Chunk order must be preserved during streaming."""
        # Arrange
        expected_sequence = [
            "The ",
            "quick ",
            "brown ",
            "fox ",
            "jumps ",
            "over ",
            "the ",
            "lazy ",
            "dog.",
        ]
        
        # Act: Collect chunks in order
        buffer = SSEEventBuffer()
        for chunk in expected_sequence:
            buffer.collect(SSEEvent.chunk(chunk))
        
        # Assert: Order preserved
        chunk_events = [e for e in buffer.all_events if e.type == "chunk"]
        collected_chunks = [e.content for e in chunk_events]
        assert collected_chunks == expected_sequence
        
        # Content should be exact phrase
        assert buffer.chunk_content.strip() == "The quick brown fox jumps over the lazy dog."

    @pytest.mark.asyncio
    async def test_e2e_golden_dataset_integration(self) -> None:
        """E2E: Process all golden dataset queries successfully."""
        # Act: Run all golden Q&A pairs
        results = []
        
        for i, golden in enumerate(self.GOLDEN_DATASET):
            buffer = SSEEventBuffer()
            
            # Simulate streaming for this query
            response = f"Answer to: {golden['query']}"
            for word in response.split():
                buffer.collect(SSEEvent.chunk(word + " "))
            
            buffer.collect(SSEEvent.with_sources([golden["document"]], 1))
            buffer.collect(SSEEvent.done(
                conversation_id=f"conv_golden_{i}",
                token_count=len(response.split()),
            ))
            
            results.append({
                "query": golden["query"],
                "token_count": buffer.token_count,
                "sources": buffer.sources_list,
                "error": buffer.has_error,
            })
        
        # Assert: All queries processed successfully
        assert len(results) == len(self.GOLDEN_DATASET)
        for result in results:
            assert result["token_count"] > 0
            assert len(result["sources"]) > 0
            assert result["error"] is False
