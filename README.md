# CourseFlow

> AI-Powered Knowledge Q&A System (RAG-based) - Domain-agnostic learning assistant supporting any subject

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 🗺️ Navigation

**Quick Links:**
- 📖 [Quick Start Guide](docs/QUICKSTART.md) - 新手入門指南
- 🤝 [Contributing Guide](CONTRIBUTING.md) - 貢獻指南
- 📚 [Features](docs/features/) - 功能文檔
- 📊 [Changelog](docs/CHANGELOG.md) - 版本更新記錄
- 🏗️ [Architecture](docs/ARCHITECTURE.md) - 系統架構設計

## 📋 Feature Status

| # | Feature | Status | Documentation |
|---|---------|--------|---|
| 001 | RAG Q&A System | ✅ Complete | [詳情](docs/features/001-rag-qa.md) |
| 002 | Document Ingestion | ✅ Complete | [詳情](docs/features/002-doc-ingestion.md) |
| 003 | Conversation Context | ✅ Complete | - |
| 004 | Streaming Responses | ✅ Complete | - |
| 005 | Production Polish | ✅ Complete | - |
| 006 | Demo Protection | ✅ Complete | - |
| 007 | React Frontend | ✅ Complete | - |
| 008 | Zeabur Deployment | ✅ Complete | - |
| 009 | Wikipedia Scraper | ✅ Complete | [詳情](docs/features/009-web-scraping.md) |

## 📖 Overview

CourseFlow is a **Retrieval-Augmented Generation (RAG)** system that helps students learn any subject by answering questions using a curated knowledge base. Unlike traditional chatbots, CourseFlow grounds its answers in authoritative educational materials, reducing hallucinations and providing cited sources.

### Key Features

- **🎯 Domain-Agnostic**: Supports any subject (programming, science, history, math, etc.)
- **💰 Zero-Cost Architecture**: Runs entirely on free-tier services (Gemini API, ChromaDB, SQLite)
- **⚡ High Performance**: <2s RAG query latency (p95), async/await native
- **🏗️ Clean Architecture**: Hexagonal architecture with clear separation of concerns
- **🔍 Semantic Search**: ChromaDB vector database with cosine similarity retrieval
- **📊 Production-Ready**: Rate limiting, token tracking, structured logging, health checks

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Google Gemini API key (free tier: [Get API Key](https://ai.google.dev/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/courseflow.git
   cd courseflow
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Run the API server**
   ```bash
   uvicorn src.courseflow.api.main:app --reload
   ```

6. **Access API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/api/v1/health

## 📚 Usage Examples

### Ask a Question

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'
```

### Stream a Question (SSE)

```bash
curl -N -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain photosynthesis step by step","conversation_id":null}'
```

Streaming events follow this order:
- `chunk` (repeated): incremental answer text
- `sources` (once): retrieved source files
- `done` (once): final marker with `conversation_id` and `token_count`
- `error` (terminal): structured error (`no_relevant_documents`, `rate_limit_exceeded`, etc.)

### Ingest a Document

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@docs/biology/photosynthesis.md" \
  -F 'metadata={"subject":"biology"}'
```

**Supported formats**: `.md`, `.markdown`, `.txt`, `.pdf`  
**Validation**: max file size 10MB, extension + MIME type checks, sanitized filename/subject.

### List Ingested Documents

```bash
curl "http://localhost:8000/api/v1/documents?subject=biology&limit=20"
```

### List Available Subjects

```bash
curl "http://localhost:8000/api/v1/subjects"
```

**Response:**
```json
{
  "data": {
    "query_id": "e6bd5196-a61f-4e7a-91f2-1ddb6ce6ca85",
    "answer": "Photosynthesis is the process by which green plants convert light energy into chemical energy...",
    "sources": [
      {
        "content": "Photosynthesis is...",
        "source": "docs/biology/photosynthesis.md",
        "subject": "biology",
        "similarity_score": 0.85
      }
    ]
  },
  "metadata": {
    "latency_ms": 1310,
    "timestamp": "2026-02-10T06:00:00",
    "token_usage": {
      "prompt_tokens": 2654,
      "completion_tokens": 143,
      "total_tokens": 2797
    }
  }
}
```

### Check System Health

```bash
curl http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "ok",
  "services": {
    "chromadb": {
      "status": "ok",
      "document_count": 17
    },
    "sqlite": {
      "status": "ok",
      "queries_last_24h": 5
    },
    "rate_limit": {
      "status": "ok",
      "requests_in_last_minute": 2,
      "max_requests_per_minute": 15,
      "available_requests": 13
    }
  }
}
```

### Query with Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/query",
    json={"query": "Explain async/await in Python"}
)

data = response.json()
print(f"Answer: {data['data']['answer']}")
print(f"Sources: {len(data['data']['sources'])}")
print(f"Latency: {data['metadata']['latency_ms']}ms")
```

### Handling Rate Limits

```bash
# When quota exceeded, you'll receive:
{
  "error": {
    "type": "quota_exceeded",
    "message": "Rate limit exceeded (local guard)",
    "details": {
      "retry_after": 45,
      "source": "local_guard"
    }
  }
}
# Check Retry-After header: 45 seconds
```

## 📚 Usage (Deprecated - See Above)

### Ask a Question

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is photosynthesis?",
    "subject": "biology"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "answer": "Photosynthesis is the process by which plants convert light energy into chemical energy...",
    "sources": ["biology/photosynthesis.md"],
    "retrieval_count": 3
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-02-07T12:34:56Z",
    "latency_ms": 1234,
    "token_count": 567
  }
}
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## 🏗️ Architecture

CourseFlow follows **Hexagonal Architecture** (Ports & Adapters):

```
src/courseflow/
├── domain/              # Business logic (LLM-agnostic)
│   ├── models.py        # Core data models
│   ├── ports.py         # Interfaces (VectorStorePort, LLMPort)
│   └── exceptions.py    # Custom exceptions
├── application/         # Use cases
│   ├── rag_service.py   # RAG query orchestration
│   └── ingestion_service.py  # Document ingestion
├── infrastructure/      # Adapters (external dependencies)
│   ├── llm/
│   │   └── gemini.py    # Gemini API client
│   ├── vector_store/
│   │   └── chroma.py    # ChromaDB adapter
│   └── repositories/
│       └── conversation_repo.py  # SQLite storage
└── api/                 # FastAPI routes
    ├── main.py          # App initialization
    └── routes/
        ├── query.py     # Query endpoints
        └── health.py    # Health check
```

### Tech Stack

- **API Framework**: FastAPI (async/await native)
- **LLM Provider**: Google Gemini 1.5 Flash (free tier)
- **Vector Database**: ChromaDB (local, persistent)
- **Database**: SQLite with aiosqlite
- **Testing**: pytest + pytest-asyncio + pytest-cov
- **Linting**: ruff + mypy --strict

## 🧪 Testing

### Run All Tests

```bash
pytest -v --cov
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests (DB, API)
pytest tests/integration/ -v

# End-to-end RAG pipeline tests
pytest tests/e2e/ -v
```

### Coverage Requirements

- Minimum coverage: **80%**
- Critical paths (RAG pipeline): **100%**

## 📊 Performance Benchmarks

| Metric | Target | Notes |
|--------|--------|-------|
| RAG Query (p95) | <2s | End-to-end latency |
| Embedding Generation | <300ms | Gemini API |
| Vector Search | <200ms | ChromaDB local |
| LLM First Token | <1s | Streaming mode |
| Health Check | <100ms | Simple readiness probe |

## 🔒 Rate Limiting

Gemini free tier limits (enforced by CourseFlow):

- **15 requests/minute (RPM)**
- **1,500 requests/day**
- **1M tokens/minute (TPM)**

When quota is exceeded, API returns HTTP 429 with `retry_after` header.

## 📖 Documentation

- **API Documentation**: http://localhost:8000/docs (when server is running)
- **Project Constitution**: [.specify/memory/constitution.md](.specify/memory/constitution.md)
- **Architecture Guide**: Coming soon
- **Deployment Guide**: Coming soon

## 🛠️ Development

### Code Quality Standards

All code must adhere to [CourseFlow Constitution](.specify/memory/constitution.md):

- **Clean Code**: Self-documenting, <50 lines/function, <500 lines/file
- **Testing**: 80% coverage minimum, test-first development
- **Linting**: `ruff check` (zero errors), `mypy --strict`
- **Reviews**: All PRs require review before merge

### Pre-commit Hooks

Install pre-commit hooks to auto-format and lint:

```bash
pre-commit install
```

### CI/CD Pipeline

GitHub Actions runs on every push:

1. Install dependencies
2. Run linting (`ruff check`, `mypy`)
3. Run tests (`pytest --cov`)
4. Verify coverage ≥80%

## 🌍 Supported Subjects

CourseFlow is **domain-agnostic** and supports:

- **Programming**: Python, JavaScript, async/await concepts
- **Science**: Biology (photosynthesis, mitosis), Physics, Chemistry
- **History**: World War II, Ancient Rome, Industrial Revolution
- **Math**: Calculus (derivatives, integrals), Linear Algebra

Add new subjects by uploading documents to `docs/{subject}/`.

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please review the **[Contributing Guide](CONTRIBUTING.md)** for:
- Development workflow
- Code standards and conventions
- Testing requirements
- Documentation guidelines
- Commit message format

For detailed feature documentation, see [docs/features/](docs/features/).

## 🙏 Acknowledgments

- **Google Gemini**: Free-tier LLM API
- **ChromaDB**: Open-source vector database
- **FastAPI**: Modern Python web framework

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Built with ❤️ as a portfolio/demo project showcasing AI engineering and system design**
