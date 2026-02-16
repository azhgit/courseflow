# Research: Demo Quota Protection Middleware

**Date**: 2026-02-16  
**Feature**: 006-demo-protection

## Overview

This document consolidates research findings for implementing quota protection middleware. All technical context items were sufficiently clear from existing codebase and constitution requirements. No external research needed.

---

## 1. Rolling Window Implementation

### Decision: In-Memory Deque with Timestamp Pruning

**Rationale**:
- Python's `collections.deque` provides O(1) append and O(n) filtering for old timestamps
- For demo scale (~1000 IPs max, 20 queries/hour each), memory footprint is negligible (<1MB)
- Simple to implement and test

**Implementation Pattern**:
```python
from collections import defaultdict, deque
from datetime import datetime, timedelta

class RollingWindowTracker:
    def __init__(self, window_seconds: int = 3600):
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[datetime]] = defaultdict(deque)
    
    def is_allowed(self, ip: str, limit: int) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Prune old requests
        while self.requests[ip] and self.requests[ip][0] < cutoff:
            self.requests[ip].popleft()
        
        # Check limit
        if len(self.requests[ip]) >= limit:
            return False
        
        # Record request
        self.requests[ip].append(now)
        return True
```

**Alternatives Considered**:
- **Redis with sorted sets**: Rejected due to zero-cost constraint (no external services)
- **SQLite persistence**: Rejected for per-IP tracking (adds latency, unnecessary for session-based counters)
- **Token bucket algorithm**: More complex, unnecessary for simple hourly cap

**Dependency Versions**: None (uses stdlib `collections`, `datetime`)

---

## 2. Daily Quota Persistence

### Decision: SQLite with APScheduler for Midnight Reset

**Rationale**:
- Already using SQLite via `aiosqlite>=0.19.0` (from existing dependency list)
- APScheduler already in dependencies (`apscheduler>=3.10.4`) for scheduled tasks
- Simple schema: single row with `date`, `used_count`, `daily_limit`

**Implementation Pattern**:
```python
# Domain model
@dataclass
class DailyQuotaLedger:
    date: str  # YYYY-MM-DD
    used: int
    limit: int
    
    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)
    
    @property
    def percentage_used(self) -> float:
        return (self.used / self.limit) * 100 if self.limit > 0 else 0

# SQLite adapter
class SQLiteQuotaStore:
    async def get_daily_usage(self) -> DailyQuotaLedger:
        today = datetime.utcnow().date().isoformat()
        # Query or create row for today
        ...
    
    async def increment_usage(self) -> None:
        # Atomic UPDATE daily_quota SET used = used + 1 WHERE date = ?
        ...

# APScheduler reset task
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()
scheduler.add_job(
    reset_daily_quota,
    trigger=CronTrigger(hour=0, minute=0, timezone='UTC'),
    id='daily_quota_reset'
)
```

**Alternatives Considered**:
- **In-memory only**: Rejected (violates FR-012: persist across restarts)
- **File-based JSON**: Less robust than SQLite for concurrent writes

**Dependency Versions**:
- `aiosqlite>=0.19.0` (already in `pyproject.toml`)
- `apscheduler>=3.10.4` (already in `pyproject.toml`)

---

## 3. Cache Matching & Normalization

### Decision: Lowercase + Regex Punctuation Strip + Whitespace Collapse

**Rationale**:
- Spec requirement (FR-006): "lowercase, strip punctuation, collapse whitespace"
- Python's `re.sub()` handles punctuation stripping efficiently
- No need for fuzzy matching (exact match after normalization)

**Implementation Pattern**:
```python
import re

def normalize_question(text: str) -> str:
    """Normalize question for cache matching per FR-006."""
    # Lowercase
    normalized = text.lower()
    # Strip punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    # Collapse whitespace
    normalized = ' '.join(normalized.split())
    return normalized

# Usage
cache = {
    normalize_question("What is async/await?"): "Async/await is...",
    normalize_question("How does RAG work?"): "RAG combines...",
    # ... 10 demo questions total
}

def get_cached_answer(question: str) -> str | None:
    normalized = normalize_question(question)
    return cache.get(normalized)
```

**Alternatives Considered**:
- **Fuzzy matching (Levenshtein)**: Rejected (adds complexity, spec requires exact match)
- **Embedding similarity**: Overkill for 10 demo questions

**Dependency Versions**: None (uses stdlib `re`)

---

## 4. Streaming Simulation for Cached Responses

### Decision: AsyncIO Sleep + Word-by-Word Chunking

**Rationale**:
- Spec requirement (FR-008): 30ms default delay per word
- FastAPI supports Server-Sent Events (SSE) via `StreamingResponse`
- Simple implementation: split cached answer into words, yield with delay

**Implementation Pattern**:
```python
import asyncio
from fastapi.responses import StreamingResponse

async def stream_cached_answer(answer: str, delay_ms: int = 30) -> StreamingResponse:
    async def word_generator():
        words = answer.split()
        for i, word in enumerate(words):
            # Add space between words (except first)
            chunk = word if i == 0 else f" {word}"
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(delay_ms / 1000)  # Convert ms to seconds
    
    return StreamingResponse(
        word_generator(),
        media_type="text/event-stream"
    )
```

**Handling Client Disconnect** (FR-016):
- FastAPI automatically detects disconnects via `asyncio.CancelledError`
- No error logging needed (per spec)

**Alternatives Considered**:
- **Character-by-character**: Too slow, spec says word-by-word
- **Fixed chunk size**: Less natural UX than word boundaries

**Dependency Versions**: None (uses stdlib `asyncio`, FastAPI built-in streaming)

---

## 5. IP Address Extraction

### Decision: Use FastAPI `Request.client.host` with X-Forwarded-For Fallback

**Rationale**:
- FastAPI provides `Request.client.host` for direct connections
- Behind proxies, check `X-Forwarded-For` header (standard proxy pattern)
- Fail with HTTP 400 if IP unavailable (FR-015)

**Implementation Pattern**:
```python
from fastapi import Request, HTTPException

def get_client_ip(request: Request) -> str:
    # Check proxy headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        # Take first IP (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Direct connection
    if request.client and request.client.host:
        return request.client.host
    
    # Unable to determine IP
    raise HTTPException(
        status_code=400,
        detail="Unable to determine client IP address"
    )
```

**Edge Case Handling**:
- Shared public IPs (office NAT): Spec acknowledges this in "Edge Cases" section, no special handling needed (users share quota)
- IPv6: FastAPI handles automatically

**Alternatives Considered**:
- **CloudFlare-specific headers**: Not applicable (local development, no CDN)

**Dependency Versions**: None (uses FastAPI built-in `Request`)

---

## 6. Middleware Integration

### Decision: FastAPI Middleware with Dependency Injection

**Rationale**:
- FastAPI supports custom middleware via `BaseHTTPMiddleware`
- Inject quota service via `Depends()` for testability
- Middleware runs before route handlers, perfect for enforcement

**Implementation Pattern**:
```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

class QuotaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if request is to /api/v1/query or /api/v1/query/stream
        if request.url.path.startswith("/api/v1/query"):
            quota_service = request.app.state.quota_service
            
            try:
                ip = get_client_ip(request)
                quota_service.check_quota(ip)  # Raises if exceeded
            except QuotaExceededError as e:
                return JSONResponse(
                    status_code=429,
                    content={"error": str(e), "retry_after": e.retry_after}
                )
        
        response = await call_next(request)
        return response

# App setup
app = FastAPI()
app.add_middleware(QuotaMiddleware)
```

**Alternatives Considered**:
- **Route-level dependencies**: More invasive, duplicates logic across routes
- **Decorators**: Less idiomatic for FastAPI

**Dependency Versions**: None (uses FastAPI built-in middleware)

---

## 7. Configuration Management

### Decision: Extend Pydantic Settings with Quota Config

**Rationale**:
- Already using `pydantic-settings>=2.1.0` for `config.py`
- Environment-based configuration per FR-011

**Implementation Pattern**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Quota settings
    quota_hourly_limit: int = 20
    quota_daily_budget: int = 300
    quota_cache_enabled: bool = True
    quota_stream_delay_ms: int = 30
    
    class Config:
        env_file = ".env"
```

**Environment Variables**:
```bash
QUOTA_HOURLY_LIMIT=20
QUOTA_DAILY_BUDGET=300
QUOTA_CACHE_ENABLED=true
QUOTA_STREAM_DELAY_MS=30
```

**Alternatives Considered**:
- **Separate config file**: Adds complexity, Pydantic already handles env vars

**Dependency Versions**:
- `pydantic-settings>=2.1.0` (already in `pyproject.toml`)

---

## Summary of Technical Decisions

| Area | Technology/Pattern | Version | Rationale |
|------|-------------------|---------|-----------|
| Rolling window | In-memory deque | stdlib | O(1) append, demo scale fits in memory |
| Daily persistence | SQLite + APScheduler | aiosqlite 0.19+, apscheduler 3.10+ | Already in deps, robust persistence |
| Cache matching | Regex normalization | stdlib re | Simple, matches spec requirements |
| Streaming | AsyncIO + SSE | stdlib asyncio | Native FastAPI support |
| IP extraction | Request.client + headers | FastAPI built-in | Standard proxy-aware pattern |
| Middleware | FastAPI middleware | FastAPI built-in | Non-invasive enforcement |
| Configuration | Pydantic Settings | pydantic-settings 2.1+ | Already in use, env-based config |

**Zero External Dependencies Added**: All functionality uses existing dependencies or stdlib.

**Constitution Alignment**:
- ✅ Zero-cost constraint maintained (no new paid services)
- ✅ Hexagonal architecture preserved (domain → application → infrastructure)
- ✅ Async-first (all I/O is async/await)
- ✅ Type safety (Pydantic models for all data)

---

## Phase 0 Complete

All technical unknowns resolved. Ready to proceed to Phase 1 (Design & Contracts).
