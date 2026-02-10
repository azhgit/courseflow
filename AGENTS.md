# CourseFlow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-09 07:15:10 UTC

**Constitution**: All development must comply with `.specify/memory/constitution.md` principles:
- Code Quality Standards (clean code, <50 lines/function, documentation)
- Testing Standards (80% coverage, test-first for complex features)
- AI Engineering Standards (token tracking, retry logic, RAG quality metrics)
- Architecture & Tech Stack (hexagonal architecture, async-first)
- Performance Requirements (<2s p95 RAG queries, indexed DB queries)
- Zero-Cost Constraints (free-tier APIs only, local storage)
- Domain-Agnostic Design (any subject supported)
- User Experience (API-first, consistent JSON responses)

## Active Technologies

**Current Feature (001-rag-qa)**: FastAPI 0.109+, httpx (async HTTP), ChromaDB 0.4.22+, aiosqlite, Google Gemini 1.5 Flash API + ChromaDB (vector store at ./data/chroma), SQLite (metadata at ./data/courseflow.db)

**Technology Details**:
- **Language**: Python 3.11+ (async/await, improved type hints)
- **API Framework**: FastAPI 0.109+ (async, OpenAPI auto-docs, Pydantic validation)
- **AI/ML Stack**:
  - LLM: Google Gemini 1.5 Flash API (free tier: 15 RPM, 1M TPM)
  - Embeddings: Gemini text-embedding-004 (768 dimensions)
  - Vector Database: ChromaDB 0.4.22+ (local, persistent, cosine similarity)
- **Data Layer**:
  - Database: SQLite with aiosqlite (local, `./data/courseflow.db`)
  - Vector Store: ChromaDB (`./data/chroma`)
- **Development Tools**:
  - Linting: ruff (replaces flake8, black, isort)
  - Type Checking: mypy --strict
  - Testing: pytest + pytest-asyncio + pytest-cov
  - HTTP Client: httpx (async)

## Project Structure

```text
src/courseflow/
├── domain/                    # Business logic (LLM-agnostic)
│   ├── models.py              # Core data models (Query, Document, Answer)
│   ├── ports.py               # Interfaces (VectorStorePort, LLMPort)
│   └── exceptions.py          # Custom exceptions
├── application/               # Use cases
│   ├── rag_service.py         # RAG query orchestration
│   └── rate_limiter.py        # Rate limit tracking (15 RPM)
├── infrastructure/            # Adapters (external dependencies)
│   ├── llm/gemini.py          # Gemini API client (async, retry)
│   ├── vector_store/chroma.py # ChromaDB adapter
│   ├── embeddings/gemini.py   # Gemini embeddings
│   └── repositories/query_repo.py  # SQLite query storage
├── api/                       # FastAPI routes
│   ├── main.py                # App initialization
│   ├── routes/query.py        # POST /api/v1/query
│   └── dependencies.py        # DI setup
└── config.py                  # Settings (Pydantic BaseSettings)

tests/
├── unit/                      # Isolated tests (mocks)
├── integration/               # API + DB tests
├── e2e/                       # Full RAG pipeline
└── fixtures/golden_qa_pairs.json  # Test dataset

data/                          # Local data (gitignored)
├── chroma/                    # ChromaDB persistence
└── courseflow.db              # SQLite database

docs/                          # Knowledge base (10 pre-loaded docs)
├── programming/python-async.md
├── biology/photosynthesis.md
└── history/world-war-2.md
```

## Commands

**Python 3.11+ (FastAPI + RAG)**:
```bash
# Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Development
uvicorn src.courseflow.api.main:app --reload  # Start API server
python scripts/ingest_docs.py                 # Load knowledge base

# Testing
pytest                                        # All tests
pytest tests/unit/                            # Unit tests only
pytest --cov=src/courseflow --cov-report=html # With coverage

# Code Quality
ruff check .                                  # Lint
ruff format .                                 # Format
mypy --strict src/                            # Type check

# Database
sqlite3 data/courseflow.db                    # Query SQLite
```

## Code Style

**Python 3.11+**: 
- Follow PEP 8 (enforced by ruff)
- Type hints required (mypy --strict)
- Async/await for all I/O operations
- Pydantic models for all API requests/responses
- Docstrings for all public APIs (Google style)
- Max function length: 50 lines (80 for RAG orchestration with justification)
- Max file length: 500 lines

**FastAPI Patterns**:
- Use `Depends()` for dependency injection
- Pydantic `BaseSettings` for configuration
- Structured logging with request_id for traceability
- Consistent error responses (type, message, retry_after)

**RAG-Specific**:
- Always log token usage (prompt + completion)
- Implement retry logic with exponential backoff (1s, 2s, 4s)
- Track retrieval metrics (similarity scores, latency)
- Use golden dataset for testing (15+ Q&A pairs)

## Recent Changes

### Feature 001-rag-qa (2025-02-08)
**Added**:
- RAG question answering system (vector search + LLM generation)
- Gemini 1.5 Flash integration with retry logic
- ChromaDB vector store with 0.5 similarity threshold
- Rate limiting (15 RPM, 1500 req/day)
- SQLite query logging for metrics
- 10 pre-loaded documents (biology, programming, history)
- OpenAPI documentation (`/docs` endpoint)

**Technologies Introduced**:
- Python 3.11+ (async/await)
- FastAPI 0.109+
- Google Gemini API (LLM + embeddings)
- ChromaDB 0.4.22+
- SQLite with aiosqlite

<!-- MANUAL ADDITIONS START -->
<!-- Add any manual context here; it will be preserved across updates -->
<!-- MANUAL ADDITIONS END -->
