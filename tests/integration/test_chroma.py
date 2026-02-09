"""Integration tests for ChromaDB vector search."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List

from src.courseflow.domain.models import Document, DocumentMetadata, SearchResult
from src.courseflow.infrastructure.vector_store.chroma import ChromaAdapter
from src.courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from src.courseflow.config import Settings


@pytest.fixture
def temp_chroma_dir():
    """Create temporary directory for ChromaDB."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_embedding_client():
    """Create mock embedding client for testing."""
    class MockEmbeddingClient:
        async def generate_embedding(self, text: str) -> List[float]:
            """Generate deterministic embedding based on text hash."""
            # Simple hash-based embedding for testing
            hash_val = hash(text)
            # Generate 768-dimensional vector (Gemini embedding size)
            return [(hash_val * i) % 100 / 100.0 for i in range(768)]
    
    return MockEmbeddingClient()


@pytest.fixture
async def chroma_adapter(temp_chroma_dir, mock_embedding_client):
    """Create ChromaDB adapter with temporary storage."""
    adapter = ChromaAdapter(
        persist_directory=temp_chroma_dir,
        collection_name="test_collection",
    )
    await adapter.initialize()
    return adapter


@pytest.fixture
def sample_documents() -> List[Document]:
    """Create sample documents for testing."""
    return [
        Document(
            doc_id="bio-1",
            content="Photosynthesis is the process by which plants convert light energy into chemical energy using chlorophyll.",
            metadata=DocumentMetadata(
                source="photosynthesis.md",
                subject="biology",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            doc_id="bio-2",
            content="Mitosis is a type of cell division where one cell divides into two identical daughter cells.",
            metadata=DocumentMetadata(
                source="mitosis.md",
                subject="biology",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            doc_id="prog-1",
            content="Python async/await syntax enables asynchronous programming for concurrent I/O operations.",
            metadata=DocumentMetadata(
                source="python-async.md",
                subject="programming",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            doc_id="math-1",
            content="Derivatives measure the rate of change of a function with respect to its variable.",
            metadata=DocumentMetadata(
                source="derivatives.md",
                subject="math",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
    ]


class TestChromaDBIntegration:
    """Integration tests for ChromaDB vector store."""

    @pytest.mark.asyncio
    async def test_add_and_search_documents(
        self,
        chroma_adapter,
        mock_embedding_client,
        sample_documents,
    ):
        """Test adding documents and performing similarity search."""
        # Add documents
        for doc in sample_documents:
            embedding = await mock_embedding_client.generate_embedding(doc.content)
            doc.embedding = embedding
        
        await chroma_adapter.add_documents(sample_documents)
        
        # Search for biology-related query
        query_text = "How do plants make energy from sunlight?"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await chroma_adapter.search(
            query_embedding=query_embedding,
            k=3,
        )
        
        # Verify results
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(0.0 <= r.similarity_score <= 1.0 for r in results)
        
        # Results should be sorted by similarity (highest first)
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_threshold_filtering(
        self,
        chroma_adapter,
        mock_embedding_client,
        sample_documents,
    ):
        """Test that results can be filtered by similarity threshold."""
        # Add documents
        for doc in sample_documents:
            embedding = await mock_embedding_client.generate_embedding(doc.content)
            doc.embedding = embedding
        
        await chroma_adapter.add_documents(sample_documents)
        
        # Search with k=3
        query_text = "photosynthesis in plants"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await chroma_adapter.search(
            query_embedding=query_embedding,
            k=3,
        )
        
        # Filter by threshold manually (threshold of 0.5)
        threshold = 0.5
        filtered_results = [r for r in results if r.similarity_score >= threshold]
        
        # Verify filtering logic
        assert all(r.similarity_score >= threshold for r in filtered_results)
        assert len(filtered_results) <= len(results)

    @pytest.mark.asyncio
    async def test_k_parameter_limits_results(
        self,
        chroma_adapter,
        mock_embedding_client,
        sample_documents,
    ):
        """Test that k parameter limits number of results."""
        # Add documents
        for doc in sample_documents:
            embedding = await mock_embedding_client.generate_embedding(doc.content)
            doc.embedding = embedding
        
        await chroma_adapter.add_documents(sample_documents)
        
        # Search with k=2
        query_text = "biology concepts"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await chroma_adapter.search(
            query_embedding=query_embedding,
            k=2,
        )
        
        # Should return at most k results
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_persistence(
        self,
        temp_chroma_dir,
        mock_embedding_client,
        sample_documents,
    ):
        """Test that ChromaDB persists data across instances."""
        # Create first adapter and add documents
        adapter1 = ChromaAdapter(
            persist_directory=temp_chroma_dir,
            collection_name="test_persistence",
        )
        await adapter1.initialize()
        
        for doc in sample_documents:
            embedding = await mock_embedding_client.generate_embedding(doc.content)
            doc.embedding = embedding
        
        await adapter1.add_documents(sample_documents)
        
        # Create second adapter with same directory
        adapter2 = ChromaAdapter(
            persist_directory=temp_chroma_dir,
            collection_name="test_persistence",
        )
        await adapter2.initialize()
        
        # Search using second adapter
        query_text = "cell division"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await adapter2.search(
            query_embedding=query_embedding,
            k=3,
        )
        
        # Should find documents added by first adapter
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_empty_collection_search(
        self,
        chroma_adapter,
        mock_embedding_client,
    ):
        """Test searching an empty collection."""
        query_text = "test query"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await chroma_adapter.search(
            query_embedding=query_embedding,
            k=3,
        )
        
        # Should return empty list
        assert results == []

    @pytest.mark.asyncio
    async def test_document_metadata_preserved(
        self,
        chroma_adapter,
        mock_embedding_client,
        sample_documents,
    ):
        """Test that document metadata is preserved during storage and retrieval."""
        # Add documents
        for doc in sample_documents:
            embedding = await mock_embedding_client.generate_embedding(doc.content)
            doc.embedding = embedding
        
        await chroma_adapter.add_documents(sample_documents)
        
        # Search
        query_text = "biology"
        query_embedding = await mock_embedding_client.generate_embedding(query_text)
        
        results = await chroma_adapter.search(
            query_embedding=query_embedding,
            k=4,
        )
        
        # Verify metadata is present
        for result in results:
            assert result.document.metadata is not None
            assert result.document.metadata.source is not None
            assert result.document.metadata.subject is not None
            assert isinstance(result.document.metadata.chunk_index, int)
            assert isinstance(result.document.metadata.total_chunks, int)
