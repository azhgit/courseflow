# Middleware Behavior Specification

**Feature**: 006-demo-protection  
**Component**: Quota Protection Middleware

## Overview

The quota middleware intercepts all requests to `/api/v1/query` and `/api/v1/query/stream` to enforce quota limits and serve cached demo responses.

---

## Enforcement Flow

```
Request → Extract Client IP → Check Cache → Check IP Limit → Check Daily Quota → Allow/Reject
```

### Step 1: IP Extraction

**Sources** (in priority order):
1. `X-Forwarded-For` header (first IP if comma-separated)
2. `Request.client.host` (direct connection)

**Error Handling**:
- If IP cannot be determined → HTTP 400 with `IPAddressUnavailable` error

### Step 2: Cache Matching

**Process**:
1. Normalize user question: `lowercase → strip punctuation → collapse whitespace`
2. Compare against normalized cached questions (exact match)
3. If match found → serve cached answer, skip quota checks

**Cache Hit Behavior**:
- Response is streamed word-by-word (30ms delay per word)
- Daily quota counter is NOT incremented
- IP quota counter is NOT incremented
- Cache hit counter IS incremented (for hit rate calculation)

### Step 3: Per-IP Hourly Limit

**Logic**:
```python
# Rolling 60-minute window
current_requests = count_requests_in_last_hour(ip)
if current_requests >= hourly_limit:
    raise IPLimitExceededError(retry_after=seconds_until_oldest_request_expires)
```

**Error Response** (HTTP 429):
```json
{
  "error": "IPLimitExceeded",
  "message": "IP 192.168.1.100 exceeded hourly limit (20 requests/hour). Retry after 1800 seconds.",
  "details": {
    "ip": "192.168.1.100",
    "limit": 20,
    "retry_after_seconds": 1800
  },
  "timestamp": "2026-02-16T14:30:00Z",
  "path": "/api/v1/query"
}
```

**Headers**:
```
Retry-After: 1800
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708106400
```

### Step 4: Global Daily Quota

**Logic**:
```python
daily_ledger = get_daily_ledger()
if daily_ledger.used >= daily_ledger.limit:
    raise DailyQuotaExceededError(reset_at=next_midnight_utc)
```

**Error Response** (HTTP 429):
```json
{
  "error": "DailyQuotaExceeded",
  "message": "Daily quota exhausted (300/300). Resets at 2026-02-17T00:00:00Z.",
  "details": {
    "used": 300,
    "limit": 300,
    "reset_at": "2026-02-17T00:00:00Z"
  },
  "timestamp": "2026-02-16T23:45:00Z",
  "path": "/api/v1/query/stream"
}
```

**Headers**:
```
Retry-After: 900  # Seconds until midnight UTC
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708128000
```

### Step 5: Request Allowed

**Actions**:
1. Record IP request timestamp (for rolling window)
2. Increment daily usage counter (atomic)
3. Add rate limit headers to response
4. Allow request to proceed to RAG pipeline

---

## Response Headers (All Query Requests)

**Success (200) or Allowed (non-quota-error)**:
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 12
X-RateLimit-Reset: 1708106400
X-Cache-Hit: true  # Only present if cache hit
```

**Rate Limited (429)**:
```
Retry-After: 1800
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708106400
```

---

## Cache Configuration

**Default Demo Questions** (10 total):

1. "What is async/await in Python?"
2. "How does RAG work?"
3. "Explain photosynthesis."
4. "What is the derivative of x squared?"
5. "How did World War 2 start?"
6. "What is machine learning?"
7. "Explain REST APIs."
8. "What is Git version control?"
9. "How do vaccines work?"
10. "What is the Pythagorean theorem?"

**Normalization Example**:
```python
# Input: "What is async/await in Python?"
# Normalized: "what is asyncawait in python"

# Input: "What's async/await in Python?!"
# Normalized: "whats asyncawait in python"

# Both match the same cached entry
```

---

## Storage Behavior

### In-Memory (Per-IP Tracking)

**Data Structure**:
```python
{
  "192.168.1.100": deque([
    datetime(2026, 2, 16, 13, 30, 0),
    datetime(2026, 2, 16, 13, 45, 0),
    datetime(2026, 2, 16, 14, 10, 0),
    # ... up to 20 timestamps
  ]),
  "10.0.0.5": deque([...])
}
```

**Lifecycle**:
- Created on first request from IP
- Pruned on each request (remove timestamps > 60 minutes old)
- Reset on server restart (acceptable per spec)

### SQLite (Daily Quota)

**Schema**:
```sql
CREATE TABLE daily_quota (
    date TEXT PRIMARY KEY,  -- YYYY-MM-DD
    used INTEGER NOT NULL DEFAULT 0,
    limit INTEGER NOT NULL,
    cache_hits INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Operations**:
- `get_daily_ledger()`: SELECT or INSERT for today's date
- `increment_daily_usage()`: `UPDATE daily_quota SET used = used + 1 WHERE date = ?`
- `reset_daily_usage()`: Scheduled job at midnight UTC (APScheduler)

---

## Error Scenarios

### 1. Storage Unavailable (HTTP 503)

**Triggers**:
- SQLite database locked
- Database file permission error
- Connection timeout

**Behavior**:
- Fail closed (reject request)
- Return HTTP 503 with clear error message

**Response**:
```json
{
  "error": "StorageUnavailable",
  "message": "Quota storage is temporarily unavailable",
  "details": {
    "reason": "Database connection timeout"
  },
  "timestamp": "2026-02-16T14:30:00Z",
  "path": "/api/v1/query"
}
```

### 2. IP Address Unavailable (HTTP 400)

**Triggers**:
- No `X-Forwarded-For` header
- No `Request.client` available
- Malformed proxy headers

**Response**:
```json
{
  "error": "IPAddressUnavailable",
  "message": "Unable to determine client IP address from request metadata",
  "details": {},
  "timestamp": "2026-02-16T14:30:00Z",
  "path": "/api/v1/query"
}
```

### 3. Client Disconnect During Streaming (FR-016)

**Behavior**:
- Detect `asyncio.CancelledError`
- Abort streaming immediately
- Do NOT log as error (expected behavior)
- Do NOT retry or cleanup (client disconnected)

---

## Configuration (Environment Variables)

```bash
# Quota limits
QUOTA_HOURLY_LIMIT=20         # Per-IP hourly limit
QUOTA_DAILY_BUDGET=300        # Global daily budget

# Cache settings
QUOTA_CACHE_ENABLED=true      # Enable/disable cache
QUOTA_STREAM_DELAY_MS=30      # Word delay for cached streaming
```

**Validation**:
- `QUOTA_HOURLY_LIMIT`: 1-1000
- `QUOTA_DAILY_BUDGET`: 1-10000 (must be >= hourly limit)
- `QUOTA_STREAM_DELAY_MS`: 10-1000

---

## Monitoring & Observability

### Structured Logs

**Request Allowed**:
```json
{
  "level": "INFO",
  "message": "quota_check_passed",
  "ip": "192.168.1.100",
  "ip_count": 5,
  "daily_used": 150,
  "daily_limit": 300,
  "cache_hit": false,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

**Request Rejected**:
```json
{
  "level": "WARN",
  "message": "quota_limit_exceeded",
  "ip": "192.168.1.100",
  "reason": "ip_hourly_limit",
  "retry_after": 1800,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

**Cache Hit**:
```json
{
  "level": "INFO",
  "message": "cache_hit",
  "ip": "192.168.1.100",
  "question_normalized": "what is asyncawait in python",
  "cache_size": 10,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

### Metrics (Future: Prometheus/StatsD)

- `quota.requests.total` (counter)
- `quota.requests.allowed` (counter)
- `quota.requests.rejected` (counter, labels: reason=ip_limit|daily_limit)
- `quota.cache.hits` (counter)
- `quota.cache.misses` (counter)
- `quota.daily.usage` (gauge)
- `quota.daily.percentage` (gauge)
- `quota.ip.active_count` (gauge) - Number of IPs in tracking map

---

## Testing Scenarios

### Scenario 1: Normal Request Flow

```
1. POST /api/v1/query with valid question (non-cached)
2. Middleware extracts IP: 192.168.1.100
3. Cache miss
4. IP count: 5/20 (allowed)
5. Daily usage: 150/300 (allowed)
6. Record IP timestamp
7. Increment daily usage: 151
8. Add headers: X-RateLimit-*
9. Allow request → RAG pipeline
```

### Scenario 2: Cache Hit

```
1. POST /api/v1/query with question: "What is async/await in Python?"
2. Normalize: "what is asyncawait in python"
3. Cache hit found
4. Return cached answer (streaming with 30ms delay)
5. Skip IP and daily quota checks
6. Add header: X-Cache-Hit: true
7. Increment cache hit counter
```

### Scenario 3: IP Limit Exceeded

```
1. POST /api/v1/query from IP: 192.168.1.100
2. IP count in last hour: 20/20
3. Raise IPLimitExceededError
4. Return HTTP 429 with Retry-After: 1800
5. Do NOT allow request
```

### Scenario 4: Daily Quota Exhausted

```
1. POST /api/v1/query from IP: 10.0.0.5
2. IP count: 2/20 (allowed)
3. Daily usage: 300/300 (exhausted)
4. Raise DailyQuotaExceededError
5. Return HTTP 429 with reset_at: next midnight UTC
6. Do NOT allow request
```

### Scenario 5: Midnight Reset

```
Time: 2026-02-16 23:59:59 UTC
- Daily usage: 299/300
- APScheduler job pending

Time: 2026-02-17 00:00:00 UTC
- APScheduler triggers reset_daily_quota()
- UPDATE daily_quota SET used = 0, cache_hits = 0 WHERE date = '2026-02-17'
- New quota window starts

Time: 2026-02-17 00:00:05 UTC
- First request of new day
- Daily usage: 0/300 (fresh quota)
```

---

## Implementation Checklist

- [ ] Middleware intercepts `/api/v1/query` and `/api/v1/query/stream`
- [ ] IP extraction with fallback (X-Forwarded-For → Request.client)
- [ ] Cache normalization matches spec (lowercase, no punctuation, collapsed whitespace)
- [ ] Rolling window tracking (deque with timestamp pruning)
- [ ] SQLite daily usage persistence (atomic increment)
- [ ] APScheduler midnight reset job (cron trigger: 0 0 * * *)
- [ ] Fail-closed on storage errors (HTTP 503)
- [ ] Error responses include retry guidance (Retry-After header)
- [ ] Rate limit headers on all responses
- [ ] Cached streaming simulation (30ms word delay)
- [ ] Client disconnect handling (no error logging)
- [ ] Configuration validation on startup
- [ ] Structured logging for all quota events
- [ ] Quota status endpoint (`GET /api/v1/quota/status`)
- [ ] Health endpoint updated (includes `quota_warning`)
