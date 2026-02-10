"""End-to-end tests for RAG pipeline."""

import pytest
import tempfile
import shutil
import os
from typing import List

from courseflow.domain.models import Document, DocumentMetadata, Query
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.config import Settings


@pytest.fixture
def temp_dirs():
    """Create temporary directories for ChromaDB and SQLite."""
    chroma_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test.db")
    
    yield chroma_dir, db_path
    
    shutil.rmtree(chroma_dir, ignore_errors=True)
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.fixture
def sample_knowledge_base() -> List[Document]:
    """Create sample knowledge base documents."""
    return [
        Document(
            id="bio-photosynthesis-1",
            content=(
                "Photosynthesis is the process by which plants, algae, and some bacteria "
                "convert light energy (usually from the sun) into chemical energy stored "
                "in glucose molecules. This process occurs primarily in the chloroplasts "
                "of plant cells, using chlorophyll as the key pigment to capture light energy. "
                "The overall equation is: 6CO2 + 6H2O + light energy → C6H12O6 + 6O2."
            ),
            metadata=DocumentMetadata(
                source="photosynthesis.md",
                subject="biology",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            id="bio-mitosis-1",
            content=(
                "Mitosis is a type of cell division where one parent cell divides to produce "
                "two genetically identical daughter cells. The process consists of several phases: "
                "prophase (chromatin condenses into chromosomes), metaphase (chromosomes align "
                "at the cell's equator), anaphase (sister chromatids separate), and telophase "
                "(nuclear membranes reform). Mitosis is essential for growth, tissue repair, "
                "and asexual reproduction in eukaryotic organisms."
            ),
            metadata=DocumentMetadata(
                source="mitosis.md",
                subject="biology",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            id="prog-async-1",
            content=(
                "Python's async/await syntax enables asynchronous programming for handling "
                "concurrent I/O operations efficiently. The 'async def' keyword defines "
                "a coroutine function, while 'await' pauses execution until an awaitable "
                "object completes. This is particularly useful for network requests, file I/O, "
                "and database operations. Example: async def fetch_data(): data = await "
                "client.get(url). Use asyncio.run() to execute async functions."
            ),
            metadata=DocumentMetadata(
                source="python-async.md",
                subject="programming",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            id="math-derivatives-1",
            content=(
                "In calculus, the derivative measures the rate of change of a function with "
                "respect to its variable. The derivative of f(x) at point x is defined as "
                "the limit: f'(x) = lim(h→0) [f(x+h) - f(x)]/h. Common derivative rules "
                "include: power rule (d/dx[x^n] = nx^(n-1)), product rule, quotient rule, "
                "and chain rule. Derivatives are used to find slopes of tangent lines, "
                "optimize functions, and model rates of change in physics and engineering."
            ),
            metadata=DocumentMetadata(
                source="derivatives.md",
                subject="math",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
        Document(
            id="hist-wwii-1",
            content=(
                "World War II (1939-1945) was a global conflict involving most of the world's "
                "nations, divided into two opposing military alliances: the Allies (led by "
                "the United States, Soviet Union, and United Kingdom) and the Axis powers "
                "(led by Germany, Italy, and Japan). The war began with Germany's invasion "
                "of Poland in September 1939 and ended with Japan's surrender in August 1945 "
                "after atomic bombs were dropped on Hiroshima and Nagasaki."
            ),
            metadata=DocumentMetadata(
                source="world-war-2.md",
                subject="history",
                chunk_index=0,
                total_chunks=1,
            ),
        ),
    ]


class TestRAGPipelineE2E:
    """End-to-end tests for complete RAG pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        "GEMINI_API_KEY" not in os.environ,
        reason="Requires GEMINI_API_KEY environment variable",
    )
    async def test_full_rag_pipeline_biology_query(
        self,
        temp_dirs,
        sample_knowledge_base,
    ):
        """Test full RAG pipeline with biology query using real Gemini API."""
        chroma_dir, db_path = temp_dirs
        
        # Initialize components
        settings = Settings()
        embedding_client = GeminiEmbeddingClient(api_key=settings.gemini_api_key)
        vector_store = ChromaAdapter(persist_directory=chroma_dir)
        await vector_store.initialize()
        
        # Ingest documents
        for doc in sample_knowledge_base:
            doc.embedding = await embedding_client.generate_embedding(doc.content)
        await vector_store.add_documents(sample_knowledge_base)
        
        # Create RAG service (will be implemented in T031)
        from courseflow.application.rag_service import RAGService
        from courseflow.infrastructure.llm.gemini import GeminiLLMClient
        from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
        
        llm_client = GeminiLLMClient(api_key=settings.gemini_api_key)
        query_repo = SQLiteQueryRepository(db_path=db_path)
        await query_repo.initialize()
        
        rag_service = RAGService(
            embedding_port=embedding_client,
            vector_store=vector_store,
            llm_port=llm_client,
            query_repo=query_repo,
            similarity_threshold=0.5,
        )
        
        # Execute query
        query = Query(text="What is photosynthesis?")
        answer = await rag_service.answer_query(query)
        
        # Verify response
        assert answer is not None
        assert answer.query_id == query.query_id
        assert len(answer.answer_text) > 0
        assert "photosynthesis" in answer.answer_text.lower()
        
        # Verify sources
        assert len(answer.sources) > 0
        assert any("photosynthesis" in source.document.content.lower() for source in answer.sources)
        
        # Verify similarity scores
        assert all(source.similarity_score >= 0.5 for source in answer.sources)
        
        # Verify latency
        assert answer.latency_ms < 3000  # Under 3 seconds per spec

    @pytest.mark.asyncio
    async def test_rag_pipeline_with_mock_llm(
        self,
        temp_dirs,
        sample_knowledge_base,
    ):
        """Test RAG pipeline with mocked LLM (no API key required)."""
        chroma_dir, db_path = temp_dirs
        
        # Mock embedding client
        class MockEmbeddingClient:
            async def generate_embedding(self, text: str) -> List[float]:
                hash_val = hash(text)
                return [(hash_val * i) % 100 / 100.0 for i in range(768)]
        
        # Mock LLM client
        class MockLLMClient:
            async def generate_answer(self, query: str, context: list):
                from courseflow.domain.models import TokenUsage
                return (
                    f"Mock answer for: {query}. Based on context: {context[0].content[:50]}...",
                    TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                )
        
        # Initialize components with mocks
        embedding_client = MockEmbeddingClient()
        vector_store = ChromaAdapter(persist_directory=chroma_dir)
        await vector_store.initialize()
        
        # Ingest documents
        for doc in sample_knowledge_base:
            doc.embedding = await embedding_client.generate_embedding(doc.content)
        await vector_store.add_documents(sample_knowledge_base)
        
        # Create RAG service
        from courseflow.application.rag_service import RAGService
        from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
        
        llm_client = MockLLMClient()
        query_repo = SQLiteQueryRepository(db_path=db_path)
        await query_repo.initialize()
        
        rag_service = RAGService(
            embedding_port=embedding_client,
            vector_store=vector_store,
            llm_port=llm_client,
            query_repo=query_repo,
            similarity_threshold=0.5,
        )
        
        # Execute query
        query = Query(text="What is photosynthesis?")
        answer = await rag_service.answer_query(query)
        
        # Verify response structure
        assert answer is not None
        assert answer.query_id == query.query_id
        assert len(answer.sources) > 0
        assert answer.token_usage is not None

    @pytest.mark.asyncio
    async def test_multi_subject_queries(
        self,
        temp_dirs,
        sample_knowledge_base,
    ):
        """Test RAG pipeline handles queries from different subjects."""
        chroma_dir, db_path = temp_dirs
        
        # Mock components
        class MockEmbeddingClient:
            async def generate_embedding(self, text: str) -> List[float]:
                hash_val = hash(text)
                return [(hash_val * i) % 100 / 100.0 for i in range(768)]
        
        class MockLLMClient:
            async def generate_answer(self, query: str, context: list):
                from courseflow.domain.models import TokenUsage
                return (
                    f"Answer based on context",
                    TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                )
        
        # Setup
        embedding_client = MockEmbeddingClient()
        vector_store = ChromaAdapter(persist_directory=chroma_dir)
        await vector_store.initialize()
        
        for doc in sample_knowledge_base:
            doc.embedding = await embedding_client.generate_embedding(doc.content)
        await vector_store.add_documents(sample_knowledge_base)
        
        from courseflow.application.rag_service import RAGService
        from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
        
        llm_client = MockLLMClient()
        query_repo = SQLiteQueryRepository(db_path=db_path)
        await query_repo.initialize()
        
        rag_service = RAGService(
            embedding_port=embedding_client,
            vector_store=vector_store,
            llm_port=llm_client,
            query_repo=query_repo,
            similarity_threshold=0.5,
        )
        
        # Test queries from different subjects
        queries = [
            "What is photosynthesis?",  # biology
            "How to use async/await?",  # programming
            "What are derivatives?",     # math
            "When did WWII start?",      # history
        ]
        
        for query_text in queries:
            query = Query(text=query_text)
            answer = await rag_service.answer_query(query)
            
            assert answer is not None
            assert len(answer.sources) > 0

    @pytest.mark.asyncio
    async def test_irrelevant_query_handling(
        self,
        temp_dirs,
        sample_knowledge_base,
    ):
        """Test that irrelevant queries are properly handled."""
        chroma_dir, db_path = temp_dirs
        
        # Mock components
        class MockEmbeddingClient:
            async def generate_embedding(self, text: str) -> List[float]:
                # Return very different embedding for irrelevant query
                if "quantum" in text.lower():
                    return [-0.01] * 768
                hash_val = hash(text)
                return [(hash_val * i) % 100 / 100.0 for i in range(768)]
        
        # Setup
        embedding_client = MockEmbeddingClient()
        vector_store = ChromaAdapter(persist_directory=chroma_dir)
        await vector_store.initialize()
        
        for doc in sample_knowledge_base:
            doc.embedding = await embedding_client.generate_embedding(doc.content)
        await vector_store.add_documents(sample_knowledge_base)
        
        from courseflow.application.rag_service import RAGService
        from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository
        from courseflow.domain.exceptions import NoRelevantDocumentsError
        
        class MockLLMClient:
            async def generate_answer(self, query: str, context: list):
                from courseflow.domain.models import TokenUsage
                return (
                    "Answer",
                    TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                )
        
        llm_client = MockLLMClient()
        query_repo = SQLiteQueryRepository(db_path=db_path)
        await query_repo.initialize()
        
        rag_service = RAGService(
            embedding_port=embedding_client,
            vector_store=vector_store,
            llm_port=llm_client,
            query_repo=query_repo,
            similarity_threshold=0.7,  # High threshold
        )
        
        # Execute irrelevant query
        query = Query(text="What is quantum entanglement?")
        
        with pytest.raises(NoRelevantDocumentsError):
            await rag_service.answer_query(query)
