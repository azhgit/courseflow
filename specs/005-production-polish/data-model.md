# Data Model: Production-Ready Evaluation System

**Feature**: 005-production-polish  
**Date**: 2025-02-14  
**Purpose**: Define domain entities, relationships, and validation rules

---

## Overview

The evaluation system models automated quality testing of the RAG pipeline using golden Q&A test pairs. The data model consists of 4 core entities with clear relationships and validation rules.

```
EvaluationRun (aggregate root)
  │
  ├── Metrics (embedded value object)
  │
  └── TestCaseResult[] (composition, 1-to-many)
        │
        └── references GoldenPair (read-only reference data)
```

---

## Entity Definitions

### 1. EvaluationRun (Aggregate Root)

**Purpose**: Represents a single execution of the evaluation suite against golden dataset

**Lifecycle**: Created → Running → Completed/Failed

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

class EvaluationStatus(str, Enum):
    """Status of an evaluation run"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class EvaluationRun:
    """
    Aggregate root for evaluation execution.
    
    Represents a single run of the automated evaluation suite.
    Contains aggregated metrics and references to individual test results.
    """
    run_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: EvaluationStatus = EvaluationStatus.RUNNING
    duration_ms: int | None = None  # Total execution time
    metrics: "Metrics | None" = None  # Computed after completion
    passed: bool = False  # True if all quality thresholds met
    error_message: str | None = None  # Set if status=FAILED
    
    # Metadata
    golden_dataset_version: str = "1.0"  # Track dataset changes
    test_case_count: int = 15  # Expected: 15 golden pairs
    
    def mark_completed(self, metrics: "Metrics", duration_ms: int) -> None:
        """Transition to completed state with results"""
        self.status = EvaluationStatus.COMPLETED
        self.metrics = metrics
        self.duration_ms = duration_ms
        self.passed = self._check_quality_thresholds(metrics)
    
    def mark_failed(self, error: str) -> None:
        """Transition to failed state with error"""
        self.status = EvaluationStatus.FAILED
        self.error_message = error
        self.passed = False
    
    def _check_quality_thresholds(self, metrics: "Metrics") -> bool:
        """Check if metrics meet minimum quality thresholds"""
        return (
            metrics.retrieval_precision_avg >= 0.70 and  # ≥70% precision
            metrics.keyword_match_avg >= 0.80 and        # ≥80% keyword match
            metrics.latency_p95_ms < 10000               # <10s p95 latency
        )
```

**Validation Rules**:
- `run_id`: Must be valid UUID v4
- `timestamp`: Must be UTC timezone
- `status`: Must be one of {running, completed, failed}
- `duration_ms`: Must be positive integer when completed
- `test_case_count`: Must equal 15 (golden dataset size)
- `passed`: Can only be True if status=COMPLETED and thresholds met

**Invariants**:
- If `status == COMPLETED`, then `metrics` is not None
- If `status == FAILED`, then `error_message` is not None
- If `status == RUNNING`, then `metrics` is None

---

### 2. TestCaseResult (Value Object)

**Purpose**: Individual test case result for one golden Q&A pair

**Immutable**: Created once per golden pair, never modified

```python
@dataclass(frozen=True)
class TestCaseResult:
    """
    Immutable result for a single golden Q&A pair evaluation.
    
    Value object - has no identity, identified by combination of fields.
    """
    question: str
    expected_answer: str
    expected_chunks: list[str]  # Expected chunk IDs for retrieval
    keywords: list[str]  # Keywords to check in generated answer
    
    # Results (computed during evaluation)
    actual_answer: str
    retrieved_chunks: list[str]  # Actual chunk IDs retrieved
    retrieval_precision: float  # 0.0-1.0 (relevant/total retrieved)
    keyword_match_rate: float   # 0.0-1.0 (matched/total keywords)
    latency_ms: int             # Query latency in milliseconds
    
    # Derived
    passed: bool  # True if individual thresholds met
    
    def __post_init__(self):
        """Validate field constraints"""
        assert 0.0 <= self.retrieval_precision <= 1.0, "Precision must be 0-1"
        assert 0.0 <= self.keyword_match_rate <= 1.0, "Match rate must be 0-1"
        assert self.latency_ms >= 0, "Latency must be non-negative"
        assert len(self.question) > 0, "Question cannot be empty"
        assert len(self.expected_chunks) > 0, "Must have expected chunks"
        assert len(self.keywords) > 0, "Must have keywords"
```

**Validation Rules**:
- `retrieval_precision`: Float in range [0.0, 1.0]
- `keyword_match_rate`: Float in range [0.0, 1.0]
- `latency_ms`: Non-negative integer
- `question`: Non-empty string
- `expected_chunks`: Non-empty list of chunk ID strings
- `keywords`: Non-empty list of keyword strings
- `retrieved_chunks`: List of chunk ID strings (may be empty if no retrieval)

**Computation**:
- `retrieval_precision = len(expected ∩ retrieved) / len(retrieved)` (or 0.0 if no retrieval)
- `keyword_match_rate = len(keywords ∩ answer_words) / len(keywords)`
- `passed = (precision ≥ 0.70 AND match_rate ≥ 0.80 AND latency < 10000)`

---

### 3. GoldenPair (Reference Data)

**Purpose**: Test case definition loaded from JSON file

**Lifecycle**: Read-only, loaded from `tests/fixtures/golden_dataset.json`

```python
from pydantic import BaseModel, Field

class GoldenPair(BaseModel):
    """
    Golden test case definition.
    
    Loaded from JSON file, immutable during runtime.
    Pydantic model provides validation on load.
    """
    question: str = Field(..., min_length=1, description="Question to test")
    expected_answer: str = Field(..., min_length=1, description="Expected answer content")
    expected_chunks: list[str] = Field(..., min_items=1, description="Chunk IDs that should be retrieved")
    keywords: list[str] = Field(..., min_items=1, description="Keywords to check in answer")
    
    # Metadata (optional)
    subject: str | None = Field(None, description="Subject area (biology, programming, etc.)")
    difficulty: str | None = Field(None, description="Difficulty level (beginner, intermediate, advanced)")
    
    class Config:
        frozen = True  # Immutable
        schema_extra = {
            "example": {
                "question": "What is photosynthesis?",
                "expected_answer": "Photosynthesis is the process by which plants convert light energy into chemical energy.",
                "expected_chunks": ["biology_photosynthesis_chunk_1", "biology_photosynthesis_chunk_2"],
                "keywords": ["light", "energy", "plants", "chlorophyll"],
                "subject": "biology",
                "difficulty": "beginner"
            }
        }
```

**JSON Schema** (for `golden_dataset.json`):
```json
{
  "version": "1.0",
  "pairs": [
    {
      "question": "string (required)",
      "expected_answer": "string (required)",
      "expected_chunks": ["string", "..."] (required, min 1),
      "keywords": ["string", "..."] (required, min 1),
      "subject": "string (optional)",
      "difficulty": "string (optional)"
    }
  ]
}
```

**Validation Rules**:
- Must have exactly 15 pairs in dataset
- Each pair must have non-empty question, expected_answer
- Each pair must have at least 1 expected chunk and 1 keyword
- Chunk IDs must match format from existing RAG system

**Location**: `tests/fixtures/golden_dataset.json`

---

### 4. Metrics (Embedded Value Object)

**Purpose**: Aggregated statistics computed from test case results

**Lifecycle**: Computed once per EvaluationRun after all tests complete

```python
@dataclass(frozen=True)
class Metrics:
    """
    Aggregated metrics computed from all test case results.
    
    Embedded value object within EvaluationRun.
    Immutable - computed once and never modified.
    """
    # Precision metrics
    retrieval_precision_avg: float  # Mean precision across all tests (0.0-1.0)
    retrieval_precision_min: float  # Worst-case precision (0.0-1.0)
    retrieval_precision_max: float  # Best-case precision (0.0-1.0)
    
    # Keyword match metrics
    keyword_match_avg: float        # Mean keyword match rate (0.0-1.0)
    keyword_match_min: float        # Worst-case match rate (0.0-1.0)
    keyword_match_max: float        # Best-case match rate (0.0-1.0)
    
    # Latency metrics
    latency_p50_ms: float           # Median latency (milliseconds)
    latency_p95_ms: float           # 95th percentile latency (milliseconds)
    latency_min_ms: int             # Fastest query (milliseconds)
    latency_max_ms: int             # Slowest query (milliseconds)
    
    # Pass/fail summary
    pass_rate: float                # Percentage of tests that passed (0.0-1.0)
    tests_passed: int               # Count of passed tests
    tests_failed: int               # Count of failed tests
    
    def __post_init__(self):
        """Validate metric ranges"""
        assert 0.0 <= self.retrieval_precision_avg <= 1.0
        assert 0.0 <= self.keyword_match_avg <= 1.0
        assert 0.0 <= self.pass_rate <= 1.0
        assert self.latency_p50_ms >= 0
        assert self.latency_p95_ms >= self.latency_p50_ms  # p95 ≥ p50
        assert self.tests_passed + self.tests_failed == 15  # Total = 15
```

**Computation** (from list of TestCaseResult):
```python
def compute_metrics(results: list[TestCaseResult]) -> Metrics:
    """Compute aggregated metrics from test results"""
    precisions = [r.retrieval_precision for r in results]
    matches = [r.keyword_match_rate for r in results]
    latencies = [r.latency_ms for r in results]
    passed_count = sum(1 for r in results if r.passed)
    
    # Compute percentiles using stdlib statistics
    import statistics
    quantiles = statistics.quantiles(latencies, n=100, method='inclusive')
    p50 = quantiles[49]  # Median
    p95 = quantiles[94]  # 95th percentile
    
    return Metrics(
        retrieval_precision_avg=statistics.mean(precisions),
        retrieval_precision_min=min(precisions),
        retrieval_precision_max=max(precisions),
        keyword_match_avg=statistics.mean(matches),
        keyword_match_min=min(matches),
        keyword_match_max=max(matches),
        latency_p50_ms=p50,
        latency_p95_ms=p95,
        latency_min_ms=min(latencies),
        latency_max_ms=max(latencies),
        pass_rate=passed_count / len(results),
        tests_passed=passed_count,
        tests_failed=len(results) - passed_count
    )
```

**Validation Rules**:
- All precision/match metrics in range [0.0, 1.0]
- `latency_p95_ms >= latency_p50_ms` (percentile ordering)
- `tests_passed + tests_failed == 15` (total test count)

---

## Relationships

### EvaluationRun → TestCaseResult (Composition, 1-to-Many)

```python
# In repository/storage layer
class EvaluationRepository:
    async def save_run(self, run: EvaluationRun, results: list[TestCaseResult]) -> None:
        """Save run and associated results in single transaction"""
        async with aiosqlite.connect(self.db_path) as db:
            # Insert run
            await db.execute(
                "INSERT INTO evaluation_runs (...) VALUES (...)",
                run.to_tuple()
            )
            # Insert results (cascade)
            for result in results:
                await db.execute(
                    "INSERT INTO test_case_results (run_id, ...) VALUES (?, ...)",
                    (run.run_id, *result.to_tuple())
                )
            await db.commit()
```

**Cascade Rules**:
- Deleting EvaluationRun deletes all associated TestCaseResults
- Cannot delete TestCaseResult independently (owned by EvaluationRun)

### EvaluationRun → Metrics (Embedded)

Metrics is embedded as JSON blob in `evaluation_runs` table (denormalized for query efficiency).

```sql
CREATE TABLE evaluation_runs (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    metrics_json TEXT,  -- JSON serialized Metrics object
    ...
);
```

---

## Database Schema

### evaluation_runs table

```sql
CREATE TABLE IF NOT EXISTS evaluation_runs (
    run_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,  -- ISO 8601 format
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
    duration_ms INTEGER,
    passed INTEGER NOT NULL DEFAULT 0,  -- Boolean (0/1)
    error_message TEXT,
    golden_dataset_version TEXT NOT NULL DEFAULT '1.0',
    test_case_count INTEGER NOT NULL DEFAULT 15,
    
    -- Embedded metrics (denormalized for query performance)
    metrics_json TEXT,  -- JSON serialized Metrics object
    
    -- Indexes
    created_at_utc DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX idx_timestamp ON evaluation_runs(timestamp DESC);
CREATE INDEX idx_status ON evaluation_runs(status);
CREATE INDEX idx_passed_timestamp ON evaluation_runs(passed DESC, timestamp DESC);
```

### test_case_results table

```sql
CREATE TABLE IF NOT EXISTS test_case_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    question TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    expected_chunks_json TEXT NOT NULL,  -- JSON array
    keywords_json TEXT NOT NULL,         -- JSON array
    actual_answer TEXT NOT NULL,
    retrieved_chunks_json TEXT NOT NULL, -- JSON array
    retrieval_precision REAL NOT NULL CHECK(retrieval_precision >= 0.0 AND retrieval_precision <= 1.0),
    keyword_match_rate REAL NOT NULL CHECK(keyword_match_rate >= 0.0 AND keyword_match_rate <= 1.0),
    latency_ms INTEGER NOT NULL CHECK(latency_ms >= 0),
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    
    FOREIGN KEY (run_id) REFERENCES evaluation_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_run_id ON test_case_results(run_id);
```

---

## Validation Summary

| Entity | Validation Rules | Enforced By |
|--------|-----------------|-------------|
| **EvaluationRun** | - UUID v4 format<br>- Valid status enum<br>- Positive duration_ms<br>- Metrics not null if completed | Dataclass + business logic |
| **TestCaseResult** | - Precision/match in [0.0, 1.0]<br>- Non-negative latency<br>- Non-empty required fields | `__post_init__` assertions |
| **GoldenPair** | - Non-empty strings<br>- At least 1 chunk and keyword | Pydantic validation |
| **Metrics** | - Precision/match in [0.0, 1.0]<br>- p95 ≥ p50<br>- Total tests = 15 | `__post_init__` assertions |

---

## State Transitions

### EvaluationRun Lifecycle

```
CREATED (constructor)
   │
   ├─→ RUNNING (initial state)
   │      │
   │      ├─→ COMPLETED (mark_completed)
   │      │      └─→ [terminal state]
   │      │
   │      └─→ FAILED (mark_failed)
   │             └─→ [terminal state]
```

**Allowed transitions**:
- RUNNING → COMPLETED (normal completion)
- RUNNING → FAILED (error during execution)

**Forbidden transitions**:
- COMPLETED → RUNNING (no retry from completed state)
- FAILED → RUNNING (no retry from failed state)
- COMPLETED ↔ FAILED (terminal states are immutable)

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **EvaluationRun as aggregate root** | Owns TestCaseResults lifecycle, enforces consistency |
| **TestCaseResult as frozen dataclass** | Immutable value object, thread-safe |
| **GoldenPair as Pydantic model** | Validation on JSON load, schema enforcement |
| **Metrics embedded in EvaluationRun** | Avoids join query overhead, metrics always retrieved with run |
| **JSON arrays in SQLite** | Avoids N+1 queries, acceptable for small lists (<50 items) |
| **Cascade delete for TestCaseResults** | Results have no meaning without parent run |
| **UUIDs for run_id** | Globally unique, supports distributed systems (future) |

---

**Data Model Complete**: Ready for API contract design (Phase 1 next step).
