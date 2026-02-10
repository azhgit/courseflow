# Research: Basic RAG Question Answering

**Feature**: 001-rag-qa | **Date**: 2025-02-08

## Overview

This document consolidates research findings for all technical decisions and unknowns identified during implementation planning. All "NEEDS CLARIFICATION" items from the Technical Context have been resolved.

---

## 1. ChromaDB Configuration & Best Practices

### Decision
Use ChromaDB 0.4.22+ with **persistent local storage** at `./data/chroma`, cosine similarity metric, and default HNSW index for vector search.

### Rationale
- **Persistence**: Local file-based storage eliminates dependency on external services and aligns with zero-cost constraint
- **Cosine Similarity**: Industry standard for text embeddings (range 0-1), intuitive threshold interpretation (0.5 = 50% similar)
- **HNSW Index**: ChromaDB's default Hierarchical Navigable Small World graph provides O(log N) search with 90%+ recall at <200ms for 10K docs
- **Simple API**: No complex configuration needed for 10-document knowledge base

### Implementation Details
```python
import chromadb
from chromadb.config import Settings

# Initialize persistent client
client = chromadb.PersistentClient(
    path="./data/chroma",
    settings=Settings(
        anonymized_telemetry=False,  # Disable telemetry for privacy
        allow_reset=True  # Enable for testing
    )
)

# Create/get collection with cosine similarity
collection = client.get_or_create_collection(
    name="courseflow_docs",
    metadata={"hnsw:space": "cosine"}  # Cosine similarity metric
)
```

### Alternatives Considered
- **Faiss**: More complex setup, overkill for 10 documents, requires separate persistence layer
- **Pinecone/Weaviate**: Hosted services violate zero-cost constraint
- **In-memory ChromaDB**: Data loss on restart, not suitable for persistent knowledge base

### References
- [ChromaDB Docs - Embeddings](https://docs.trychroma.com/embeddings)
- [HNSW Algorithm Paper](https://arxiv.org/abs/1603.09320)

---

## 2. Gemini API Integration & Error Handling

### Decision
Use **Google Gemini 1.5 Flash** with `httpx` async client, implement exponential backoff retry (1s, 2s, 4s), and categorize errors into: quota_exceeded, timeout, service_unavailable.

### Rationale
- **httpx over requests**: Native async support, required for FastAPI async handlers
- **Exponential Backoff**: Industry standard (AWS SDK, Google Cloud SDK) for transient failures
  - Retry delays: 1s → 2s → 4s (max 3 attempts)
  - Prevents thundering herd problem during API outages
- **Error Categorization**: Enables client-side handling (e.g., show "retry in 60s" for quota vs. "service down" for 503)

### Implementation Details
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True
    )
    async def generate_answer(self, prompt: str) -> str:
        response = await self.client.post(
            f"{self.base_url}/models/gemini-1.5-flash:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        
        if response.status_code == 429:
            raise QuotaExceededError("Gemini API quota exceeded")
        elif response.status_code >= 500:
            raise ServiceUnavailableError("Gemini API temporarily unavailable")
        
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
```

### Rate Limit Tracking
- **Free Tier Limits**: 15 RPM, 1500 requests/day, 1M tokens/minute
- **Tracking Strategy**: Store last 15 request timestamps in-memory (deque), reject if window full
- **Token Tracking**: Parse response headers for quota usage (if available) or estimate from prompt/response length

### Alternatives Considered
- **Simple 1-retry**: Spec requirement (FR-004a), but insufficient for production-quality demo
- **requests library**: Blocking I/O, incompatible with FastAPI async
- **Custom backoff logic**: Reinventing wheel; `tenacity` library is battle-tested

### References
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Google Cloud Retry Best Practices](https://cloud.google.com/apis/design/errors#retry)
- [tenacity Python Library](https://tenacity.readthedocs.io/)

---

## 3. Embedding Generation & Caching Strategy

### Decision
Use **Gemini text-embedding-004** (768 dimensions) with local caching in ChromaDB. Do NOT re-embed documents; only embed user queries.

### Rationale
- **Gemini Embeddings**: Free tier, same provider as LLM (simpler auth), 768-dim vectors (good quality/size trade-off)
- **ChromaDB Persistence**: Automatically caches document embeddings on disk; no separate cache layer needed
- **Query-Only Embedding**: Documents embedded once during ingestion; user queries embedded on-demand
- **Cost Optimization**: 10 documents × ~500 tokens/doc = ~5K tokens (one-time). User queries: ~20 tokens × 1500 queries/day = 30K tokens/day (well within 1M TPM limit)

### Implementation Details
```python
async def embed_text(text: str) -> list[float]:
    """Generate embedding for text using Gemini text-embedding-004."""
    response = await httpx_client.post(
        f"{base_url}/models/text-embedding-004:embedContent",
        headers={"x-goog-api-key": api_key},
        json={"content": {"parts": [{"text": text}]}}
    )
    return response.json()["embedding"]["values"]  # 768-dim float array
```

### Document Chunking Strategy
- **Chunk Size**: 300-500 tokens (constitution mandate)
- **Chunking Method**: Split on paragraph boundaries (avoid mid-sentence splits)
  - Use `\n\n` as primary delimiter
  - Fallback: Split on sentence boundaries if paragraph >500 tokens
- **Overlap**: 50-token overlap between chunks (preserve context continuity)

### Alternatives Considered
- **OpenAI text-embedding-ada-002**: Paid API, violates zero-cost constraint
- **Local Sentence Transformers**: Requires model download (~500MB), slower inference, but viable fallback
- **No Caching**: Redundant API calls waste quota; ChromaDB persistence is free

### References
- [Gemini Embeddings Guide](https://ai.google.dev/gemini-api/docs/embeddings)
- [Text Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/)

---

## 4. SQLite Schema & Query Optimization

### Decision
Use **SQLite with aiosqlite** for query metadata storage. Schema includes: queries table (id, text, timestamp, embedding_tokens, generation_tokens, latency_ms) with index on timestamp.

### Rationale
- **Lightweight**: No separate DB server, file-based (./data/courseflow.db)
- **aiosqlite**: Async wrapper for SQLite, compatible with FastAPI async handlers
- **Schema Design**: Captures all required metrics (token usage, latency) for monitoring
- **Indexes**: B-tree index on timestamp enables fast date range queries (e.g., "queries in last 24h")

### Schema
```sql
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    answer_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    embedding_tokens INTEGER,
    generation_tokens INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER,
    retrieval_count INTEGER,
    top_similarity_score REAL,
    error_type TEXT,  -- NULL if success, else 'quota_exceeded', 'timeout', etc.
    request_id TEXT UNIQUE
);

CREATE INDEX idx_queries_timestamp ON queries(timestamp);
CREATE INDEX idx_queries_error_type ON queries(error_type) WHERE error_type IS NOT NULL;
```

### Query Patterns
```python
# Get queries in last 24 hours
SELECT COUNT(*) FROM queries 
WHERE timestamp > datetime('now', '-1 day');

# Get average latency (p95 requires window functions in SQLite 3.25+)
SELECT AVG(latency_ms), MAX(latency_ms) FROM queries
WHERE timestamp > datetime('now', '-1 hour');

# Get token usage per day
SELECT DATE(timestamp) as day, SUM(total_tokens) as tokens
FROM queries
GROUP BY DATE(timestamp)
ORDER BY day DESC;
```

### Alternatives Considered
- **PostgreSQL**: Overkill for simple metrics, requires separate server (violates zero-cost)
- **No Database**: Lose query history, can't track quota usage over time
- **JSON Files**: No querying capability, manual parsing required

### References
- [SQLite DateTime Functions](https://www.sqlite.org/lang_datefunc.html)
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/)

---

## 5. FastAPI Async Patterns & Dependency Injection

### Decision
Use **FastAPI Depends()** for service injection, initialize services once per request, and use `asyncio.gather()` for concurrent operations.

### Rationale
- **Dependency Injection**: FastAPI's `Depends()` provides clean service lifecycle management
  - Services initialized per request (clean state)
  - Easy to mock for testing (override dependencies)
- **Async Orchestration**: `asyncio.gather()` runs embedding + DB operations concurrently
  - Example: Embed query + check rate limit in parallel (saves ~100ms)
- **Connection Pooling**: aiosqlite handles SQLite connection pooling automatically

### Implementation Pattern
```python
# dependencies.py
async def get_rag_service() -> RAGService:
    """Dependency injection for RAG service."""
    chroma_client = chromadb.PersistentClient(path="./data/chroma")
    vector_store = ChromaAdapter(chroma_client)
    llm_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
    embedding_client = GeminiEmbeddingClient(api_key=settings.GEMINI_API_KEY)
    
    return RAGService(
        vector_store=vector_store,
        llm_client=llm_client,
        embedding_client=embedding_client
    )

# routes/query.py
@router.post("/api/v1/query")
async def query_endpoint(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service),
    db: AsyncConnection = Depends(get_db_connection)
):
    # Concurrent operations
    embedding_task = rag_service.embed_query(request.query)
    rate_limit_task = check_rate_limit(db)
    
    embedding, is_allowed = await asyncio.gather(embedding_task, rate_limit_task)
    
    if not is_allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Sequential operations (depend on embedding)
    results = await rag_service.retrieve(embedding)
    answer = await rag_service.generate(request.query, results)
    
    return {"answer": answer, "sources": [r.metadata for r in results]}
```

### Concurrency Opportunities
1. **Embed + Rate Limit Check**: Run in parallel (no dependencies)
2. **Log Metrics + Return Response**: Fire-and-forget logging (don't block response)
3. **Multiple Queries**: FastAPI handles concurrent requests via async event loop

### Alternatives Considered
- **Sync Code**: Simpler but blocks event loop (violates constitution async-first requirement)
- **Manual Thread Pool**: Complexity overhead, `asyncio` sufficient for I/O-bound tasks
- **Global Service Instances**: Harder to test (can't mock), shared state issues

### References
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python asyncio Best Practices](https://superfastpython.com/asyncio-best-practices/)

---

## 6. Testing Strategy & Golden Dataset Design

### Decision
Create **golden dataset** of 15 question-answer pairs across 3 subjects (programming, biology, history). Test retrieval precision (>70% top-5), similarity threshold (>0.7 top-1), and answer keyword matching.

### Rationale
- **Multi-Subject Coverage**: Validates domain-agnostic design
- **Retrieval Metrics**: 
  - Precision@5: Measures if correct documents appear in top 5 results
  - Top-1 Similarity: Ensures best match is highly relevant (>0.7 cosine similarity)
- **Answer Quality**: Keyword matching (not exact match) accommodates LLM variability while ensuring grounding

### Golden Dataset Structure
```json
{
  "golden_pairs": [
    {
      "id": "bio-001",
      "subject": "biology",
      "question": "What is photosynthesis?",
      "expected_docs": ["docs/biology/photosynthesis.md"],
      "expected_keywords": ["light energy", "glucose", "chlorophyll", "carbon dioxide"],
      "min_similarity": 0.75
    },
    {
      "id": "prog-001",
      "subject": "programming",
      "question": "How do I use async/await in Python?",
      "expected_docs": ["docs/programming/python-async.md"],
      "expected_keywords": ["async def", "await", "coroutine", "asyncio"],
      "min_similarity": 0.70
    },
    // ... 13 more pairs
  ]
}
```

### Test Assertions
```python
def test_retrieval_quality(golden_dataset):
    for pair in golden_dataset["golden_pairs"]:
        # Embed query
        embedding = embed_text(pair["question"])
        
        # Retrieve top 5
        results = vector_store.search(embedding, k=5)
        
        # Assert: Top-1 similarity > threshold
        assert results[0].similarity > pair["min_similarity"]
        
        # Assert: Expected docs in top 5
        retrieved_docs = [r.metadata["source"] for r in results]
        assert any(doc in retrieved_docs for doc in pair["expected_docs"])

def test_answer_quality(golden_dataset):
    for pair in golden_dataset["golden_pairs"]:
        answer = rag_service.query(pair["question"])
        
        # Assert: Answer contains expected keywords (>50% match)
        matched_keywords = sum(
            kw.lower() in answer.lower() 
            for kw in pair["expected_keywords"]
        )
        assert matched_keywords >= len(pair["expected_keywords"]) * 0.5
```

### Coverage Strategy
- **Unit Tests**: Domain models (100%), ports (mocks), rate limiter logic
- **Integration Tests**: API endpoints (FastAPI TestClient), ChromaDB, SQLite
- **E2E Tests**: Full RAG pipeline with golden dataset (mocked Gemini or real API)

### Alternatives Considered
- **Manual Testing Only**: Not reproducible, doesn't scale
- **Exact Answer Matching**: Too brittle (LLM outputs vary)
- **No Retrieval Testing**: Can't validate vector search quality

### References
- [RAG Evaluation Best Practices](https://www.pinecone.io/learn/rag-evaluation/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

---

## 7. Rate Limiting Implementation

### Decision
Implement **sliding window rate limiter** using in-memory deque storing last 15 request timestamps. Check if oldest timestamp is >60s ago before allowing new request.

### Rationale
- **Sliding Window**: More fair than fixed window (prevents burst at window boundary)
- **In-Memory**: Fast (<1ms check), sufficient for single-instance deployment
- **Simple Logic**: No external dependencies (Redis), easy to test

### Implementation
```python
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = deque(maxlen=max_requests)  # Auto-evicts oldest
    
    async def is_allowed(self) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after_seconds)."""
        now = datetime.utcnow()
        
        # Remove timestamps outside window
        while self.requests and now - self.requests[0] > self.window:
            self.requests.popleft()
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True, 0
        
        # Calculate retry_after
        oldest = self.requests[0]
        retry_after = int((oldest + self.window - now).total_seconds()) + 1
        return False, retry_after
```

### Multi-Instance Consideration
- **Current**: Single instance, in-memory sufficient
- **Future**: If deploying multiple instances, migrate to Redis-based rate limiter
  - Use Redis sorted sets with timestamp scores
  - Same sliding window logic, distributed state

### Alternatives Considered
- **Fixed Window**: Simpler but allows 30 requests in 1 second (15 at end of minute 1, 15 at start of minute 2)
- **Token Bucket**: More complex, overkill for static 15 RPM limit
- **Redis Immediately**: Adds dependency, violates zero-cost for single instance

### References
- [Rate Limiting Algorithms](https://www.quinbay.com/blog/understanding-rate-limiting-algorithms)
- [Redis Rate Limiter Pattern](https://redis.io/docs/manual/patterns/rate-limiter/)

---

## 8. Document Ingestion Strategy

### Decision
Create **one-time ingestion script** (`scripts/ingest_docs.py`) that chunks documents, generates embeddings, and stores in ChromaDB. Not exposed as API endpoint in v1.

### Rationale
- **Scope**: Spec explicitly excludes document ingestion API (Out of Scope section)
- **Pre-loaded Docs**: 10 documents assumed to be ingested before deployment
- **Script Approach**: Simple Python script run once during setup, no API security/validation needed

### Ingestion Script Workflow
```python
# scripts/ingest_docs.py
import asyncio
from pathlib import Path
import chromadb

async def ingest_documents(docs_dir: str = "./docs"):
    client = chromadb.PersistentClient(path="./data/chroma")
    collection = client.get_or_create_collection("courseflow_docs")
    
    for doc_path in Path(docs_dir).rglob("*.md"):
        # Read document
        content = doc_path.read_text()
        
        # Chunk document (300-500 tokens)
        chunks = chunk_text(content, max_tokens=500)
        
        # Generate embeddings (batched API calls)
        embeddings = await embed_texts_batch(chunks)
        
        # Store in ChromaDB
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{
                "source": str(doc_path),
                "subject": doc_path.parent.name,  # e.g., "biology"
                "chunk_index": i
            } for i in range(len(chunks))],
            ids=[f"{doc_path.stem}-chunk-{i}" for i in range(len(chunks))]
        )
        
        print(f"Ingested {doc_path} ({len(chunks)} chunks)")

if __name__ == "__main__":
    asyncio.run(ingest_documents())
```

### Chunking Implementation
```python
def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    """Chunk text on paragraph boundaries with token overlap."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para_tokens = len(para.split())  # Rough token estimate
        
        if len(current_chunk.split()) + para_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Keep last 50 tokens for overlap
                overlap_text = " ".join(current_chunk.split()[-overlap:])
                current_chunk = overlap_text + " " + para
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
```

### Alternatives Considered
- **API Endpoint**: Out of scope per spec, adds security complexity
- **No Script**: Manual ingestion error-prone, not reproducible
- **Streaming Ingestion**: Overkill for 10 static documents

### References
- [ChromaDB Adding Data](https://docs.trychroma.com/guides#adding-data-to-a-collection)
- [Text Chunking Best Practices](https://www.pinecone.io/learn/chunking-strategies/)

---

## 9. Error Response Schema Design

### Decision
Use **consistent JSON schema** for all responses (success + error), include `request_id` for tracing, and provide actionable error messages with `retry_after` when applicable.

### Rationale
- **Consistency**: Same structure simplifies client parsing
- **Traceability**: `request_id` enables debugging (correlate logs)
- **Actionability**: Error messages guide user action (e.g., "retry in 60s")

### Response Schema
```python
from pydantic import BaseModel
from typing import Optional

class QueryResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    metadata: dict
    error: Optional[dict] = None

# Success response
{
  "success": true,
  "data": {
    "answer": "Photosynthesis is the process...",
    "sources": ["docs/biology/photosynthesis.md"],
    "retrieval_count": 3,
    "top_similarity": 0.87
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-02-08T12:34:56Z",
    "latency_ms": 1234,
    "token_count": 567
  },
  "error": null
}

# Error response (quota exceeded)
{
  "success": false,
  "data": null,
  "metadata": {
    "request_id": "req_def456",
    "timestamp": "2025-02-08T12:35:01Z",
    "latency_ms": 12
  },
  "error": {
    "type": "quota_exceeded",
    "message": "Gemini API quota exceeded (15 RPM limit). Please retry after 48 seconds.",
    "retry_after": 48
  }
}

# Error response (no relevant docs)
{
  "success": false,
  "data": null,
  "metadata": {...},
  "error": {
    "type": "no_relevant_documents",
    "message": "No relevant information found in knowledge base",
    "details": {
      "threshold": 0.5,
      "max_similarity": 0.32
    }
  }
}
```

### Error Types
- `validation_error`: Invalid query (empty, too long)
- `quota_exceeded`: Rate limit hit (429)
- `no_relevant_documents`: Vector search below threshold
- `service_unavailable`: Gemini API down (503)
- `timeout`: LLM response timeout
- `internal_error`: Unexpected failure (500)

### Alternatives Considered
- **Different Schemas for Success/Error**: Harder for clients to parse
- **No request_id**: Can't correlate logs, harder to debug
- **Generic Error Messages**: Not actionable (e.g., "Error 429" tells user nothing)

### References
- [API Error Handling Best Practices](https://www.baeldung.com/rest-api-error-handling-best-practices)
- [Pydantic Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)

---

## 10. Configuration Management & Environment Variables

### Decision
Use **Pydantic BaseSettings** for configuration, load from `.env` file, validate at startup, and fail fast on missing required variables.

### Rationale
- **Type Safety**: Pydantic validates types (e.g., int for port, URL for API endpoint)
- **Fail Fast**: Missing `GEMINI_API_KEY` raises error at startup (not during first request)
- **12-Factor App**: Environment variables enable deployment flexibility (dev/staging/prod)

### Configuration Schema
```python
# src/courseflow/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Gemini API
    GEMINI_API_KEY: str  # Required
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    
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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()  # Validates on import
```

### .env.example
```bash
# Gemini API (REQUIRED)
GEMINI_API_KEY=your_api_key_here

# ChromaDB (Optional - defaults provided)
CHROMA_PERSIST_DIR=./data/chroma

# Rate Limiting (Optional)
RATE_LIMIT_RPM=15
RATE_LIMIT_DAILY=1500

# Vector Search (Optional)
SIMILARITY_THRESHOLD=0.5
TOP_K_RESULTS=3

# Logging (Optional)
LOG_LEVEL=INFO
```

### Alternatives Considered
- **python-dotenv + os.getenv()**: No validation, typos fail silently
- **config.yaml**: Harder to override in deployed environments
- **Hardcoded Values**: Can't change without code modification

### References
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-Factor App Config](https://12factor.net/config)

---

## Summary

All technical decisions have been researched and documented. Key findings:

1. **ChromaDB**: Persistent local storage with cosine similarity and HNSW indexing
2. **Gemini API**: Exponential backoff retry with error categorization
3. **Embeddings**: text-embedding-004 with ChromaDB auto-caching
4. **SQLite**: Indexed schema for query metrics tracking
5. **FastAPI**: Dependency injection with async concurrency (asyncio.gather)
6. **Testing**: Golden dataset (15 Q&A pairs) with retrieval + answer quality metrics
7. **Rate Limiting**: Sliding window (in-memory deque) for 15 RPM enforcement
8. **Ingestion**: One-time script with paragraph-based chunking (300-500 tokens)
9. **Error Handling**: Consistent JSON schema with actionable messages
10. **Configuration**: Pydantic BaseSettings with .env validation

**No remaining "NEEDS CLARIFICATION" items.** Ready to proceed to Phase 1 (Design).
