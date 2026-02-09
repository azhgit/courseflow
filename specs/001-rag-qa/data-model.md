# Data Model: Basic RAG Question Answering

**Feature**: 001-rag-qa | **Date**: 2025-02-08

## Overview

This document defines all entities, value objects, and their relationships for the RAG question answering system. The design follows domain-driven design principles with entities in the domain layer independent of infrastructure concerns.

---

## Domain Entities

### 1. Query

**Description**: Represents a user's question submitted to the RAG system.

**Purpose**: Captures the user's intent and serves as the input to the RAG pipeline.

**Attributes**:

| Attribute | Type | Required | Validation | Description |
|-----------|------|----------|------------|-------------|
| `id` | UUID | Yes | Auto-generated | Unique identifier for traceability |
| `text` | str | Yes | Non-empty, ≤1000 chars | The question text submitted by user |
| `timestamp` | datetime | Yes | Auto-generated (UTC) | When query was received |
| `embedding` | list[float] | No | 768-dim vector | Gemini embedding of query text (generated during processing) |

**Business Rules**:
- Query text MUST NOT be empty or whitespace-only (FR-002)
- Query text MUST NOT exceed 1000 characters (edge case handling)
- Timestamp MUST be UTC for consistent rate limit tracking

**State Transitions**: N/A (immutable value object)

**Example**:
```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID, uuid4

class Query(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str = Field(..., min_length=1, max_length=1000)
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    embedding: list[float] | None = None
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Query text must not be empty or whitespace")
        return v.strip()
```

---

### 2. Document

**Description**: Represents a chunk of educational content in the knowledge base.

**Purpose**: Stores pre-loaded documents that are searched to answer queries.

**Attributes**:

| Attribute | Type | Required | Validation | Description |
|-----------|------|----------|------------|-------------|
| `id` | str | Yes | Unique | Document identifier (e.g., "bio-photosynthesis-chunk-0") |
| `content` | str | Yes | 300-500 tokens | Text content of document chunk |
| `embedding` | list[float] | Yes | 768-dim vector | Gemini embedding of content (pre-computed) |
| `metadata` | DocumentMetadata | Yes | Valid metadata | Subject, source, chunk info |

**Nested: DocumentMetadata**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | str | Yes | File path (e.g., "docs/biology/photosynthesis.md") |
| `subject` | str | Yes | Subject domain (e.g., "biology", "programming") |
| `topic` | str | No | Specific topic (e.g., "photosynthesis", "async-await") |
| `chunk_index` | int | Yes | Position in original document (0-indexed) |

**Business Rules**:
- Content MUST be chunked to 300-500 tokens (constitution requirement)
- Embedding MUST be 768-dimensional (Gemini text-embedding-004)
- Subject MUST be domain-agnostic (any subject supported)

**Relationships**:
- **Retrieved by**: Query (via vector similarity search)
- **Used in**: Answer generation (as context)

**Example**:
```python
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    source: str
    subject: str
    topic: str | None = None
    chunk_index: int = Field(ge=0)

class Document(BaseModel):
    id: str
    content: str = Field(..., min_length=100, max_length=3000)
    embedding: list[float] = Field(..., min_items=768, max_items=768)
    metadata: DocumentMetadata
```

---

### 3. SearchResult

**Description**: Represents a document retrieved during vector search with similarity score.

**Purpose**: Links Query to relevant Documents with ranking information.

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `document` | Document | Yes | The retrieved document |
| `similarity_score` | float | Yes | Cosine similarity (0-1 range) |
| `rank` | int | Yes | Position in search results (1-indexed) |

**Business Rules**:
- Similarity score MUST be ≥0.5 to pass threshold filter (FR-003a)
- Rank 1 MUST have highest similarity score
- At most TOP_K results returned (default: 3)

**Example**:
```python
class SearchResult(BaseModel):
    document: Document
    similarity_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    
    class Config:
        # Ensures rank 1 has highest score
        validate_assignment = True
```

---

### 4. Answer

**Description**: Represents the AI-generated response to a query.

**Purpose**: Captures the LLM's answer based on retrieved context.

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | str | Yes | The generated answer text |
| `query_id` | UUID | Yes | Reference to original query |
| `sources` | list[str] | Yes | Source document paths (from retrieved docs) |
| `retrieval_count` | int | Yes | Number of documents used in generation |
| `top_similarity` | float | Yes | Highest similarity score from retrieval |
| `token_count` | TokenUsage | Yes | LLM token consumption |
| `timestamp` | datetime | Yes | When answer was generated (UTC) |

**Nested: TokenUsage**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt_tokens` | int | Yes | Tokens in LLM prompt (query + context) |
| `completion_tokens` | int | Yes | Tokens in LLM response (answer) |
| `total_tokens` | int | Yes | prompt_tokens + completion_tokens |

**Business Rules**:
- Answer MUST be grounded in retrieved documents (hallucination prevention)
- Token count MUST be logged for all LLM calls (constitution requirement)
- Sources MUST match retrieved documents

**Relationships**:
- **Generated from**: Query (one-to-one)
- **Based on**: SearchResult[] (one-to-many)

**Example**:
```python
class TokenUsage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    
    @validator('total_tokens')
    def validate_total(cls, v, values):
        expected = values.get('prompt_tokens', 0) + values.get('completion_tokens', 0)
        if v != expected:
            raise ValueError(f"total_tokens must equal prompt + completion ({expected})")
        return v

class Answer(BaseModel):
    text: str = Field(..., min_length=1)
    query_id: UUID
    sources: list[str] = Field(default_factory=list)
    retrieval_count: int = Field(ge=0, le=10)
    top_similarity: float = Field(ge=0.0, le=1.0)
    token_count: TokenUsage
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
```

---

### 5. RateLimitTracker

**Description**: Tracks API quota usage to enforce rate limits.

**Purpose**: Prevents exceeding Gemini free tier limits (15 RPM, 1500 req/day).

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_timestamps` | deque[datetime] | Yes | Last N request timestamps (sliding window) |
| `max_requests_per_minute` | int | Yes | RPM limit (default: 15) |
| `max_requests_per_day` | int | Yes | Daily limit (default: 1500) |
| `window_seconds` | int | Yes | Time window for RPM (default: 60) |

**Business Rules**:
- Request allowed if len(timestamps in last 60s) < 15 (FR-006)
- Request allowed if len(timestamps in last 24h) < 1500
- Oldest timestamps auto-evicted (deque maxlen behavior)

**State Transitions**:
```
[Empty] → [Add Request] → [Under Limit]
[Under Limit] → [Add Request] → [At Limit]
[At Limit] → [Add Request] → [Rejected: 429]
[At Limit] → [Wait 60s] → [Under Limit]
```

**Example**:
```python
from collections import deque
from datetime import datetime, timedelta

class RateLimitTracker(BaseModel):
    request_timestamps: deque[datetime] = Field(default_factory=lambda: deque(maxlen=15))
    max_requests_per_minute: int = 15
    max_requests_per_day: int = 1500
    window_seconds: int = 60
    
    def is_allowed(self) -> tuple[bool, int]:
        """Check if request allowed. Returns (allowed, retry_after_seconds)."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Remove stale timestamps
        while self.request_timestamps and self.request_timestamps[0] < cutoff:
            self.request_timestamps.popleft()
        
        # Check limit
        if len(self.request_timestamps) < self.max_requests_per_minute:
            self.request_timestamps.append(now)
            return True, 0
        
        # Calculate retry_after
        oldest = self.request_timestamps[0]
        retry_after = int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds()) + 1
        return False, retry_after
    
    class Config:
        arbitrary_types_allowed = True  # For deque
```

---

### 6. QueryRecord (Persistence)

**Description**: Persisted query metadata for analytics and monitoring.

**Purpose**: Store query history in SQLite for quota tracking and performance metrics.

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | int | Yes | Auto-increment primary key |
| `request_id` | UUID | Yes | Unique identifier (matches Query.id) |
| `query_text` | str | Yes | User's question |
| `answer_text` | str | No | Generated answer (NULL if error) |
| `timestamp` | datetime | Yes | UTC timestamp |
| `embedding_tokens` | int | No | Tokens used for query embedding |
| `generation_tokens` | int | No | Tokens used for answer generation |
| `total_tokens` | int | No | Sum of embedding + generation tokens |
| `latency_ms` | int | Yes | End-to-end response time |
| `retrieval_count` | int | No | Number of docs retrieved |
| `top_similarity_score` | float | No | Highest similarity score |
| `error_type` | str | No | Error category (NULL if success) |

**Business Rules**:
- Timestamp indexed for fast date range queries (last 24h quota check)
- Error type indexed for failure analysis (WHERE error_type IS NOT NULL)
- request_id UNIQUE constraint prevents duplicate logging

**Example (SQLAlchemy ORM)**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class QueryRecord(Base):
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), unique=True, nullable=False)
    query_text = Column(String, nullable=False)
    answer_text = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    embedding_tokens = Column(Integer, nullable=True)
    generation_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    retrieval_count = Column(Integer, nullable=True)
    top_similarity_score = Column(Float, nullable=True)
    error_type = Column(String, nullable=True, index=True)
    
    __table_args__ = (
        Index('idx_queries_timestamp', 'timestamp'),
        Index('idx_queries_error_type', 'error_type', postgresql_where=(error_type != None)),
    )
```

---

## Value Objects

### ErrorResponse

**Description**: Structured error information for API responses.

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | str | Yes | Error category (e.g., "quota_exceeded") |
| `message` | str | Yes | Human-readable error description |
| `retry_after` | int | No | Seconds until retry allowed (for 429 errors) |
| `details` | dict | No | Additional context (e.g., threshold values) |

**Error Types**:
- `validation_error`: Invalid query input
- `quota_exceeded`: Rate limit hit (429)
- `no_relevant_documents`: No docs above similarity threshold
- `service_unavailable`: Gemini API down (503)
- `timeout`: LLM response timeout
- `internal_error`: Unexpected failure (500)

**Example**:
```python
class ErrorResponse(BaseModel):
    type: str
    message: str
    retry_after: int | None = None
    details: dict | None = None
```

---

## Domain Relationships

```
┌─────────────┐
│   Query     │
│  (User Q)   │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────────┐      ┌──────────────┐
│  SearchResult   │◄─────│  Document    │
│ (Doc + Score)   │ N:1  │ (KB Content) │
└────────┬────────┘      └──────────────┘
         │
         │ N:1
         ▼
    ┌─────────┐
    │ Answer  │
    │ (LLM)   │
    └─────────┘
         │
         │ 1:1
         ▼
  ┌──────────────┐
  │ QueryRecord  │
  │ (SQLite)     │
  └──────────────┘

┌──────────────────┐
│ RateLimitTracker │ (Singleton)
│ (15 RPM Guard)   │
└──────────────────┘
```

**Flow**:
1. User submits **Query**
2. **RateLimitTracker** checks if allowed
3. Query embedded and searches for **SearchResults** (top-3 **Documents**)
4. **SearchResults** filtered by similarity threshold (≥0.5)
5. If no results → Error: "No relevant information found"
6. **Documents** fed to LLM to generate **Answer**
7. **Answer** and metadata persisted as **QueryRecord**

---

## Validation Rules Summary

| Entity | Field | Rule | Error Type |
|--------|-------|------|------------|
| Query | text | Non-empty, ≤1000 chars | validation_error |
| Document | embedding | Exactly 768 dimensions | internal_error |
| SearchResult | similarity_score | ≥0.5 (threshold) | no_relevant_documents |
| Answer | sources | Must match retrieved docs | internal_error |
| RateLimitTracker | request count | ≤15 in 60s window | quota_exceeded |
| QueryRecord | request_id | Unique (no duplicates) | internal_error |

---

## Database Schema (SQLite)

```sql
-- Query metadata and metrics
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    query_text TEXT NOT NULL,
    answer_text TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding_tokens INTEGER,
    generation_tokens INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER NOT NULL,
    retrieval_count INTEGER,
    top_similarity_score REAL,
    error_type TEXT
);

-- Indexes for performance
CREATE INDEX idx_queries_timestamp ON queries(timestamp);
CREATE INDEX idx_queries_error_type ON queries(error_type) WHERE error_type IS NOT NULL;

-- Example queries
-- Get queries in last 24 hours (for daily quota check)
SELECT COUNT(*) FROM queries WHERE timestamp > datetime('now', '-1 day');

-- Get average latency (p95 requires window functions)
SELECT AVG(latency_ms), MAX(latency_ms) FROM queries WHERE timestamp > datetime('now', '-1 hour');

-- Get token usage per day
SELECT DATE(timestamp) as day, SUM(total_tokens) as tokens FROM queries GROUP BY DATE(timestamp) ORDER BY day DESC;
```

**Note**: ChromaDB manages document embeddings internally (no SQL schema needed).

---

## Configuration Model

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Gemini API
    GEMINI_API_KEY: str  # Required
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "courseflow_docs"
    
    # SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/courseflow.db"
    
    # Rate Limiting
    RATE_LIMIT_RPM: int = 15
    RATE_LIMIT_DAILY: int = 1500
    
    # Vector Search
    SIMILARITY_THRESHOLD: float = 0.5
    TOP_K_RESULTS: int = 3
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]
    
    # Timeouts
    LLM_TIMEOUT_SECONDS: int = 30
    EMBEDDING_TIMEOUT_SECONDS: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

---

## Summary

**Core Entities**: Query, Document, SearchResult, Answer, RateLimitTracker, QueryRecord

**Key Relationships**:
- Query → SearchResult[] → Answer (RAG pipeline)
- SearchResult → Document (vector search)
- Answer → QueryRecord (persistence)

**Validation Strategy**:
- Pydantic models for runtime validation
- SQLite constraints for data integrity
- Business rules enforced in application layer (services)

**Next Steps**: Generate API contracts (OpenAPI) based on these models in the contracts/ directory.
