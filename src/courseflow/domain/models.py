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


# =============================================================================
# Multi-turn Conversation Domain Models
# =============================================================================


class Conversation(BaseModel):
    """Aggregate root for multi-turn conversation sessions.

    Represents a conversation thread where a learner can ask multiple
    follow-up questions while the system maintains context.

    Attributes:
        id: Unique UUID4 identifier for the conversation
        created_at: Timestamp when conversation was created (UTC)
    """

    id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: datetime) -> datetime:
        """Ensure created_at is not in the future."""
        now = datetime.now(UTC)
        if v > now:
            raise ValueError("created_at cannot be in the future")
        return v


class ConversationTurn(BaseModel):
    """Entity representing a single message in a conversation.

    Turns are always created in pairs (user query + assistant response)
    and are immutable after creation.

    Attributes:
        id: Auto-increment sequence number within database
        conversation_id: UUID of parent conversation
        role: 'user' for learner queries, 'assistant' for AI responses
        content: Full message text (query or answer)
        token_count: Pre-calculated token count (using tiktoken)
        created_at: Timestamp when turn was created (UTC)
    """

    id: int | None = None  # None before persistence, auto-assigned after
    conversation_id: UUID
    role: str = Field(..., pattern=r"^(user|assistant)$")
    content: str = Field(..., min_length=1)
    token_count: int = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: datetime) -> datetime:
        """Ensure created_at is not in the future."""
        now = datetime.now(UTC)
        if v > now:
            raise ValueError("created_at cannot be in the future")
        return v


class TurnHistory(BaseModel):
    """Value object representing trimmed conversation history.

    Encapsulates token budget enforcement and turn ordering logic.
    Immutable - created once and never modified.

    Attributes:
        turns: Tuple of turns (immutable), ordered by created_at DESC
        total_tokens: Sum of token_count across all turns
        is_trimmed: True if original history exceeded budget
    """

    turns: tuple[ConversationTurn, ...] = Field(default_factory=tuple)
    total_tokens: int = Field(default=0, ge=0)
    is_trimmed: bool = False

    model_config = {"frozen": True}  # Immutable value object

    @classmethod
    def from_turns(
        cls,
        turns: list[ConversationTurn],
        max_tokens: int = 2000,
        max_count: int = 5,
    ) -> "TurnHistory":
        """Create TurnHistory with token budget enforcement.

        Trimming algorithm (oldest-first):
        1. Calculate total tokens of all turns
        2. If under budget and count ≤ max_count: return all turns
        3. Otherwise: remove oldest turns until budget met
        4. Hard limit: keep at most max_count turns

        Args:
            turns: List of turns to filter (assumed ordered by created_at ASC)
            max_tokens: Token budget limit (default 2000)
            max_count: Hard limit on turn count (default 5)

        Returns:
            TurnHistory with trimmed turns and budget enforcement
        """
        if not turns:
            return cls(turns=(), total_tokens=0, is_trimmed=False)

        # Create mutable copy for trimming
        mutable_turns = turns.copy()
        original_count = len(mutable_turns)

        # Calculate initial total
        total = sum(t.token_count for t in mutable_turns)

        # Trim oldest turns if over budget
        while total > max_tokens and len(mutable_turns) > 1:
            removed = mutable_turns.pop(0)  # Remove oldest (first in ASC order)
            total -= removed.token_count

        # Apply hard limit on turn count
        if len(mutable_turns) > max_count:
            mutable_turns = mutable_turns[-max_count:]  # Keep last N
            total = sum(t.token_count for t in mutable_turns)

        is_trimmed = len(mutable_turns) < original_count

        return cls(
            turns=tuple(mutable_turns),
            total_tokens=total,
            is_trimmed=is_trimmed,
        )

    def to_llm_context(self) -> str:
        """Format turns as LLM prompt context.

        Returns:
            Formatted string with turns separated by double newlines,
            prefixed with "User:" or "Assistant:" labels.
            Empty string if no turns.
        """
        if not self.turns:
            return ""

        context_parts = []
        for turn in self.turns:
            prefix = "User" if turn.role == "user" else "Assistant"
            context_parts.append(f"{prefix}: {turn.content}")

        return "\n\n".join(context_parts)


class StreamingQuery(BaseModel):
    """Request model for streaming question answering endpoint.

    Extends single-turn Query with optional conversation_id for multi-turn support.

    Attributes:
        query: Non-empty question string (validated, whitespace stripped)
        conversation_id: Optional UUID string for continuation. None triggers new conversation.
    """

    query: str = Field(
        ...,
        min_length=1,
        description="Non-empty question text",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation UUID (null creates new)",
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        """Ensure query is not empty or whitespace-only (per clarification Q2)."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only")
        return v.strip()


class SSEEvent(BaseModel):
    """Server-Sent Event (SSE) message for streaming responses.

    Immutable value object representing one SSE event in the streaming response.
    Four event types: chunk, sources, done, error.

    Attributes:
        type: Event type literal ("chunk" | "sources" | "done" | "error")
        content: Text chunk (chunk events only)
        sources: List of document names retrieved (sources events only)
        retrieval_count: Number of chunks retrieved (sources events only)
        conversation_id: UUID of conversation (done events only)
        token_count: Total tokens in response (done events only)
        error: Error code (error events only)
        message: Human-readable error message (error events only)
    """

    type: str = Field(
        ...,
        description='Event type: "chunk" | "sources" | "done" | "error"',
    )
    content: str | None = Field(
        default=None,
        description="Text content for chunk events",
    )
    sources: list[str] | None = Field(
        default=None,
        description="Document sources for sources event",
    )
    retrieval_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of chunks retrieved for sources event",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Conversation UUID for done event",
    )
    token_count: int | None = Field(
        default=None,
        ge=0,
        description="Total tokens for done event",
    )
    error: str | None = Field(
        default=None,
        description="Error code for error event",
    )
    message: str | None = Field(
        default=None,
        description="Error message for error event",
    )
    retry_after: int | None = Field(
        default=None,
        ge=0,
        description="Seconds to wait before retry (for rate limit errors)",
    )

    model_config = {"frozen": True}  # Immutable value object

    def to_sse(self) -> str:
        """Serialize to SSE format (data: {...}\\n\\n).

        Returns:
            String in Server-Sent Events format with double newline terminator.
            Example: 'data: {"type": "chunk", "content": "text"}\\n\\n'
        """
        # Build JSON payload with only non-None fields
        payload: dict[str, Any] = {"type": self.type}

        if self.content is not None:
            payload["content"] = self.content
        if self.sources is not None:
            payload["sources"] = self.sources
        if self.retrieval_count is not None:
            payload["retrieval_count"] = self.retrieval_count
        if self.conversation_id is not None:
            payload["conversation_id"] = self.conversation_id
        if self.token_count is not None:
            payload["token_count"] = self.token_count
        if self.error is not None:
            payload["error"] = self.error
        if self.message is not None:
            payload["message"] = self.message
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after

        import json

        json_str = json.dumps(payload, ensure_ascii=False)
        return f"data: {json_str}\n\n"

    @classmethod
    def chunk(cls, content: str) -> "SSEEvent":
        """Factory: Chunk event.

        Args:
            content: Text chunk from LLM response

        Returns:
            SSEEvent with type="chunk"
        """
        return cls(type="chunk", content=content)

    @classmethod
    def with_sources(cls, sources: list[str], retrieval_count: int) -> "SSEEvent":
        """Factory: Sources event.

        Args:
            sources: List of document filenames retrieved
            retrieval_count: Number of chunks used from retrieval

        Returns:
            SSEEvent with type="sources"
        """
        return cls(
            type="sources",
            sources=sources,
            retrieval_count=retrieval_count,
        )

    @classmethod
    def done(cls, conversation_id: str, token_count: int) -> "SSEEvent":
        """Factory: Done event.

        Args:
            conversation_id: UUID of conversation (new or existing)
            token_count: Total tokens in complete response

        Returns:
            SSEEvent with type="done"
        """
        return cls(
            type="done",
            conversation_id=conversation_id,
            token_count=token_count,
        )

    @classmethod
    def failure(cls, error: str, message: str) -> "SSEEvent":
        """Factory: Error event.

        Args:
            error: Error code (e.g., "no_relevant_documents", "rate_limit_exceeded")
            message: Human-readable error description

        Returns:
            SSEEvent with type="error"
        """
        return cls(
            type="error",
            error=error,
            message=message,
        )


# ============================================================================
# Quota Protection Models (006-demo-protection feature)
# ============================================================================


class QuotaWindow:
    """Tracks request timestamps for a single IP address over a rolling time window.

    Maintains a rolling window of request timestamps for quota enforcement.
    Automatically prunes old timestamps outside the window.
    """

    def __init__(
        self,
        ip_address: str,
        request_timestamps: list[datetime] | None = None,
        window_duration_seconds: int = 3600,
    ):
        """Initialize quota window for an IP.

        Args:
            ip_address: The IP address to track
            request_timestamps: Ordered list of past request times (oldest first)
            window_duration_seconds: Rolling window size in seconds (default 1 hour)
        """
        self.ip_address = ip_address
        self.request_timestamps = request_timestamps or []
        self.window_duration_seconds = window_duration_seconds

    def is_within_limit(self, limit: int, current_time: datetime | None = None) -> bool:
        """Check if another request is allowed given the limit.

        Args:
            limit: Maximum requests allowed in window
            current_time: Current time (defaults to now)

        Returns:
            True if request count < limit, False if limit reached
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        # Prune old requests first
        self.prune_old_requests(current_time)

        # Check if we're within limit
        return len(self.request_timestamps) < limit

    def record_request(self, timestamp: datetime | None = None) -> None:
        """Add a new request timestamp to the window.

        Args:
            timestamp: Request timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)
        self.request_timestamps.append(timestamp)

    def prune_old_requests(self, current_time: datetime | None = None) -> None:
        """Remove timestamps outside the rolling window.

        Args:
            current_time: Current time for cutoff calculation
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        cutoff = current_time - timedelta(seconds=self.window_duration_seconds)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts >= cutoff]

    @property
    def current_count(self) -> int:
        """Number of requests currently in the window."""
        return len(self.request_timestamps)


class DailyQuotaLedger(BaseModel):
    """Represents global daily usage across all IPs for current calendar day (UTC).

    Tracks daily quota consumption and determines if budget is exhausted.
    """

    date: str  # ISO 8601 date (YYYY-MM-DD)
    used: int = 0  # Queries consumed today
    limit: int = 300  # Configured daily budget

    @property
    def remaining(self) -> int:
        """Queries remaining in daily budget."""
        return max(0, self.limit - self.used)

    @property
    def percentage_used(self) -> float:
        """Percentage of daily budget consumed (0-100)."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

    @property
    def is_warning(self) -> bool:
        """True if usage >= 80% of limit."""
        return self.percentage_used >= 80.0

    @property
    def is_exhausted(self) -> bool:
        """True if usage >= limit."""
        return self.used >= self.limit

    def increment(self) -> None:
        """Increment usage by 1."""
        self.used += 1

    def reset(self, new_date: str) -> None:
        """Reset usage for a new day."""
        self.date = new_date
        self.used = 0


class DemoCacheEntry(BaseModel):
    """Represents a pre-cached demo question with normalized form and answer.

    Enables exact matching of user questions to cached responses.
    """

    original_question: str  # Human-readable form
    normalized_question: str  # Lowercase, no punctuation, collapsed whitespace
    answer: str  # Pre-computed answer text
    subject: str | None = None  # Optional subject tag

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize question per FR-006: lowercase, strip punctuation, collapse whitespace.

        Args:
            text: Raw question text

        Returns:
            Normalized question (lowercase, no punctuation, single spaces)
        """
        import re

        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)  # Remove punctuation
        normalized = " ".join(normalized.split())  # Collapse whitespace
        return normalized

    @classmethod
    def create(
        cls,
        question: str,
        answer: str,
        subject: str | None = None,
    ) -> "DemoCacheEntry":
        """Factory method to create entry with automatic normalization.

        Args:
            question: Original question text
            answer: Pre-computed answer
            subject: Optional subject category

        Returns:
            DemoCacheEntry with normalized question
        """
        return cls(
            original_question=question,
            normalized_question=cls.normalize(question),
            answer=answer,
            subject=subject,
        )

    def matches(self, user_question: str) -> bool:
        """Check if user question matches this cached entry.

        Args:
            user_question: User's input question

        Returns:
            True if normalized user question matches cached question
        """
        return self.normalized_question == self.normalize(user_question)


class QuotaStatus(BaseModel):
    """Value object: Snapshot of current quota state for status endpoint responses."""

    # Daily quota info
    daily_used: int
    daily_limit: int
    daily_remaining: int
    daily_percentage_used: float
    daily_reset_at: str  # ISO 8601 timestamp (next midnight UTC)
    quota_warning: bool  # True if >= 80% used

    # Cache info
    cached_questions_count: int
    cache_hit_rate: float  # 0-100 percentage (today's cache hits / total queries)

    # Metadata
    current_time: str  # ISO 8601 timestamp

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "daily": {
                "used": self.daily_used,
                "limit": self.daily_limit,
                "remaining": self.daily_remaining,
                "percentage_used": round(self.daily_percentage_used, 2),
                "reset_at": self.daily_reset_at,
            },
            "cache": {
                "questions_count": self.cached_questions_count,
                "hit_rate": round(self.cache_hit_rate, 2),
            },
            "quota_warning": self.quota_warning,
            "timestamp": self.current_time,
        }
