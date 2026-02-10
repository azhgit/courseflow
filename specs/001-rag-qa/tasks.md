# Tasks: Basic RAG Question Answering

**Input**: Design documents from `/specs/001-rag-qa/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/openapi.yaml, research.md, quickstart.md

**Constitution Compliance**: All tasks align with constitution principles:
- Code Quality: Functions <50 lines (exceptions documented in plan.md complexity table), files <500 lines, documented code
- Testing Standards: 80% coverage minimum, pytest + pytest-asyncio for async code
- Performance: API <3s p95 response time, <2s target for RAG pipeline
- Zero-Cost Constraint: Local storage only (ChromaDB + SQLite), Gemini free tier (15 RPM)

**Tests**: Tests are included per specification requirements and TDD approach for critical RAG logic.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure following hexagonal architecture: src/courseflow/{domain/,application/,infrastructure/,api/,config.py}
- [X] T002 Initialize Python 3.11+ project with pyproject.toml dependencies (FastAPI 0.109+, ChromaDB 0.4.22+, httpx, aiosqlite, pydantic, pydantic-settings, google-generativeai)
- [X] T003 [P] Configure ruff (linting + formatting) in pyproject.toml with line-length=100
- [X] T004 [P] Configure mypy strict type checking in pyproject.toml
- [X] T005 [P] Configure pytest and pytest-asyncio in pyproject.toml
- [X] T006 [P] Create .env.example with all required environment variables (GEMINI_API_KEY, RATE_LIMIT_RPM, SIMILARITY_THRESHOLD, etc.)
- [X] T007 [P] Create .gitignore with data/, .venv/, .env, __pycache__/, .pytest_cache/
- [X] T008 Create data/ directory structure: data/chroma/ and data/ (for courseflow.db)
- [X] T009 Create docs/ directory structure with sample documents: docs/biology/, docs/programming/, docs/history/, docs/math/
- [X] T010 [P] Add 10 sample markdown documents (2-3 per subject: photosynthesis.md, mitosis.md, python-async.md, python-functions.md, wwii.md, derivatives.md, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T011 Create domain models in src/courseflow/domain/models.py (Query, Document, DocumentMetadata, SearchResult, Answer, TokenUsage, RateLimitTracker with Pydantic validators)
- [X] T012 [P] Create domain ports in src/courseflow/domain/ports.py (VectorStorePort, LLMPort, EmbeddingPort, QueryRepositoryPort as abstract base classes)
- [X] T013 [P] Create domain exceptions in src/courseflow/domain/exceptions.py (QuotaExceededError, NoRelevantDocumentsError, ServiceUnavailableError, ValidationError)
- [X] T014 Create configuration in src/courseflow/config.py (Settings class using Pydantic BaseSettings with validation)
- [X] T015 Create Gemini embedding client in src/courseflow/infrastructure/embeddings/gemini.py (implements EmbeddingPort with async generate_embedding method)
- [X] T016 [P] Create ChromaDB adapter in src/courseflow/infrastructure/vector_store/chroma.py (implements VectorStorePort with search, add_documents, persistence)
- [X] T017 [P] Create SQLite query repository in src/courseflow/infrastructure/repositories/query_repo.py (implements QueryRepositoryPort with aiosqlite for async DB operations)
- [X] T018 Create database initialization script in scripts/init_db.py (creates queries table with indexes per data-model.md schema)
- [X] T019 Create FastAPI app initialization in src/courseflow/api/main.py (app factory, CORS middleware, lifespan context manager for DB/ChromaDB initialization)
- [X] T020 [P] Create API dependencies in src/courseflow/api/dependencies.py (dependency injection for Settings, ChromaDB client, DB connection, rate limiter)
- [X] T021 [P] Create health check endpoint in src/courseflow/api/routes/health.py (GET /api/v1/health with ChromaDB, SQLite, and Gemini API connectivity checks)
- [X] T022 Create document ingestion script in scripts/ingest_docs.py (reads docs/ markdown files, chunks to 300-500 tokens, generates embeddings, stores in ChromaDB)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single-Turn Question Answering (Priority: P1) 🎯 MVP

**Goal**: Enable learners to ask single questions and receive AI-generated answers based on the knowledge base

**Independent Test**: Send POST /api/v1/query with "What is photosynthesis?" and verify relevant answer returns within 3 seconds with sources listed

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T023 [P] [US1] Create unit tests for Query model validation in tests/unit/test_models.py (test empty text rejection, max length validation, whitespace trimming)
- [X] T024 [P] [US1] Create unit tests for RAG service with mocked dependencies in tests/unit/test_rag_service.py (test retrieval logic, threshold filtering, LLM call orchestration)
- [X] T025 [P] [US1] Create integration test for ChromaDB vector search in tests/integration/test_chroma.py (test real similarity search, threshold filtering with k=3)
- [X] T026 [P] [US1] Create integration test for SQLite query repository in tests/integration/test_query_repo.py (test query logging, timestamp indexing)
- [X] T027 [P] [US1] Create contract test for POST /api/v1/query endpoint in tests/integration/test_api_query.py (test request/response schema validation per openapi.yaml)
- [X] T028 [P] [US1] Create end-to-end test for RAG pipeline in tests/e2e/test_rag_pipeline.py (test full flow with real ChromaDB, mocked Gemini or golden dataset)
- [X] T029 [P] [US1] Create test fixtures in tests/fixtures/golden_qa_pairs.json (MINIMUM 10 question-answer pairs covering all subjects: biology, programming, history, math - as required by constitution RAG testing standards)

### Implementation for User Story 1

- [X] T030 [US1] Implement Gemini LLM client in src/courseflow/infrastructure/llm/gemini.py (implements LLMPort with async generate_answer, exponential backoff retry using tenacity, error categorization per research.md)
- [X] T031 [US1] Implement RAG service in src/courseflow/application/rag_service.py (orchestrates: embedding → vector search → threshold filter → LLM generation → response formatting)
- [X] T032 [US1] Implement query endpoint in src/courseflow/api/routes/query.py (POST /api/v1/query handler with request validation, RAG service call, error handling, response formatting per openapi.yaml)
- [X] T033 [US1] Add structured logging for RAG pipeline in src/courseflow/application/rag_service.py (log query_id, latency, retrieval_count, token_count, similarity_scores)
- [X] T034 [US1] Add error response formatting in src/courseflow/api/routes/query.py (map domain exceptions to HTTP status codes and ErrorResponse schema)
- [X] T035 [US1] Add request/response validation middleware in src/courseflow/api/main.py (validate all requests against Pydantic schemas, return 400 for validation errors)

**Checkpoint**: User Story 1 complete - can query knowledge base and receive AI-generated answers with source attribution

---

## Phase 4: User Story 2 - Rate Limit Handling (Priority: P2)

**Goal**: Provide clear feedback when free-tier API quota is exceeded so learners understand system limitations

**Independent Test**: Send 16 requests within 60 seconds and verify request #16 receives 429 error with retry_after value

### Tests for User Story 2

- [X] T036 [P] [US2] Create unit tests for RateLimitTracker in tests/unit/test_rate_limiter.py (test sliding window logic, is_allowed method, retry_after calculation)
- [X] T037 [P] [US2] Create integration test for rate limiting in tests/integration/test_api_query.py (test 15 RPM enforcement, 429 response, Retry-After header)

### Implementation for User Story 2

- [X] T038 [US2] Implement rate limiter service in src/courseflow/application/rate_limiter.py (uses RateLimitTracker model, tracks per-minute and per-day windows, calculates retry_after)
- [X] T039 [US2] Add rate limiting middleware to query endpoint in src/courseflow/api/routes/query.py (check rate limit before RAG service call, return 429 with retry_after on quota exceeded)
- [X] T040 [US2] Add Retry-After HTTP header to 429 responses in src/courseflow/api/routes/query.py (set header value from QuotaExceededError retry_after attribute)
- [X] T041 [US2] Update error response formatting in src/courseflow/api/routes/query.py (include retry_after in ErrorResponse.error for quota_exceeded type)
- [X] T042 [US2] Add rate limit monitoring to health endpoint in src/courseflow/api/routes/health.py (return current quota usage: requests_in_last_minute, requests_in_last_day)

**Checkpoint**: User Stories 1 AND 2 complete - system handles queries and gracefully enforces rate limits with clear user feedback

---

## Phase 5: User Story 3 - Empty or Irrelevant Query Handling (Priority: P3)

**Goal**: Help learners understand when their question cannot be answered based on available knowledge base

**Independent Test**: Send query "What is the capital of France?" to biology-focused knowledge base and verify "No relevant information found" error response

### Tests for User Story 3

- [X] T043 [P] [US3] Create unit tests for query validation in tests/unit/test_models.py (test empty string rejection, whitespace-only rejection, max length 1000 chars)
- [X] T044 [P] [US3] Create integration test for threshold filtering in tests/integration/test_chroma.py (test queries with max_similarity < 0.5 return empty results)
- [ ] T045 [P] [US3] Create contract test for validation errors in tests/integration/test_api_query.py (test empty query returns 400, irrelevant query returns 404)

### Implementation for User Story 3

- [X] T046 [US3] Add query text validation in src/courseflow/domain/models.py Query class (Pydantic validator for non-empty, max 1000 chars, strip whitespace)
- [X] T047 [US3] Add similarity threshold filtering in src/courseflow/application/rag_service.py (filter SearchResults to only include similarity_score >= 0.5, raise NoRelevantDocumentsError if empty)
- [X] T048 [US3] Add "No relevant information found" error handling in src/courseflow/api/routes/query.py (catch NoRelevantDocumentsError, return 404 with error message and threshold details)
- [ ] T049 [US3] Add query length validation in src/courseflow/api/routes/query.py (return 400 if query exceeds 1000 characters with clear error message)
- [ ] T050 [US3] Update error response to include similarity threshold details in src/courseflow/api/routes/query.py (add threshold and max_similarity to ErrorResponse.error.details for no_relevant_documents type)

**Checkpoint**: All user stories complete - system handles successful queries, rate limits, and edge cases with appropriate error messages

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [ ] T051 [P] Add comprehensive docstrings to all public APIs in src/courseflow/domain/, src/courseflow/application/, src/courseflow/infrastructure/
- [ ] T052 [P] Add inline documentation for complex RAG orchestration in src/courseflow/application/rag_service.py (document each pipeline step)
- [ ] T053 [P] Create README.md in repository root (project overview, quickstart link, architecture diagram, contribution guidelines)
- [ ] T054 [P] Generate API documentation from FastAPI OpenAPI schema (verify /docs endpoint matches contracts/openapi.yaml)
- [ ] T055 Run full test suite with coverage report (pytest --cov=src/courseflow --cov-report=html, verify >= 80% coverage)
- [ ] T056 [P] Add performance monitoring for RAG pipeline in src/courseflow/application/rag_service.py (log embedding_time_ms, search_time_ms, llm_time_ms, total_time_ms)
- [ ] T057 Add query performance metrics to SQLite logging in src/courseflow/infrastructure/repositories/query_repo.py (store latency_ms breakdown: embedding, search, generation)
- [ ] T058 Optimize ChromaDB persistence settings in src/courseflow/infrastructure/vector_store/chroma.py (configure batch size for bulk ingestion)
- [ ] T059 Add input sanitization for LLM prompts in src/courseflow/infrastructure/llm/gemini.py (prevent prompt injection attacks)
- [ ] T060 [P] Run quickstart.md validation (follow all steps, verify all commands succeed, test all example queries)
- [ ] T061 [P] Run security audit with bandit (bandit -r src/courseflow, fix any HIGH severity issues)
- [ ] T062 [P] Run type checking with mypy (mypy src/courseflow --strict, fix all type errors)
- [ ] T063 Code cleanup and refactoring (remove TODOs, ensure all functions < 50 lines or documented in complexity table, remove unused imports)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T010) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion (T011-T022)
- **User Story 2 (Phase 4)**: Depends on Foundational completion (T011-T022) - Can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on Foundational completion (T011-T022) - Can run parallel to US1/US2
- **Polish (Phase 6)**: Depends on all user stories (T023-T050)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - **MVP target**
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (adds rate limiting orthogonally)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2 (adds validation and error handling)

### Within Each User Story

- Tests (T023-T029, T036-T037, T043-T045) MUST be written and FAIL before implementation
- Within US1: Tests can run parallel → Gemini client (T030) before RAG service (T031) → RAG service before query endpoint (T032) → Logging and error handling last (T033-T035)
- Within US2: Tests can run parallel → Rate limiter (T038) before middleware (T039-T042)
- Within US3: Tests can run parallel → Validation (T046-T050) can run in any order (different concerns)

### Parallel Opportunities

- **Setup Phase**: T003-T007 (config files), T010 (sample docs) can all run parallel
- **Foundational Phase**: T012-T013 (ports + exceptions), T015-T017 (infrastructure adapters), T020-T021 (API setup) can run parallel in groups
- **Once Foundational Completes**: All three user stories (US1, US2, US3) can be worked on in parallel by different developers
- **Within US1**: T023-T029 (all tests) can run parallel
- **Within US2**: T036-T037 (all tests) can run parallel
- **Within US3**: T043-T045 (all tests) can run parallel
- **Polish Phase**: T051-T054 (documentation), T061-T062 (linting/type checking) can run parallel

---

## Parallel Example: User Story 1 (Single-Turn QA)

```bash
# Step 1: Launch all tests together (TDD approach):
Task T023: "Unit tests for Query model in tests/unit/test_models.py"
Task T024: "Unit tests for RAG service in tests/unit/test_rag_service.py"
Task T025: "Integration test for ChromaDB in tests/integration/test_chroma.py"
Task T026: "Integration test for SQLite in tests/integration/test_query_repo.py"
Task T027: "Contract test for POST /api/v1/query in tests/integration/test_api_query.py"
Task T028: "E2E test for RAG pipeline in tests/e2e/test_rag_pipeline.py"
Task T029: "Create test fixtures in tests/fixtures/golden_qa_pairs.json"

# Step 2: Verify all tests FAIL (no implementation yet)

# Step 3: Implement sequentially (dependencies):
Task T030: "Gemini LLM client in src/courseflow/infrastructure/llm/gemini.py"
Task T031: "RAG service in src/courseflow/application/rag_service.py" (depends on T030)
Task T032: "Query endpoint in src/courseflow/api/routes/query.py" (depends on T031)

# Step 4: Launch logging and error handling in parallel:
Task T033: "Add logging to RAG service"
Task T034: "Add error response formatting to query endpoint"
Task T035: "Add validation middleware to main.py"

# Step 5: Verify all tests PASS
```

---

## Parallel Example: After Foundational Phase Complete

```bash
# With 3 developers, all user stories can proceed in parallel:

Developer A (US1 - Single-Turn QA):
- Tests: T023-T029 (all parallel)
- Implementation: T030 → T031 → T032 → {T033, T034, T035} parallel

Developer B (US2 - Rate Limiting):
- Tests: T036-T037 (parallel)
- Implementation: T038 → {T039, T040, T041, T042} parallel

Developer C (US3 - Error Handling):
- Tests: T043-T045 (all parallel)
- Implementation: {T046, T047, T048, T049, T050} (can run parallel - different files/concerns)

# All stories integrate cleanly because they're orthogonal:
- US1: Core RAG functionality
- US2: Rate limiting layer (middleware)
- US3: Validation and error responses
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Fastest Path to Value)

1. **Complete Phase 1**: Setup (T001-T010) - ~2 hours
2. **Complete Phase 2**: Foundational (T011-T022) - ~8 hours ⚠️ CRITICAL
3. **Complete Phase 3**: User Story 1 (T023-T035) - ~10 hours
4. **STOP and VALIDATE**: 
   - Run `pytest tests/` (all US1 tests should pass)
   - Run `python scripts/ingest_docs.py` (load knowledge base)
   - Start server: `uvicorn src.courseflow.api.main:app --reload`
   - Test query: `curl -X POST http://localhost:8000/api/v1/query -d '{"query": "What is photosynthesis?"}'`
   - Verify answer returned in < 3 seconds with sources
5. **Deploy/Demo MVP**: Basic RAG QA is functional

**Total MVP time**: ~20 hours (single developer) or ~10 hours (team of 3 parallel)

### Incremental Delivery (Recommended)

1. **Foundation** (Phase 1 + 2) → ~10 hours
   - Checkpoint: Health endpoint returns "ok", database initialized
2. **+ User Story 1** (Phase 3) → +10 hours
   - Checkpoint: Can ask questions and receive answers
   - **Deploy/Demo**: MVP functional - learners can query knowledge base
3. **+ User Story 2** (Phase 4) → +4 hours
   - Checkpoint: Rate limiting enforced, clear 429 errors with retry_after
   - **Deploy/Demo**: Production-ready rate limiting
4. **+ User Story 3** (Phase 5) → +3 hours
   - Checkpoint: Graceful handling of edge cases (empty queries, irrelevant questions)
   - **Deploy/Demo**: Robust error handling
5. **+ Polish** (Phase 6) → +4 hours
   - Checkpoint: Documentation complete, 80%+ test coverage, security audit passed
   - **Deploy/Demo**: Production-ready release

**Total time**: ~31 hours (single developer) or ~15 hours (team of 3)

### Parallel Team Strategy (Fastest)

**Prerequisites**: 3 developers available

1. **Team completes Setup + Foundational together** (Phase 1 + 2) → ~10 hours
   - All developers collaborate on foundation (critical path)
   - Checkpoint: Run `pytest tests/` (should have no tests yet), health endpoint works

2. **Once Foundational complete, parallelize user stories**:
   - **Developer A**: User Story 1 (T023-T035) → 10 hours
   - **Developer B**: User Story 2 (T036-T042) → 4 hours (then helps with US1 or US3)
   - **Developer C**: User Story 3 (T043-T050) → 3 hours (then helps with US1)

3. **Team completes Polish together** (Phase 6) → ~4 hours
   - Run full test suite, coverage report, security audit
   - Update documentation, validate quickstart

**Total time**: ~14 hours (team of 3 working in parallel)

### Checkpoint Validation at Each Stage

After **Setup (Phase 1)**:
- [ ] Directory structure exists: `src/courseflow/`, `tests/`, `docs/`, `data/`, `scripts/`
- [ ] Dependencies installed: `pip install -e .` succeeds
- [ ] Linting works: `ruff check src/`
- [ ] 10 sample documents in `docs/` (2-3 per subject)

After **Foundational (Phase 2)**:
- [ ] Database initialized: `python scripts/init_db.py` creates `data/courseflow.db`
- [ ] Health endpoint works: `curl http://localhost:8000/api/v1/health` returns `{"status": "ok"}`
- [ ] ChromaDB accessible: `python -c "import chromadb; chromadb.PersistentClient(path='./data/chroma')"`
- [ ] Ingestion works: `python scripts/ingest_docs.py` loads 10 documents
- [ ] All domain models importable: `python -c "from src.courseflow.domain.models import Query, Document, Answer"`

After **User Story 1 (Phase 3)**:
- [ ] All US1 tests pass: `pytest tests/unit/test_rag_service.py tests/integration/test_api_query.py tests/e2e/test_rag_pipeline.py`
- [ ] Query endpoint works: `curl -X POST http://localhost:8000/api/v1/query -d '{"query": "What is photosynthesis?"}'` returns answer
- [ ] Response includes sources: Check `data.sources` is not empty
- [ ] Response time < 3s: Check `metadata.latency_ms < 3000`
- [ ] SQLite logging works: `sqlite3 data/courseflow.db "SELECT COUNT(*) FROM queries"` > 0

After **User Story 2 (Phase 4)**:
- [ ] Rate limit enforced: Send 16 requests in 60s, verify request #16 returns 429
- [ ] Retry-After header present: Check response headers include `Retry-After: XX`
- [ ] Error message clear: Response includes "Gemini API quota exceeded (15 RPM limit)"
- [ ] US1 still works: Previous query test still succeeds

After **User Story 3 (Phase 5)**:
- [ ] Empty query rejected: `curl ... -d '{"query": ""}'` returns 400 validation error
- [ ] Irrelevant query handled: Query about unrelated topic returns 404 "No relevant information found"
- [ ] Max length enforced: 1001-character query returns 400 error
- [ ] US1 and US2 still work: Previous tests still pass

After **Polish (Phase 6)**:
- [ ] Test coverage >= 80%: `pytest --cov=src/courseflow --cov-report=term` shows 80%+
- [ ] Type checking passes: `mypy src/courseflow --strict` no errors
- [ ] Security audit passes: `bandit -r src/courseflow` no HIGH issues
- [ ] Quickstart works: Follow all steps in `specs/001-rag-qa/quickstart.md` successfully
- [ ] Documentation complete: All functions have docstrings, README.md exists, /docs endpoint works

---

## Success Criteria Mapping

### From spec.md Success Criteria:

**SC-001**: Biology query "What is photosynthesis?" returns relevant answer
- Validated by: T028 (E2E test), T060 (quickstart validation)
- Tasks: T031 (RAG service), T032 (query endpoint)

**SC-002**: Programming query "How to use async/await?" returns relevant answer
- Validated by: T028 (E2E test with multiple subjects), T029 (golden dataset includes programming)
- Tasks: T031 (RAG service), T032 (query endpoint)

**SC-003**: Answers include specific content from knowledge base (not generic)
- Validated by: T028 (E2E test verifies source attribution), T034 (response includes sources)
- Tasks: T031 (RAG service retrieval logic), T032 (response formatting)

**SC-004**: 90% of queries respond within 3 seconds
- Validated by: T027 (contract test checks latency), T056 (performance monitoring), T057 (metrics logging)
- Tasks: T030 (Gemini client with timeout), T031 (RAG orchestration), T056 (monitoring)

**SC-005**: Quota exceeded errors include clear retry message
- Validated by: T037 (integration test for 429 response), T060 (quickstart validation)
- Tasks: T038 (rate limiter), T039 (middleware), T040 (Retry-After header), T041 (error response)

**SC-006**: System handles queries from any subject domain
- Validated by: T028 (E2E test with multi-domain dataset), T029 (golden dataset covers biology, programming, history, math)
- Tasks: T016 (ChromaDB adapter - domain-agnostic), T022 (ingestion script), T031 (RAG service)

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** (US1, US2, US3) maps task to specific user story for traceability
- **Each user story is independently completable and testable** (can stop after any phase)
- **Tests written FIRST** (TDD approach) - ensure they FAIL before implementing
- **Commit after each task or logical group** for easy rollback
- **Stop at any checkpoint** to validate story independently before proceeding
- **Complexity tracking**: RAG orchestration (T031) may exceed 50 lines (documented in plan.md complexity table)
- **Zero-cost compliance**: All tasks use local storage (ChromaDB, SQLite) and Gemini free tier
- **Constitution compliance**: 80% test coverage enforced in T055, type checking in T062, security audit in T061

---

## Total Task Breakdown

- **Phase 1 (Setup)**: 10 tasks (T001-T010)
- **Phase 2 (Foundational)**: 12 tasks (T011-T022) ⚠️ BLOCKS all user stories
- **Phase 3 (User Story 1)**: 13 tasks (T023-T035) - 7 tests + 6 implementation
- **Phase 4 (User Story 2)**: 7 tasks (T036-T042) - 2 tests + 5 implementation
- **Phase 5 (User Story 3)**: 8 tasks (T043-T050) - 3 tests + 5 implementation
- **Phase 6 (Polish)**: 13 tasks (T051-T063)

**Total**: 63 tasks

**MVP (US1 only)**: 35 tasks (Phase 1 + 2 + 3)
**Full feature**: 63 tasks (all phases)

**Estimated effort**:
- Single developer: ~31 hours (full feature), ~20 hours (MVP)
- Team of 3 (parallel): ~15 hours (full feature), ~10 hours (MVP)
