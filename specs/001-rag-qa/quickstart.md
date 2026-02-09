# Quickstart Guide: RAG Question Answering

**Feature**: 001-rag-qa | **Last Updated**: 2025-02-08

## Overview

This guide helps developers set up and run the CourseFlow RAG (Retrieval-Augmented Generation) question answering system locally in under 10 minutes.

**What you'll build**: A working API that answers questions about pre-loaded educational content using AI.

**Prerequisites**:
- Python 3.11 or higher
- Google Gemini API key (free tier)
- 500MB disk space
- macOS or Linux (Windows via WSL)

---

## Step 1: Get a Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

**Cost**: Free tier includes:
- 15 requests per minute
- 1,500 requests per day
- 1M tokens per minute

---

## Step 2: Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/courseflow.git
cd courseflow

# Checkout feature branch
git checkout 001-rag-qa

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
python -c "import chromadb; import fastapi; print('✓ Dependencies installed')"
```

**Expected time**: 2-3 minutes

---

## Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Gemini API key
# Use your favorite editor (nano, vim, VSCode, etc.)
nano .env
```

**Update this line** in `.env`:
```bash
GEMINI_API_KEY=your_api_key_here  # Replace with actual key
```

**Optional settings** (defaults are fine for quickstart):
```bash
# Rate limiting (free tier limits)
RATE_LIMIT_RPM=15
RATE_LIMIT_DAILY=1500

# Vector search settings
SIMILARITY_THRESHOLD=0.5  # Minimum relevance score
TOP_K_RESULTS=3           # Number of docs to retrieve

# Logging
LOG_LEVEL=INFO
```

**Expected time**: 1 minute

---

## Step 4: Initialize Knowledge Base

Load the 10 pre-loaded documents into ChromaDB:

```bash
# Run ingestion script
python scripts/ingest_docs.py

# Expected output:
# Ingested docs/biology/photosynthesis.md (2 chunks)
# Ingested docs/biology/mitosis.md (2 chunks)
# Ingested docs/programming/python-async.md (3 chunks)
# ...
# ✓ Ingested 10 documents (25 chunks total)
```

**What this does**:
1. Reads markdown files from `docs/` directory
2. Chunks documents into 300-500 token segments
3. Generates embeddings using Gemini API
4. Stores in ChromaDB at `./data/chroma`

**Expected time**: 1-2 minutes (depends on API speed)

**Troubleshooting**:
- **Error: "Invalid API key"**: Check your `GEMINI_API_KEY` in `.env`
- **Error: "Rate limit exceeded"**: Wait 60 seconds and retry
- **Error: "Module not found"**: Ensure virtual environment is activated

---

## Step 5: Start the API Server

```bash
# Start FastAPI development server
uvicorn src.courseflow.api.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
# INFO:     Started server process
# INFO:     Application startup complete.
```

**Server will be available at**: `http://localhost:8000`

**Expected time**: 10 seconds

---

## Step 6: Test the API

### Option 1: Interactive API Documentation (Recommended)

1. Open browser: http://localhost:8000/docs
2. Click **POST /api/v1/query**
3. Click **Try it out**
4. Enter a question in the request body:
   ```json
   {
     "query": "What is photosynthesis?"
   }
   ```
5. Click **Execute**
6. See the response with AI-generated answer

### Option 2: Command Line (curl)

```bash
# Ask a biology question
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'

# Expected response (trimmed):
{
  "success": true,
  "data": {
    "answer": "Photosynthesis is the process by which plants...",
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
```

### Option 3: Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "How do I use async/await in Python?"}
)

data = response.json()
print(data["data"]["answer"])
# Output: "To use async/await in Python, you define..."
```

**Expected time**: 1-3 seconds per query

---

## Example Queries by Subject

### Biology
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is mitosis?"}'
```

### Programming
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain Python decorators"}'
```

### History
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What caused World War II?"}'
```

### Math
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do you calculate derivatives?"}'
```

---

## Understanding Responses

### Successful Response

```json
{
  "success": true,
  "data": {
    "answer": "Mitosis is the process of cell division...",
    "sources": ["docs/biology/mitosis.md"],
    "retrieval_count": 3,
    "top_similarity": 0.92
  },
  "metadata": {
    "request_id": "req_xyz789",
    "timestamp": "2025-02-08T13:00:00Z",
    "latency_ms": 987,
    "token_count": 423
  },
  "error": null
}
```

**Fields explained**:
- `success`: `true` if query succeeded
- `data.answer`: AI-generated answer based on knowledge base
- `data.sources`: Source document paths (for citation)
- `data.retrieval_count`: How many documents were used (max 3)
- `data.top_similarity`: Relevance score of best match (0-1 scale)
- `metadata.latency_ms`: Response time in milliseconds
- `metadata.token_count`: Gemini API tokens consumed

### Error Response (Rate Limit)

```json
{
  "success": false,
  "data": null,
  "metadata": {
    "request_id": "req_limit123",
    "timestamp": "2025-02-08T13:01:00Z",
    "latency_ms": 8
  },
  "error": {
    "type": "quota_exceeded",
    "message": "Gemini API quota exceeded (15 RPM limit). Please retry after 48 seconds.",
    "retry_after": 48
  }
}
```

**What to do**: Wait `retry_after` seconds before retrying.

### Error Response (No Relevant Docs)

```json
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

**What to do**: Rephrase your question or ask about content in the knowledge base.

---

## Health Check

Verify system status:

```bash
curl http://localhost:8000/api/v1/health
```

**Expected response**:
```json
{
  "status": "ok",
  "timestamp": "2025-02-08T13:05:00Z",
  "services": {
    "chromadb": "ok",
    "database": "ok",
    "gemini_api": "ok"
  },
  "version": "1.0.0"
}
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest tests/e2e/            # End-to-end tests

# Run with coverage report
pytest --cov=src/courseflow --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Expected output**:
```
======================== test session starts ========================
collected 42 items

tests/unit/test_models.py ...................... [ 52%]
tests/unit/test_rag_service.py ................ [ 85%]
tests/integration/test_api_query.py .......... [100%]

======================== 42 passed in 12.34s ========================
```

---

## Stopping the Server

Press `CTRL+C` in the terminal running `uvicorn`.

**Clean shutdown**:
```bash
# Stop server
CTRL+C

# Deactivate virtual environment
deactivate
```

---

## Next Steps

### Add Your Own Documents

1. Create a new markdown file in `docs/` (e.g., `docs/chemistry/periodic-table.md`)
2. Re-run ingestion script:
   ```bash
   python scripts/ingest_docs.py
   ```
3. Query the new content

### Monitor Usage

Check query history:
```bash
# View SQLite database
sqlite3 data/courseflow.db

# SQL queries
SELECT COUNT(*) FROM queries WHERE timestamp > datetime('now', '-1 day');
SELECT AVG(latency_ms), MAX(latency_ms) FROM queries;
```

### Customize Settings

Edit `.env` to change:
- `SIMILARITY_THRESHOLD`: Lower = more results, less relevant
- `TOP_K_RESULTS`: More results = better context, slower response
- `RATE_LIMIT_RPM`: Adjust based on your API quota

---

## Troubleshooting

### API returns 500 errors
- Check server logs in terminal
- Verify `GEMINI_API_KEY` is valid
- Ensure ChromaDB initialized: `ls -la data/chroma/`

### "No module named 'courseflow'" error
- Ensure virtual environment is activated: `source .venv/bin/activate`
- Re-install: `pip install -e .`

### Slow responses (>5 seconds)
- Check network connection to Gemini API
- Verify ChromaDB index exists: `python -c "import chromadb; client = chromadb.PersistentClient(path='./data/chroma'); print(client.list_collections())"`

### Rate limit errors
- Wait 60 seconds between requests
- Check daily quota: `SELECT COUNT(*) FROM queries WHERE timestamp > datetime('now', '-1 day');` (should be <1500)

---

## Architecture Overview

```
User Query
    ↓
FastAPI Endpoint (/api/v1/query)
    ↓
Rate Limiter (15 RPM check)
    ↓
Query Embedding (Gemini text-embedding-004)
    ↓
Vector Search (ChromaDB, k=3, threshold=0.5)
    ↓
Context Retrieval (top 3 documents)
    ↓
Answer Generation (Gemini 1.5 Flash)
    ↓
Response + Logging (SQLite)
    ↓
JSON Response
```

---

## API Reference

**Base URL**: `http://localhost:8000`

**Endpoints**:
- `POST /api/v1/query` - Submit a question
- `GET /api/v1/health` - Health check

**Full API documentation**: http://localhost:8000/docs (when server is running)

**OpenAPI schema**: http://localhost:8000/openapi.json

---

## Resources

- **Feature Spec**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Research**: [research.md](./research.md)
- **API Contract**: [contracts/openapi.yaml](./contracts/openapi.yaml)
- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs
- **ChromaDB Docs**: https://docs.trychroma.com/

---

## Summary

✅ **You've successfully**:
1. Set up Python 3.11+ environment
2. Configured Gemini API key
3. Ingested 10 documents into ChromaDB
4. Started FastAPI server
5. Tested question answering API
6. Understood rate limits and error handling

**Total time**: ~10 minutes

**Next**: Try asking your own questions or add custom documents to the knowledge base!
