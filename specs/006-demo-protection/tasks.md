# Tasks: Demo Quota Protection Middleware

**Feature**: 006-demo-protection  
**Generated**: 2026-02-16  
**Status**: Ready for Implementation  
**Total Tasks**: 28 (4 setup, 7 foundational, 6 US1, 6 US2, 5 US3)

---

## Overview

This document defines all implementation tasks organized by user story. Each task is independently actionable and includes clear file paths, test criteria, and parallelization opportunities.

**Execution Strategy**:
- **Phase 1** (Setup): Initialize project structure and dependencies
- **Phase 2** (Foundational): Implement core domain models and exceptions
- **Phase 3** (User Story 1 - P1): Per-IP hourly rate limiting and daily budget enforcement
- **Phase 4** (User Story 2 - P2): Demo cache with streaming simulation
- **Phase 5** (User Story 3 - P3): Quota status monitoring and health indicators
- **Final Phase**: Polish, integration testing, and documentation

**MVP Scope**: User Story 1 + Phase 2 foundational layer (enables core quota protection)

---

## Phase 1: Setup & Initialization

### Goals
- Prepare project structure for quota protection feature
- Verify dependencies are available
- Create basic configuration

### Independent Test Criteria
- Configuration loads correctly from environment variables
- New directories exist with correct structure
- No import errors when loading modules

### Tasks

- [ ] T001 Verify Python 3.11+ and FastAPI 0.109+ are installed per constitution requirements
- [ ] T002 Create domain model directory structure: `src/courseflow/domain/` (models.py, ports.py, exceptions.py)
- [ ] T003 Create infrastructure quota directory: `src/courseflow/infrastructure/quota/` (in_memory_quota.py, sqlite_quota.py)
- [ ] T004 Create middleware directory: `src/courseflow/api/middleware/` and routes file `src/courseflow/api/routes/quota.py`

---

## Phase 2: Foundational - Domain Models & Ports

### Goals
- Define core domain entities for quota management
- Establish ports interface for infrastructure adapters
- Create custom domain exceptions

### Dependencies
- Phase 1 (directories must exist)
- Phase 3 (quotaservice depends on these models)

### Independent Test Criteria
- All domain models are instantiable with valid data
- Models validate inputs correctly (invalid IPs, negative counts rejected)
- Ports interface is properly abstract (cannot be instantiated)
- Exceptions contain required fields and messages

### Tasks

- [ ] T005 [P] Implement domain entities in `src/courseflow/domain/models.py`: QuotaWindow, DailyQuotaLedger, DemoCacheEntry with validation, dataclass structure per specification
- [ ] T006 [P] Implement value object QuotaStatus in `src/courseflow/domain/models.py` with to_dict() method for JSON serialization
- [ ] T007 [P] Implement custom exceptions in `src/courseflow/domain/exceptions.py`: QuotaError, IPLimitExceededError, DailyQuotaExceededError, QuotaStorageError with retry_after and reset_at fields
- [ ] T008 [P] Implement abstract port QuotaStorePort in `src/courseflow/domain/ports.py` with methods: get_daily_ledger(), increment_daily_usage(), reset_daily_usage(), get_cache_hit_count(), increment_cache_hit()
- [ ] T009 Create unit tests in `tests/unit/test_quota_models.py` for: QuotaWindow rolling window logic, DailyQuotaLedger percentage calculation, DemoCacheEntry normalization per FR-006
- [ ] T010 Create unit tests in `tests/unit/test_quota_exceptions.py` for exception instantiation, message formatting, and required field presence
- [ ] T011 Extend `src/courseflow/config.py` with quota settings: quota_hourly_limit (default 20), quota_daily_budget (default 300), quota_cache_enabled (default true), quota_stream_delay_ms (default 30)

---

## Phase 3: User Story 1 - Keep Demo Queries Available (Per-IP & Daily Limits)

**Priority**: P1  
**Goal**: Enforce per-IP hourly limits and global daily budget to protect demo availability

### Dependencies
- Phase 2 (models and ports required)

### Independent Test Criteria
- Per-IP hourly limit rejects 21st request from same IP
- Daily budget limit rejects requests when global quota exhausted
- Rate limit headers included in responses
- Retry-after guidance provided in error responses
- 503 error when quota storage unavailable
- 400 error when IP cannot be determined

### Tasks

- [ ] T012 [US1] Implement in-memory quota store in `src/courseflow/infrastructure/quota/in_memory_quota.py`: InMemoryQuotaStore adapter with rolling window tracking per IP, implements QuotaStorePort
- [ ] T013 [US1] Implement SQLite quota store in `src/courseflow/infrastructure/quota/sqlite_quota.py`: SQLiteQuotaStore adapter with daily_quota table, ACID updates, implements QuotaStorePort, includes APScheduler daily reset task
- [ ] T014 [US1] [P] Implement QuotaService in `src/courseflow/application/quota_service.py`: check_and_enforce_quota(), increment_daily_usage(), get_daily_status() with logic for both per-IP and daily limits, handles QuotaStorageError with proper error propagation
- [ ] T015 [US1] Implement quota middleware in `src/courseflow/api/middleware/quota_middleware.py`: QuotaMiddleware class that enforces quota on /api/v1/query and /api/v1/query/stream routes, extracts IP with X-Forwarded-For fallback, converts QuotaExceededError to HTTP 429
- [ ] T016 [US1] Create integration tests in `tests/integration/test_quota_enforcement.py`: test 20th request succeeds per IP, test 21st request rejected, test daily limit enforcement, test 503 on storage error, test 400 on missing IP
- [ ] T017 [US1] Update `src/courseflow/api/main.py` to integrate: instantiate quota services in app startup, add QuotaMiddleware to middleware stack, register APScheduler for daily reset, inject quota_service into app.state

---

## Phase 4: User Story 2 - Serve Cached Demo Questions

**Priority**: P2  
**Goal**: Serve pre-cached answers without consuming quota, with streaming simulation

### Dependencies
- Phase 2 (domain models required)
- Phase 3 (quota enforcement available for bypass logic)

### Independent Test Criteria
- Cache hit detected for all 10 demo questions (with punctuation/case variations)
- Cache-hit responses don't increment daily usage counter
- Cache-hit responses don't increment per-IP counter
- Cached answers streamed word-by-word with correct delay
- Non-cached questions bypass cache path
- Normalization handles punctuation, case, whitespace per FR-006

### Tasks

- [ ] T018 [US2] Create demo cache data in `src/courseflow/infrastructure/cache/demo_cache.py`: Define 10 pre-cached DemoCacheEntry instances with normalized questions and answers (include Python async, RAG, biology, history topics)
- [ ] T018 [US2] Implement CacheService in `src/courseflow/application/cache_service.py`: find_cached_answer(query: str) returns DemoCacheEntry or None, handles normalization, test against all 10 demo questions
- [ ] T019 [US2] Implement streaming response handler in `src/courseflow/api/routes/query.py`: stream_cached_answer(answer: str, delay_ms: int) yields word-by-word with asyncio.sleep, handles client disconnect gracefully per FR-016
- [ ] T020 [US2] Modify query route handler in `src/courseflow/api/routes/query.py` to check cache before quota consumption: if cache hit, skip quota.check_and_enforce(), add X-Cache-Hit: true header, stream response with delay
- [ ] T021 [US2] Create unit tests in `tests/unit/test_cache_service.py`: test cache hit with exact match, test cache hit with punctuation variations, test cache hit with case variations, test cache miss for non-cached questions
- [ ] T022 [US2] Create integration tests in `tests/integration/test_cache_streaming.py`: test full request cycle for cached question, verify quota not incremented on cache hit, verify streaming response format, test client disconnect handling

---

## Phase 5: User Story 3 - Monitor Quota Health

**Priority**: P3  
**Goal**: Provide visibility into quota status and warning signals

### Dependencies
- Phase 2 (quota models and store)
- Phase 3 (daily quota tracking)

### Independent Test Criteria
- Status endpoint returns accurate daily used/remaining counts
- Percentage calculation matches expected values (e.g., 245/300 = 81.67%)
- Warning state true when usage >= 80%, false below threshold
- Reset timestamp is next midnight UTC
- Cache hit rate calculated correctly (today's cache hits / total queries)
- Health endpoint includes quota_warning field when applicable

### Tasks

- [ ] T023 [US3] Implement status aggregation in `src/courseflow/application/quota_service.py`: get_quota_status() returns QuotaStatus value object with all fields populated: daily_used, daily_remaining, daily_percentage_used, quota_warning, cached_questions_count, cache_hit_rate
- [ ] T024 [US3] Implement quota status endpoint in `src/courseflow/api/routes/quota.py`: GET /api/v1/quota/status returns QuotaStatus.to_dict() as JSON with correct fields and types
- [ ] T025 [US3] [P] Modify health endpoint in `src/courseflow/api/routes/health.py`: include quota_warning boolean field, set to true when daily usage >= 80%, set to false otherwise, do NOT mark overall service unhealthy due to quota warning alone
- [ ] T026 [US3] Create integration tests in `tests/integration/test_quota_status.py`: test endpoint returns all required fields, test percentage calculation accuracy, test warning threshold at 80%, test cache hit rate calculation with known values
- [ ] T027 [US3] Create end-to-end tests in `tests/e2e/test_quota_flow.py`: simulate usage progression from 0% to 100%, verify warning state transitions, verify accurate cache hit rate reporting

---

## Final Phase: Polish & Integration

### Goals
- Comprehensive testing across all features
- Documentation updates
- Performance validation

### Tasks

- [ ] T028 Update `QUICKSTART.md` with quota protection examples: test commands for rate limit, cache hit, quota status, daily reset behavior
- [ ] T029 [P] Run full test suite: `pytest tests/ -v --cov=src/courseflow --cov-report=html` targeting 80%+ coverage for quota module
- [ ] T030 [P] Validate performance: confirm quota checks add <5ms overhead per request, maintain <2s RAG p95 latency for non-cached queries
- [ ] T031 [P] Document API contracts: update OpenAPI spec (contracts/openapi.yaml) with 429 responses, X-Cache-Hit header, X-RateLimit-* headers, quota_warning in health endpoint

---

## Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ├─→ Phase 3 (US1 - Rate Limiting) ──┐
    │                                     └─→ Phase 4 (US2 - Caching)
    │                                     ┌─→ Phase 5 (US3 - Monitoring)
    └─→ Phase 5 (US3 - Monitoring) ─────┘
                                        ↓
                            Final Phase (Polish & Integration)
```

---

## Parallelization Opportunities

### Phase 2 (Parallel Tasks)
- **T005, T006, T007, T008**: All domain model implementation (independent files, no cross-dependencies)
- **T009, T010**: Unit tests (can run in parallel after models exist)

### Phase 3 (Parallel Tasks)
- **T012, T013**: In-memory and SQLite adapters (independent implementations)
- **T016, T017**: Integration tests and main.py updates (after T014, T015 complete)

### Phase 4 (Parallel Tasks)
- **T018, T019, T020**: Cache service and route handlers (depends on Phase 3 complete)
- **T021, T022**: Unit and integration tests (depends on implementations)

### Phase 5 (Parallel Tasks)
- **T023, T024, T025**: Status aggregation, endpoint, health endpoint (can start after Phase 3 complete)
- **T026, T027**: Status tests (depend on implementations)

### Final Phase (Parallel Tasks)
- **T029, T030, T031**: Testing, performance validation, documentation (independent)

---

## Success Criteria Mapping

| Success Criterion | Task(s) | Test(s) |
|-------------------|---------|---------|
| SC-001: 21st request rejected per IP | T012, T015 | T016 |
| SC-002: Daily limit enforced | T013, T014 | T016 |
| SC-003: Cache hits bypass quota | T018-T020 | T022 |
| SC-004: Accurate quota reporting | T023-T024 | T026 |
| SC-005: Warning at 80% usage | T025 | T026 |
| SC-006: Streaming response <1s | T019 | T022 |

---

## Configuration for Different Scenarios

### Production Demo
```env
QUOTA_HOURLY_LIMIT=20
QUOTA_DAILY_BUDGET=300
QUOTA_CACHE_ENABLED=true
QUOTA_STREAM_DELAY_MS=30
```

### Testing/Local Development
```env
QUOTA_HOURLY_LIMIT=5         # Easier to hit limit
QUOTA_DAILY_BUDGET=20        # Easier to exhaust
QUOTA_CACHE_ENABLED=true
QUOTA_STREAM_DELAY_MS=5      # Faster for tests
```

### Stress Testing
```env
QUOTA_HOURLY_LIMIT=100
QUOTA_DAILY_BUDGET=1000
QUOTA_CACHE_ENABLED=false    # Test without cache
QUOTA_STREAM_DELAY_MS=0      # Instant delivery
```

---

## Implementation Notes

### Hexagonal Architecture Adherence
- **Domain Layer**: Models, value objects, ports (pure Python)
- **Application Layer**: QuotaService, CacheService (business logic)
- **Infrastructure Layer**: SQLiteQuotaStore, InMemoryQuotaStore (adapters)
- **API Layer**: Middleware, routes (FastAPI integration)

### Type Safety
- All models use Pydantic-compatible dataclasses
- Type hints required for all function parameters and returns
- Run `mypy --strict src/` after implementation

### Testing Strategy
- Unit tests: Domain logic, normalization, calculations
- Integration tests: Middleware enforcement, endpoint accuracy
- E2E tests: Full request flow with various scenarios
- Target: 80%+ coverage for quota module

### Performance Targets
- Quota check: <5ms overhead per request
- Cache lookup: <1ms (dict/set lookup)
- Streaming: First word within 1 second
- RAG p95 latency: Maintained <2s (cache bypass, not affected)

---

## Files Modified/Created

### New Files
- `src/courseflow/domain/models.py` (QuotaWindow, DailyQuotaLedger, DemoCacheEntry, QuotaStatus)
- `src/courseflow/domain/ports.py` (QuotaStorePort)
- `src/courseflow/domain/exceptions.py` (quota exceptions)
- `src/courseflow/application/quota_service.py` (QuotaService)
- `src/courseflow/application/cache_service.py` (CacheService)
- `src/courseflow/infrastructure/quota/in_memory_quota.py` (InMemoryQuotaStore)
- `src/courseflow/infrastructure/quota/sqlite_quota.py` (SQLiteQuotaStore)
- `src/courseflow/infrastructure/cache/demo_cache.py` (demo questions)
- `src/courseflow/api/middleware/quota_middleware.py` (QuotaMiddleware)
- `src/courseflow/api/routes/quota.py` (quota endpoints)
- `tests/unit/test_quota_models.py`
- `tests/unit/test_quota_exceptions.py`
- `tests/unit/test_cache_service.py`
- `tests/integration/test_quota_enforcement.py`
- `tests/integration/test_quota_status.py`
- `tests/integration/test_cache_streaming.py`
- `tests/e2e/test_quota_flow.py`

### Modified Files
- `src/courseflow/config.py` (add quota settings)
- `src/courseflow/api/main.py` (integrate middleware, services)
- `src/courseflow/api/routes/query.py` (cache check, streaming)
- `src/courseflow/api/routes/health.py` (add quota_warning)
- `QUICKSTART.md` (quota examples)

---

## MVP Delivery Checklist

**Minimum Viable Product** = User Story 1 (Rate Limiting) + Foundational Layer

- [ ] Phase 1: Setup complete
- [ ] Phase 2: Foundational domain models complete
- [ ] Phase 3: User Story 1 complete (per-IP + daily limits)
- [ ] Integration tests pass for US1
- [ ] Performance validated (<5ms overhead, <2s p95 RAG)
- [ ] Configuration working (.env or environment variables)
- [ ] Deployed to staging and tested with demo traffic

**Additional for Production**:
- [ ] Phase 4: Cache service (reduces quota consumption)
- [ ] Phase 5: Monitoring endpoints (visibility)
- [ ] Final phase: Documentation and performance tuning
- [ ] E2E tests pass across all scenarios
- [ ] 80%+ test coverage achieved
