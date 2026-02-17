# Environment Variables Documentation

## Overview

CourseFlow uses environment variables for configuration in both backend and frontend. This document lists all required and optional variables.

## Backend Environment Variables

### Required Variables

| Variable | Description | Example | Notes |
|----------|-------------|---------|-------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` | Required for LLM calls. Get from [Google AI Studio](https://makersuite.google.com/app/apikey) |

### Optional Variables (with defaults)

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` | Production: set to frontend URL |
| `RATE_LIMIT_RPM` | Requests per minute limit for Gemini API | `15` | Free tier limit |
| `RATE_LIMIT_DAILY` | Requests per day limit | `1500` | Free tier limit |
| `DATABASE_URL` | SQLite database path | `sqlite+aiosqlite:///./data/courseflow.db` | Relative to project root |
| `CHROMA_PERSIST_DIR` | ChromaDB persistence directory | `./data/chroma` | Relative to project root |
| `CHROMA_COLLECTION_NAME` | ChromaDB collection name | `courseflow_docs` | Change if you have multiple collections |
| `SIMILARITY_THRESHOLD` | Vector similarity threshold (0.0-1.0) | `0.5` | Lower = more permissive matching |
| `TOP_K_RESULTS` | Number of top chunks to retrieve | `3` | Higher = more context, slower |
| `API_V1_PREFIX` | API route prefix | `/api/v1` | Change if versioning strategy differs |
| `LLM_TIMEOUT_SECONDS` | Timeout for LLM API calls | `30` | Increase for long responses |
| `EMBEDDING_TIMEOUT_SECONDS` | Timeout for embedding API calls | `10` | Usually fast, rarely needs increase |
| `LOG_LEVEL` | Logging level | `INFO` | Options: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `QUOTA_HOURLY_LIMIT` | Per-IP requests per hour | `20` | Rate limiting (Feature 006) |
| `QUOTA_DAILY_BUDGET` | Global daily request budget | `300` | Quota protection (Feature 006) |
| `QUOTA_CACHE_ENABLED` | Enable demo cache bypass | `true` | Set to `false` to disable caching |
| `QUOTA_STREAM_DELAY_MS` | Word delay for cached responses (ms) | `30` | Simulates streaming for cached responses |

### Evaluation System Variables

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `EVAL_DATABASE_PATH` | Evaluation results database path | `./data/evaluations.db` | Separate from main database |
| `EVAL_GOLDEN_DATASET_PATH` | Golden dataset for evaluation | `./tests/fixtures/golden_dataset.json` | Test cases for automated evaluation |
| `EVAL_SCHEDULE_ENABLED` | Enable scheduled evaluations | `true` | Set to `false` to disable auto-eval |
| `EVAL_SCHEDULE_HOUR` | Hour to run daily evaluation (0-23) | `2` | UTC time, 2 AM default |
| `EVAL_SCHEDULE_MINUTE` | Minute to run evaluation (0-59) | `0` | Combined with hour for precise scheduling |
| `EVAL_PRECISION_THRESHOLD` | Precision threshold for passing eval | `0.70` | 70% precision required |
| `EVAL_KEYWORD_MATCH_THRESHOLD` | Keyword match threshold | `0.80` | 80% keyword coverage required |
| `EVAL_LATENCY_P95_THRESHOLD_MS` | P95 latency threshold (ms) | `10000` | 10 seconds max for 95th percentile |

### Zeabur-Specific Variables

| Variable | Description | Example | Notes |
|----------|-------------|---------|-------|
| `PORT` | Port to bind server | `8000` | **Automatically set by Zeabur** - do not override |

## Frontend Environment Variables

### Required Variables

| Variable | Description | Example | Notes |
|----------|-------------|---------|-------|
| `VITE_API_BASE_URL` | Backend API base URL | `https://courseflow-backend.zeabur.app` | **Must be set for production builds** |

### Development vs Production

**Development (`.env`):**
```env
VITE_API_BASE_URL=http://localhost:8000
```

**Production (`.env.production` or Zeabur dashboard):**
```env
VITE_API_BASE_URL=https://courseflow-backend-xxx.zeabur.app
```

**Important:** Frontend environment variables must be prefixed with `VITE_` to be accessible in the browser.

## Configuration Hierarchy

### Backend

1. **Environment variables** (highest priority)
2. `.env` file in project root
3. Default values in `src/courseflow/config.py`

### Frontend

1. **Zeabur dashboard environment variables** (production)
2. `.env.production` file (production builds)
3. `.env` file (development)
4. Default: `http://localhost:8000` (hardcoded fallback)

## Setting Environment Variables

### Local Development

**Backend:**
1. Copy `.env.example` to `.env` (if exists)
2. Or create `.env` file in project root
3. Add required variables:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   ```

**Frontend:**
1. Create `src/frontend/.env` file
2. Add:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Zeabur Production

**Backend:**
1. Go to Zeabur dashboard
2. Select `courseflow-backend` service
3. Go to "Environment Variables" tab
4. Click "Add Variable"
5. Enter `GEMINI_API_KEY` and your actual key
6. Add any other overrides (CORS_ORIGINS, etc.)
7. Click "Redeploy" to apply changes

**Frontend:**
1. Go to Zeabur dashboard
2. Select `courseflow-frontend` service
3. Go to "Environment Variables" tab
4. Click "Add Variable"
5. Enter `VITE_API_BASE_URL` and your backend URL
6. Click "Redeploy" to apply changes

## Security Best Practices

### ✅ DO:
- Store `GEMINI_API_KEY` only in Zeabur dashboard (never commit to Git)
- Use separate API keys for dev/staging/production
- Rotate API keys periodically
- Set restrictive CORS_ORIGINS in production
- Use environment-specific `.env` files

### ❌ DON'T:
- Commit `.env` files to Git (add to `.gitignore`)
- Share API keys in public channels
- Use production API keys in development
- Set CORS_ORIGINS to `*` in production
- Hardcode sensitive values in source code

## Validation

### Backend Validation

Backend will fail to start if required variables are missing:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
GEMINI_API_KEY
  Field required [type=missing, input_value={}, input_type=dict]
```

**Solution:** Set the missing environment variable.

### Frontend Validation

Frontend will use fallback defaults if variables are missing:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

If you see connection errors to `http://localhost:8000` in production, you forgot to set `VITE_API_BASE_URL`.

## Troubleshooting

### "Field required" Error (Backend)

**Problem:** Backend crashes with `ValidationError: GEMINI_API_KEY Field required`

**Solution:**
1. Verify `GEMINI_API_KEY` is set in Zeabur dashboard
2. Check for typos in variable name (case-sensitive)
3. Redeploy service after setting variable

### CORS Errors (Frontend ↔ Backend)

**Problem:** Browser console shows CORS error when frontend calls backend

**Solution:**
1. Verify `CORS_ORIGINS` includes frontend URL
2. Format: comma-separated, no spaces: `https://frontend.zeabur.app,http://localhost:5173`
3. Redeploy backend after updating CORS_ORIGINS

### Frontend Connects to Localhost (Production)

**Problem:** Deployed frontend tries to connect to `http://localhost:8000`

**Solution:**
1. Verify `VITE_API_BASE_URL` is set in Zeabur frontend service
2. Check for typos in variable name (must start with `VITE_`)
3. Rebuild frontend after setting variable

### Rate Limit Not Working

**Problem:** Users can make unlimited requests

**Solution:**
1. Verify `QUOTA_HOURLY_LIMIT` is set (default: 20)
2. Check backend logs for middleware errors
3. Verify SQLite database is writable (check file permissions)

## Example Configurations

### Minimal Production Setup

**Backend:**
```env
GEMINI_API_KEY=AIzaSy...  # Required
CORS_ORIGINS=https://courseflow.zeabur.app  # Your frontend URL
```

**Frontend:**
```env
VITE_API_BASE_URL=https://courseflow-backend.zeabur.app  # Your backend URL
```

### Development Setup

**Backend (.env):**
```env
GEMINI_API_KEY=AIzaSy...  # Your dev API key
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=DEBUG
QUOTA_HOURLY_LIMIT=100  # Higher limit for testing
```

**Frontend (.env):**
```env
VITE_API_BASE_URL=http://localhost:8000
```

### Evaluation-Enabled Setup

**Backend:**
```env
GEMINI_API_KEY=AIzaSy...
EVAL_SCHEDULE_ENABLED=true
EVAL_SCHEDULE_HOUR=2
EVAL_SCHEDULE_MINUTE=0
EVAL_PRECISION_THRESHOLD=0.70
EVAL_DATABASE_PATH=./data/evaluations.db
EVAL_GOLDEN_DATASET_PATH=./tests/fixtures/golden_dataset.json
```

## References

- [Zeabur Environment Variables Guide](https://zeabur.com/docs/environment-variables)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
