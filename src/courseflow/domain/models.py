"""Domain models for the RAG question answering system.

This module defines all core business entities as Pydantic models with validation.
All models are independent of infrastructure concerns (database, API, external services).
"""

from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Query(BaseModel):
    """Represents a user's question submitted to the RAG system.

    Attributes:
        id: Unique identifier for traceability
        text: The question text submitted by user (1-1000 chars)
        timestamp: When query was received (UTC)
        embedding: Gemini embedding of query text (generated during processing)
    """

    id: UUID = Field(default_factory=uuid4)
    text: str = Field(..., min_length=1, max_length=1000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float] | None = None

    @property
    def query_id(self) -> UUID:
        """Alias for id field for backward compatibility."""
        return self.id

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure query text is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("Query text must not be empty or whitespace")
        return v.strip()


class DocumentMetadata(BaseModel):
    """Metadata for a document chunk.

    Attributes:
        source: File path (e.g., "docs/biology/photosynthesis.md")
        subject: Subject domain (e.g., "biology", "programming")
        topic: Specific topic (e.g., "photosynthesis", "async-await")
        chunk_index: Position in original document (0-indexed)
        total_chunks: Total number of chunks in the document
    """

    source: str
    subject: str
    topic: str | None = None
    chunk_index: int = Field(ge=0)
    total_chunks: int | None = Field(default=None, ge=1)


class Document(BaseModel):
    """Represents a chunk of educational content in the knowledge base.

    Attributes:
        id: Document identifier (e.g., "bio-photosynthesis-chunk-0")
        content: Text content of document chunk (100-10000 chars)
        embedding: Gemini embedding of content (768-3072 dim vector, optional)
        metadata: Subject, source, chunk info
    """

    id: str
    content: str = Field(..., min_length=100, max_length=10000)
    embedding: list[float] | None = Field(default=None, min_length=768, max_length=3072)
    metadata: DocumentMetadata


class SearchResult(BaseModel):
    """Represents a document retrieved during vector search with similarity score.

    Attributes:
        document: The retrieved document
        similarity_score: Cosine similarity (0-1 range)
    """

    document: Document
    similarity_score: float = Field(ge=0.0, le=1.0)

    model_config = {"validate_assignment": True}


class TokenUsage(BaseModel):
    """Token consumption for LLM calls.

    Attributes:
        prompt_tokens: Tokens in LLM prompt (query + context)
        completion_tokens: Tokens in LLM response (answer)
        total_tokens: Sum of prompt and completion tokens
    """

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    @field_validator("total_tokens")
    @classmethod
    def validate_total(cls, v: int, info: Any) -> int:
        """Ensure total equals sum of prompt and completion tokens."""
        prompt = info.data.get("prompt_tokens", 0)
        completion = info.data.get("completion_tokens", 0)
        expected = prompt + completion
        if v != expected:
            raise ValueError(f"total_tokens must equal prompt + completion ({expected})")
        return v


class Answer(BaseModel):
    """Represents the AI-generated response to a query.

    Attributes:
        query_id: Reference to original query
        answer_text: The generated answer text
        sources: Source documents with similarity scores
        latency_ms: Total query processing time in milliseconds
        token_usage: LLM token consumption (optional)
        timestamp: When answer was generated (UTC)
    """

    query_id: UUID
    answer_text: str = Field(..., min_length=1)
    sources: list["SearchResult"] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
    token_usage: TokenUsage | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RateLimitTracker(BaseModel):
    """Tracks API quota usage to enforce rate limits.

    This model uses a sliding window approach to track requests and enforce
    Gemini free tier limits (15 RPM, 1500 req/day).

    Attributes:
        request_timestamps: Last N request timestamps (sliding window)
        max_requests_per_minute: RPM limit (default: 15)
        max_requests_per_day: Daily limit (default: 1500)
        window_seconds: Time window for RPM (default: 60)
    """

    request_timestamps: deque[datetime] = Field(default_factory=lambda: deque(maxlen=15))
    max_requests_per_minute: int = 15
    max_requests_per_day: int = 1500
    window_seconds: int = 60

    model_config = {"arbitrary_types_allowed": True}

    def is_allowed(self) -> tuple[bool, int]:
        """Check if request is allowed under rate limits.

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int)
            - allowed: True if request can proceed, False otherwise
            - retry_after_seconds: Seconds to wait before retry (0 if allowed)
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Remove stale timestamps outside the window
        while self.request_timestamps and self.request_timestamps[0] < cutoff:
            self.request_timestamps.popleft()

        # Check if under limit
        if len(self.request_timestamps) < self.max_requests_per_minute:
            self.request_timestamps.append(now)
            return True, 0

        # Calculate retry_after (when oldest request will expire)
        oldest = self.request_timestamps[0]
        retry_after = (
            int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds()) + 1
        )
        return False, retry_after


class ErrorResponse(BaseModel):
    """Structured error information for API responses.

    Attributes:
        type: Error category (e.g., "quota_exceeded", "validation_error")
        message: Human-readable error description
        retry_after: Seconds until retry allowed (for 429 errors)
        details: Additional context (e.g., threshold values)
    """

    type: str
    message: str
    retry_after: int | None = None
    details: dict[str, Any] | None = None


# =============================================================================
# Document Ingestion Domain Models
# =============================================================================


class Subject(BaseModel):
    """Domain entity representing a subject category.

    Attributes:
        id: Unique identifier (UUID or slug-based)
        name: Lowercase slug (e.g., "biology", "programming")
        display_name: Human-readable name (e.g., "Biology", "Programming")
        created_at: When subject was added (UTC)
    """

    id: str
    name: str = Field(..., pattern=r"^[a-z][a-z0-9\-_]*$", max_length=50)
    display_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("name")
    @classmethod
    def validate_name_lowercase(cls, v: str) -> str:
        """Ensure name is lowercase."""
        if not v.islower():
            raise ValueError("Subject name must be lowercase")
        return v


class IngestionDocument(BaseModel):
    """Domain entity representing an ingested document.

    Attributes:
        id: Unique identifier (UUID)
        filename: Original filename
        subject: Subject tag (references Subject.name)
        content_hash: SHA-256 hex digest for duplicate detection
        file_format: File type ("markdown", "txt", "pdf")
        file_size_bytes: Original file size in bytes
        chunks_created: Number of chunks generated
        ingestion_time_ms: Total processing time in milliseconds
        created_at: Ingestion timestamp (UTC)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str = Field(..., min_length=1, max_length=255)
    subject: str
    content_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    file_format: str = Field(..., pattern=r"^(markdown|txt|pdf)$")
    file_size_bytes: int = Field(ge=0)
    chunks_created: int = Field(ge=0)
    ingestion_time_ms: int = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of normalized content.

        Normalization rules (per data-model.md):
        - Strip leading/trailing whitespace
        - Normalize line endings (CRLF → LF)
        - Collapse multiple spaces to single space
        - Collapse multiple newlines to single newline

        Args:
            content: Raw document text

        Returns:
            64-character hex digest of SHA-256 hash
        """
        import hashlib
        import re

        # Normalize content
        text = content.strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n+", "\n", text)

        # Compute SHA-256 hash
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def is_duplicate(self, existing_hash: str) -> bool:
        """Check if this document is a duplicate based on content hash.

        Args:
            existing_hash: Hash of existing document to compare

        Returns:
            True if hashes match (duplicate), False otherwise
        """
        return self.content_hash == existing_hash


class Chunk(BaseModel):
    """Domain entity representing a document chunk.

    Attributes:
        id: Unique identifier (UUID)
        document_id: Parent document reference
        chunk_index: Sequential position in document (0-based)
        text: Chunk content (300-500 tokens typical)
        token_count: Actual token count
        source_filename: Denormalized from document for query performance
        subject: Denormalized from document for filtering
        embedding: 768-dim vector (optional, added during processing)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int = Field(ge=0)
    text: str = Field(..., min_length=1)
    token_count: int = Field(gt=0)
    source_filename: str
    subject: str
    embedding: list[float] | None = None

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        """Ensure chunk text is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Chunk text cannot be empty or whitespace-only")
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion operation (transient, not persisted).

    Attributes:
        document_id: ID of ingested document (or empty if failed)
        filename: Original filename
        success: True if ingestion succeeded
        chunks_created: Number of chunks created (0 if skipped/failed)
        ingestion_time_ms: Total processing time in milliseconds
        skipped: True if duplicate detected (success=True, chunks=0)
        error_message: Error details if failed (None if success)
    """

    document_id: str
    filename: str
    success: bool
    chunks_created: int = Field(ge=0)
    ingestion_time_ms: int = Field(ge=0)
    skipped: bool = False
    error_message: str | None = None

    def to_api_response(self) -> dict[str, Any]:
        """Convert to API response format.

        Returns:
            Dictionary with success flag, data, and error fields
        """
        if self.error_message:
            return {
                "success": False,
                "data": None,
                "error": self.error_message,
            }

        return {
            "success": True,
            "data": {
                "document_id": self.document_id,
                "filename": self.filename,
                "chunks_created": self.chunks_created,
                "ingestion_time_ms": self.ingestion_time_ms,
                "skipped": self.skipped,
            },
            "error": None,
        }
