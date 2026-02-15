# Implementation Plan: Production-Ready Evaluation System

**Branch**: `005-production-polish` | **Date**: 2025-02-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-production-polish/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a production-ready automated evaluation system that validates RAG system quality by running 15 golden Q&A test pairs, measuring retrieval precision (exact chunk ID matching), keyword match rate, and latency (p50/p95). System persists results to SQLite with exponential backoff retry (1s/2s/4s max 3 attempts), exposes REST API for triggering evaluations and retrieving results, and implements concurrency control (HTTP 429 for concurrent requests). Baseline for regression detection uses most recent evaluation run where passed=true. Default automated schedule runs once daily.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (async/await native, type hints)
**Primary Dependencies**: FastAPI 0.109+, aiosqlite, httpx, Pydantic, pytest, APScheduler (for daily scheduling)
**Storage**: SQLite (`data/evaluations.db`) with async operations via aiosqlite
**Testing**: pytest + pytest-asyncio + pytest-cov (80% coverage minimum)
**Target Platform**: Linux server / macOS (API backend)
**Project Type**: Single project (backend API extension to existing CourseFlow RAG system)
**Performance Goals**: 
  - API response: <500ms p95 for latest results, <2s p95 for historical queries
  - Evaluation execution: Complete 15 golden pairs within 5 minutes
  - Latency measurement: ±50ms accuracy
**Constraints**: 
  - Zero-cost: SQLite only (no cloud DB)
  - Concurrency: Single evaluation run at a time (HTTP 429 for concurrent requests)
  - Data retention: 90 days minimum history
  - Retry policy: Exponential backoff 1s/2s/4s (max 3 attempts) for SQLite failures
**Scale/Scope**: 
  - 15 golden Q&A pairs per run
  - ~1000 evaluation runs expected over 90 days
  - Single-user/single-tenant deployment
  - 4 new API endpoints, 3 new domain models, 1 scheduler integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality**: 
- [x] Feature complexity justified (evaluation orchestration ~150 lines, metrics computation ~100 lines, well within limits)
- [x] Documentation strategy defined (API OpenAPI docs via FastAPI, inline docstrings, quickstart.md for users)
- [x] Code review process established (constitution adherence checklist, mypy strict, ruff linting)

**Testing Standards**:
- [x] Test strategy defined:
  - Unit tests: Metrics computation logic (precision, keyword matching, percentile calculations)
  - Integration tests: API endpoints + SQLite persistence with retry logic
  - E2E tests: Full evaluation run with golden dataset mock
- [x] Coverage targets identified (80% overall, 100% for metrics computation and retry logic)
- [x] Test-first approach planned (golden dataset validation, metrics computation tested before implementation)

**User Experience Consistency**:
- [x] Design system usage: N/A (backend API only)
- [x] Accessibility requirements: N/A (backend API only)
- [x] Responsive design: N/A (backend API only)
- [x] Error handling and loading states designed:
  - HTTP 429 for concurrent requests with `retry_after` header
  - HTTP 500 with actionable error messages for SQLite failures
  - Structured JSON error responses with `error_code`, `message`, `details`

**Performance Requirements**:
- [x] Performance targets defined (see Technical Context: <500ms p95 API, <5min evaluation)
- [x] Database query strategy planned:
  - Indexes: `run_id`, `timestamp`, `status` for fast filtering
  - No N+1 queries (single query for run + results join)
  - Async operations via aiosqlite prevent blocking
- [x] Asset optimization: N/A (backend API only)
- [x] Scalability considerations documented:
  - Single evaluation run at a time (no distributed execution)
  - 90-day retention policy prevents unbounded growth
  - SQLite sufficient for ~1000 runs (~100MB estimated)

## Project Structure

### Documentation (this feature)

```text
specs/005-production-polish/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: APScheduler patterns, SQLite retry best practices, percentile computation
├── data-model.md        # Phase 1: EvaluationRun, TestCaseResult, GoldenPair, Metrics entities
├── quickstart.md        # Phase 1: How to trigger evaluations, read results, configure schedule
├── contracts/           # Phase 1: OpenAPI spec for 4 new endpoints
│   └── eval-api.yaml    # POST /api/v1/eval/run, GET /api/v1/eval/run, GET /api/v1/eval/run/:id, GET /api/v1/eval/baseline
└── tasks.md             # Phase 2: NOT created by /speckit.plan (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/courseflow/
├── domain/
│   ├── models.py                  # EXISTING: Query, Document, RAGResult
│   ├── eval_models.py             # NEW: EvaluationRun, TestCaseResult, GoldenPair, Metrics
│   ├── ports.py                   # EXISTING: VectorStorePort, LLMPort
│   ├── eval_ports.py              # NEW: EvaluationServicePort, EvaluationRepositoryPort
│   └── exceptions.py              # EXISTING: + new EvaluationInProgressException
├── application/
│   ├── rag_service.py             # EXISTING: RAG query orchestration
│   ├── evaluation_service.py      # NEW: Evaluation orchestration, metrics computation
│   └── ingestion_service.py       # EXISTING: Document ingestion
├── infrastructure/
│   ├── llm/
│   │   └── gemini.py              # EXISTING: Gemini API client
│   ├── vector_store/
│   │   └── chroma.py              # EXISTING: ChromaDB adapter
│   ├── embeddings/
│   │   └── gemini.py              # EXISTING: Gemini embeddings
│   ├── repositories/
│   │   ├── conversation_repo.py   # EXISTING: SQLite conversation storage
│   │   └── evaluation_repo.py     # NEW: SQLite evaluation storage with retry logic
│   └── scheduler/
│       └── eval_scheduler.py      # NEW: APScheduler integration for daily runs
├── api/
│   ├── main.py                    # EXISTING: App initialization (register new eval routes)
│   ├── routes/
│   │   ├── query.py               # EXISTING: Query endpoints
│   │   ├── health.py              # EXISTING: Health check
│   │   └── evaluation.py          # NEW: 4 evaluation endpoints
│   └── dependencies.py            # EXISTING: DI setup (add eval service injection)
└── config.py                      # EXISTING: Settings (add eval config)

tests/
├── unit/
│   ├── test_metrics_computation.py        # NEW: Test precision, keyword match, percentiles
│   └── test_evaluation_service.py         # NEW: Test orchestration logic
├── integration/
│   ├── test_evaluation_api.py             # NEW: Test API endpoints + SQLite persistence
│   └── test_evaluation_repo_retry.py      # NEW: Test exponential backoff retry logic
├── e2e/
│   └── test_full_evaluation_run.py        # NEW: End-to-end evaluation with mock RAG
└── fixtures/
    └── golden_dataset.json                # NEW: 15 test Q&A pairs

data/
├── chroma/                        # EXISTING: ChromaDB persistence
├── courseflow.db                  # EXISTING: SQLite database
└── evaluations.db                 # NEW: Evaluation results (or table in courseflow.db)
```

**Structure Decision**: Single project structure (Option 1) extended with evaluation subsystem. New modules follow hexagonal architecture: domain models (`eval_models.py`), application service (`evaluation_service.py`), infrastructure adapters (`evaluation_repo.py`, `eval_scheduler.py`), and API routes (`evaluation.py`). This maintains consistency with existing CourseFlow architecture while isolating evaluation concerns.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
