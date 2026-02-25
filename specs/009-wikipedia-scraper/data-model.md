# Data Model: Wikipedia Knowledge Base Scraper

**Feature**: Wikipedia Knowledge Base Scraper  
**Phase**: Phase 1 - Data Model Design  
**Date**: 2025-02-23

## Overview

This document defines all domain entities, their fields, validation rules, relationships, and state transitions for the Wikipedia scraping feature. All models use Pydantic for validation and serialization.

---

## Entity Relationship Diagram

```
┌──────────────────┐
│  ScrapingJob     │
│  ─────────────   │
│  - id            │
│  - topics        │──┐
│  - config        │  │
│  - status        │  │
│  - statistics    │  │
│  - errors        │  │
└──────────────────┘  │
                      │ creates
                      │
                      v
        ┌──────────────────────┐
        │  WikipediaArticle    │
        │  ──────────────────  │
        │  - title             │
        │  - canonical_title   │──┐
        │  - source_url        │  │
        │  - content           │  │
        │  - word_count        │  │
        │  - retrieved_at      │  │
        └──────────────────────┘  │
                                  │ chunked into
                                  │
                                  v
                    ┌──────────────────────┐
                    │  ContentChunk        │
                    │  ──────────────────  │
                    │  - id                │
                    │  - text              │──────> ChromaDB
                    │  - chunk_index       │        (vectorized)
                    │  - article_title     │
                    │  - source_url        │
                    │  - created_at        │
                    └──────────────────────┘
```

---

## Core Entities

### 1. ScrapingJob

Represents a single scraping operation triggered via CLI.

**Purpose**: Track job lifecycle, configuration, and results for audit trail and debugging.

#### Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | UUID | Yes | Unique job identifier | Auto-generated via uuid4() |
| `topics` | list[str] | Yes | Wikipedia article titles to scrape | Non-empty, 1-100 topics, unique values |
| `config` | ScrapingConfig | Yes | Job configuration (rate limit, dry-run, etc.) | Nested model validation |
| `status` | JobStatus | Yes | Current job state | Enum: PENDING, RUNNING, COMPLETED, FAILED, PARTIAL_SUCCESS |
| `start_time` | datetime | Yes | Job start timestamp (UTC) | Auto-set on creation |
| `end_time` | datetime \| None | No | Job completion timestamp (UTC) | None while running, set on completion |
| `statistics` | JobStatistics | Yes | Success/fail counts, timing metrics | Nested model validation |
| `errors` | list[ArticleError] | No | Errors encountered during scraping | Empty list if no errors |

#### Validation Rules

```python
from pydantic import BaseModel, Field, field_validator, UUID4
from datetime import datetime, UTC
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"

class ScrapingJob(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    topics: list[str] = Field(min_length=1, max_length=100)
    config: ScrapingConfig
    status: JobStatus = JobStatus.PENDING
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    statistics: JobStatistics
    errors: list[ArticleError] = Field(default_factory=list)
    
    @field_validator('topics')
    @classmethod
    def validate_unique_topics(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Topics must be unique (no duplicates)")
        return v
    
    @field_validator('topics')
    @classmethod
    def validate_non_empty_titles(cls, v: list[str]) -> list[str]:
        for topic in v:
            if not topic.strip():
                raise ValueError("Article titles cannot be empty")
        return v
```

#### State Transitions

```
PENDING ──(start_scraping)──> RUNNING
                                  │
                                  ├──(all succeed)──> COMPLETED
                                  ├──(all fail)─────> FAILED
                                  └──(some fail)────> PARTIAL_SUCCESS
```

**State Rules**:
- `PENDING`: Job created, not yet started (initial state)
- `RUNNING`: Scraping in progress, no final outcome yet
- `COMPLETED`: All articles successfully scraped, chunked, and ingested
- `FAILED`: All articles failed (network error, all 404s, ChromaDB down)
- `PARTIAL_SUCCESS`: Some articles succeeded, some failed (log errors in `errors` field)

**Exit Codes** (for CLI):
- `COMPLETED` → exit 0
- `FAILED` → exit 1
- `PARTIAL_SUCCESS` → exit 2

---

### 2. ScrapingConfig

Job-specific configuration (not global settings).

#### Fields

| Field | Type | Default | Description | Validation |
|-------|------|---------|-------------|------------|
| `rate_limit` | float | 1.0 | Requests per second | 0.1 ≤ value ≤ 10.0 |
| `retry_attempts` | int | 3 | Max retries for transient failures | 0 ≤ value ≤ 5 |
| `timeout_seconds` | int | 30 | HTTP request timeout | 5 ≤ value ≤ 300 |
| `dry_run` | bool | False | Preview mode (no actual scraping) | - |
| `chunk_size` | int | 1000 | Target words per chunk | 100 ≤ value ≤ 5000 |
| `chunk_overlap` | int | 100 | Overlap words between chunks | 0 ≤ value ≤ chunk_size / 2 |

#### Validation

```python
class ScrapingConfig(BaseModel):
    rate_limit: float = Field(default=1.0, ge=0.1, le=10.0)
    retry_attempts: int = Field(default=3, ge=0, le=5)
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    dry_run: bool = False
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=100, ge=0)
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap_size(cls, v: int, info) -> int:
        chunk_size = info.data.get('chunk_size', 1000)
        if v > chunk_size / 2:
            raise ValueError(f"Overlap ({v}) cannot exceed half of chunk size ({chunk_size})")
        return v
```

---

### 3. JobStatistics

Aggregated metrics for a scraping job.

#### Fields

| Field | Type | Description | Computed? |
|-------|------|-------------|-----------|
| `total_articles` | int | Total articles attempted | len(topics) |
| `successful_articles` | int | Articles successfully processed | Count where no error |
| `failed_articles` | int | Articles that failed | Count with errors |
| `total_chunks_created` | int | Total chunks ingested to ChromaDB | Sum of chunks across all articles |
| `total_processing_time_seconds` | float | Total elapsed time | end_time - start_time |

#### Validation

```python
class JobStatistics(BaseModel):
    total_articles: int = Field(ge=0)
    successful_articles: int = Field(ge=0)
    failed_articles: int = Field(ge=0)
    total_chunks_created: int = Field(ge=0)
    total_processing_time_seconds: float = Field(ge=0.0)
    
    @model_validator(mode='after')
    def validate_article_counts(self):
        if self.successful_articles + self.failed_articles != self.total_articles:
            raise ValueError("successful + failed must equal total articles")
        return self
```

---

### 4. ArticleError

Represents an error encountered while processing a single article.

#### Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `article_title` | str | Article that failed | "Python (programming language)" |
| `error_type` | str | Category of error | "network", "not_found", "rate_limit", "parsing" |
| `error_message` | str | Human-readable error description | "Article not found (404)" |
| `retry_count` | int | Number of retries attempted | 3 |

#### Validation

```python
class ArticleError(BaseModel):
    article_title: str
    error_type: str = Field(pattern="^(network|not_found|rate_limit|parsing|storage)$")
    error_message: str
    retry_count: int = Field(ge=0)
```

---

### 5. WikipediaArticle

Represents retrieved content from Wikipedia MediaWiki API.

**Purpose**: Intermediate representation after fetching from API, before chunking.

#### Fields

| Field | Type | Required | Description | Source |
|-------|------|----------|-------------|--------|
| `title` | str | Yes | User-provided article title | CLI input |
| `canonical_title` | str | Yes | Final title after following redirects | API response |
| `source_url` | HttpUrl | Yes | Wikipedia article URL (canonical) | API response |
| `content` | str | Yes | Extracted main article text | API response (processed) |
| `retrieved_at` | datetime | Yes | Retrieval timestamp (UTC) | Auto-generated |
| `word_count` | int | Yes | Total words in article | Calculated from content |
| `api_response_metadata` | dict | No | Raw metadata from API | API response |

#### Validation

```python
from pydantic import HttpUrl, field_validator

class WikipediaArticle(BaseModel):
    title: str
    canonical_title: str
    source_url: HttpUrl
    content: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    word_count: int = Field(gt=0)
    api_response_metadata: dict = Field(default_factory=dict)
    
    @field_validator('content')
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 100:
            # Log warning: stub article
            import logging
            logging.warning(f"Article content is very short: {len(v)} characters")
        return v
    
    @field_validator('source_url')
    @classmethod
    def validate_wikipedia_domain(cls, v: HttpUrl) -> HttpUrl:
        if "wikipedia.org" not in str(v):
            raise ValueError("URL must be from wikipedia.org domain")
        return v
    
    @property
    def requires_chunking(self) -> bool:
        """Whether article needs to be split into multiple chunks."""
        return self.word_count > 1000  # Chunk size threshold
```

#### API Response Metadata

Optional fields stored for debugging/audit:

```python
{
    "revision_id": int,          # Wikipedia revision ID
    "last_modified": str,        # ISO 8601 timestamp of last edit
    "page_id": int,              # Wikipedia internal page ID
    "api_version": str,          # "rest_v1"
}
```

---

### 6. ContentChunk

Represents a processed text segment ready for embedding and ChromaDB storage.

**Purpose**: Final representation ingested into vector database.

#### Fields

| Field | Type | Required | Description | Computed? |
|-------|------|----------|-------------|-----------|
| `id` | UUID | Yes | Unique chunk identifier | Auto-generated |
| `text` | str | Yes | Chunk content (≤1000 words, complete sentences) | Extracted |
| `chunk_index` | int | Yes | Position in article (0-based) | Sequential |
| `total_chunks` | int | Yes | Total chunks from parent article | Calculated |
| `article_title` | str | Yes | Parent article canonical title | From WikipediaArticle |
| `source_url` | HttpUrl | Yes | Parent article URL | From WikipediaArticle |
| `word_count` | int | Yes | Words in this chunk | Calculated |
| `overlap_start` | int | Yes | Character offset where overlap with previous chunk starts | Calculated (0 if first) |
| `overlap_end` | int | Yes | Character offset where overlap with next chunk starts | Calculated (len(text) if last) |
| `created_at` | datetime | Yes | Chunk creation timestamp (UTC) | Auto-generated |

#### Validation

```python
class ContentChunk(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    text: str
    chunk_index: int = Field(ge=0)
    total_chunks: int = Field(gt=0)
    article_title: str
    source_url: HttpUrl
    word_count: int = Field(gt=0)
    overlap_start: int = Field(ge=0)
    overlap_end: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    @field_validator('text')
    @classmethod
    def validate_chunk_size(cls, v: str) -> str:
        words = len(v.split())
        if words > 1200:  # 1000 + 100 overlap + 100 buffer
            raise ValueError(f"Chunk too large: {words} words (max 1200)")
        if words == 0:
            raise ValueError("Chunk cannot be empty")
        return v
    
    @field_validator('chunk_index')
    @classmethod
    def validate_chunk_index_bounds(cls, v: int, info) -> int:
        total = info.data.get('total_chunks')
        if total and v >= total:
            raise ValueError(f"chunk_index ({v}) must be < total_chunks ({total})")
        return v
    
    @field_validator('overlap_end')
    @classmethod
    def validate_overlap_end(cls, v: int, info) -> int:
        text = info.data.get('text', '')
        if v > len(text):
            raise ValueError(f"overlap_end ({v}) cannot exceed text length ({len(text)})")
        return v
    
    def to_chroma_metadata(self) -> dict:
        """Convert to ChromaDB metadata dict."""
        return {
            "article_title": self.article_title,
            "source_url": str(self.source_url),
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "scrape_timestamp": self.created_at.isoformat(),
            "word_count": self.word_count,
        }
    
    def to_chroma_id(self) -> str:
        """Generate deterministic ChromaDB document ID."""
        import hashlib
        url_hash = hashlib.md5(str(self.source_url).encode()).hexdigest()[:8]
        return f"{url_hash}_{self.chunk_index}"
```

#### ChromaDB Representation

When ingested to ChromaDB:

```python
{
    "id": "a3f8e92c_0",  # Deterministic ID for deduplication
    "document": "Python is a high-level, general-purpose programming language...",
    "metadata": {
        "article_title": "Python (programming language)",
        "source_url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "chunk_index": 0,
        "total_chunks": 16,
        "scrape_timestamp": "2025-02-23T14:32:01Z",
        "word_count": 987
    },
    "embedding": [0.123, -0.456, ...]  # 768-dim Gemini embedding
}
```

---

## Relationships

### ScrapingJob → WikipediaArticle

- **Cardinality**: One-to-Many
- **Direction**: ScrapingJob creates multiple WikipediaArticles
- **Lifecycle**: WikipediaArticles are transient (not persisted, only logged in statistics)

### WikipediaArticle → ContentChunk

- **Cardinality**: One-to-Many
- **Direction**: WikipediaArticle is split into multiple ContentChunks
- **Lifecycle**: ContentChunks persist in ChromaDB, WikipediaArticle discarded after chunking
- **Grouping**: All chunks from same article share `source_url` (deduplication key)

### ContentChunk → ChromaDB

- **Cardinality**: One-to-One (each chunk becomes one ChromaDB document)
- **Direction**: ContentChunk is serialized into ChromaDB format
- **Deduplication**: `to_chroma_id()` generates deterministic ID based on URL + chunk_index

---

## Data Flow

```
CLI Input (topics)
    ↓
ScrapingJob (created, status=PENDING)
    ↓
status → RUNNING
    ↓
For each topic:
    ↓
    Fetch from MediaWiki API
    ↓
    WikipediaArticle (transient)
    ↓
    Extract content (ProcessingPort)
    ↓
    Chunk content (ProcessingPort)
    ↓
    Multiple ContentChunks
    ↓
    Ingest to ChromaDB (StoragePort)
    ↓
    Update statistics
    ↓
status → COMPLETED | FAILED | PARTIAL_SUCCESS
    ↓
ScrapingJob (finalized, end_time set)
```

---

## Validation Summary

### Field-Level Validation

| Entity | Field | Rule | Error Message |
|--------|-------|------|---------------|
| ScrapingJob | topics | 1-100 items | "Topics must contain 1-100 articles" |
| ScrapingJob | topics | Unique values | "Topics must be unique (no duplicates)" |
| ScrapingConfig | rate_limit | 0.1 ≤ x ≤ 10.0 | "Rate limit must be between 0.1 and 10.0 req/sec" |
| ScrapingConfig | chunk_overlap | ≤ chunk_size / 2 | "Overlap cannot exceed half of chunk size" |
| WikipediaArticle | content | ≥ 100 chars | Warning logged (not error) |
| WikipediaArticle | source_url | Contains "wikipedia.org" | "URL must be from wikipedia.org" |
| ContentChunk | text | ≤ 1200 words | "Chunk too large: {words} words (max 1200)" |
| ContentChunk | chunk_index | < total_chunks | "chunk_index must be < total_chunks" |

### Cross-Field Validation

| Entity | Rule | Validator |
|--------|------|-----------|
| JobStatistics | successful + failed = total | `validate_article_counts` |
| ScrapingConfig | overlap ≤ chunk_size / 2 | `validate_overlap_size` |
| ContentChunk | overlap_end ≤ len(text) | `validate_overlap_end` |

---

## Serialization

All entities support JSON serialization via Pydantic:

```python
# Serialize to JSON
job = ScrapingJob(...)
json_str = job.model_dump_json(indent=2)

# Deserialize from JSON
job = ScrapingJob.model_validate_json(json_str)

# Serialize to dict (for SQLite storage)
job_dict = job.model_dump()
```

### SQLite Storage

ScrapingJob is persisted to SQLite:

```python
import json

# Store
async with aiosqlite.connect("courseflow.db") as db:
    await db.execute(
        "INSERT INTO scraping_jobs (id, topics, config, status, ...) VALUES (?, ?, ?, ?, ...)",
        (
            str(job.id),
            json.dumps([t for t in job.topics]),
            job.config.model_dump_json(),
            job.status.value,
            # ... other fields
        )
    )

# Retrieve
cursor = await db.execute("SELECT * FROM scraping_jobs WHERE id = ?", (job_id,))
row = await cursor.fetchone()
job = ScrapingJob(
    id=UUID(row['id']),
    topics=json.loads(row['topics']),
    config=ScrapingConfig.model_validate_json(row['config']),
    # ... other fields
)
```

---

## Invariants

**Must always be true** (enforced by validation):

1. **Job status consistency**: 
   - `PENDING` → `end_time` is None
   - `COMPLETED | FAILED | PARTIAL_SUCCESS` → `end_time` is set

2. **Article counts**:
   - `statistics.successful_articles + statistics.failed_articles == statistics.total_articles`

3. **Chunk ordering**:
   - Chunks from same article have sequential `chunk_index` (0, 1, 2, ...)
   - `chunk_index < total_chunks` for all chunks

4. **URL consistency**:
   - All chunks from same article have identical `source_url`
   - `source_url` is canonical (after redirects)

5. **Sentence boundaries**:
   - Chunk text always ends with complete sentence (validated via NLTK)
   - No partial UTF-8 sequences at chunk boundaries

6. **Overlap regions**:
   - `overlap_start` of chunk N+1 corresponds to `overlap_end` of chunk N
   - Overlap region contains complete sentences only

---

## Usage Examples

### Create Scraping Job

```python
from courseflow.domain.scraping.models import ScrapingJob, ScrapingConfig

job = ScrapingJob(
    topics=["Python (programming language)", "Machine learning"],
    config=ScrapingConfig(
        rate_limit=1.0,
        dry_run=False,
        chunk_size=1000,
        chunk_overlap=100
    ),
    statistics=JobStatistics(
        total_articles=2,
        successful_articles=0,
        failed_articles=0,
        total_chunks_created=0,
        total_processing_time_seconds=0.0
    )
)

print(job.status)  # JobStatus.PENDING
```

### Process Article

```python
article = WikipediaArticle(
    title="Python (programming language)",
    canonical_title="Python (programming language)",
    source_url="https://en.wikipedia.org/wiki/Python_(programming_language)",
    content="Python is a high-level...",
    word_count=15234
)

print(article.requires_chunking)  # True (>1000 words)
```

### Create Chunk

```python
chunk = ContentChunk(
    text="Python is a high-level, general-purpose programming language...",
    chunk_index=0,
    total_chunks=16,
    article_title="Python (programming language)",
    source_url="https://en.wikipedia.org/wiki/Python_(programming_language)",
    word_count=987,
    overlap_start=0,  # First chunk, no overlap with previous
    overlap_end=887   # 100 words before end
)

# Prepare for ChromaDB ingestion
chroma_id = chunk.to_chroma_id()  # "a3f8e92c_0"
metadata = chunk.to_chroma_metadata()
```

---

## Migration Path

If schema changes in future versions:

### Adding Fields (Non-breaking)

```python
class ContentChunk(BaseModel):
    # ... existing fields
    language: str = "en"  # New field with default (optional)
```

Existing chunks in ChromaDB are unaffected (metadata can be extended).

### Changing Field Types (Breaking)

Requires data migration:

1. Add new field with new type
2. Migrate data in background
3. Deprecate old field
4. Remove old field in next major version

Example:
```python
# V1
class ContentChunk(BaseModel):
    word_count: int

# V1.5 (transition)
class ContentChunk(BaseModel):
    word_count: int  # Deprecated
    word_count_v2: float  # New (fractional words for better accuracy)

# V2
class ContentChunk(BaseModel):
    word_count: float  # Old field removed, renamed
```

---

## Testing Fixtures

### Minimal Valid Entities

```python
# Minimal ScrapingJob
minimal_job = ScrapingJob(
    topics=["Test"],
    config=ScrapingConfig(),
    statistics=JobStatistics(
        total_articles=1,
        successful_articles=0,
        failed_articles=0,
        total_chunks_created=0,
        total_processing_time_seconds=0.0
    )
)

# Minimal WikipediaArticle
minimal_article = WikipediaArticle(
    title="Test",
    canonical_title="Test",
    source_url="https://en.wikipedia.org/wiki/Test",
    content="Test content with more than one hundred characters to pass validation rules for minimum content length.",
    word_count=15
)

# Minimal ContentChunk
minimal_chunk = ContentChunk(
    text="Test content.",
    chunk_index=0,
    total_chunks=1,
    article_title="Test",
    source_url="https://en.wikipedia.org/wiki/Test",
    word_count=2,
    overlap_start=0,
    overlap_end=13
)
```

---

**Data Model Complete**: All entities defined with validation rules, relationships, and usage examples.
