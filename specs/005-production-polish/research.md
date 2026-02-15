# Research: Production-Ready Evaluation System

**Feature**: 005-production-polish  
**Date**: 2025-02-14  
**Purpose**: Resolve technical unknowns before design phase

## Research Questions

### 1. APScheduler Integration for Daily Evaluation Runs

**Question**: How to integrate APScheduler with FastAPI for automated daily evaluation runs?

**Decision**: Use `APScheduler` 3.10+ with `AsyncIOScheduler` for async/await compatibility with FastAPI

**Rationale**:
- APScheduler is mature, well-documented, and widely used in Python async applications
- `AsyncIOScheduler` runs in the same event loop as FastAPI, avoiding thread safety issues
- Supports cron-style scheduling (`cron(hour=2, minute=0)`) for daily runs at 2 AM
- Integrates cleanly with FastAPI lifespan events for startup/shutdown

**Implementation Pattern**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_evaluation,
        trigger="cron",
        hour=2,
        minute=0,
        id="daily_evaluation"
    )
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

**Alternatives Considered**:
- **Celery Beat**: Rejected - requires Redis/RabbitMQ (violates zero-cost constraint)
- **systemd timers**: Rejected - requires system-level configuration, less portable
- **Manual cron jobs**: Rejected - external dependency, harder to test/configure

**Dependencies**: `APScheduler==3.10.4` (compatible with Python 3.11+)

---

### 2. SQLite Exponential Backoff Retry Strategy

**Question**: What is the best practice for implementing exponential backoff retry for SQLite locked database errors?

**Decision**: Use `tenacity` library with exponential backoff (1s, 2s, 4s, max 3 attempts) for `sqlite3.OperationalError: database is locked`

**Rationale**:
- `tenacity` provides declarative retry logic with exponential backoff
- SQLite locks occur when concurrent writes attempt access (common in async environments)
- Exponential backoff (1s → 2s → 4s) gives time for lock to release without excessive waiting
- 3 attempts balance between reliability (recover from transient locks) and fail-fast (permanent issues)

**Implementation Pattern**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import sqlite3

@retry(
    retry=retry_if_exception_type(sqlite3.OperationalError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
async def save_evaluation_run(self, run: EvaluationRun) -> None:
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            "INSERT INTO evaluation_runs (...) VALUES (...)",
            run.to_tuple()
        )
        await db.commit()
```

**Error Handling**:
- After 3 failed attempts, raise `EvaluationPersistenceError` with actionable message
- Log each retry attempt with WARNING level
- Ensure partial writes are rolled back (SQLite transactions handle this)

**Alternatives Considered**:
- **Manual retry loop**: Rejected - verbose, error-prone, reinvents wheel
- **asyncio.sleep() with manual backoff**: Rejected - less maintainable than tenacity
- **Increase SQLite timeout**: Rejected - doesn't solve fundamental concurrency issue

**Dependencies**: `tenacity==8.2.3` (async/await compatible)

---

### 3. Percentile Computation (p50, p95) for Latency Metrics

**Question**: What library/method should be used to compute p50 and p95 latency percentiles?

**Decision**: Use Python `statistics.quantiles()` (stdlib, Python 3.8+) for percentile computation

**Rationale**:
- Built-in standard library function, no external dependency
- `statistics.quantiles(data, n=100, method='inclusive')` returns 99 quantiles (p1-p99)
- For p50 (median): `quantiles[49]` (index 49 of 99 quantiles)
- For p95: `quantiles[94]` (index 94 of 99 quantiles)
- Handles edge cases (single data point, empty list) gracefully

**Implementation Pattern**:
```python
import statistics

def compute_percentiles(latencies: list[float]) -> tuple[float, float]:
    """Compute p50 and p95 percentiles from latency list (in milliseconds)."""
    if len(latencies) == 0:
        return (0.0, 0.0)
    if len(latencies) == 1:
        return (latencies[0], latencies[0])
    
    # Compute 99 quantiles (p1-p99)
    quantiles = statistics.quantiles(latencies, n=100, method='inclusive')
    p50 = quantiles[49]  # Median
    p95 = quantiles[94]  # 95th percentile
    return (p50, p95)
```

**Alternatives Considered**:
- **NumPy `np.percentile()`**: Rejected - adds heavy dependency for simple calculation
- **Manual sorting + index calculation**: Rejected - error-prone, reinvents stdlib
- **Pandas `df.quantile()`**: Rejected - overkill dependency for 15-element list

**Dependencies**: None (stdlib `statistics` module)

**Edge Cases Handled**:
- Empty list → (0.0, 0.0)
- Single element → (element, element)
- 2-14 elements → quantiles handles gracefully (linear interpolation)

---

### 4. Exact Chunk ID Matching for Retrieval Precision

**Question**: How to implement exact chunk ID matching for retrieval precision calculation?

**Decision**: Use set intersection for exact match comparison: `len(expected_ids & retrieved_ids) / len(retrieved_ids)`

**Rationale**:
- Sets provide O(1) membership testing and efficient intersection
- Exact ID matching (no fuzzy/semantic matching) per clarified requirement
- Precision formula: `relevant_retrieved / total_retrieved` (standard IR metric)
- Handles duplicates automatically (sets deduplicate)

**Implementation Pattern**:
```python
def calculate_retrieval_precision(
    expected_chunk_ids: list[str],
    retrieved_chunk_ids: list[str]
) -> float:
    """
    Calculate retrieval precision as exact chunk ID match rate.
    
    Precision = (relevant chunks retrieved) / (total chunks retrieved)
    Exact match: chunk IDs must match character-for-character.
    """
    if len(retrieved_chunk_ids) == 0:
        return 0.0  # No retrieval = 0% precision
    
    expected_set = set(expected_chunk_ids)
    retrieved_set = set(retrieved_chunk_ids)
    
    relevant_count = len(expected_set & retrieved_set)  # Intersection
    total_retrieved = len(retrieved_set)
    
    return relevant_count / total_retrieved
```

**Assumptions**:
- Chunk IDs are strings (e.g., `"doc_123_chunk_5"`)
- Case-sensitive matching (exact byte-for-byte comparison)
- No partial matches (e.g., `"chunk_1"` ≠ `"chunk_10"`)

**Edge Cases**:
- Zero retrieved chunks → 0.0 precision (not error)
- Zero expected chunks but non-zero retrieved → 0.0 precision (all irrelevant)
- All retrieved chunks are relevant → 1.0 precision (perfect)

**Alternatives Considered**:
- **Fuzzy matching (Levenshtein distance)**: Rejected - spec requires exact matching
- **Semantic embedding similarity**: Rejected - too complex for ID matching
- **Manual loop with string equality**: Rejected - less efficient than sets

---

### 5. Keyword Match Rate Computation

**Question**: How to compute keyword match rate (case-insensitive, exact term matching)?

**Decision**: Use set intersection with case-normalized (lowercase) keywords

**Rationale**:
- Case-insensitive per assumption in spec (not explicitly stated, but reasonable default)
- Exact term matching (no stemming/lemmatization) keeps logic simple and predictable
- Set intersection handles duplicates and provides O(1) lookup

**Implementation Pattern**:
```python
def calculate_keyword_match_rate(
    expected_keywords: list[str],
    generated_answer: str
) -> float:
    """
    Calculate keyword match rate as exact term matching (case-insensitive).
    
    Match rate = (keywords found in answer) / (total keywords expected)
    """
    if len(expected_keywords) == 0:
        return 1.0  # No keywords to match = 100% match by default
    
    # Normalize to lowercase for case-insensitive matching
    expected_set = {kw.lower() for kw in expected_keywords}
    answer_words = set(generated_answer.lower().split())
    
    matched_count = len(expected_set & answer_words)
    total_keywords = len(expected_set)
    
    return matched_count / total_keywords
```

**Assumptions**:
- Keywords are single words (no multi-word phrases like "neural network")
- Whitespace tokenization sufficient (no need for advanced NLP tokenization)
- Case-insensitive: "Python" matches "python"
- No stemming: "running" does NOT match "run"

**Edge Cases**:
- Zero expected keywords → 1.0 match rate (nothing to fail)
- Empty generated answer → 0.0 match rate (no matches possible)
- All keywords present → 1.0 match rate (perfect)

**Alternatives Considered**:
- **Stemming/lemmatization (NLTK, spaCy)**: Rejected - adds complexity, not required by spec
- **Regex word boundary matching**: Rejected - overkill for simple whitespace split
- **Substring matching**: Rejected - "run" would match "running" (not exact matching)

---

### 6. Concurrency Control (Single Evaluation Run at a Time)

**Question**: How to enforce single evaluation run at a time and return HTTP 429 for concurrent requests?

**Decision**: Use `asyncio.Lock` to guard evaluation execution, check lock status in API endpoint

**Rationale**:
- `asyncio.Lock` is async/await native, no blocking calls
- Lock is process-local (sufficient for single FastAPI instance)
- API endpoint checks `lock.locked()` and returns HTTP 429 immediately if locked
- Avoids queueing complexity (spec requires immediate rejection)

**Implementation Pattern**:
```python
from asyncio import Lock
from fastapi import HTTPException

class EvaluationService:
    def __init__(self):
        self._eval_lock = Lock()
    
    async def run_evaluation(self) -> EvaluationRun:
        if self._eval_lock.locked():
            raise HTTPException(
                status_code=429,
                detail="Evaluation already in progress. Retry after completion.",
                headers={"Retry-After": "300"}  # Suggest 5 min retry
            )
        
        async with self._eval_lock:
            # Run evaluation logic here
            result = await self._execute_evaluation()
            return result
```

**API Response for HTTP 429**:
```json
{
  "error": "evaluation_in_progress",
  "message": "Evaluation already in progress. Retry after completion.",
  "retry_after": 300
}
```

**Alternatives Considered**:
- **Request queue (FIFO)**: Rejected - spec requires immediate rejection, not queueing
- **Database flag (`is_running` column)**: Rejected - slower than in-memory lock, race conditions
- **Redis distributed lock**: Rejected - violates zero-cost constraint

**Limitations**:
- Lock is process-local only (if multiple FastAPI workers deployed, need distributed lock)
- Acceptable for single-instance deployment (portfolio/demo use case)

---

### 7. Baseline Selection for Regression Detection

**Question**: How to select baseline evaluation run (most recent where `passed=true`)?

**Decision**: Query SQLite with `WHERE passed=true ORDER BY timestamp DESC LIMIT 1`

**Rationale**:
- SQL query is simple, efficient (indexed by `timestamp` and `passed`)
- "Most recent passed" ensures baseline is a known-good state
- If no passed runs exist, return `None` (no baseline to compare against)

**Implementation Pattern**:
```python
async def get_baseline_run(self) -> EvaluationRun | None:
    """Retrieve most recent evaluation run where passed=true."""
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM evaluation_runs
            WHERE passed = 1
            ORDER BY timestamp DESC
            LIMIT 1
            """,
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return EvaluationRun.from_row(row)
```

**Database Schema Requirement**:
- `passed` column: BOOLEAN (1 = passed, 0 = failed)
- Index: `CREATE INDEX idx_passed_timestamp ON evaluation_runs(passed, timestamp DESC)`

**Edge Cases**:
- No passed runs exist → `None` (first run, or all runs failed)
- Multiple runs with same timestamp → `LIMIT 1` returns arbitrary one (acceptable)

**Alternatives Considered**:
- **Explicitly tagged baseline**: Rejected - requires manual intervention (not automated)
- **Most recent run (regardless of pass/fail)**: Rejected - spec requires `passed=true`

---

## Dependency Summary

| Dependency | Version | Purpose | Status |
|------------|---------|---------|--------|
| `FastAPI` | 0.109+ | EXISTING: API framework | ✅ Already in project |
| `aiosqlite` | 0.19.0 | EXISTING: Async SQLite adapter | ✅ Already in project |
| `Pydantic` | 2.0+ | EXISTING: Data validation | ✅ Already in project |
| `pytest` | 7.4+ | EXISTING: Testing framework | ✅ Already in project |
| `pytest-asyncio` | 0.21+ | EXISTING: Async test support | ✅ Already in project |
| `APScheduler` | 3.10.4 | NEW: Automated scheduling | 🆕 Add to dependencies |
| `tenacity` | 8.2.3 | NEW: Retry with backoff | 🆕 Add to dependencies |

**Installation Command**:
```bash
uv add APScheduler==3.10.4 tenacity==8.2.3
```

---

## Best Practices Summary

1. **Async/Await Consistency**: All I/O operations use async/await (SQLite via aiosqlite, scheduler via AsyncIOScheduler)
2. **Type Safety**: Full type hints for all functions (`mypy --strict` compliance)
3. **Error Handling**: Explicit exception types (`EvaluationInProgressException`, `EvaluationPersistenceError`)
4. **Logging**: Structured logs with context (run_id, timestamp, metrics)
5. **Idempotency**: Evaluation runs produce consistent metrics for same golden dataset
6. **Testability**: Pure functions for metrics computation (no side effects, easy to unit test)

---

**Phase 0 Complete**: All technical unknowns resolved. Ready for Phase 1 design.
