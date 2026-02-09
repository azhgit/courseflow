"""Unit tests for domain models."""

import pytest
from uuid import UUID
from pydantic import ValidationError

from src.courseflow.domain.models import (
    Query,
    Document,
    DocumentMetadata,
    SearchResult,
    Answer,
    TokenUsage,
    RateLimitTracker,
)


class TestQueryModel:
    """Test Query model validation."""

    def test_valid_query(self):
        """Test valid query creation."""
        query = Query(text="What is photosynthesis?")
        assert query.text == "What is photosynthesis?"
        assert query.query_id is not None

    def test_empty_text_rejection(self):
        """Test that empty query text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Query(text="")
        assert "text" in str(exc_info.value)

    def test_whitespace_only_rejection(self):
        """Test that whitespace-only query is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Query(text="   ")
        assert "text" in str(exc_info.value)

    def test_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed."""
        query = Query(text="  What is photosynthesis?  ")
        assert query.text == "What is photosynthesis?"

    def test_max_length_validation(self):
        """Test that query exceeding 1000 characters is rejected."""
        long_text = "a" * 1001
        with pytest.raises(ValidationError) as exc_info:
            Query(text=long_text)
        assert "1000" in str(exc_info.value) or "max_length" in str(exc_info.value)

    def test_max_length_boundary(self):
        """Test that 1000 character query is accepted."""
        boundary_text = "a" * 1000
        query = Query(text=boundary_text)
        assert len(query.text) == 1000

    def test_query_id_generation(self):
        """Test that query_id is auto-generated if not provided."""
        query1 = Query(text="Test 1")
        query2 = Query(text="Test 2")
        assert query1.query_id != query2.query_id
        assert query1.query_id is not None
        assert isinstance(query1.query_id, UUID)


class TestDocumentModel:
    """Test Document model."""

    def test_valid_document(self):
        """Test valid document creation."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Photosynthesis is the process...",
            metadata=metadata,
        )
        assert doc.doc_id == "test-1"
        assert doc.content.startswith("Photosynthesis")
        assert doc.metadata.source == "test.md"

    def test_document_without_embedding(self):
        """Test document can be created without embedding vector."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Test content",
            metadata=metadata,
        )
        assert doc.embedding is None


class TestSearchResultModel:
    """Test SearchResult model."""

    def test_valid_search_result(self):
        """Test valid search result creation."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Photosynthesis content",
            metadata=metadata,
        )
        result = SearchResult(
            document=doc,
            similarity_score=0.85,
        )
        assert result.similarity_score == 0.85
        assert result.document.doc_id == "test-1"

    def test_similarity_score_validation(self):
        """Test similarity score must be between 0 and 1."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Test",
            metadata=metadata,
        )
        
        # Valid scores
        SearchResult(document=doc, similarity_score=0.0)
        SearchResult(document=doc, similarity_score=0.5)
        SearchResult(document=doc, similarity_score=1.0)
        
        # Invalid scores
        with pytest.raises(ValidationError):
            SearchResult(document=doc, similarity_score=-0.1)
        with pytest.raises(ValidationError):
            SearchResult(document=doc, similarity_score=1.1)


class TestAnswerModel:
    """Test Answer model."""

    def test_valid_answer(self):
        """Test valid answer creation."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Photosynthesis content",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        answer = Answer(
            query_id="q-123",
            answer_text="Photosynthesis is...",
            sources=[search_result],
            latency_ms=1500,
        )
        
        assert answer.query_id == "q-123"
        assert answer.answer_text == "Photosynthesis is..."
        assert len(answer.sources) == 1
        assert answer.latency_ms == 1500

    def test_answer_with_token_usage(self):
        """Test answer with token usage tracking."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            doc_id="test-1",
            content="Test content",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        token_usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        
        answer = Answer(
            query_id="q-123",
            answer_text="Test answer",
            sources=[search_result],
            latency_ms=1500,
            token_usage=token_usage,
        )
        
        assert answer.token_usage.total_tokens == 150


class TestRateLimitTracker:
    """Test RateLimitTracker model."""

    def test_rate_limit_initialization(self):
        """Test rate limit tracker initialization."""
        tracker = RateLimitTracker(
            requests_per_minute=15,
            requests_per_day=1500,
        )
        assert tracker.requests_per_minute == 15
        assert tracker.requests_per_day == 1500
        assert len(tracker.request_timestamps) == 0

    def test_add_request_timestamp(self):
        """Test adding request timestamps."""
        tracker = RateLimitTracker(
            requests_per_minute=15,
            requests_per_day=1500,
        )
        import time
        timestamp = time.time()
        tracker.request_timestamps.append(timestamp)
        assert len(tracker.request_timestamps) == 1
        assert tracker.request_timestamps[0] == timestamp
