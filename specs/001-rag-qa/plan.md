# Implementation Plan: Basic RAG Question Answering

**Branch**: `001-rag-qa` | **Date**: 2025-02-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-rag-qa/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a basic RAG (Retrieval-Augmented Generation) question answering system that allows learners to ask single-turn questions about content in a pre-loaded knowledge base and receive AI-generated answers. The system must operate within free-tier API constraints (Google Gemini), use local storage (ChromaDB + SQLite), and respond to queries within 3 seconds while enforcing rate limits (15 RPM).

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (required for async performance improvements)
**Primary Dependencies**: FastAPI 0.109+, httpx (async HTTP), ChromaDB 0.4.22+, aiosqlite, Google Gemini 1.5 Flash API
**Storage**: ChromaDB (vector store at ./data/chroma), SQLite (metadata at ./data/courseflow.db)
**Testing**: pytest + pytest-asyncio + pytest-cov (80% coverage minimum)
**Target Platform**: Linux/macOS server (local development, future deployment to free-tier hosting)
**Project Type**: Single backend API (FastAPI)
**Performance Goals**: <2s p95 API response time (RAG query end-to-end), <3s p95 for complete user query
**Constraints**: Zero-cost (free-tier APIs only), 15 RPM Gemini limit, 1500 req/day, <512MB RAM, local-only storage
**Scale/Scope**: 10 pre-loaded documents, single-turn queries only, domain-agnostic (any subject)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality**: 
- [x] Feature complexity justified (RAG pipeline orchestration may exceed 50 lines, tracked in complexity table)
- [x] Documentation strategy defined (OpenAPI docs auto-generated, inline docstrings for all public APIs, README quickstart)
- [x] Code review process established (automated checks: ruff, mypy --strict, pytest coverage >80%)

**Testing Standards**:
- [x] Test strategy defined (unit: domain models + ports, integration: API + DB, e2e: RAG pipeline with golden dataset)
- [x] Coverage targets identified (80% overall, 100% for RAG service core logic)
- [x] Test-first approach planned for critical RAG retrieval logic

**User Experience Consistency**:
- [x] Design system usage confirmed (N/A - API-only, consistent JSON response schema defined)
- [x] Accessibility requirements identified (N/A - API-only, future UI will adopt WCAG 2.1 AA)
- [x] Responsive design breakpoints planned (N/A - API-only)
- [x] Error handling and loading states designed (structured error responses with retry_after, HTTP 429/503 for quota/service failures)

**Performance Requirements**:
- [x] Performance targets defined (p95 <2s RAG query, <300ms embedding, <200ms vector search, <1s LLM first token)
- [x] Database query strategy planned (SQLite with indexes on timestamps, aiosqlite connection pooling, query logging for >100ms)
- [x] Asset optimization planned (N/A - API-only)
- [x] Scalability considerations documented (rate limiting at 15 RPM, caching strategy for repeated queries, local ChromaDB <100MB)

**Constitution Violations Requiring Justification**: See Complexity Tracking section below.

**Post-Phase 1 Re-evaluation** (2025-02-08):
- ✅ All design artifacts generated (data-model.md, contracts/, quickstart.md)
- ✅ No new complexity violations introduced during design phase
- ✅ Architecture follows hexagonal pattern (ports/adapters clearly defined)
- ✅ API contracts validated against Pydantic models
- ✅ Agent context updated with technology stack
- 🚧 **Gate Status**: PASSED - Ready for Phase 2 (task generation via /speckit.tasks command)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/courseflow/
├── domain/                    # Business logic (LLM-agnostic)
│   ├── models.py              # Core data models (Query, Document, Answer, RateLimitTracker)
│   ├── ports.py               # Interfaces (VectorStorePort, LLMPort, EmbeddingPort)
│   └── exceptions.py          # Custom exceptions (QuotaExceededError, NoRelevantDocumentsError)
├── application/               # Use cases
│   ├── rag_service.py         # RAG query orchestration (retrieve + generate)
│   └── rate_limiter.py        # Rate limit tracking (15 RPM enforcement)
├── infrastructure/            # Adapters (external dependencies)
│   ├── llm/
│   │   └── gemini.py          # Gemini API client (async, retry logic)
│   ├── vector_store/
│   │   └── chroma.py          # ChromaDB adapter (similarity search, persistence)
│   ├── embeddings/
│   │   └── gemini.py          # Gemini text-embedding-004 client
│   └── repositories/
│       └── query_repo.py      # SQLite query metadata storage (aiosqlite)
├── api/                       # FastAPI routes
│   ├── main.py                # App initialization, middleware, CORS
│   ├── routes/
│   │   ├── query.py           # POST /api/v1/query endpoint
│   │   └── health.py          # GET /api/v1/health endpoint
│   └── dependencies.py        # DI setup (FastAPI Depends())
└── config.py                  # Settings (Pydantic BaseSettings, env vars)

tests/
├── unit/                      # Isolated tests (domain models, mocks)
│   ├── test_models.py
│   ├── test_rag_service.py    # Mock LLM/vector store
│   └── test_rate_limiter.py
├── integration/               # API + DB tests
│   ├── test_api_query.py      # FastAPI TestClient
│   ├── test_chroma.py         # Real ChromaDB integration
│   └── test_query_repo.py     # Real SQLite integration
├── e2e/                       # Full RAG pipeline tests
│   └── test_rag_pipeline.py   # Real API + ChromaDB + Gemini (or mocked)
└── fixtures/                  # Test data (golden dataset)
    └── golden_qa_pairs.json   # 10-20 test questions + expected answers

data/                          # Local data (gitignored)
├── chroma/                    # ChromaDB persistence
└── courseflow.db              # SQLite database

docs/                          # Knowledge base documents (10 pre-loaded)
├── programming/
│   ├── python-async.md
│   └── python-functions.md
├── biology/
│   ├── photosynthesis.md
│   └── mitosis.md
└── history/
    └── world-war-2.md

scripts/
└── ingest_docs.py             # Bulk document ingestion (embeddings + ChromaDB)
```

**Structure Decision**: Single backend API project (Option 1) using hexagonal architecture. This aligns with the constitution's mandated structure (Section IV) and supports domain-driven design with clear separation between business logic (domain), use cases (application), infrastructure adapters, and API layer.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| RAG service orchestration may exceed 50-line function limit | Single RAG query requires: (1) rate limit check, (2) query validation, (3) embedding generation, (4) vector search with threshold filtering, (5) LLM call with retry logic, (6) response formatting, (7) logging. Splitting into 7+ tiny functions reduces readability for inherently sequential pipeline. | Pure functional decomposition (7 separate functions) breaks flow traceability; async/await orchestration logic is clearer when steps are visible in single method with clear sections (documented with comments). Alternative: Keep under 80 lines with inline documentation. |
| Gemini client may need complex retry logic (exponential backoff) | Gemini free tier has rate limits (429), timeouts, and transient failures. Robust error handling requires: (1) detect error type, (2) exponential backoff calculation, (3) retry attempt tracking, (4) final fallback error categorization. | Simple 1-retry logic from spec (FR-004a) insufficient for production-quality demo; exponential backoff (1s, 2s, 4s) is industry standard and demonstrates proper API client design. Will use httpx-retry library to keep custom code minimal. |
