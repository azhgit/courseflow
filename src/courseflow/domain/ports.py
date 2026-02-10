"""Domain ports (interfaces) for the RAG system.

Ports define abstract interfaces for external dependencies following hexagonal architecture.
Infrastructure adapters implement these ports to connect to actual services (ChromaDB, Gemini, etc.).
"""

from abc import ABC, abstractmethod

from courseflow.domain.models import Answer, Document, Query, SearchResult


class VectorStorePort(ABC):
    """Port for vector database operations (similarity search)."""

    @abstractmethod
    async def search(
        self, query_embedding: list[float], k: int = 3, threshold: float = 0.5
    ) -> list[SearchResult]:
        """Search for similar documents using vector similarity.

        Args:
            query_embedding: Query vector (768-dim)
            k: Number of results to return (top-k)
            threshold: Minimum similarity score (0-1)

        Returns:
            List of SearchResult objects ranked by similarity

        Raises:
            ServiceUnavailableError: If vector store is unreachable
        """
        pass

    @abstractmethod
    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of Document objects with embeddings

        Raises:
            ServiceUnavailableError: If vector store is unreachable
        """
        pass


class LLMPort(ABC):
    """Port for Large Language Model operations (text generation)."""

    @abstractmethod
    async def generate_answer(
        self, query: str, context: list[Document], timeout: int = 30
    ) -> tuple[str, int, int]:
        """Generate answer to query based on retrieved context.

        Args:
            query: User's question
            context: Retrieved documents to use as context
            timeout: Maximum time to wait for response (seconds)

        Returns:
            Tuple of (answer_text, prompt_tokens, completion_tokens)

        Raises:
            QuotaExceededError: If API quota is exceeded
            TimeoutError: If request times out
            ServiceUnavailableError: If LLM service is unreachable
        """
        pass


class EmbeddingPort(ABC):
    """Port for text embedding operations (vector generation)."""

    @abstractmethod
    async def generate_embedding(self, text: str, timeout: int = 10) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed
            timeout: Maximum time to wait for response (seconds)

        Returns:
            768-dimensional embedding vector

        Raises:
            QuotaExceededError: If API quota is exceeded
            TimeoutError: If request times out
            ServiceUnavailableError: If embedding service is unreachable
        """
        pass


class QueryRepositoryPort(ABC):
    """Port for query metadata persistence (logging and analytics)."""

    @abstractmethod
    async def save_query(
        self,
        query: Query,
        answer: Answer | None,
        latency_ms: int,
        error_type: str | None = None,
    ) -> None:
        """Save query metadata to persistent storage.

        Args:
            query: The user's query
            answer: The generated answer (None if error occurred)
            latency_ms: End-to-end response time in milliseconds
            error_type: Error category if request failed (None if success)

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def get_recent_query_count(self, hours: int = 24) -> int:
        """Get number of queries in the last N hours.

        Args:
            hours: Time window in hours (default: 24)

        Returns:
            Number of queries in the specified time window

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass
