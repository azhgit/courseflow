# Quickstart: Production-Ready Evaluation System

**Feature**: 005-production-polish  
**Audience**: QA Engineers, DevOps, Developers  
**Reading Time**: 10 minutes

---

## Overview

The evaluation system automatically validates RAG system quality by running 15 golden Q&A test pairs and measuring:
- **Retrieval Precision**: How many correct chunks were retrieved (exact chunk ID matching)
- **Keyword Match Rate**: How many expected keywords appear in generated answers
- **Latency**: Query response times (p50, p95 percentiles)

**Key Benefits**:
- ✅ Objective quality metrics (no manual testing)
- ✅ Regression detection (compare against baseline)
- ✅ Historical trend analysis (track performance over time)
- ✅ Automated scheduling (daily evaluations by default)

---

## Prerequisites

1. **CourseFlow Running**: Ensure RAG system is operational
   ```bash
   # Start CourseFlow API
   uvicorn courseflow.api.main:app --reload
   ```

2. **Golden Dataset**: 15 Q&A test pairs in `tests/fixtures/golden_dataset.json`
   ```json
   {
     "version": "1.0",
     "pairs": [
       {
         "question": "What is photosynthesis?",
         "expected_answer": "Photosynthesis is the process...",
         "expected_chunks": ["biology_photosynthesis_chunk_1", ...],
         "keywords": ["light", "energy", "plants", "chlorophyll"]
       },
       ...14 more pairs
     ]
   }
   ```

3. **Dependencies Installed**:
   ```bash
   uv add APScheduler==3.10.4 tenacity==8.2.3
   ```

---

## Quick Start (30 Seconds)

### 1. Trigger Evaluation

```bash
# Start evaluation run
curl -X POST http://localhost:8000/api/v1/eval/run \
  -H "Content-Type: application/json"

# Response (202 Accepted):
{
  "success": true,
  "data": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "started_at": "2025-02-14T10:30:00Z",
    "estimated_duration_ms": 180000
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-02-14T10:30:00Z"
  },
  "error": null
}
```

### 2. Check Results

```bash
# Get evaluation results
curl http://localhost:8000/api/v1/eval/run/550e8400-e29b-41d4-a716-446655440000

# Response (200 OK):
{
  "success": true,
  "data": {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "duration_ms": 175320,
    "passed": true,
    "metrics": {
      "retrieval_precision_avg": 0.85,
      "keyword_match_avg": 0.92,
      "latency_p50_ms": 1250,
      "latency_p95_ms": 2800,
      "pass_rate": 0.93,
      "tests_passed": 14,
      "tests_failed": 1
    }
  }
}
```

### 3. View Historical Trends

```bash
# List last 10 evaluation runs
curl "http://localhost:8000/api/v1/eval/run?page=1&page_size=10"
```

---

## Common Use Cases

### Use Case 1: Pre-Deployment Quality Check

**Scenario**: Before deploying code changes, verify RAG system still meets quality thresholds

```bash
# Step 1: Trigger evaluation
RUN_ID=$(curl -X POST http://localhost:8000/api/v1/eval/run | jq -r '.data.run_id')

# Step 2: Wait for completion (polls every 10 seconds, max 5 minutes)
for i in {1..30}; do
  STATUS=$(curl http://localhost:8000/api/v1/eval/run/$RUN_ID | jq -r '.data.status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 10
done

# Step 3: Check if passed
PASSED=$(curl http://localhost:8000/api/v1/eval/run/$RUN_ID | jq -r '.data.passed')
if [ "$PASSED" = "true" ]; then
  echo "✅ Quality check PASSED - safe to deploy"
  exit 0
else
  echo "❌ Quality check FAILED - do not deploy"
  exit 1
fi
```

**Integration**: Add to CI/CD pipeline before deployment step

---

### Use Case 2: Regression Detection

**Scenario**: Compare current evaluation against last known-good baseline

```bash
# Step 1: Get baseline metrics (most recent passed run)
BASELINE=$(curl http://localhost:8000/api/v1/eval/baseline | jq '.data.metrics')
BASELINE_PRECISION=$(echo $BASELINE | jq -r '.retrieval_precision_avg')

# Step 2: Run current evaluation
RUN_ID=$(curl -X POST http://localhost:8000/api/v1/eval/run | jq -r '.data.run_id')
# ... wait for completion ...

# Step 3: Get current metrics
CURRENT=$(curl http://localhost:8000/api/v1/eval/run/$RUN_ID | jq '.data.metrics')
CURRENT_PRECISION=$(echo $CURRENT | jq -r '.retrieval_precision_avg')

# Step 4: Compare (flag if degradation >10%)
DEGRADATION=$(echo "($BASELINE_PRECISION - $CURRENT_PRECISION) / $BASELINE_PRECISION * 100" | bc -l)
if (( $(echo "$DEGRADATION > 10" | bc -l) )); then
  echo "⚠️ REGRESSION DETECTED: Precision dropped ${DEGRADATION}%"
  echo "Baseline: $BASELINE_PRECISION | Current: $CURRENT_PRECISION"
fi
```

---

### Use Case 3: Performance Monitoring Dashboard

**Scenario**: Track latency trends over last 30 days

```bash
# Fetch all evaluations from last 30 days
SINCE=$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl "http://localhost:8000/api/v1/eval/run?since=$SINCE&page_size=100" \
  | jq '.data.items[] | {timestamp, latency_p95_ms: .metrics.latency_p95_ms}' \
  | tee latency_trends.jsonl

# Process with your monitoring tool (Grafana, Datadog, etc.)
```

---

### Use Case 4: Debugging Failed Tests

**Scenario**: Investigate why specific test cases failed

```bash
# Get full details including individual test results
curl "http://localhost:8000/api/v1/eval/run/$RUN_ID?include_results=true" \
  | jq '.data.results[] | select(.passed == false)' \
  | jq '{
      question,
      expected_chunks,
      retrieved_chunks,
      retrieval_precision,
      keyword_match_rate,
      latency_ms
    }'

# Example output:
{
  "question": "What is async/await in Python?",
  "expected_chunks": ["python_async_chunk_1", "python_async_chunk_2"],
  "retrieved_chunks": ["python_async_chunk_1", "python_functions_chunk_3"],
  "retrieval_precision": 0.5,     # Only 1/2 chunks correct
  "keyword_match_rate": 0.6,      # 3/5 keywords found
  "latency_ms": 1450
}
```

**Analysis**: Chunk 2 was not retrieved → Check vector database indexing

---

## API Endpoints Reference

### POST /api/v1/eval/run

**Purpose**: Trigger new evaluation run

**Request Body** (optional):
```json
{
  "dataset_version": "1.0",
  "notify_on_completion": false
}
```

**Responses**:
- `202 Accepted`: Evaluation started successfully
- `429 Too Many Requests`: Another evaluation is running (retry after header provided)
- `500 Internal Server Error`: System failure

**Concurrency Note**: Only one evaluation can run at a time. Concurrent requests return HTTP 429.

---

### GET /api/v1/eval/run

**Purpose**: List historical evaluation runs

**Query Parameters**:
- `page` (int, default 1): Page number
- `page_size` (int, default 20, max 100): Items per page
- `status` (enum): Filter by `running`, `completed`, `failed`
- `passed` (bool): Filter by pass/fail status
- `since` (ISO 8601): Return runs after this timestamp
- `until` (ISO 8601): Return runs before this timestamp

**Example**:
```bash
# Get all failed runs from last week
SINCE=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)
curl "http://localhost:8000/api/v1/eval/run?passed=false&since=$SINCE"
```

---

### GET /api/v1/eval/run/{run_id}

**Purpose**: Get detailed results for specific evaluation run

**Query Parameters**:
- `include_results` (bool, default true): Include individual test case results

**Response**: Full evaluation details with metrics and individual test results

**Example**:
```bash
# Get summary only (faster, smaller response)
curl "http://localhost:8000/api/v1/eval/run/$RUN_ID?include_results=false"
```

---

### GET /api/v1/eval/baseline

**Purpose**: Get most recent evaluation run where `passed=true`

**Use Case**: Baseline for regression detection

**Response**: 
- Full evaluation details if baseline exists
- `data: null` if no baseline exists (first run or all runs failed)

**Example**:
```bash
# Check if baseline exists
BASELINE=$(curl http://localhost:8000/api/v1/eval/baseline | jq -r '.data')
if [ "$BASELINE" = "null" ]; then
  echo "No baseline established yet (first run)"
else
  echo "Baseline: $(echo $BASELINE | jq -r '.run_id')"
fi
```

---

## Automated Scheduling

Evaluations run automatically **once daily at 2 AM UTC** by default.

### Viewing Schedule

```python
# Check scheduler configuration
from courseflow.infrastructure.scheduler.eval_scheduler import get_scheduler_status

status = await get_scheduler_status()
print(f"Next run: {status['next_run_time']}")
print(f"Schedule: {status['trigger']}")  # "cron(hour=2, minute=0)"
```

### Changing Schedule

**Option 1**: Environment variable
```bash
# Set in .env file
EVAL_SCHEDULE_CRON="0 14 * * *"  # 2 PM UTC daily
```

**Option 2**: Programmatic configuration
```python
# In src/courseflow/config.py
class Settings(BaseSettings):
    eval_schedule_hour: int = 2  # Default 2 AM
    eval_schedule_minute: int = 0
```

### Disabling Automated Runs

```bash
# Set in .env file
EVAL_AUTO_SCHEDULE_ENABLED=false
```

---

## Quality Thresholds

Evaluation runs are marked as `passed=true` if **all** thresholds are met:

| Metric | Threshold | Configurable |
|--------|-----------|--------------|
| **Retrieval Precision (avg)** | ≥ 70% | Yes (env: `EVAL_PRECISION_THRESHOLD`) |
| **Keyword Match Rate (avg)** | ≥ 80% | Yes (env: `EVAL_KEYWORD_THRESHOLD`) |
| **Latency p95** | < 10 seconds | Yes (env: `EVAL_LATENCY_THRESHOLD_MS`) |

### Customizing Thresholds

```bash
# In .env file
EVAL_PRECISION_THRESHOLD=0.75      # 75% retrieval precision
EVAL_KEYWORD_THRESHOLD=0.85        # 85% keyword match
EVAL_LATENCY_THRESHOLD_MS=8000     # 8 seconds p95 latency
```

---

## Troubleshooting

### Problem: Evaluation returns HTTP 429

**Cause**: Another evaluation is already running

**Solution**:
```bash
# Check current running evaluation
curl http://localhost:8000/api/v1/eval/run?status=running

# Wait for completion or cancel (requires admin endpoint)
# Then retry
```

---

### Problem: All tests fail with 0% precision

**Cause**: Chunk IDs in golden dataset don't match actual RAG system chunk IDs

**Solution**:
```bash
# Step 1: Run a sample query and check chunk IDs returned
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}' \
  | jq '.data.sources[].chunk_id'

# Output: ["bio_photo_001", "bio_photo_002"]

# Step 2: Update golden dataset to use these exact chunk IDs
# Edit tests/fixtures/golden_dataset.json
{
  "question": "What is photosynthesis?",
  "expected_chunks": ["bio_photo_001", "bio_photo_002"],  # Match exactly
  ...
}
```

---

### Problem: SQLite database locked errors

**Cause**: Concurrent writes to SQLite (retry logic should handle this)

**Logs**:
```
WARNING: SQLite locked, retrying in 1s (attempt 1/3)
WARNING: SQLite locked, retrying in 2s (attempt 2/3)
ERROR: SQLite persistence failed after 3 attempts
```

**Solution**:
- **Automatic**: Retry logic handles transient locks (1s, 2s, 4s backoff)
- **Manual**: If persistent, check file permissions on `data/evaluations.db`
- **Workaround**: Reduce concurrent API requests during evaluation

---

### Problem: Evaluation never completes (status stuck on "running")

**Cause**: Evaluation process crashed or timed out

**Solution**:
```bash
# Check logs for errors
tail -f logs/courseflow.log | grep "evaluation"

# Restart FastAPI server
# Evaluation will automatically be marked as "failed" on restart
```

---

## Limitations & Known Issues

### Single-Worker Deployment Only

**Concurrency control uses in-memory lock** (`asyncio.Lock`), which works only for single-worker deployments.

**Workaround for multi-worker**:
- Deploy with single worker: `uvicorn courseflow.api.main:app --workers 1`
- For multi-worker, upgrade to distributed lock (Redis) in future version

**Documentation**: [Architecture Review](./architecture-review.md#6-concurrency-control-strategy-review)

---

### Keyword Matching Limitation

**Current implementation**: Whitespace tokenization only (no multi-word phrases)

**Example**:
- ✅ Works: `keywords: ["neural", "network"]` → matches "neural" AND "network" separately
- ❌ Limitation: Cannot match exact phrase "neural network" as single unit

**Workaround**: Use single-word keywords or accept lower match rate

**Future Enhancement**: Add NLP tokenization (spaCy) for multi-word phrase matching

---

## Best Practices

### 1. Maintain Golden Dataset Quality

- **Review quarterly**: Update expected answers as RAG system improves
- **Add new subjects**: Expand coverage beyond initial 15 pairs
- **Version control**: Track changes to golden dataset in git

### 2. Monitor Trends, Not Absolutes

- Single failed run ≠ crisis
- Look for **sustained degradation** over multiple runs
- Set up alerts for **3 consecutive failures** (not single failure)

### 3. Integrate with CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Run RAG Evaluation
  run: |
    RUN_ID=$(curl -X POST http://localhost:8000/api/v1/eval/run | jq -r '.data.run_id')
    # ... wait for completion ...
    PASSED=$(curl http://localhost:8000/api/v1/eval/run/$RUN_ID | jq -r '.data.passed')
    if [ "$PASSED" != "true" ]; then
      echo "Quality check failed"
      exit 1
    fi
```

### 4. Establish Baseline Early

- Run evaluation **before making changes** to establish baseline
- Use baseline for regression detection on every change
- Re-baseline after intentional improvements

---

## Next Steps

- **Implementation**: See [tasks.md](./tasks.md) for step-by-step implementation checklist
- **API Details**: See [contracts/eval-api.yaml](./contracts/eval-api.yaml) for full OpenAPI spec
- **Data Model**: See [data-model.md](./data-model.md) for entity definitions
- **Research**: See [research.md](./research.md) for technical decisions and algorithms

---

**Questions?** Check the [Architecture Review](./architecture-review.md) or open an issue on GitHub.
