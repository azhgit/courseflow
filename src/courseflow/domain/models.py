"""Domain models for the RAG question answering system.

This module defines all core business entities as Pydantic models with validation.
All models are independent of infrastructure concerns (database, API, external services).
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Optional
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
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    embedding: Optional[list[float]] = None
    
    @field_validator('text')
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
    """
    
    source: str
    subject: str
    topic: Optional[str] = None
    chunk_index: int = Field(ge=0)


class Document(BaseModel):
    """Represents a chunk of educational content in the knowledge base.
    
    Attributes:
        id: Document identifier (e.g., "bio-photosynthesis-chunk-0")
        content: Text content of document chunk (300-500 tokens)
        embedding: Gemini embedding of content (768-dim vector)
        metadata: Subject, source, chunk info
    """
    
    id: str
    content: str = Field(..., min_length=100, max_length=10000)
    embedding: list[float] = Field(..., min_length=768, max_length=3072)
    metadata: DocumentMetadata


class SearchResult(BaseModel):
    """Represents a document retrieved during vector search with similarity score.
    
    Attributes:
        document: The retrieved document
        similarity_score: Cosine similarity (0-1 range)
        rank: Position in search results (1-indexed)
    """
    
    document: Document
    similarity_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    
    model_config = {'validate_assignment': True}


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
    
    @field_validator('total_tokens')
    @classmethod
    def validate_total(cls, v: int, info: any) -> int:
        """Ensure total equals sum of prompt and completion tokens."""
        prompt = info.data.get('prompt_tokens', 0)
        completion = info.data.get('completion_tokens', 0)
        expected = prompt + completion
        if v != expected:
            raise ValueError(f"total_tokens must equal prompt + completion ({expected})")
        return v


class Answer(BaseModel):
    """Represents the AI-generated response to a query.
    
    Attributes:
        text: The generated answer text
        query_id: Reference to original query
        sources: Source document paths (from retrieved docs)
        retrieval_count: Number of documents used in generation
        top_similarity: Highest similarity score from retrieval
        token_count: LLM token consumption
        timestamp: When answer was generated (UTC)
    """
    
    text: str = Field(..., min_length=1)
    query_id: UUID
    sources: list[str] = Field(default_factory=list)
    retrieval_count: int = Field(ge=0, le=10)
    top_similarity: float = Field(ge=0.0, le=1.0)
    token_count: TokenUsage
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


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
    
    model_config = {'arbitrary_types_allowed': True}
    
    def is_allowed(self) -> tuple[bool, int]:
        """Check if request is allowed under rate limits.
        
        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int)
            - allowed: True if request can proceed, False otherwise
            - retry_after_seconds: Seconds to wait before retry (0 if allowed)
        """
        now = datetime.utcnow()
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
        retry_after = int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds()) + 1
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
    retry_after: Optional[int] = None
    details: Optional[dict] = None
