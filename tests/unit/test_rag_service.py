"""Unit tests for RAG service with mocked dependencies."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from src.courseflow.domain.models import (
    Query,
    Document,
    DocumentMetadata,
    SearchResult,
    Answer,
    TokenUsage,
)
from src.courseflow.domain.exceptions import (
    NoRelevantDocumentsError,
    QuotaExceededError,
)


class TestRAGService:
    """Test RAG service orchestration with mocked dependencies."""

    @pytest.fixture
    def mock_embedding_port(self):
        """Create mock embedding port."""
        mock = AsyncMock()
        mock.generate_embedding.return_value = [0.1] * 768  # Mock embedding vector
        return mock

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_llm_port(self):
        """Create mock LLM port."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_query_repo(self):
        """Create mock query repository."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Create sample documents for testing."""
        metadata1 = DocumentMetadata(
            source="photosynthesis.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        metadata2 = DocumentMetadata(
            source="mitosis.md",
            subject="biology",
            chunk_index=0,
            total_chunks=1,
        )
        
        return [
            Document(
                doc_id="doc-1",
                content="Photosynthesis is the process by which plants convert light energy...",
                metadata=metadata1,
            ),
            Document(
                doc_id="doc-2",
                content="Mitosis is a type of cell division...",
                metadata=metadata2,
            ),
        ]

    @pytest.fixture
    def sample_search_results(self, sample_documents) -> List[SearchResult]:
        """Create sample search results."""
        return [
            SearchResult(document=sample_documents[0], similarity_score=0.85),
            SearchResult(document=sample_documents[1], similarity_score=0.65),
        ]

    @pytest.mark.asyncio
    async def test_successful_rag_query(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
        sample_search_results,
    ):
        """Test successful RAG query flow."""
        # Import here to avoid circular dependency
        from src.courseflow.application.rag_service import RAGService
        
        # Setup mocks
        mock_vector_store.search.return_value = sample_search_results
        mock_llm_port.generate_answer.return_value = (
            "Photosynthesis is the process by which plants convert light energy into chemical energy.",
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        
        # Create service
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        # Execute query
        query = Query(text="What is photosynthesis?")
        answer = await service.answer_query(query)
        
        # Verify calls
        mock_embedding_port.generate_embedding.assert_called_once_with("What is photosynthesis?")
        mock_vector_store.search.assert_called_once()
        mock_llm_port.generate_answer.assert_called_once()
        mock_query_repo.save_query.assert_called_once()
        
        # Verify result
        assert answer.query_id == query.query_id
        assert "Photosynthesis" in answer.answer_text
        assert len(answer.sources) == 2
        assert answer.token_usage.total_tokens == 150

    @pytest.mark.asyncio
    async def test_threshold_filtering(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
        sample_search_results,
    ):
        """Test that results below similarity threshold are filtered."""
        from src.courseflow.application.rag_service import RAGService
        
        # Setup mock with low-similarity results
        low_similarity_results = [
            SearchResult(
                document=sample_search_results[0].document,
                similarity_score=0.3,  # Below threshold
            )
        ]
        mock_vector_store.search.return_value = low_similarity_results
        
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        query = Query(text="Irrelevant question")
        
        # Should raise NoRelevantDocumentsError
        with pytest.raises(NoRelevantDocumentsError) as exc_info:
            await service.answer_query(query)
        
        assert "0.5" in str(exc_info.value) or "threshold" in str(exc_info.value).lower()
        
        # LLM should not be called if no relevant documents
        mock_llm_port.generate_answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
    ):
        """Test handling of empty search results."""
        from src.courseflow.application.rag_service import RAGService
        
        mock_vector_store.search.return_value = []
        
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        query = Query(text="Unknown topic")
        
        with pytest.raises(NoRelevantDocumentsError):
            await service.answer_query(query)

    @pytest.mark.asyncio
    async def test_llm_quota_exceeded(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
        sample_search_results,
    ):
        """Test handling of LLM quota exceeded error."""
        from src.courseflow.application.rag_service import RAGService
        
        mock_vector_store.search.return_value = sample_search_results
        mock_llm_port.generate_answer.side_effect = QuotaExceededError(
            message="Gemini API quota exceeded",
            retry_after=60,
        )
        
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        query = Query(text="What is photosynthesis?")
        
        with pytest.raises(QuotaExceededError) as exc_info:
            await service.answer_query(query)
        
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_retrieval_count_logging(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
        sample_search_results,
    ):
        """Test that retrieval count is properly logged."""
        from src.courseflow.application.rag_service import RAGService
        
        mock_vector_store.search.return_value = sample_search_results
        mock_llm_port.generate_answer.return_value = (
            "Answer text",
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        query = Query(text="What is photosynthesis?")
        answer = await service.answer_query(query)
        
        # Verify that 2 sources were returned (both above threshold)
        assert len(answer.sources) == 2
        assert answer.sources[0].similarity_score == 0.85
        assert answer.sources[1].similarity_score == 0.65

    @pytest.mark.asyncio
    async def test_similarity_scores_included(
        self,
        mock_embedding_port,
        mock_vector_store,
        mock_llm_port,
        mock_query_repo,
        sample_search_results,
    ):
        """Test that similarity scores are preserved in results."""
        from src.courseflow.application.rag_service import RAGService
        
        mock_vector_store.search.return_value = sample_search_results
        mock_llm_port.generate_answer.return_value = (
            "Answer",
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        
        service = RAGService(
            embedding_port=mock_embedding_port,
            vector_store=mock_vector_store,
            llm_port=mock_llm_port,
            query_repo=mock_query_repo,
            similarity_threshold=0.5,
        )
        
        query = Query(text="Test query")
        answer = await service.answer_query(query)
        
        # Verify similarity scores are included
        scores = [source.similarity_score for source in answer.sources]
        assert scores == [0.85, 0.65]
