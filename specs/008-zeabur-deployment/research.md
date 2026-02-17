# Research: Zeabur Deployment

**Feature**: 008-zeabur-deployment  
**Date**: 2025-02-17  
**Status**: Phase 0 Complete

## Overview

This document contains research findings for deploying CourseFlow to Zeabur Free Trial, including deployment configuration, environment variable patterns, rate limiting strategies, and cold start handling.

---

## 1. Zeabur Deployment Configuration

### Decision
Use Zeabur's automatic detection with optional `zeabur.json` override for build/start commands. Backend deployed as containerized service; frontend deployed as static site.

### Rationale
- Zeabur auto-detects Python (backend) and Node.js (frontend) projects
- `zeabur.json` provides explicit control over build process
- Separate services enable independent scaling (future) and CDN optimization for frontend
- Free Trial includes 512MB RAM, 1 vCPU per service, sufficient for demo

### Alternatives Considered
1. **Single Monolith Service**: Rejected because FastAPI cannot serve React static files efficiently; separate CDN for frontend improves load times
2. **Manual Docker Configuration**: Rejected because Zeabur auto-generates Dockerfile from `zeabur.json`; simpler configuration
3. **Render or Fly.io**: Rejected because Zeabur offers better Free Trial ($5 credit vs $0); simpler GitHub integration

### Configuration Format

**Backend `zeabur.json`**:
```json
{
  "name": "courseflow-backend",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "uvicorn src.courseflow.api.main:app --host 0.0.0.0 --port $PORT",
  "env": {
    "PORT": "8000"
  }
}
```

**Frontend `zeabur.json`**:
```json
{
  "name": "courseflow-frontend",
  "buildCommand": "npm install && npm run build",
  "outputDirectory": "dist",
  "type": "static"
}
```

### PORT Binding
- Zeabur injects `$PORT` environment variable dynamically (typically 3000-5000 range)
- Backend MUST bind to `$PORT`, not hardcoded port
- Update uvicorn command: `--port $PORT` instead of `--port 8000`

### GitHub Webhook
- Zeabur auto-configures webhook when repository is linked
- Webhook triggers rebuild on push to `main` branch
- No manual webhook setup required
- Verify webhook exists: GitHub repo → Settings → Webhooks → Check for `zeabur.com` URL

### Build Timeout
- Zeabur Free Trial: 15-minute build timeout
- Backend build: ~2-3 minutes (pip install dependencies)
- Frontend build: ~1-2 minutes (npm install + vite build)
- Total deployment time: ~5 minutes (build + startup)

### Trade-offs Accepted
- ✅ Single instance per service (no load balancing) - acceptable for demo
- ✅ Ephemeral storage (SQLite resets on redeploy) - acceptable for demo data
- ✅ No staging environment - acceptable for simple feature
- ❌ No custom domain - must use `*.zeabur.app` subdomain

---

## 2. Frontend Build-Time Environment Variables

### Decision
Use Vite's `import.meta.env.VITE_API_URL` pattern with build-time injection via Zeabur dashboard environment variables.

### Rationale
- Vite exposes `VITE_*` prefixed env vars to client-side code
- Build-time injection (not runtime) enables static deployment (no server required)
- Supports separate dev/prod builds without code changes
- Aligns with Vite best practices and zero-cost constraint

### Implementation Pattern

**vite.config.ts** (no changes required):
```typescript
// Vite automatically exposes VITE_* env vars
export default defineConfig({
  // ... existing config
});
```

**src/config/env.ts** (new file):
```typescript
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**src/services/api.ts** (updated):
```typescript
import axios from 'axios';
import { API_URL } from '../config/env';

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
});
```

**Environment Variable Setup**:
- Local dev: `.env.local` → `VITE_API_URL=http://localhost:8000`
- Production: Zeabur dashboard → `VITE_API_URL=https://courseflow-backend.zeabur.app`

### Alternatives Considered
1. **Runtime Config Fetching**: Rejected because requires server to serve config.json; violates static site deployment pattern
2. **Hardcoded URLs**: Rejected because requires code changes for dev/prod; not maintainable
3. **Build Script Arguments**: Rejected because Zeabur doesn't support custom build args easily; env vars simpler

### Trade-offs Accepted
- ✅ Build-time variable (not runtime) - requires rebuild to change URL
- ✅ Prefix requirement (`VITE_*`) - Vite security feature, prevents accidental secret exposure

---

## 3. Rate Limiting with SQLite

### Decision
Implement rate limiter as FastAPI middleware with SQLite storage for IP-based counters, 1-hour rolling window, 20 requests per hour limit.

### Rationale
- SQLite persists across container restarts (stored in mounted volume or committed data directory)
- Simple IP-based tracking (no authentication required for demo)
- 20 req/hour = ~0.33 RPM, well under Gemini 15 RPM limit
- Middleware approach = centralized rate limiting for all endpoints

### Schema Design

```sql
CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    last_request TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rate_limits_ip ON rate_limits(ip_address);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);
```

### Rate Limit Algorithm

**Rolling Window Approach**:
1. Check if entry exists for IP address
2. If entry exists and window not expired (`window_start + 1 hour > NOW`):
   - If `request_count < 20`: Increment counter, allow request
   - If `request_count >= 20`: Return HTTP 429
3. If entry exists and window expired:
   - Reset `request_count = 1`, `window_start = NOW`, allow request
4. If entry doesn't exist:
   - Create entry with `request_count = 1`, `window_start = NOW`, allow request

### Middleware Implementation Pattern

```python
from fastapi import Request, HTTPException
from datetime import datetime, timedelta

async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    
    # Get or create rate limit entry
    entry = await rate_limit_repo.get_by_ip(ip)
    
    if entry:
        window_expired = (datetime.utcnow() - entry.window_start) > timedelta(hours=1)
        
        if window_expired:
            # Reset window
            await rate_limit_repo.reset_window(ip)
            response = await call_next(request)
            return response
        elif entry.request_count >= 20:
            # Limit exceeded
            retry_after = int((entry.window_start + timedelta(hours=1) - datetime.utcnow()).total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        else:
            # Increment counter
            await rate_limit_repo.increment(ip)
    else:
        # Create new entry
        await rate_limit_repo.create_entry(ip)
    
    response = await call_next(request)
    return response
```

### Async SQLite with aiosqlite

**Connection Pattern**:
```python
import aiosqlite

async def get_db_connection():
    conn = await aiosqlite.connect('data/courseflow.db')
    conn.row_factory = aiosqlite.Row
    return conn
```

**Query Pattern**:
```python
async def get_by_ip(self, ip: str):
    async with self.get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM rate_limits WHERE ip_address = ?",
            (ip,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
```

### Alternatives Considered
1. **Redis Rate Limiting**: Rejected because requires external Redis instance; violates zero-cost constraint
2. **In-Memory Rate Limiting**: Rejected because counters reset on container restart; unacceptable for demo persistence requirement (SC-009)
3. **Token Bucket Algorithm**: Rejected because rolling window simpler for hourly limit; token bucket better for bursty traffic

### Trade-offs Accepted
- ✅ IP-based tracking (not user-based) - acceptable for demo; simpler than authentication
- ✅ 1-hour window (not sliding window) - simpler implementation; slight inaccuracy acceptable
- ✅ SQLite local (not distributed) - acceptable for single-instance deployment

---

## 4. Frontend Retry Logic with Exponential Backoff

### Decision
Implement axios response interceptor with exponential backoff (1s, 2s, 4s delays) for 3 retry attempts on timeout or 503 errors.

### Rationale
- Handles cold start delays (up to 30 seconds per spec edge case)
- Exponential backoff prevents overwhelming backend during startup
- Retry on timeout (`ECONNABORTED`) and 503 (Service Unavailable)
- 3 attempts with 1s + 2s + 4s = 7s total retry window, covers typical cold start

### Implementation Pattern

```typescript
import axios, { AxiosError, AxiosRequestConfig } from 'axios';

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000, // 10s per attempt
});

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & { _retryCount?: number };
    
    if (!config._retryCount) {
      config._retryCount = 0;
    }
    
    // Max 3 retries
    if (config._retryCount >= 3) {
      return Promise.reject(error);
    }
    
    // Retry conditions
    const isTimeout = error.code === 'ECONNABORTED';
    const is503 = error.response?.status === 503;
    const shouldRetry = isTimeout || is503;
    
    if (shouldRetry) {
      config._retryCount++;
      
      // Exponential backoff: 2^(n-1) seconds
      const delay = Math.pow(2, config._retryCount - 1) * 1000;
      
      console.log(`Retrying request (attempt ${config._retryCount}/3) after ${delay}ms...`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      
      return axiosInstance(config);
    }
    
    return Promise.reject(error);
  }
);

export default axiosInstance;
```

### User Feedback Pattern

**Loading State with Retry Counter**:
```typescript
const [loading, setLoading] = useState(false);
const [retryAttempt, setRetryAttempt] = useState(0);

// Intercept retry events
axiosInstance.interceptors.request.use((config) => {
  if (config._retryCount) {
    setRetryAttempt(config._retryCount);
  }
  return config;
});

// UI component
{loading && (
  <div>
    <Spinner />
    {retryAttempt > 0 && (
      <p>Backend starting up... Retry attempt {retryAttempt}/3</p>
    )}
  </div>
)}
```

### Alternatives Considered
1. **axios-retry Library**: Considered but rejected; custom interceptor simpler, no additional dependency, same functionality
2. **Fixed Delay Retry**: Rejected because exponential backoff better handles varying cold start times
3. **Infinite Retries**: Rejected because must fail eventually to show user-friendly error

### Trade-offs Accepted
- ✅ Max 3 retries (7s total wait) - may not cover extreme cold starts >7s; acceptable per spec edge case
- ✅ Retry on timeout + 503 only (not other errors) - prevents retry loops on permanent failures
- ✅ Client-side retry (not server-side queue) - simpler architecture; acceptable for single-user demo

---

## 5. ChromaDB in Containerized Environment

### Decision
Commit ChromaDB data directory (`data/chroma/`) to repository; no runtime ingestion required for deployment.

### Rationale
- Knowledge base is static (pre-loaded in Feature 001)
- No dynamic ingestion during deployment = faster startup
- Committed data = no separate data migration step
- Current size ~50-100MB, well under 2GB container storage limit

### Persistence Strategy

**Local Development**:
- ChromaDB persists to `backend/data/chroma/`
- Gitignored in development (`.gitignore`: `data/chroma/`)

**Deployment**:
- Un-gitignore ChromaDB data for deployment branch
- Add to repository: `git add -f data/chroma/`
- Container includes pre-built knowledge base
- No API calls to Gemini for embeddings during startup

### Container Directory Structure

```
/app/
├── src/
├── data/
│   ├── chroma/          # ChromaDB persistence (committed)
│   │   ├── index/
│   │   └── metadata.db
│   └── courseflow.db    # SQLite (ephemeral, reset on redeploy)
```

### File Permissions

Zeabur containers run as non-root user; ensure directories are writable:
```dockerfile
# Dockerfile (if custom)
RUN mkdir -p /app/data/chroma /app/data && \
    chmod -R 777 /app/data
```

### Size Verification

```bash
# Check ChromaDB size before commit
du -sh data/chroma/
# Expected: ~50-100MB for 10K document chunks
```

### Alternatives Considered
1. **Runtime Ingestion**: Rejected because requires Gemini API calls during deployment; slower startup, unnecessary API usage
2. **External Vector DB (Pinecone)**: Rejected because violates zero-cost constraint; requires paid service
3. **Download Data from S3**: Rejected because requires AWS setup; more complex than committing to repo

### Trade-offs Accepted
- ✅ Large repository size (~50-100MB increase) - acceptable for demo; simplifies deployment
- ✅ Data baked into container (not dynamic) - acceptable for static knowledge base
- ✅ No data backup strategy - acceptable for demo; can re-ingest from docs/ if lost

---

## 6. Health Check Endpoint Design

### Decision
Implement `/api/v1/health` endpoint returning HTTP 200 with component status (database, vector_store, llm_api) without authentication.

### Rationale
- Zeabur uses health check to verify deployment success
- Public endpoint enables external monitoring (e.g., UptimeRobot)
- Component status helps debug partial failures
- No authentication required (status info not sensitive)

### Endpoint Response Schema

**Healthy (HTTP 200)**:
```json
{
  "status": "healthy",
  "timestamp": "2025-02-17T12:34:56Z",
  "components": {
    "database": "ok",
    "vector_store": "ok",
    "llm_api": "ok"
  }
}
```

**Degraded (HTTP 503)**:
```json
{
  "status": "degraded",
  "timestamp": "2025-02-17T12:34:56Z",
  "components": {
    "database": "ok",
    "vector_store": "ok",
    "llm_api": "unavailable"
  }
}
```

### Component Health Checks

1. **Database**: Verify SQLite connection
   ```python
   try:
       async with aiosqlite.connect('data/courseflow.db') as conn:
           await conn.execute("SELECT 1")
       return "ok"
   except Exception:
       return "unavailable"
   ```

2. **Vector Store**: Verify ChromaDB client
   ```python
   try:
       client = chromadb.PersistentClient(path="data/chroma")
       client.heartbeat()  # Verify connection
       return "ok"
   except Exception:
       return "unavailable"
   ```

3. **LLM API**: Optional shallow check (no API call to avoid quota usage)
   ```python
   # Option 1: Check API key exists
   if GEMINI_API_KEY:
       return "ok"
   else:
       return "unavailable"
   
   # Option 2: Skip LLM check (not critical for health)
   return "ok"
   ```

### Health Check Status Logic

- **Healthy**: All components "ok" → HTTP 200
- **Degraded**: At least one component "unavailable" but database "ok" → HTTP 503
- **Unavailable**: Database "unavailable" → HTTP 503

### Alternatives Considered
1. **Deep Health Check (LLM API Test Call)**: Rejected because consumes quota; shallow check (API key existence) sufficient
2. **Authenticated Health Check**: Rejected because complicates monitoring; status info not sensitive
3. **Separate Liveness/Readiness Endpoints**: Rejected because overkill for single-instance deployment

### Trade-offs Accepted
- ✅ Shallow health check (no LLM test call) - may miss Gemini API issues; acceptable to avoid quota usage
- ✅ Public endpoint (no auth) - acceptable for demo; status info not sensitive
- ✅ Synchronous checks (no timeout) - acceptable for fast local checks (DB, ChromaDB)

---

## Summary of Key Decisions

| Area | Decision | Primary Rationale |
|------|----------|------------------|
| Deployment Platform | Zeabur Free Trial (2 services) | $5 credit, auto-GitHub integration, simple config |
| Backend Config | `zeabur.json` + PORT binding | Explicit build control, dynamic port assignment |
| Frontend Config | VITE_API_URL build-time injection | Static site deployment, dev/prod separation |
| Rate Limiting | SQLite + middleware (20 req/hour) | Persists across restarts, simple IP tracking |
| Cold Start Handling | Axios retry interceptor (1s, 2s, 4s) | Exponential backoff, 3 attempts = 7s coverage |
| ChromaDB Storage | Committed to repository | Pre-built knowledge base, faster startup |
| Health Check | `/api/v1/health` (public, shallow) | Deployment verification, no quota usage |

---

## Dependency Versions Resolved

All dependencies use existing versions from Features 001 and 007:

- **Python**: 3.11+ (existing)
- **FastAPI**: 0.109+ (existing)
- **uvicorn**: 0.27.0+ (existing)
- **aiosqlite**: 0.19.0+ (existing)
- **chromadb**: 0.4.22+ (existing)
- **Node.js**: 18+ (existing)
- **React**: 18.2.0+ (existing)
- **Vite**: 5.0.0+ (existing)
- **axios**: 1.6.0+ (existing)

**No new dependencies required** - all functionality implemented with existing packages.

---

## Next Steps

1. ✅ Research complete → Proceed to Phase 1 (Design & Contracts)
2. Generate `data-model.md` (rate limit schema)
3. Generate `contracts/health-check.yaml` (OpenAPI spec)
4. Generate `quickstart.md` (deployment guide)
5. Run `/speckit.tasks` to create implementation tasks

---

**Research Status**: ✅ COMPLETE
