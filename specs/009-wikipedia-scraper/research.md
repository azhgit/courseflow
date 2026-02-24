# Research: Wikipedia Knowledge Base Scraper

**Feature**: Wikipedia Knowledge Base Scraper  
**Phase**: Phase 0 - Technology Research & Decisions  
**Date**: 2025-02-23

## Overview

This document captures all technology decisions, dependency versions, best practices research, and alternatives considered for implementing the Wikipedia scraping feature with hexagonal architecture.

---

## 1. MediaWiki API Selection

### Decision: Use MediaWiki REST API v1

**Selected**: `https://en.wikipedia.org/api/rest_v1/`

**Rationale**:
- **Official API**: Maintained by Wikimedia Foundation, stable and documented
- **Structured responses**: JSON format, no HTML parsing needed
- **Redirect handling**: Built-in redirect resolution via API
- **Metadata included**: Provides revision IDs, timestamps, canonical URLs
- **Rate limit friendly**: Clear documentation on recommended limits (1 req/sec for bots)

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **HTML scraping** | Fragile (HTML structure changes), violates Wikipedia ToS, parsing complexity, no structured data |
| **MediaWiki Action API** (`api.php`)| Older API, more complex query syntax, REST API is recommended for new projects |
| **Wikipedia dumps** | Static data (not real-time), massive file sizes (>50GB compressed), complex parsing |
| **DBpedia API** | Third-party maintained, incomplete data, not as fresh as Wikipedia, additional dependency |

**Version**: REST API v1 (stable, no breaking changes expected)

**Documentation**: https://en.wikipedia.org/api/rest_v1/

**Key Endpoints**:
```
GET /page/title/{title}        # Metadata + existence check
GET /page/html/{title}          # Full HTML content
GET /page/summary/{title}       # Summary (sufficient for short articles)
GET /page/mobile-sections/{title}  # Mobile-optimized sections
```

**Best Practices**:
- Set `User-Agent` header: `CourseFlow/0.1 (contact@example.com)`
- Respect 1 req/sec limit for bots (configurable via CLI)
- Handle 429 (rate limit), 404 (not found), 503 (service unavailable)
- Follow redirects: Use `redirect` field in response
- Cache-Control: Respect `max-age` headers for caching (future optimization)

---

## 2. HTTP Client Library

### Decision: Use httpx (already in project)

**Selected**: `httpx>=0.26.0`

**Rationale**:
- **Already in dependencies**: Used for Gemini API calls, no new dependency
- **Async/await native**: Fully async, integrates with FastAPI/asyncio ecosystem
- **Timeout control**: Fine-grained timeout configuration (connect, read, write)
- **HTTP/2 support**: Faster for multiple requests (though we're rate-limited)
- **Connection pooling**: Efficient for repeated requests to same host
- **Type hints**: Excellent type safety for mypy strict mode

**Configuration for Wikipedia**:
```python
import httpx

client = httpx.AsyncClient(
    base_url="https://en.wikipedia.org/api/rest_v1",
    timeout=httpx.Timeout(30.0, connect=10.0),
    headers={
        "User-Agent": "CourseFlow/0.1 (your-email@example.com)",
        "Accept": "application/json"
    },
    follow_redirects=True,
    limits=httpx.Limits(max_keepalive_connections=5)
)
```

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **requests** | Synchronous only (blocks async loop), no async/await support, outdated for modern Python |
| **aiohttp** | httpx is more Pythonic, better type hints, requests-compatible API (easier migration) |
| **urllib3** | Low-level, more boilerplate, no async support built-in |

**Version**: 0.26.0 (current in project, stable)

---

## 3. Retry Logic & Exponential Backoff

### Decision: Use tenacity (already in project)

**Selected**: `tenacity>=8.2.0`

**Rationale**:
- **Already in dependencies**: No new addition needed
- **Declarative syntax**: Clean decorator-based retry logic
- **Async support**: Native async/await compatibility
- **Exponential backoff**: Built-in exponential/jitter strategies
- **Conditional retries**: Retry only on specific exceptions (429, 503)
- **Max attempts**: Configurable retry limits (default 3)

**Configuration for Wikipedia**:
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 1s, 2s, 4s
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    reraise=True
)
async def fetch_with_retry(url: str) -> dict:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
```

**Backoff Strategy**:
- Initial delay: 1 second
- Multiplier: 2x (exponential)
- Max attempts: 3
- Sequence: 1s → 2s → 4s → fail
- Total max wait: 7 seconds across all retries

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **backoff** | Less feature-rich than tenacity, smaller community, no async advantages |
| **Manual retry loops** | Error-prone, harder to test, less maintainable, reinventing wheel |
| **aiohttp-retry** | Couples retry logic to aiohttp (we use httpx), less flexible |

**Version**: 8.2.0 (current in project)

---

## 4. CLI Framework

### Decision: Add Click

**Selected**: `click>=8.1.0` (NEW DEPENDENCY)

**Rationale**:
- **Industry standard**: Used by Flask, pip, AWS CLI, highly mature
- **Nested commands**: Supports subcommands (scrape, list, delete, search-test)
- **Type safety**: Integrates with Python type hints for validation
- **Autocompletion**: Shell completion support (bash, zsh, fish)
- **Testing**: `CliRunner` for isolated CLI tests
- **Documentation**: Excellent docs, large community

**Example CLI structure**:
```python
import click

@click.group()
def scraper():
    """Wikipedia scraper commands."""
    pass

@scraper.command()
@click.option('--topics', multiple=True, required=True)
@click.option('--rate-limit', default=1.0, type=float)
@click.option('--dry-run', is_flag=True)
def scrape(topics: tuple[str, ...], rate_limit: float, dry_run: bool):
    """Scrape Wikipedia articles."""
    # Implementation
    pass
```

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **argparse** | Stdlib but verbose, poor subcommand ergonomics, less Pythonic for complex CLIs |
| **Typer** | Built on Click but adds FastAPI-style syntax, less mature, overkill for our needs |
| **docopt** | Parses docstrings for CLI, too magical, harder to maintain, less type-safe |
| **fire (Google)** | Auto-generates CLI from functions, lacks explicit control, poor for complex CLIs |

**Version**: 8.1.0+ (latest stable, Python 3.11+ compatible)

**Installation**: `pip install click>=8.1.0` (will add to pyproject.toml)

---

## 5. Sentence Tokenization for Chunking

### Decision: Use NLTK Punkt tokenizer (already in project)

**Selected**: `nltk>=3.9.0` (already in dependencies)

**Rationale**:
- **Already in dependencies**: No new addition
- **Accurate tokenization**: Punkt algorithm handles edge cases (Dr., Mr., abbreviations)
- **Language support**: Works for English Wikipedia articles
- **Sentence boundaries**: Preserves semantic context, critical for embeddings
- **Lightweight**: Only need punkt tokenizer data (~2MB download)

**Setup Required**:
```python
import nltk
nltk.download('punkt')  # One-time setup

from nltk.tokenize import sent_tokenize

text = "Dr. Smith studied AI. It was fascinating."
sentences = sent_tokenize(text)
# ["Dr. Smith studied AI.", "It was fascinating."]
```

**Chunking Algorithm**:
1. Tokenize article into sentences
2. Group sentences until reaching ~1000 words
3. If last sentence exceeds limit, include it anyway (preserve sentence integrity)
4. Overlap: Include last 100 words from previous chunk in next chunk
5. Validate: No mid-sentence cuts, no partial UTF-8 sequences

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **Regex sentence splitting** (`\.\\s+`)| Fails on abbreviations (Dr., etc.), not robust, poor edge case handling |
| **spaCy sentence tokenizer** | Heavy dependency (100MB+ models), overkill for sentence splitting only |
| **tiktoken (token-based chunking)** | Chunks by tokens not sentences, breaks semantic boundaries, worse for embeddings |
| **LangChain RecursiveCharacterTextSplitter** | Another dependency, does sentence splitting internally (NLTK under hood) |

**Version**: 3.9.0 (current in project)

**Data dependency**: Punkt tokenizer (~2MB, one-time download documented in quickstart)

---

## 6. Rate Limiting Implementation

### Decision: Implement custom token bucket algorithm

**Selected**: Custom implementation with asyncio

**Rationale**:
- **Simple to implement**: ~50 lines of code, no external dependency
- **Async-friendly**: Uses `asyncio.sleep()` for delays, non-blocking
- **Configurable**: Easy to adjust tokens per second via CLI/config
- **Testable**: Straightforward to test with time mocking (freezegun)
- **Transparent**: No magic, clear logic for debugging

**Algorithm** (Token Bucket):
```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, rate: float):
        """Rate in requests per second."""
        self.rate = rate
        self.interval = 1.0 / rate  # seconds per request
        self.last_request_time: datetime | None = None
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        if self.last_request_time is None:
            self.last_request_time = datetime.now()
            return
        
        elapsed = (datetime.now() - self.last_request_time).total_seconds()
        wait_time = self.interval - elapsed
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
```

**Configuration**:
- Default: 1.0 requests/second (1 second interval)
- Min: 0.1 requests/second (10 second interval, very conservative)
- Max: 10.0 requests/second (0.1 second interval, use cautiously)

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **aiolimiter** | External dependency (adds another package), not significantly better than custom |
| **Sliding window** | More complex, overkill for sequential scraping, harder to reason about |
| **Leaky bucket** | Conceptually similar to token bucket, no advantage for our use case |
| **Redis-based rate limiting** | Requires Redis, overkill for single-process CLI, adds infrastructure dependency |

**Testing**: Use `freezegun` or `pytest-mock` to mock `datetime.now()` for deterministic tests

---

## 7. HTTP Mocking for Integration Tests

### Decision: Use VCR.py

**Selected**: `vcrpy>=4.4.0` (NEW DEV DEPENDENCY)

**Rationale**:
- **Record/replay HTTP**: Record real Wikipedia responses once, replay in CI (fast, deterministic)
- **No network in CI**: Tests run offline, no flakiness from network issues
- **Version control**: Store cassettes in repo (small JSON files)
- **Async support**: Works with httpx (via `vcr.use_cassette` decorator)
- **Flexible matching**: Match by URL, method, headers (configurable)

**Usage**:
```python
import vcr
import pytest
from courseflow.infrastructure.scrapers.mediawiki import MediaWikiAdapter

@pytest.mark.asyncio
@vcr.use_cassette('tests/fixtures/vcr_cassettes/python_article.yaml')
async def test_fetch_article():
    adapter = MediaWikiAdapter()
    article = await adapter.fetch_article("Python (programming language)")
    
    assert article.canonical_title == "Python (programming language)"
    assert "high-level" in article.content.lower()
    assert article.word_count > 5000
```

**Configuration**:
```python
# tests/conftest.py
import vcr

my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/vcr_cassettes',
    record_mode='once',  # Record on first run, replay thereafter
    match_on=['uri', 'method'],
    filter_headers=['authorization'],  # Remove sensitive headers
)
```

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **responses** | Only works with requests library (we use httpx), not async-compatible |
| **respx** | httpx-specific mocking, works but VCR.py is more mature and portable |
| **httpx.MockTransport** | Built-in but requires manual response crafting (tedious for complex Wikipedia responses) |
| **Real API calls in tests** | Slow (network latency), flaky (Wikipedia downtime), rate limit concerns |

**Version**: 4.4.0+ (latest stable, async support)

**Installation**: `pip install vcrpy>=4.4.0` (dev dependency)

---

## 8. ChromaDB Collection Strategy

### Decision: Reuse existing ChromaDB setup, create separate collection

**Selected**: Existing ChromaDB infrastructure with new collection

**Configuration**:
- **Collection name**: `wikipedia_kb` (separate from main `documents` collection)
- **Embedding model**: Gemini text-embedding-004 (existing, 768 dimensions)
- **Distance metric**: Cosine similarity (existing default)
- **Persistence**: Local disk (`./data/chroma/`)
- **Index**: HNSW (default, efficient for 10K-100K vectors)

**Rationale**:
- **Reuse existing adapter**: ChromaDB client already implemented in `infrastructure/vector_store/chroma.py`
- **Separate collection**: Isolates Wikipedia content from course materials (different metadata schemas)
- **Same embeddings**: Consistency with main RAG system, no new embedding model needed
- **Course-wide search**: Single collection enables global search across all Wikipedia articles

**Metadata Schema**:
```python
{
    "article_title": str,        # "Python (programming language)"
    "source_url": str,           # "https://en.wikipedia.org/wiki/..."
    "chunk_index": int,          # 0, 1, 2, ... (position in article)
    "total_chunks": int,         # Total chunks from parent article
    "scrape_timestamp": str,     # ISO 8601: "2025-02-23T14:32:01Z"
    "word_count": int,           # Words in chunk (for debugging/filtering)
}
```

**Document ID Strategy**:
- Format: `{url_hash}_{chunk_index}`
- Example: `a3f8e92c_0`, `a3f8e92c_1`, `a3f8e92c_2`
- Deterministic: Same article always gets same IDs (idempotent re-scraping)
- Deduplication: Re-scraping replaces old chunks automatically

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **Single collection with type field** | Mixing Wikipedia and course content complicates queries, shared namespace for IDs |
| **Separate ChromaDB instance** | Unnecessary complexity, more infrastructure, same machine limitations apply |
| **File-based storage** | No semantic search, would need separate vector store later, defeats purpose |

---

## 9. Scraping Job Metadata Storage

### Decision: Use SQLite via aiosqlite (existing)

**Selected**: Existing SQLite database with new table

**Schema**:
```sql
CREATE TABLE scraping_jobs (
    id TEXT PRIMARY KEY,              -- UUID
    topics TEXT NOT NULL,             -- JSON array: ["Python", "Machine learning"]
    config TEXT NOT NULL,             -- JSON: {"rate_limit": 1.0, ...}
    status TEXT NOT NULL,             -- "pending", "running", "completed", "failed"
    start_time TEXT NOT NULL,         -- ISO 8601
    end_time TEXT,                    -- ISO 8601, NULL if running
    statistics TEXT NOT NULL,         -- JSON: {"total_articles": 2, ...}
    errors TEXT,                      -- JSON array of errors, NULL if none
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX idx_scraping_jobs_start_time ON scraping_jobs(start_time);
```

**Purpose**:
- Audit trail: Track all scraping operations
- Debugging: Investigate failures, retry failed jobs
- Statistics: Success rates, processing times
- Future dashboard: Display scraping history

**Alternatives Considered**:

| Alternative | Why Rejected |
|-------------|--------------|
| **In-memory only** | No persistence, lose history on restart, no audit trail |
| **Log files** | Unstructured, hard to query, no relational data |
| **Separate PostgreSQL** | Overkill for CLI metadata, violates zero-cost constraint |

**Version**: aiosqlite (already in project via `aiosqlite>=0.19.0`)

---

## 10. Best Practices from RAG Research

### Chunking Best Practices

**Optimal Chunk Size**:
- **Research recommendation**: 300-500 tokens (~200-350 words) for best retrieval precision
- **Spec requirement**: 1000 words with 100-word overlap (will follow spec, document trade-off)

**Trade-off**:
- Larger chunks (1000 words): More context per chunk, fewer total chunks, faster ingestion
- Smaller chunks (300 words): More precise retrieval, better semantic focus, more chunks to manage

**Decision**: Follow spec (1000 words), allow configuration for future tuning

**Overlap Strategy**:
- **Purpose**: Preserve context across chunk boundaries
- **Amount**: 100 words (10% of chunk size) per spec
- **Implementation**: Last N sentences from previous chunk become first N sentences of next chunk
- **Validation**: Overlap region must contain complete sentences only

**Sentence Boundary Rule** (CRITICAL):
- NEVER split mid-sentence (corrupts embeddings, breaks semantic meaning)
- ALWAYS use NLTK sentence tokenizer (handles edge cases: abbreviations, ellipses)
- If adding sentence exceeds target by <20%, include it anyway (preserve semantic unit)

---

### Error Handling Best Practices

**Error Classification**:

| Error Type | Transient? | Action | Exit Code |
|------------|------------|--------|-----------|
| 404 Not Found | No | Log, skip article, continue | 2 (partial success) |
| 429 Rate Limit | Yes | Retry with exponential backoff (3x) | 0 or 2 |
| 503 Service Unavailable | Yes | Retry with exponential backoff (3x) | 0 or 2 |
| Timeout | Yes | Retry (3x), then skip | 2 (partial success) |
| Network unreachable | No | Fail immediately, log all | 1 (total failure) |
| Parsing error | No | Log, skip article, continue | 2 (partial success) |
| ChromaDB error | Depends | Retry (3x), then fail job | 1 (total failure) |

**Logging Strategy**:
- **INFO**: Start/end of job, successful article processing, chunk counts
- **WARNING**: Retries, stub articles (<100 words), articles approaching chunk limit
- **ERROR**: Failed articles, exhausted retries, parsing failures

**Partial Success Handling**:
- Continue processing remaining articles after individual failure
- Return exit code 2 (partial success) if some articles succeeded
- Provide detailed error report at end (which articles failed, why)

---

### Testing Best Practices for Hexagonal Architecture

**Layered Testing Strategy**:

1. **Unit Tests** (Domain Layer):
   - Mock all ports completely (no real httpx, chromadb, nltk calls)
   - Test business logic in isolation (job orchestration, validation)
   - Fast (<1 second for full domain test suite)
   - 100% coverage target for domain layer

2. **Integration Tests** (Adapters):
   - Test real adapter implementations
   - Mock only external services (VCR.py for Wikipedia, test ChromaDB instance)
   - Verify adapters conform to port contracts
   - 80% coverage target for adapters

3. **Contract Tests** (Port Compliance):
   - Parametrized tests that verify all adapters implement same port
   - Example: Test MediaWikiAdapter and MockScrapingAdapter both work with same orchestrator
   - Ensures Liskov Substitution Principle (LSP)

4. **E2E Tests** (Full Pipeline):
   - CLI → Domain → Adapters → External systems
   - Use VCR cassettes for Wikipedia, test ChromaDB instance
   - 3-5 full pipeline tests (happy path, partial failure, rate limit)

**Port Mocking Pattern**:
```python
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def mock_scraping_port():
    port = AsyncMock(spec=ScrapingPort)
    port.fetch_article.return_value = WikipediaArticle(
        title="Test Article",
        content="This is test content.",
        # ... other fields
    )
    return port

async def test_orchestrator_with_mock(mock_scraping_port):
    orchestrator = ScrapingOrchestrator(
        scraping_port=mock_scraping_port,
        storage_port=mock_storage_port,
        processing_port=mock_processing_port,
    )
    
    job = await orchestrator.scrape_articles(["Test Article"])
    
    assert job.status == JobStatus.COMPLETED
    mock_scraping_port.fetch_article.assert_called_once_with("Test Article")
```

---

## Dependencies Summary

### Existing Dependencies (No Changes)

| Package | Version | Purpose | Already In Project? |
|---------|---------|---------|---------------------|
| httpx | >=0.26.0 | Async HTTP client for MediaWiki API | ✅ Yes |
| tenacity | >=8.2.0 | Retry logic with exponential backoff | ✅ Yes |
| nltk | >=3.9.0 | Sentence tokenization for chunking | ✅ Yes |
| chromadb | >=0.4.22 | Vector database for embeddings | ✅ Yes |
| aiosqlite | >=0.19.0 | Async SQLite for job metadata | ✅ Yes |
| pydantic | >=2.5.0 | Data validation and models | ✅ Yes |

### New Dependencies (To Add)

| Package | Version | Purpose | Type |
|---------|---------|---------|------|
| click | >=8.1.0 | CLI framework | Production |
| vcrpy | >=4.4.0 | HTTP mocking for integration tests | Dev |

### Data Dependencies

| Resource | Size | Installation | Purpose |
|----------|------|--------------|---------|
| NLTK punkt | ~2MB | `nltk.download('punkt')` | Sentence tokenization |

---

## Configuration Values

### Default Configuration

```python
# config.py additions
class WikipediaScrapingConfig(BaseSettings):
    # MediaWiki API
    wikipedia_base_url: str = "https://en.wikipedia.org/api/rest_v1"
    wikipedia_user_agent: str = "CourseFlow/0.1 (contact@example.com)"
    
    # Rate limiting
    wikipedia_rate_limit: float = 1.0  # requests/second
    wikipedia_timeout: int = 30  # seconds
    
    # Retry strategy
    wikipedia_retry_attempts: int = 3
    wikipedia_retry_min_wait: int = 1  # seconds
    wikipedia_retry_max_wait: int = 10  # seconds
    
    # Chunking
    chunk_size_words: int = 1000
    chunk_overlap_words: int = 100
    max_chunks_per_article: int = 50  # Safety limit
    
    # ChromaDB
    chroma_collection_wikipedia: str = "wikipedia_kb"
    
    # Logging
    scraping_log_level: str = "INFO"
```

---

## Risk Mitigation Summary

| Risk | Mitigation Strategy |
|------|---------------------|
| Wikipedia API changes | Use stable REST API v1, comprehensive integration tests with VCR.py (detect changes early) |
| Rate limiting too strict | Configurable via CLI/config, provide clear progress feedback, document recommended limits |
| Sentence tokenization failures | NLTK Punkt handles edge cases, add fallback regex splitter, validate with diverse test articles |
| ChromaDB conflicts | Use article URL as deduplication key, implement check_article_exists, provide delete command |
| Memory issues on large articles | Streaming processing (never buffer full article), 50-chunk limit with warning |
| Concurrent scraping | Document as V1 limitation, recommend sequential execution, future: job queue with locking |

---

## Next Steps (Phase 1)

With all research complete and decisions documented:

1. ✅ Update `pyproject.toml` with new dependencies (click, vcrpy)
2. ✅ Create domain models (ScrapingJob, WikipediaArticle, ContentChunk)
3. ✅ Define port interfaces (ScrapingPort, StoragePort, ProcessingPort)
4. ✅ Implement adapters (MediaWikiAdapter, ContentProcessor, ChromaDBAdapter)
5. ✅ Create CLI structure (Click commands)
6. ✅ Write unit tests (domain logic with mocked ports)
7. ✅ Write integration tests (adapters with VCR.py/test ChromaDB)
8. ✅ Update documentation (README, architecture diagrams)

**Research Phase Complete**: All unknowns resolved, ready for implementation planning.
