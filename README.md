# CourseFlow

> AI-Powered Knowledge Q&A System (RAG-based) - Domain-agnostic learning assistant supporting any subject

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

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

## 📚 Usage

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

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

All contributions must comply with the [CourseFlow Constitution](.specify/memory/constitution.md).

## 🙏 Acknowledgments

- **Google Gemini**: Free-tier LLM API
- **ChromaDB**: Open-source vector database
- **FastAPI**: Modern Python web framework

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Built with ❤️ as a portfolio/demo project showcasing AI engineering and system design**
