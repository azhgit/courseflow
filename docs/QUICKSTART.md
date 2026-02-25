# CourseFlow Quick Start

This guide gets CourseFlow running locally with the minimum setup.

## Prerequisites

- Python 3.11+
- A Gemini API key

## 1) Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 2) Configure environment

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key
```

## 3) Initialize local data

```bash
mkdir -p data
python scripts/init_db.py
python scripts/ingest_docs.py
```

## 4) Run the API server

```bash
uvicorn src.courseflow.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs:
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 5) Verify core endpoints

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

### Ask a question

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is photosynthesis?"}'
```

### Streaming query (SSE)

```bash
curl -N -X POST http://localhost:8000/api/v1/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain photosynthesis step by step"}'
```

### Quota status

```bash
curl http://localhost:8000/api/v1/quota/status
```

## 6) Optional: Scrape Wikipedia content (Feature 009)

### Dry run

```bash
python -m courseflow.cli.scraper --topics "French_Revolution" --dry-run
```

### Real scrape

```bash
python -m courseflow.cli.scraper --topics "French_Revolution" "World_War_I" --rate-limit 1.0
```

After scraping, query the API again to confirm retrieval works with newly ingested content.

## Troubleshooting

- **401/403 from Gemini**: verify `GEMINI_API_KEY` in `.env`.
- **No relevant documents found**: ingest docs first (`python scripts/ingest_docs.py`) or scrape new topics.
- **Rate limit errors**: wait for reset or use cached demo prompts.
