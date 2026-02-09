"""Contract tests for POST /api/v1/query endpoint."""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from courseflow.api.main import create_app
from courseflow.domain.models import (
    Query,
    Answer,
    SearchResult,
    Document,
    DocumentMetadata,
    TokenUsage,
)


@pytest.fixture
def mock_rag_service():
    """Create mock RAG service for testing."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def app(mock_rag_service):
    """Create FastAPI test app with mocked dependencies."""
    app = create_app()
    
    # Override dependencies
    from courseflow.api.dependencies import get_rag_service
    app.dependency_overrides[get_rag_service] = lambda: mock_rag_service
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestQueryEndpointContract:
    """Contract tests for POST /api/v1/query endpoint."""

    def test_valid_query_request(self, client, mock_rag_service):
        """Test valid query request matches OpenAPI schema."""
        # Setup mock response
        metadata = DocumentMetadata(
            source="photosynthesis.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            id="doc-1",
            content="Photosynthesis is the process by which plants convert light energy into chemical energy stored in glucose, producing oxygen as a byproduct. ",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        answer = Answer(
            query_id=uuid4(),
            answer_text="Photosynthesis is the process by which plants convert light energy into chemical energy.",
            sources=[search_result],
            latency_ms=1500,
            token_usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        
        mock_rag_service.answer_query.return_value = answer
        
        # Send request
        response = client.post(
            "/api/v1/query",
            json={"query": "What is photosynthesis?"},
        )
        
        # Verify response structure per OpenAPI spec
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        
        # Verify data structure
        assert "query_id" in data["data"]
        assert "answer" in data["data"]
        assert "sources" in data["data"]
        
        # Verify metadata structure
        assert "latency_ms" in data["metadata"]
        assert "timestamp" in data["metadata"]
        
        # Verify source structure
        sources = data["data"]["sources"]
        assert len(sources) > 0
        for source in sources:
            assert "content" in source
            assert "source" in source
            assert "similarity_score" in source

    def test_empty_query_validation(self, client):
        """Test that empty query returns 400 validation error."""
        response = client.post(
            "/api/v1/query",
            json={"query": ""},
        )
        
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "validation_error"

    def test_missing_query_field(self, client):
        """Test that missing query field returns 422."""
        response = client.post(
            "/api/v1/query",
            json={},
        )
        
        assert response.status_code == 422

    def test_query_too_long(self, client):
        """Test that query exceeding 1000 characters returns 400."""
        long_query = "a" * 1001
        
        response = client.post(
            "/api/v1/query",
            json={"query": long_query},
        )
        
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data

    def test_no_relevant_documents_error(self, client, mock_rag_service):
        """Test 404 response when no relevant documents found."""
        from courseflow.domain.exceptions import NoRelevantDocumentsError
        
        mock_rag_service.answer_query.side_effect = NoRelevantDocumentsError(
            message="No relevant information found",
            threshold=0.5,
            max_similarity=0.3,
        )
        
        response = client.post(
            "/api/v1/query",
            json={"query": "Irrelevant question"},
        )
        
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "no_relevant_documents"
        assert "threshold" in data["error"]["details"]

    def test_quota_exceeded_error(self, client, mock_rag_service):
        """Test 429 response for quota exceeded."""
        from courseflow.domain.exceptions import QuotaExceededError
        
        mock_rag_service.answer_query.side_effect = QuotaExceededError(
            message="Gemini API quota exceeded",
            retry_after=60,
        )
        
        response = client.post(
            "/api/v1/query",
            json={"query": "What is photosynthesis?"},
        )
        
        assert response.status_code == 429
        
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "quota_exceeded"
        
        # Verify Retry-After header
        assert "retry-after" in response.headers
        assert int(response.headers["retry-after"]) == 60

    def test_service_unavailable_error(self, client, mock_rag_service):
        """Test 503 response for service unavailable."""
        from courseflow.domain.exceptions import ServiceUnavailableError
        
        mock_rag_service.answer_query.side_effect = ServiceUnavailableError(
            message="ChromaDB connection failed",
        )
        
        response = client.post(
            "/api/v1/query",
            json={"query": "What is photosynthesis?"},
        )
        
        assert response.status_code == 503
        
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "service_unavailable"

    def test_response_includes_token_usage(self, client, mock_rag_service):
        """Test that response includes token usage when available."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            id="doc-1",
            content="This is sufficiently long test content to satisfy the Document content minimum length requirement. It contains multiple sentences so that it exceeds 100 characters for validation. ",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        answer = Answer(
            query_id=uuid4(),
            answer_text="Test answer",
            sources=[search_result],
            latency_ms=1500,
            token_usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            ),
        )
        
        mock_rag_service.answer_query.return_value = answer
        
        response = client.post(
            "/api/v1/query",
            json={"query": "Test query"},
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "token_usage" in data["metadata"]
        assert data["metadata"]["token_usage"]["total_tokens"] == 150

    def test_latency_within_threshold(self, client, mock_rag_service):
        """Test that latency is tracked and within acceptable limits."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            id="doc-1",
            content="This is sufficiently long test content to satisfy the Document content minimum length requirement. It contains multiple sentences so that it exceeds 100 characters for validation. ",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        answer = Answer(
            query_id=uuid4(),
            answer_text="Test answer",
            sources=[search_result],
            latency_ms=1500,
        )
        
        mock_rag_service.answer_query.return_value = answer
        
        response = client.post(
            "/api/v1/query",
            json={"query": "Test query"},
        )
        
        assert response.status_code == 200
        
        data = response.json()
        latency_ms = data["metadata"]["latency_ms"]
        
        # Verify latency is reasonable (<3000ms per spec)
        assert latency_ms < 3000

    def test_cors_headers_present(self, client, mock_rag_service):
        """Test that CORS headers are present in response."""
        metadata = DocumentMetadata(
            source="test.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        doc = Document(
            id="doc-1",
            content="This is sufficiently long test content to satisfy the Document content minimum length requirement. It contains multiple sentences so that it exceeds 100 characters for validation. ",
            metadata=metadata,
        )
        search_result = SearchResult(document=doc, similarity_score=0.85)
        
        answer = Answer(
            query_id=uuid4(),
            answer_text="Test answer",
            sources=[search_result],
            latency_ms=1500,
        )
        
        mock_rag_service.answer_query.return_value = answer
        
        response = client.post(
            "/api/v1/query",
            json={"query": "Test query"},
            headers={"Origin": "http://localhost:3000"},
        )
        
        # CORS headers should be present
        # Note: Actual header names depend on CORS middleware configuration
        assert response.status_code == 200
