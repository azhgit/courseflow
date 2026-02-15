---
description: "Implementation tasks for Production-Ready Evaluation System"
---

# Tasks: Production-Ready Evaluation System

**Input**: Design documents from `/specs/005-production-polish/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Constitution Compliance**: All tasks must align with constitution principles:
- Code Quality: Functions <50 lines, files <500 lines, documented code
- Testing Standards: 80% coverage minimum, test-first for critical metrics logic
- Performance: API <500ms p95 for latest results, <2s p95 for historical queries
- Reliability: Exponential backoff retry (1s/2s/4s max 3 attempts) for SQLite failures

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [x] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project structure:
- Domain models: `src/courseflow/domain/`
- Services: `src/courseflow/application/`
- Infrastructure: `src/courseflow/infrastructure/`
- API routes: `src/courseflow/api/routes/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Add APScheduler==3.10.4 and tenacity==8.2.3 to pyproject.toml dependencies
- [x] T002 [P] Create golden dataset fixture at tests/fixtures/golden_dataset.json with exactly 15 Q&A pairs (use exact chunk ID format from existing RAG system)
- [x] T003 [P] Create evaluation database schema in src/courseflow/infrastructure/repositories/evaluation_repo.py (tables: evaluation_runs, test_case_results with indexes on timestamp, status, passed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create domain exceptions in src/courseflow/domain/exceptions.py (EvaluationInProgressException, EvaluationPersistenceError)
- [x] T005 [P] Create EvaluationRun entity in src/courseflow/domain/eval_models.py (with status enum, mark_completed/mark_failed methods, quality threshold checking)
- [x] T006 [P] Create TestCaseResult value object in src/courseflow/domain/eval_models.py (frozen dataclass with validation in __post_init__)
- [x] T007 [P] Create GoldenPair model in src/courseflow/domain/eval_models.py (Pydantic model with schema validation)
- [x] T008 [P] Create Metrics value object in src/courseflow/domain/eval_models.py (frozen dataclass with range validation)
- [x] T009 Create evaluation ports in src/courseflow/domain/eval_ports.py (EvaluationServicePort, EvaluationRepositoryPort abstract interfaces)
- [x] T010 Update config.py to add evaluation settings (thresholds, schedule config, database path)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automated Quality Validation (Priority: P1) 🎯 MVP

**Goal**: QA engineers can trigger evaluations via API and receive objective quality metrics (precision, keyword match, latency) without manual intervention

**Independent Test**: Trigger evaluation via POST /api/v1/eval/run, wait for completion, verify metrics are computed and returned correctly with all 15 test cases executed

### Core Metrics Logic for User Story 1

**NOTE: Implement these FIRST as they are foundational for evaluation**

- [x] T011 [P] [US1] Implement exact chunk ID matching function in src/courseflow/application/evaluation_service.py (use set intersection: len(expected ∩ retrieved) / len(retrieved), return 0.0 if no retrieval)
- [x] T012 [P] [US1] Implement keyword match rate function in src/courseflow/application/evaluation_service.py (case-insensitive set intersection, whitespace tokenization)
- [x] T013 [P] [US1] Implement percentile computation function using statistics.quantiles() in src/courseflow/application/evaluation_service.py (p50=quantiles[49], p95=quantiles[94])
- [x] T014 [US1] Implement compute_metrics() aggregation function in src/courseflow/application/evaluation_service.py (aggregate from list of TestCaseResult, compute all precision/keyword/latency stats)

### Unit Tests for Metrics (Test-First)

**⚠️ Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US1] Unit test for exact chunk ID matching in tests/unit/test_metrics_computation.py (test cases: zero retrieval, all relevant, partial match, no match, duplicate handling)
- [x] T016 [P] [US1] Unit test for keyword match rate in tests/unit/test_metrics_computation.py (test cases: zero keywords, all matched, partial match, case-insensitive, empty answer)
- [x] T017 [P] [US1] Unit test for percentile computation in tests/unit/test_metrics_computation.py (test cases: 15 latencies, single value, empty list, p95 >= p50 validation)
- [x] T018 [P] [US1] Unit test for compute_metrics aggregation in tests/unit/test_metrics_computation.py (test cases: verify averages, min/max, pass_rate calculation, tests_passed + tests_failed = 15)

### Repository Implementation for User Story 1

- [x] T019 [US1] Implement EvaluationRepository in src/courseflow/infrastructure/repositories/evaluation_repo.py (save_run, get_run_by_id, list_runs with filtering/pagination, get_baseline_run using WHERE passed=1 ORDER BY timestamp DESC LIMIT 1)
- [x] T020 [US1] Add SQLite retry decorator using tenacity in src/courseflow/infrastructure/repositories/evaluation_repo.py (@retry with exponential backoff 1s/2s/4s max 3 attempts for OperationalError)
- [x] T021 [US1] Implement database initialization in src/courseflow/infrastructure/repositories/evaluation_repo.py (create_tables with indexes: idx_timestamp, idx_status, idx_passed_timestamp)

### Service Implementation for User Story 1

- [x] T022 [US1] Implement EvaluationService in src/courseflow/application/evaluation_service.py (constructor with asyncio.Lock for concurrency control)
- [x] T023 [US1] Implement run_evaluation() method in src/courseflow/application/evaluation_service.py (check lock.locked() and raise EvaluationInProgressException if locked, execute with async with lock)
- [x] T024 [US1] Implement golden dataset loading in src/courseflow/application/evaluation_service.py (load from tests/fixtures/golden_dataset.json, validate schema with Pydantic)
- [x] T025 [US1] Implement single test case execution in src/courseflow/application/evaluation_service.py (call existing RAG service, measure latency with time.perf_counter(), compute precision and keyword match, return TestCaseResult)
- [x] T026 [US1] Implement evaluation orchestration in src/courseflow/application/evaluation_service.py (execute all 15 pairs, collect results even if individual tests fail, compute aggregated metrics, mark run completed/failed)
- [x] T027 [US1] Add error handling and logging in src/courseflow/application/evaluation_service.py (log each test start/completion, handle RAG service failures gracefully, ensure partial results preserved)

### API Implementation for User Story 1

- [x] T028 [US1] Create evaluation routes in src/courseflow/api/routes/evaluation.py (POST /api/v1/eval/run endpoint)
- [x] T029 [US1] Implement POST /api/v1/eval/run handler in src/courseflow/api/routes/evaluation.py (handle EvaluationInProgressException → HTTP 429 with Retry-After: 300 header, start async evaluation, return 202 Accepted with run_id)
- [x] T030 [US1] Implement GET /api/v1/eval/run/{run_id} handler in src/courseflow/api/routes/evaluation.py (retrieve run details with optional include_results query param, return 404 if not found)
- [x] T031 [US1] Add dependency injection in src/courseflow/api/dependencies.py (create EvaluationService singleton, inject EvaluationRepository)
- [x] T032 [US1] Register evaluation routes in src/courseflow/api/main.py (app.include_router with /api/v1/eval prefix)

### Integration Tests for User Story 1

- [x] T033 [US1] Integration test for POST /api/v1/eval/run in tests/integration/test_evaluation_api.py (test successful trigger returns 202 with run_id, verify run persisted to SQLite)
- [x] T034 [US1] Integration test for HTTP 429 concurrency guard in tests/integration/test_evaluation_api.py (start evaluation, trigger second concurrent request, verify 429 response with Retry-After header)
- [x] T035 [US1] Integration test for GET /api/v1/eval/run/{run_id} in tests/integration/test_evaluation_api.py (test completed run returns metrics, test running run returns status=running, test 404 for invalid run_id)
- [x] T036 [US1] Integration test for SQLite retry logic in tests/integration/test_evaluation_repo_retry.py (mock OperationalError, verify 3 retry attempts with 1s/2s/4s delays, verify final failure raises EvaluationPersistenceError)

### E2E Test for User Story 1

- [x] T037 [US1] E2E test for full evaluation run in tests/e2e/test_full_evaluation_run.py (mock RAG service responses, trigger evaluation, wait for completion, verify all 15 test cases executed, verify metrics computed correctly, verify results persisted)

**Checkpoint**: At this point, User Story 1 should be fully functional - trigger evaluations and get metrics independently

---

## Phase 4: User Story 2 - Performance Monitoring (Priority: P2)

**Goal**: DevOps teams can view historical evaluation results and latency trends to detect performance degradation over time

**Independent Test**: Run 3 evaluations, persist results to SQLite, query via GET /api/v1/eval/run with filtering (status, date range), verify historical metrics retrieved accurately

### API Implementation for User Story 2

- [x] T038 [P] [US2] Implement GET /api/v1/eval/run list handler in src/courseflow/api/routes/evaluation.py (pagination with page/page_size params, filter by status/passed/since/until query params)
- [x] T039 [P] [US2] Add pagination helper in src/courseflow/infrastructure/repositories/evaluation_repo.py (compute total, pages, has_next/has_prev for PaginationInfo response)
- [x] T040 [US2] Add date range filtering in src/courseflow/infrastructure/repositories/evaluation_repo.py (WHERE timestamp >= ? AND timestamp <= ? clauses)

### Integration Tests for User Story 2

- [x] T041 [P] [US2] Integration test for GET /api/v1/eval/run pagination in tests/integration/test_evaluation_api.py (create 25 runs, request page 1 with page_size=20, verify pagination info correct)
- [x] T042 [P] [US2] Integration test for status filtering in tests/integration/test_evaluation_api.py (create completed/failed runs, filter by status=completed, verify only completed returned)
- [x] T043 [P] [US2] Integration test for date range filtering in tests/integration/test_evaluation_api.py (create runs with different timestamps, filter by since/until, verify correct date filtering)
- [x] T044 [P] [US2] Integration test for API performance in tests/integration/test_evaluation_api.py (query latest result <500ms p95, query 100 historical results <2s p95)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - trigger evaluations + view historical trends independently

---

## Phase 5: User Story 3 - Regression Detection (Priority: P3)

**Goal**: Developers can compare current evaluation results against baseline metrics to detect quality regressions immediately after code changes

**Independent Test**: Establish baseline with passed=true run, create new run with degraded metrics, verify baseline endpoint returns correct run and comparison logic detects regression >10%

### API Implementation for User Story 3

- [x] T045 [US3] Implement GET /api/v1/eval/baseline handler in src/courseflow/api/routes/evaluation.py (call repository get_baseline_run, return null if no baseline exists, return full run details if exists)
- [x] T046 [US3] Add compare_to_baseline() method in src/courseflow/application/evaluation_service.py (fetch baseline via get_baseline_run, compute % difference for precision/keyword/latency, flag metrics with >10% degradation)

### Integration Tests for User Story 3

- [x] T047 [P] [US3] Integration test for GET /api/v1/eval/baseline in tests/integration/test_evaluation_api.py (test no baseline returns null, test baseline selection uses most recent passed=true run, verify baseline ignores failed runs)
- [x] T048 [P] [US3] Unit test for regression detection in tests/unit/test_evaluation_service.py (test 10% degradation threshold, test precision regression, test keyword match regression, test latency regression, test no baseline case)

**Checkpoint**: All user stories should now be independently functional - evaluations + history + regression detection

---

## Phase 6: Automated Scheduling (Priority: P3+)

**Goal**: Daily automated evaluations run at 2 AM UTC by default without manual intervention

**Independent Test**: Configure scheduler, verify job added with correct cron trigger (hour=2, minute=0), manually trigger scheduled job, verify evaluation executes

### Scheduler Implementation

- [x] T049 [P] Create APScheduler integration in src/courseflow/infrastructure/scheduler/eval_scheduler.py (AsyncIOScheduler with cron trigger: hour=2, minute=0, job_id=daily_evaluation)
- [x] T050 [P] Implement lifespan context manager in src/courseflow/api/main.py (startup: initialize scheduler, add job, start scheduler; shutdown: scheduler.shutdown())
- [x] T051 Add config for schedule customization in src/courseflow/config.py (eval_schedule_hour, eval_schedule_minute, eval_auto_schedule_enabled with defaults)

### Integration Tests for Scheduler

- [x] T052 [P] Integration test for scheduler initialization in tests/integration/test_eval_scheduler.py (verify scheduler starts on app startup, verify job registered with correct trigger, verify scheduler shuts down cleanly)
- [x] T053 [P] Unit test for scheduled evaluation execution in tests/unit/test_eval_scheduler.py (mock scheduler.add_job, verify run_evaluation called with correct params, verify error handling for failed scheduled runs)

**Checkpoint**: Automated daily evaluations now active - system fully production-ready

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T054 [P] Add comprehensive docstrings to all evaluation modules (src/courseflow/domain/eval_models.py, src/courseflow/application/evaluation_service.py, src/courseflow/infrastructure/repositories/evaluation_repo.py)
- [x] T055 [P] Add OpenAPI documentation to evaluation routes in src/courseflow/api/routes/evaluation.py (response_model, status_code, description for all endpoints)
- [x] T056 Verify quickstart.md commands work end-to-end (trigger evaluation, check results, list runs, get baseline)
- [x] T057 [P] Code cleanup and type hint verification with mypy --strict
- [x] T058 [P] Validate 80% test coverage minimum using pytest-cov (pytest --cov=courseflow.application.evaluation_service --cov=courseflow.infrastructure.repositories.evaluation_repo --cov-report=term)
- [x] T059 Security review for API endpoints (validate UUID format for run_id path param, sanitize query params, prevent SQL injection in date filtering)
- [x] T060 Performance validation (run 100 concurrent GET requests for latest result <500ms p95, run full evaluation <5min for 15 pairs)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - Core evaluation capability
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - Can start in parallel with US1, integrates for historical queries
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) + US1 repository methods - Regression detection requires baseline concept
- **Automated Scheduling (Phase 6)**: Depends on US1 complete (needs working evaluation execution)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### Critical Path

```
Setup (Phase 1) 
  → Foundational (Phase 2) [BLOCKS ALL]
    → US1: Core Metrics (T011-T014) [FOUNDATIONAL FOR US1]
      → US1: Repository (T019-T021)
      → US1: Service (T022-T027)
      → US1: API (T028-T032)
      → US1: Tests (T033-T037)
    ⟶ US2: Historical (T038-T044) [Can start after Phase 2, parallel with US1]
    ⟶ US3: Regression (T045-T048) [Needs US1 repository methods]
    → Scheduling (T049-T053) [Needs US1 complete]
  → Polish (Phase 7)
```

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - **Critical Sub-dependency**: Metrics logic (T011-T014) MUST complete before service implementation (T022-T027)
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independently testable, extends US1 repository
- **User Story 3 (P3)**: Requires US1 repository methods (get_baseline_run) - Light dependency

### Within Each User Story

**User Story 1 (Critical Order)**:
1. Metrics logic FIRST (T011-T014) - Pure functions, foundational for all evaluation
2. Unit tests for metrics (T015-T018) - Test-first for critical logic
3. Repository (T019-T021) - Persistence layer
4. Service (T022-T027) - Orchestration using metrics + repository
5. API (T028-T032) - HTTP interface
6. Integration tests (T033-T036) - Full stack validation
7. E2E test (T037) - End-to-end confidence

**User Story 2**: API handlers (T038-T040) before integration tests (T041-T044)

**User Story 3**: API handler + comparison logic (T045-T046) before tests (T047-T048)

### Parallel Opportunities

**Phase 1 (Setup)**: T002 and T003 can run in parallel (different files)

**Phase 2 (Foundational)**: T005, T006, T007, T008 can all run in parallel (different entity classes in same file, or split into separate files)

**Phase 3 (User Story 1)**:
- Metrics logic: T011, T012, T013 can run in parallel (pure functions)
- Unit tests: T015, T016, T017, T018 can all run in parallel (different test files/classes)
- Integration tests: T033, T034, T035, T036 can run in parallel (isolated test cases)

**Phase 4 (User Story 2)**: T038, T039, T040 can run in parallel if careful with file coordination, Tests T041-T044 can all run in parallel

**Phase 5 (User Story 3)**: T047, T048 can run in parallel (different test files)

**Phase 6 (Scheduling)**: T049, T050 can be coordinated, T052, T053 can run in parallel

**Phase 7 (Polish)**: T054, T055, T057, T058 can all run in parallel (different concerns)

---

## Parallel Example: User Story 1 Core Metrics

```bash
# Launch all core metrics functions together (pure functions, no dependencies):
Task T011: "Implement exact chunk ID matching function in evaluation_service.py"
Task T012: "Implement keyword match rate function in evaluation_service.py"
Task T013: "Implement percentile computation function in evaluation_service.py"
# Then T014 depends on T011-T013 completing

# Launch all unit tests together:
Task T015: "Unit test for exact chunk ID matching in test_metrics_computation.py"
Task T016: "Unit test for keyword match rate in test_metrics_computation.py"
Task T017: "Unit test for percentile computation in test_metrics_computation.py"
Task T018: "Unit test for compute_metrics aggregation in test_metrics_computation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) - RECOMMENDED

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T010) - CRITICAL blocking phase
3. Complete Phase 3: User Story 1 (T011-T037)
   - **Start with metrics logic** (T011-T014) - Most critical foundational code
   - Write unit tests first (T015-T018) - TDD for critical logic
   - Build repository, service, API in order (T019-T032)
   - Validate with integration and E2E tests (T033-T037)
4. **STOP and VALIDATE**: 
   - Trigger evaluation via API
   - Verify all 15 test cases execute
   - Verify metrics computed correctly (precision, keyword match, latency percentiles)
   - Verify SQLite retry logic works (simulate database lock)
   - Verify HTTP 429 concurrency guard works (concurrent requests)
5. Deploy/demo if ready - **FULL MVP VALUE**

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! Core evaluation capability)
3. Add User Story 2 → Test independently → Deploy/Demo (Historical trends)
4. Add User Story 3 → Test independently → Deploy/Demo (Regression detection)
5. Add Automated Scheduling (Phase 6) → Deploy/Demo (Fully automated system)
6. Polish (Phase 7) → Final production release

### Parallel Team Strategy

With 2-3 developers:

1. **Team completes Setup + Foundational together** (critical shared foundation)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (Core evaluation) - Most complex, sequential
   - **Developer B**: User Story 2 (Historical queries) - Can start after Phase 2, parallel with US1
   - **Developer C**: Golden dataset creation + documentation (T002, quickstart validation)
3. After US1 completes:
   - **Developer A**: User Story 3 (Regression) + Scheduling (needs US1 methods)
   - **Developer B**: Polish (testing, docs, performance validation)

---

## Critical Success Metrics

**After MVP (User Story 1 complete)**:
- ✅ Can trigger evaluation via POST /api/v1/eval/run
- ✅ Evaluation executes all 15 golden pairs within 5 minutes
- ✅ Exact chunk ID matching works correctly (set intersection logic)
- ✅ Keyword match rate computed with case-insensitive matching
- ✅ Percentiles computed correctly (p50, p95) using statistics.quantiles
- ✅ SQLite retry logic handles database locks (1s/2s/4s backoff max 3 attempts)
- ✅ HTTP 429 returned for concurrent evaluation requests with Retry-After header
- ✅ Results persisted to SQLite with all metrics
- ✅ GET /api/v1/eval/run/{run_id} retrieves completed results <500ms

**After Full Implementation**:
- ✅ Historical queries work with pagination and filtering (US2)
- ✅ Baseline selection returns most recent passed=true run (US3)
- ✅ Regression detection flags >10% metric degradation (US3)
- ✅ Daily automated evaluations run at 2 AM UTC (Scheduling)
- ✅ 80% test coverage achieved
- ✅ All quickstart.md examples work end-to-end
- ✅ Performance targets met: <500ms p95 for latest, <2s p95 for history, <5min full evaluation

---

## Notes

- **[P] tasks** = different files or independent sections, no execution dependencies
- **[Story] label** maps task to specific user story for traceability
- **Exact chunk ID matching**: Use set intersection, character-for-character comparison, no fuzzy matching
- **SQLite retries**: exponential backoff 1s, 2s, 4s (max 3 attempts) using tenacity decorator
- **HTTP 429 concurrency**: asyncio.Lock guards evaluation, check lock.locked() before execution
- **Baseline selection**: `WHERE passed=1 ORDER BY timestamp DESC LIMIT 1` (most recent passed)
- **Percentiles**: Use stdlib statistics.quantiles(n=100), p50=quantiles[49], p95=quantiles[94]
- **Default schedule**: APScheduler cron(hour=2, minute=0) for daily 2 AM UTC runs
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **CRITICAL**: Implement metrics logic (T011-T014) with unit tests (T015-T018) FIRST - foundational for all evaluation
