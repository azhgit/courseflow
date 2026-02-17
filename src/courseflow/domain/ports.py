"""Domain ports (interfaces) for the RAG system.

Ports define abstract interfaces for external dependencies following hexagonal architecture.
Infrastructure adapters implement these ports to connect to actual services (ChromaDB, Gemini, etc.).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from courseflow.domain.models import Answer, Document, Query, SearchResult

if TYPE_CHECKING:
    from uuid import UUID

    from courseflow.domain.models import (
        Chunk,
        Conversation,
        ConversationTurn,
        DailyQuotaLedger,
        IngestionDocument,
        Subject,
        TurnHistory,
    )


class VectorStorePort(ABC):
    """Port for vector database operations (similarity search)."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        k: int = 3,
        threshold: float = 0.5,
        subject: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar documents using vector similarity.

        Args:
            query_embedding: Query vector (768-dim)
            k: Number of results to return (top-k)
            threshold: Minimum similarity score (0-1)
            subject: Optional subject filter (e.g., "biology")

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

    @abstractmethod
    def stream(self, query: str, context: list[str]) -> AsyncGenerator[str, None]:
        """Stream answer chunks for query and context."""
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


# =============================================================================
# Document Ingestion Ports
# =============================================================================


class PDFExtractorPort(ABC):
    """Port for PDF text extraction."""

    @abstractmethod
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """Extract plain text from PDF file.

        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename (for error messages)

        Returns:
            Plain text content

        Raises:
            PDFCorruptedError: If PDF is corrupted or password-protected
            InvalidFileFormatError: If file is not a valid PDF
        """
        pass


class TokenCounterPort(ABC):
    """Port for token counting."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using LLM tokenizer.

        Args:
            text: Text to tokenize

        Returns:
            Token count (integer)
        """
        pass


class SentenceTokenizerPort(ABC):
    """Port for sentence boundary detection."""

    @abstractmethod
    def tokenize_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Document text

        Returns:
            List of sentences (preserving original whitespace)
        """
        pass


class ChunkerPort(ABC):
    """Port for semantic text chunking."""

    @abstractmethod
    def create_chunks(
        self,
        text: str,
        document_id: str,
        source_filename: str,
        subject: str,
        target_min_tokens: int = 300,
        target_max_tokens: int = 500,
    ) -> list["Chunk"]:
        """Split text into semantic chunks.

        Args:
            text: Document text
            document_id: ID of parent document
            source_filename: Original filename
            subject: Subject category
            target_min_tokens: Minimum tokens per chunk (soft limit)
            target_max_tokens: Maximum tokens per chunk (soft limit, can exceed for sentences)

        Returns:
            List of Chunk objects (without embeddings or IDs)

        Invariants:
            - Every chunk preserves sentence integrity (no mid-sentence splits)
            - Chunks are sequential (index 0, 1, 2, ...)
            - No orphan sentences (every sentence belongs to a chunk)
        """
        pass


class DocumentRepositoryPort(ABC):
    """Port for document persistence."""

    @abstractmethod
    async def save_document(self, document: "IngestionDocument") -> None:
        """Save document to database.

        Args:
            document: Document entity to persist

        Raises:
            ServiceUnavailableError: If database is unreachable
            DuplicateDocumentError: If content_hash already exists
        """
        pass

    @abstractmethod
    async def find_by_content_hash(self, content_hash: str) -> "IngestionDocument | None":
        """Find document by content hash (duplicate detection).

        Args:
            content_hash: SHA-256 hash to search for

        Returns:
            Document if found, None otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def find_by_id(self, document_id: str) -> "IngestionDocument | None":
        """Find document by ID.

        Args:
            document_id: Unique document identifier

        Returns:
            Document if found, None otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def list_all(
        self, subject: str | None = None, limit: int = 100
    ) -> list["IngestionDocument"]:
        """List all documents, optionally filtered by subject.

        Args:
            subject: Optional subject filter (e.g., "biology")
            limit: Maximum number of documents to return

        Returns:
            List of documents

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass


class ChunkRepositoryPort(ABC):
    """Port for chunk persistence."""

    @abstractmethod
    async def save_chunks(self, chunks: list["Chunk"]) -> None:
        """Batch save chunks to database and vector store.

        Args:
            chunks: List of chunks with embeddings

        Raises:
            ServiceUnavailableError: If database or vector store is unreachable
        """
        pass

    @abstractmethod
    async def delete_chunks_by_document_id(self, document_id: str) -> None:
        """Delete all chunks for a document (rollback support).

        Args:
            document_id: ID of parent document

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def find_chunks_by_document_id(self, document_id: str) -> list["Chunk"]:
        """Retrieve all chunks for a document.

        Args:
            document_id: ID of parent document

        Returns:
            List of chunks ordered by chunk_index

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass


class SubjectRepositoryPort(ABC):
    """Port for subject management."""

    @abstractmethod
    async def find_all(self) -> list["Subject"]:
        """Get all available subjects.

        Returns:
            List of all subjects

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> "Subject | None":
        """Find subject by name slug.

        Args:
            name: Subject name (lowercase slug)

        Returns:
            Subject if found, None otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def subject_exists(self, name: str) -> bool:
        """Check if subject exists (for validation).

        Args:
            name: Subject name to check

        Returns:
            True if exists, False otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass


# =============================================================================
# Conversation Repository Port
# =============================================================================


class ConversationRepositoryPort(ABC):
    """Abstract port for conversation persistence.

    Defines contract for storing and retrieving conversation sessions
    and their turns. Implementations use SQLite with aiosqlite for
    async access.

    All exceptions are from domain.exceptions module.
    """

    @abstractmethod
    async def create_conversation(self) -> "Conversation":
        """Create new conversation session.

        Returns:
            Conversation object with id and created_at set

        Raises:
            ConversationPersistenceError: If database insert fails
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: "UUID") -> "Conversation":
        """Retrieve conversation by ID.

        Args:
            conversation_id: UUID of conversation to retrieve

        Returns:
            Conversation object if found

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def conversation_exists(self, conversation_id: "UUID") -> bool:
        """Check if conversation exists (for validation).

        Args:
            conversation_id: UUID to check

        Returns:
            True if exists, False otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def add_turn(self, turn: "ConversationTurn") -> "ConversationTurn":
        """Add turn (user query or assistant response) to conversation.

        The turn is persisted with its pre-calculated token_count.
        User and assistant turns are NOT automatically paired - this is
        the responsibility of the caller (application layer).

        Args:
            turn: ConversationTurn object (id must be None)

        Returns:
            Persisted turn with id field populated by database

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ConversationPersistenceError: If insert fails
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def get_history(
        self,
        conversation_id: "UUID",
        max_tokens: int = 2000,
        max_count: int = 5,
    ) -> "TurnHistory":
        """Retrieve conversation history with token budget enforcement.

        Fetches all turns for conversation ordered by created_at ASC,
        then applies TurnHistory.from_turns() to trim based on budget.

        Args:
            conversation_id: UUID of conversation
            max_tokens: Token budget limit (default 2000)
            max_count: Hard limit on turn count (default 5)

        Returns:
            TurnHistory with trimmed turns (may be empty if conversation
            has no turns, or if oldest turns removed to meet budget)

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        pass

    @abstractmethod
    async def count_turns(self, conversation_id: "UUID") -> int:
        """Get total turn count for conversation (for metrics).

        Args:
            conversation_id: UUID of conversation

        Returns:
            Number of turns (user + assistant combined)

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        pass


# ============================================================================
# Quota Store Port (006-demo-protection feature)
# ============================================================================


class QuotaStorePort(ABC):
    """Port for quota storage (implemented by infrastructure adapters).

    Abstract interface for quota persistence. Domain does not know about
    SQLite, Redis, or other storage implementations.
    """

    @abstractmethod
    async def get_daily_ledger(self) -> "DailyQuotaLedger":
        """Fetch current day's quota ledger (creates if not exists).

        Returns:
            DailyQuotaLedger for today (creates new entry if needed)

        Raises:
            QuotaStorageError: If storage is unavailable
        """
        pass

    @abstractmethod
    async def increment_daily_usage(self) -> None:
        """Atomically increment daily usage counter by 1.

        Raises:
            QuotaStorageError: If storage is unavailable or transaction fails
        """
        pass

    @abstractmethod
    async def reset_daily_usage(self, new_date: str) -> None:
        """Reset daily usage to 0 for a new day.

        Args:
            new_date: ISO 8601 date string (YYYY-MM-DD) for new day

        Raises:
            QuotaStorageError: If storage is unavailable
        """
        pass

    @abstractmethod
    async def get_cache_hit_count(self) -> int:
        """Get number of cache hits today (for metrics).

        Returns:
            Cache hits count for current day

        Raises:
            QuotaStorageError: If storage is unavailable
        """
        pass

    @abstractmethod
    async def increment_cache_hit(self) -> None:
        """Record a cache hit (for hit rate calculation).

        Raises:
            QuotaStorageError: If storage is unavailable
        """
        pass
