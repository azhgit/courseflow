# Quickstart: Demo Quota Protection Middleware

**Feature**: 006-demo-protection  
**Last Updated**: 2026-02-16

## Overview

Protect demo quota with per-IP rate limiting, global daily budgets, and cached demo responses.

**Key Benefits**:
- ✅ Prevent single IP from exhausting daily quota
- ✅ Serve 10 demo questions without consuming quota
- ✅ Monitor quota usage with status endpoint
- ✅ Fail gracefully when quota exhausted

---

## Quick Test (5 minutes)

### 1. Start the API

```bash
cd /Users/huanganzheng/CourseFlow
uvicorn src.courseflow.api.main:app --reload
```

### 2. Check Quota Status

```bash
curl http://localhost:8000/api/v1/quota/status | jq
```

**Expected Response**:
```json
{
  "daily": {
    "used": 0,
    "limit": 300,
    "remaining": 300,
    "percentage_used": 0.00,
    "reset_at": "2026-02-17T00:00:00Z"
  },
  "cache": {
    "questions_count": 10,
    "hit_rate": 0.00
  },
  "quota_warning": false,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

### 3. Test Cache Hit (No Quota Consumed)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is async/await in Python?"}' \
  | jq
```

**Verify**:
- Response includes cached answer
- Header: `X-Cache-Hit: true`
- Quota status still shows `used: 0` (cache bypass working)

### 4. Test Non-Cached Query (Quota Consumed)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum physics?"}' \
  | jq
```

**Verify**:
- Response from RAG pipeline
- No `X-Cache-Hit` header
- Quota status shows `used: 1`

### 5. Test Rate Limit

```bash
# Send 21 requests rapidly from same IP
for i in {1..21}; do
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test query $i\"}" \
    -i | head -1
done
```

**Expected**:
- First 20 requests: `HTTP/1.1 200 OK`
- 21st request: `HTTP/1.1 429 Too Many Requests`
- Response body includes `"error": "IPLimitExceeded"` and `retry_after_seconds`

---

## Configuration

### Environment Variables

Create or update `.env`:

```bash
# Quota limits
QUOTA_HOURLY_LIMIT=20         # Per-IP hourly limit
QUOTA_DAILY_BUDGET=300        # Global daily budget

# Cache settings
QUOTA_CACHE_ENABLED=true      # Enable demo cache
QUOTA_STREAM_DELAY_MS=30      # Word delay for cached responses (ms)
```

### For Testing/Demos

Lower limits to test behavior faster:

```bash
# Test configuration (in .env)
QUOTA_HOURLY_LIMIT=5          # Easier to hit limit
QUOTA_DAILY_BUDGET=20         # Easier to exhaust
```

---

## Usage Examples

### Check Quota Before Demo

```bash
#!/bin/bash
# Script: check-quota.sh

STATUS=$(curl -s http://localhost:8000/api/v1/quota/status)
REMAINING=$(echo $STATUS | jq -r '.daily.remaining')
WARNING=$(echo $STATUS | jq -r '.quota_warning')

echo "Quota Remaining: $REMAINING"

if [ "$WARNING" = "true" ]; then
  echo "⚠️  WARNING: Quota at 80%+ usage"
fi

if [ "$REMAINING" -lt 50 ]; then
  echo "⚠️  LOW QUOTA: Less than 50 queries remaining"
fi
```

### Test Cached vs Non-Cached

```python
import requests

# Cached question (no quota consumed)
cached_response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "What is async/await in Python?"}
)
print(f"Cache Hit: {cached_response.headers.get('X-Cache-Hit', False)}")

# Non-cached question (quota consumed)
non_cached_response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "What is quantum entanglement?"}
)
print(f"Cache Hit: {non_cached_response.headers.get('X-Cache-Hit', False)}")
```

### Monitor Rate Limit Headers

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test"}' \
  -i 2>/dev/null | grep X-RateLimit
```

**Output**:
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1708106400
```

### Simulate Quota Exhaustion

```python
import requests
import time

base_url = "http://localhost:8000/api/v1"

# Get current quota
status = requests.get(f"{base_url}/quota/status").json()
remaining = status["daily"]["remaining"]

print(f"Remaining quota: {remaining}")

# Consume all quota with non-cached queries
for i in range(remaining + 1):
    response = requests.post(
        f"{base_url}/query",
        json={"query": f"Unique question {i} to avoid cache"}
    )
    
    if response.status_code == 429:
        error = response.json()
        print(f"✅ Quota exhausted at query {i+1}")
        print(f"Error: {error['error']}")
        print(f"Reset at: {error['details']['reset_at']}")
        break
    
    time.sleep(0.1)  # Avoid IP rate limit
```

---

## Monitoring

### Health Check with Quota Warning

```bash
curl http://localhost:8000/api/v1/health | jq
```

**Response when quota >80%**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-16T22:15:00Z",
  "quota_warning": true
}
```

### Quota Status Dashboard (Future)

```bash
# Watch quota in real-time
watch -n 5 'curl -s http://localhost:8000/api/v1/quota/status | jq ".daily"'
```

**Output**:
```
Every 5.0s: curl -s http://localhost:8000/api/v1/quota/status | jq ".daily"

{
  "used": 245,
  "limit": 300,
  "remaining": 55,
  "percentage_used": 81.67,
  "reset_at": "2026-02-17T00:00:00Z"
}
```

---

## Troubleshooting

### Issue: "IPAddressUnavailable" error

**Cause**: Middleware can't extract client IP

**Solution**:
1. If behind proxy, ensure `X-Forwarded-For` header is set
2. If local development, ensure `Request.client` is available

```python
# Debug IP extraction
from fastapi import Request

@app.middleware("http")
async def log_ip(request: Request, call_next):
    print(f"X-Forwarded-For: {request.headers.get('X-Forwarded-For')}")
    print(f"Client: {request.client}")
    return await call_next(request)
```

### Issue: Cache not working

**Cause**: Question normalization mismatch

**Debug**:
```python
from src.courseflow.domain.models import DemoCacheEntry

# Test normalization
question = "What's async/await in Python?!"
normalized = DemoCacheEntry.normalize(question)
print(f"Normalized: '{normalized}'")
# Expected: "whats asyncawait in python"
```

**Solution**: Ensure demo questions are normalized identically

### Issue: Quota resets unexpectedly

**Cause**: Server restart resets in-memory IP counters

**Expected Behavior**: Per-IP counters reset on restart (documented in spec)

**Note**: Daily quota persists in SQLite (survives restarts)

### Issue: Midnight reset not triggering

**Cause**: APScheduler not started

**Solution**:
```python
# Ensure scheduler is started in main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    reset_daily_quota,
    trigger=CronTrigger(hour=0, minute=0, timezone='UTC'),
    id='daily_quota_reset'
)
scheduler.start()
```

---

## Demo Script

**Scenario**: Show quota protection during live demo

```bash
#!/bin/bash
# demo.sh - Quota protection demonstration

echo "=== Quota Protection Demo ==="
echo ""

# 1. Show initial quota
echo "1. Initial quota status:"
curl -s http://localhost:8000/api/v1/quota/status | jq '.daily'
echo ""

# 2. Cache hit (no quota consumed)
echo "2. Cached question (no quota consumed):"
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is async/await in Python?"}' \
  -s | jq -r '.answer' | head -n 3
echo ""

# 3. Verify quota unchanged
echo "3. Quota after cache hit (should be unchanged):"
curl -s http://localhost:8000/api/v1/quota/status | jq '.daily.used'
echo ""

# 4. Non-cached query
echo "4. Non-cached question (quota consumed):"
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is quantum physics?"}' \
  -s | jq -r '.answer' | head -n 3
echo ""

# 5. Verify quota incremented
echo "5. Quota after non-cached query (should be +1):"
curl -s http://localhost:8000/api/v1/quota/status | jq '.daily.used'
echo ""

# 6. Test rate limit (send 21 requests)
echo "6. Testing per-IP rate limit (20 req/hour)..."
for i in {1..21}; do
  STATUS=$(curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test $i\"}" \
    -s -w "%{http_code}" -o /dev/null)
  
  if [ "$STATUS" = "429" ]; then
    echo "✅ Rate limit triggered at request $i"
    break
  fi
done
echo ""

echo "=== Demo Complete ==="
```

---

## Next Steps

1. **Run Tests**: `pytest tests/integration/test_quota_middleware.py -v`
2. **Load Test**: Use `locust` or `k6` to simulate heavy traffic
3. **Monitor Logs**: `tail -f logs/quota.log` during demos
4. **Tune Limits**: Adjust `QUOTA_DAILY_BUDGET` based on actual Gemini usage

---

## API Reference

### GET /api/v1/quota/status

**Response**:
```json
{
  "daily": {
    "used": 150,
    "limit": 300,
    "remaining": 150,
    "percentage_used": 50.00,
    "reset_at": "2026-02-17T00:00:00Z"
  },
  "cache": {
    "questions_count": 10,
    "hit_rate": 35.5
  },
  "quota_warning": false,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

### GET /api/v1/health

**Response** (with quota warning):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-16T22:15:00Z",
  "quota_warning": true
}
```

### Error Responses

**IP Limit Exceeded** (HTTP 429):
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

**Daily Quota Exceeded** (HTTP 429):
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
