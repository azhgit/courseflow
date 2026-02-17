---
description: "Implementation tasks for Zeabur deployment feature"
---

# Tasks: Zeabur Deployment

**Input**: Design documents from `/specs/008-zeabur-deployment/`  
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md  
**Branch**: `008-zeabur-deployment`

**Constitution Compliance**: All tasks must align with constitution principles:
- Code Quality: Functions <50 lines, files <500 lines, documented code
- Testing Standards: 80% coverage minimum for rate limiter and retry logic
- Performance: API <500ms p95, page load <3s, optimized assets
- Zero-Cost Constraints: Zeabur Free Trial only ($0/month + $5 credit)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/src/courseflow/`
- Frontend: `frontend/src/`
- Documentation: `docs/deployment/`
- Tests: `backend/tests/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verify prerequisites

**Estimated Time**: 30 minutes  
**Blocking**: Must complete before all user stories

- [X] T001 Verify Feature 001 (RAG QA System) and Feature 007 (React Frontend) are complete and working
  - **Acceptance**: Backend responds to `/query` endpoint, frontend submits questions successfully
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: DevOps

- [X] T002 Create branch `008-zeabur-deployment` from main
  - **Acceptance**: Branch created, checkout successful
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: DevOps

- [X] T003 [P] Create deployment documentation directory structure: `docs/deployment/`
  - **Acceptance**: Directory exists with placeholder README.md
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: DevOps

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**Estimated Time**: 2 hours  
**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create SQLite migration for rate_limits table in `backend/migrations/008_add_rate_limits.sql`
  - **Acceptance**: Migration creates table with all fields (id, ip_address, request_count, window_start, last_request, created_at) and indexes (idx_rate_limits_ip, idx_rate_limits_window, idx_rate_limits_last_request)
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Backend

- [X] T005 [P] Create RateLimitRepository interface in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Interface defines methods: get_by_ip(), create_entry(), increment_counter(), reset_window(), cleanup_old_entries()
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Backend

- [X] T006 Run SQLite migration to create rate_limits table in `data/courseflow.db`
  - **Acceptance**: Table created successfully, indexes exist, verified with SQLite CLI
  - **Dependencies**: T004
  - **Effort**: Small
  - **Component**: Backend

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Deploy for Interview (Priority: P1) 🎯 MVP

**Goal**: Deploy both backend and frontend to Zeabur with public URLs accessible for interviewers

**Independent Test**: Visit both URLs in browser, submit a question from frontend, verify streaming response arrives without CORS errors, and health check returns HTTP 200

**Estimated Time**: 6 hours

### Backend Deployment for User Story 1

- [X] T007 [P] [US1] Create backend Zeabur configuration file `backend/zeabur.json`
  - **Acceptance**: JSON includes buildCommand, startCommand, port binding ($PORT), and healthCheckPath (/api/v1/health)
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Backend
  - **File**: `backend/zeabur.json`

- [X] T008 [P] [US1] Implement health check endpoint in `backend/src/courseflow/api/routes/health.py`
  - **Acceptance**: GET /api/v1/health returns HTTP 200 with `{"status": "healthy", "components": {"database": "ok", "chroma": "ok"}}`, no authentication required
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Backend
  - **File**: `backend/src/courseflow/api/routes/health.py`

- [X] T009 [US1] Register health check route in FastAPI app main.py
  - **Acceptance**: Health check endpoint accessible at `/api/v1/health`, returns 200
  - **Dependencies**: T008
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/api/main.py`

- [X] T010 [US1] Update CORS configuration in `backend/src/courseflow/config.py` to include production frontend URL
  - **Acceptance**: CORS_ORIGINS includes `https://courseflow.zeabur.app` and `http://localhost:5173`, environment variable CORS_ORIGINS supported
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/config.py`

- [X] T011 [US1] Modify Dockerfile to bind to $PORT environment variable (Zeabur requirement)
  - **Acceptance**: Dockerfile CMD uses `--port $PORT` argument, defaults to 8000 if PORT not set
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/Dockerfile`

### Frontend Deployment for User Story 1

- [X] T012 [P] [US1] Create frontend Zeabur configuration file `frontend/zeabur.json`
  - **Acceptance**: JSON includes buildCommand (npm run build), outputDirectory (dist), and static site configuration
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Frontend
  - **File**: `frontend/zeabur.json`

- [X] T013 [P] [US1] Create environment variable configuration file `frontend/src/config/env.ts`
  - **Acceptance**: File exports API_URL from import.meta.env.VITE_API_URL, defaults to http://localhost:8000 if not set
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Frontend
  - **File**: `frontend/src/config/env.ts`

- [X] T014 [US1] Update axios client in `frontend/src/services/api.ts` to use API_URL from env.ts
  - **Acceptance**: Axios baseURL reads from env.ts, frontend compiles successfully
  - **Dependencies**: T013
  - **Effort**: Small
  - **Component**: Frontend
  - **File**: `frontend/src/services/api.ts`

- [X] T015 [P] [US1] Create `.env.production.example` template with VITE_API_URL placeholder
  - **Acceptance**: File contains `VITE_API_URL=https://courseflow-api.zeabur.app` as example, documented in README
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Frontend
  - **File**: `frontend/.env.production.example`

- [X] T016 [US1] Update Vite config in `frontend/vite.config.ts` to inject VITE_API_URL at build time
  - **Acceptance**: Vite config reads VITE_API_URL from environment, build completes successfully
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Frontend
  - **File**: `frontend/vite.config.ts`

### Deployment Execution for User Story 1

- [ ] T017 [US1] Create Zeabur project and deploy backend service
  - **Acceptance**: Backend deployed, receives public URL (e.g., https://courseflow-api.zeabur.app), health check returns 200
  - **Dependencies**: T007, T008, T009, T010, T011
  - **Effort**: Large
  - **Component**: DevOps

- [ ] T018 [US1] Configure backend environment variables in Zeabur dashboard (GEMINI_API_KEY, CORS_ORIGINS)
  - **Acceptance**: Environment variables set, backend restarts successfully, health check still returns 200
  - **Dependencies**: T017
  - **Effort**: Small
  - **Component**: DevOps

- [ ] T019 [US1] Deploy frontend service to Zeabur with VITE_API_URL environment variable
  - **Acceptance**: Frontend deployed, receives public URL (e.g., https://courseflow.zeabur.app), loads within 3 seconds
  - **Dependencies**: T012, T013, T014, T015, T016, T018
  - **Effort**: Large
  - **Component**: DevOps

- [ ] T020 [US1] Verify end-to-end query flow from frontend to backend
  - **Acceptance**: Submit question from frontend, streaming response arrives without CORS errors, no console errors (SC-001, SC-002, SC-003, SC-008)
  - **Dependencies**: T019
  - **Effort**: Medium
  - **Component**: Testing

### Documentation for User Story 1

- [X] T021 [P] [US1] Create Zeabur setup guide in `docs/deployment/zeabur-setup.md`
  - **Acceptance**: Document includes account creation, project setup, service deployment steps with screenshots
  - **Dependencies**: T017, T019
  - **Effort**: Medium
  - **Component**: Documentation
  - **File**: `docs/deployment/zeabur-setup.md`

- [X] T022 [P] [US1] Create environment variables documentation in `docs/deployment/environment-variables.md`
  - **Acceptance**: Document lists all required env vars (GEMINI_API_KEY, CORS_ORIGINS, VITE_API_URL) with descriptions and examples
  - **Dependencies**: T018
  - **Effort**: Small
  - **Component**: Documentation
  - **File**: `docs/deployment/environment-variables.md`

**Checkpoint**: User Story 1 complete - both services deployed and accessible at public URLs, E2E query works

---

## Phase 4: User Story 2 - Auto-Redeploy on Push (Priority: P1)

**Goal**: Enable automatic redeployment when commits are pushed to main branch

**Independent Test**: Push a minor code change (e.g., version bump in README) to main, verify Zeabur detects push, rebuilds, and deploys within 5 minutes

**Estimated Time**: 2 hours

### Implementation for User Story 2

- [ ] T023 [US2] Link GitHub repository to Zeabur project (GitHub webhook auto-configuration)
  - **Acceptance**: Repository linked in Zeabur dashboard, webhook created in GitHub repository settings automatically
  - **Dependencies**: T017, T019
  - **Effort**: Medium
  - **Component**: DevOps

- [ ] T024 [US2] Configure auto-deploy triggers in Zeabur for main branch
  - **Acceptance**: Zeabur configured to trigger rebuild on push to main branch only, test branches do not trigger deploy
  - **Dependencies**: T023
  - **Effort**: Small
  - **Component**: DevOps

- [ ] T025 [US2] Test auto-redeploy by pushing version bump commit to main
  - **Acceptance**: Push triggers rebuild within 1 minute, deployment completes within 5 minutes, new version live at public URL (SC-005)
  - **Dependencies**: T024
  - **Effort**: Medium
  - **Component**: Testing

### Documentation for User Story 2

- [ ] T026 [P] [US2] Document auto-deploy workflow in `docs/deployment/zeabur-setup.md` (update existing file)
  - **Acceptance**: Document includes GitHub webhook verification steps, troubleshooting failed deploys, and rebuild logs access
  - **Dependencies**: T025
  - **Effort**: Small
  - **Component**: Documentation
  - **File**: `docs/deployment/zeabur-setup.md`

**Checkpoint**: User Story 2 complete - auto-redeploy verified, documentation updated

---

## Phase 5: User Story 3 - Rate Limit Protection (Priority: P2)

**Goal**: Implement rate limiting to protect demo quota (20 requests per hour per IP)

**Independent Test**: Send 21 consecutive requests from single IP, verify 21st request returns HTTP 429 with appropriate error message

**Estimated Time**: 5 hours

### Tests for User Story 3 (Test-First Approach) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T027 [P] [US3] Unit test for RateLimitRepository.get_by_ip() in `backend/tests/unit/test_rate_limit_repo.py`
  - **Acceptance**: Test creates entry, retrieves by IP, verifies all fields match; test for non-existent IP returns None
  - **Dependencies**: T005
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `backend/tests/unit/test_rate_limit_repo.py`

- [ ] T028 [P] [US3] Unit test for RateLimitRepository.increment_counter() in `backend/tests/unit/test_rate_limit_repo.py`
  - **Acceptance**: Test increments counter from 1 to 2, verifies last_request timestamp updated
  - **Dependencies**: T005
  - **Effort**: Small
  - **Component**: Testing
  - **File**: `backend/tests/unit/test_rate_limit_repo.py`

- [ ] T029 [P] [US3] Unit test for RateLimitRepository.reset_window() in `backend/tests/unit/test_rate_limit_repo.py`
  - **Acceptance**: Test resets expired window, verifies count=1 and new window_start
  - **Dependencies**: T005
  - **Effort**: Small
  - **Component**: Testing
  - **File**: `backend/tests/unit/test_rate_limit_repo.py`

- [ ] T030 [P] [US3] Unit test for rate limit state transitions in `backend/tests/unit/test_rate_limit_states.py`
  - **Acceptance**: Tests cover NoEntry→Active, Active→Active (increment), Active→RateLimited, RateLimited→Reset transitions
  - **Dependencies**: T005
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `backend/tests/unit/test_rate_limit_states.py`

- [ ] T031 [US3] Run unit tests to verify they FAIL (no implementation yet)
  - **Acceptance**: All T027-T030 tests fail with expected errors (methods not implemented)
  - **Dependencies**: T027, T028, T029, T030
  - **Effort**: Small
  - **Component**: Testing

### Implementation for User Story 3

- [ ] T032 [US3] Implement RateLimitRepository.get_by_ip() method in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Method queries SQLite by ip_address, returns dict or None, T027 passes
  - **Dependencies**: T031
  - **Effort**: Medium
  - **Component**: Backend
  - **File**: `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`

- [ ] T033 [US3] Implement RateLimitRepository.create_entry() method in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Method inserts new entry with count=1, window_start=now, returns created entry dict
  - **Dependencies**: T031
  - **Effort**: Medium
  - **Component**: Backend
  - **File**: `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`

- [ ] T034 [US3] Implement RateLimitRepository.increment_counter() method in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Method increments count and updates last_request, T028 passes
  - **Dependencies**: T031
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`

- [ ] T035 [US3] Implement RateLimitRepository.reset_window() method in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Method resets count=1 and window_start=now, T029 passes
  - **Dependencies**: T031
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`

- [ ] T036 [US3] Implement RateLimitRepository.cleanup_old_entries() method in `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`
  - **Acceptance**: Method deletes entries where last_request < cutoff, returns count of deleted rows
  - **Dependencies**: T031
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/infrastructure/repositories/rate_limit_repo.py`

- [ ] T037 [US3] Create rate limiter middleware in `backend/src/courseflow/api/middleware/rate_limit.py`
  - **Acceptance**: Middleware extracts IP from request.client.host, checks rate limit, returns HTTP 429 if exceeded (count >= 20), includes retry_after header
  - **Dependencies**: T032, T033, T034, T035
  - **Effort**: Large
  - **Component**: Backend
  - **File**: `backend/src/courseflow/api/middleware/rate_limit.py`

- [ ] T038 [US3] Register rate limiter middleware in FastAPI app main.py
  - **Acceptance**: Middleware registered before all routes, rate limiting active on all endpoints except /health
  - **Dependencies**: T037
  - **Effort**: Small
  - **Component**: Backend
  - **File**: `backend/src/courseflow/api/main.py`

### Integration Tests for User Story 3

- [ ] T039 [P] [US3] Integration test: 20 requests succeed in `backend/tests/integration/test_rate_limit_middleware.py`
  - **Acceptance**: Test sends 20 consecutive requests from same IP, all return HTTP 200 (SC-004)
  - **Dependencies**: T038
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `backend/tests/integration/test_rate_limit_middleware.py`

- [ ] T040 [P] [US3] Integration test: 21st request returns HTTP 429 in `backend/tests/integration/test_rate_limit_middleware.py`
  - **Acceptance**: Test sends 21st request, returns HTTP 429 with retry_after header (SC-004)
  - **Dependencies**: T038
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `backend/tests/integration/test_rate_limit_middleware.py`

- [ ] T041 [P] [US3] Integration test: Different IPs have independent counters in `backend/tests/integration/test_rate_limit_middleware.py`
  - **Acceptance**: Test sends 20 requests from IP1, 20 from IP2, all succeed (no shared counter)
  - **Dependencies**: T038
  - **Effort**: Small
  - **Component**: Testing
  - **File**: `backend/tests/integration/test_rate_limit_middleware.py`

- [ ] T042 [US3] Integration test: Rate limit persists across container restarts in `backend/tests/integration/test_rate_limit_persistence.py`
  - **Acceptance**: Test sends 10 requests, restarts app, sends 11 more, 21st returns 429 (SC-009)
  - **Dependencies**: T038
  - **Effort**: Large
  - **Component**: Testing
  - **File**: `backend/tests/integration/test_rate_limit_persistence.py`

### Deployment for User Story 3

- [ ] T043 [US3] Deploy rate limiter to Zeabur backend service
  - **Acceptance**: Rate limiter active on production, 21st request from single IP returns HTTP 429
  - **Dependencies**: T042
  - **Effort**: Medium
  - **Component**: DevOps

- [ ] T044 [US3] Verify rate limit counters persist after Zeabur redeploy
  - **Acceptance**: Send 10 requests, trigger redeploy via git push, send 11 more requests, 21st returns 429 (SC-009)
  - **Dependencies**: T043
  - **Effort**: Medium
  - **Component**: Testing

**Checkpoint**: User Story 3 complete - rate limiting active, 80%+ test coverage achieved, persistence verified

---

## Phase 6: Edge Case Handling - Cold Start Retry Logic

**Goal**: Implement frontend retry logic with exponential backoff to handle backend cold starts (up to 30 seconds)

**Independent Test**: Stop backend service, wait for container shutdown, submit query from frontend, verify retry logic attempts 3 times with backoff (1s, 2s, 4s) and either succeeds or displays user-friendly error

**Estimated Time**: 4 hours

### Tests for Cold Start Handling (Test-First Approach) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T045 [P] Unit test for axios retry interceptor in `frontend/tests/unit/retry-interceptor.test.ts`
  - **Acceptance**: Test mocks failed requests, verifies 3 retry attempts with 1s, 2s, 4s delays (use fake timers)
  - **Dependencies**: None
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `frontend/tests/unit/retry-interceptor.test.ts`

- [ ] T046 [P] Unit test for retry exhaustion handling in `frontend/tests/unit/retry-interceptor.test.ts`
  - **Acceptance**: Test mocks 3 failed retries, verifies user-friendly error returned
  - **Dependencies**: None
  - **Effort**: Small
  - **Component**: Testing
  - **File**: `frontend/tests/unit/retry-interceptor.test.ts`

- [ ] T047 Run frontend unit tests to verify they FAIL (no implementation yet)
  - **Acceptance**: T045 and T046 fail with expected errors (interceptor not implemented)
  - **Dependencies**: T045, T046
  - **Effort**: Small
  - **Component**: Testing

### Implementation for Cold Start Handling

- [ ] T048 Implement axios retry interceptor with exponential backoff in `frontend/src/services/api.ts`
  - **Acceptance**: Interceptor catches network errors and 503 responses, retries max 3 times with delays (1s, 2s, 4s), T045 and T046 pass
  - **Dependencies**: T047
  - **Effort**: Large
  - **Component**: Frontend
  - **File**: `frontend/src/services/api.ts`

- [ ] T049 Add retry progress indicator to frontend UI in `frontend/src/components/ChatInterface.tsx`
  - **Acceptance**: Display "Connecting to backend (attempt X/3)..." during retries, show error message if exhausted
  - **Dependencies**: T048
  - **Effort**: Medium
  - **Component**: Frontend
  - **File**: `frontend/src/components/ChatInterface.tsx`

### E2E Tests for Cold Start Handling

- [ ] T050 E2E test: Cold start retry success in `frontend/tests/e2e/cold-start.spec.ts`
  - **Acceptance**: Test simulates backend unavailable for 5s, then available, verifies frontend retries and succeeds (SC-006)
  - **Dependencies**: T049
  - **Effort**: Large
  - **Component**: Testing
  - **File**: `frontend/tests/e2e/cold-start.spec.ts`

- [ ] T051 E2E test: Retry exhaustion displays error in `frontend/tests/e2e/cold-start.spec.ts`
  - **Acceptance**: Test simulates backend unavailable for 15s, verifies frontend exhausts retries and shows user-friendly error (SC-006)
  - **Dependencies**: T049
  - **Effort**: Medium
  - **Component**: Testing
  - **File**: `frontend/tests/e2e/cold-start.spec.ts`

### Deployment for Cold Start Handling

- [ ] T052 Deploy frontend retry logic to Zeabur
  - **Acceptance**: Retry logic active on production, displays retry progress during cold starts
  - **Dependencies**: T051
  - **Effort**: Small
  - **Component**: DevOps

- [ ] T053 Manual test: Verify cold start handling on production
  - **Acceptance**: Wait for backend to idle (30+ minutes), submit query, verify retry success or user-friendly error within 12 seconds (SC-006)
  - **Dependencies**: T052
  - **Effort**: Large
  - **Component**: Testing

**Checkpoint**: Cold start handling complete - retry logic active, E2E tests pass, user experience improved

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, troubleshooting guides, and final validation

**Estimated Time**: 3 hours

- [ ] T054 [P] Create troubleshooting guide in `docs/deployment/troubleshooting.md`
  - **Acceptance**: Document covers common issues (CORS errors, environment variable misconfiguration, build failures, cold start timeouts) with solutions
  - **Dependencies**: T053
  - **Effort**: Medium
  - **Component**: Documentation
  - **File**: `docs/deployment/troubleshooting.md`

- [ ] T055 [P] Update main README.md with deployment section
  - **Acceptance**: README includes links to Zeabur setup guide, public URLs, and health check endpoint documentation
  - **Dependencies**: T021, T022, T054
  - **Effort**: Small
  - **Component**: Documentation
  - **File**: `README.md`

- [ ] T056 [P] Add API documentation for health check endpoint in `docs/api/health-check.md`
  - **Acceptance**: Document describes endpoint URL, response format, and usage examples
  - **Dependencies**: T008
  - **Effort**: Small
  - **Component**: Documentation
  - **File**: `docs/api/health-check.md`

- [ ] T057 Run full test suite (unit + integration + E2E) to verify 80%+ coverage
  - **Acceptance**: All tests pass, rate limiter coverage >= 80%, retry logic coverage >= 80%
  - **Dependencies**: T042, T051
  - **Effort**: Medium
  - **Component**: Testing

- [ ] T058 Validate all success criteria from spec (SC-001 through SC-009)
  - **Acceptance**: All 9 success criteria verified on production deployment (checklist in quickstart.md)
  - **Dependencies**: T053, T057
  - **Effort**: Large
  - **Component**: Testing

- [ ] T059 Create deployment checklist in `specs/008-zeabur-deployment/checklists/deployment.md`
  - **Acceptance**: Checklist includes pre-deployment, deployment, and post-deployment verification steps
  - **Dependencies**: T058
  - **Effort**: Small
  - **Component**: Documentation
  - **File**: `specs/008-zeabur-deployment/checklists/deployment.md`

- [ ] T060 Final code review and merge to main
  - **Acceptance**: PR approved, all CI checks pass, branch merged to main, auto-deploy triggered
  - **Dependencies**: T059
  - **Effort**: Medium
  - **Component**: DevOps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T004-T006) - Core deployment
- **User Story 2 (Phase 4)**: Depends on User Story 1 (T017, T019) - Auto-deploy requires deployed services
- **User Story 3 (Phase 5)**: Depends on Foundational (T005) - Rate limiting uses repository from Phase 2
- **Cold Start Handling (Phase 6)**: Can run parallel to User Story 3 (independent feature)
- **Polish (Phase 7)**: Depends on all user stories complete (T053, T042)

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational - No dependencies on other stories
  - Backend deployment (T007-T011) can run parallel to Frontend deployment (T012-T016)
  - Deployment execution (T017-T020) is sequential (backend first, then frontend)
  
- **User Story 2 (P1)**: Depends on User Story 1 completion
  - Requires deployed services to link GitHub webhook (T023-T025)
  
- **User Story 3 (P2)**: Depends on Foundational (RateLimitRepository)
  - Tests (T027-T030) can run in parallel
  - Implementation (T032-T038) is sequential (repository methods before middleware)
  - Integration tests (T039-T042) can run in parallel

### Within Each Phase

**Phase 3 - User Story 1**:
- Backend tasks (T007-T011) are independent and can run in parallel
- Frontend tasks (T012-T016) are mostly independent except T014 depends on T013
- Deployment tasks (T017-T020) are sequential
- Documentation tasks (T021-T022) are parallel and can start after deployment

**Phase 5 - User Story 3**:
- Unit tests (T027-T030) MUST be written first and fail (T031)
- Repository implementation (T032-T036) can run after T031
- Middleware (T037-T038) depends on repository methods
- Integration tests (T039-T041) can run in parallel after T038

**Phase 6 - Cold Start Handling**:
- Frontend tests (T045-T046) MUST be written first and fail (T047)
- Implementation (T048-T049) is sequential
- E2E tests (T050-T051) can run in parallel after T049

### Parallel Opportunities

**Maximum Parallelism** (with sufficient team capacity):

1. After Foundational phase completes:
   - Team A: User Story 1 Backend (T007-T011)
   - Team B: User Story 1 Frontend (T012-T016)
   - Team C: User Story 3 Tests (T027-T030)
   - Team D: Cold Start Tests (T045-T046)

2. After User Story 1 Backend deploys:
   - Team A: User Story 2 (T023-T026)
   - Team B: User Story 1 Frontend deployment (T019-T020)

3. After tests written:
   - Team C: User Story 3 Implementation (T032-T038)
   - Team D: Cold Start Implementation (T048-T049)

4. After implementations:
   - Team C: User Story 3 Integration Tests (T039-T042)
   - Team D: Cold Start E2E Tests (T050-T051)

---

## Parallel Example: User Story 1 Backend

```bash
# Launch all backend deployment tasks together:
Task: "T007 Create backend zeabur.json"
Task: "T008 Implement health check endpoint"
Task: "T010 Update CORS configuration"
Task: "T011 Modify Dockerfile for PORT binding"

# These can all be worked on simultaneously (different files)
```

## Parallel Example: User Story 3 Tests

```bash
# Launch all rate limiter unit tests together:
Task: "T027 Test get_by_ip()"
Task: "T028 Test increment_counter()"
Task: "T029 Test reset_window()"
Task: "T030 Test state transitions"

# These can all be written in parallel (test-first approach)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: User Story 1 (T007-T022)
4. **STOP and VALIDATE**: Test deployment at public URLs, verify E2E query works
5. Deploy to production, share URLs with interviewers

**MVP Delivers**: Working public deployment with health check, CORS configured, ready for live demos

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP!)
3. Add User Story 2 → Test auto-deploy → Redeploy (CI/CD enabled!)
4. Add User Story 3 → Test rate limiting → Redeploy (Quota protected!)
5. Add Cold Start Handling → Test retry logic → Redeploy (UX improved!)

**Each increment adds value without breaking previous features**

### Parallel Team Strategy

With 3 developers:

1. **Week 1**: Team completes Setup + Foundational together
2. **Week 2** (after Foundational done):
   - Developer A: User Story 1 Backend (T007-T011) + Deployment (T017-T018)
   - Developer B: User Story 1 Frontend (T012-T016) + Deployment (T019-T020)
   - Developer C: User Story 3 Tests (T027-T031) + Cold Start Tests (T045-T047)
3. **Week 3**:
   - Developer A: User Story 2 (T023-T026)
   - Developer B: Cold Start Implementation (T048-T053)
   - Developer C: User Story 3 Implementation (T032-T044)
4. **Week 4**: All developers on Polish (T054-T060)

---

## Success Criteria Mapping

| Task ID | Success Criteria | Test Method |
|---------|------------------|-------------|
| T020 | SC-001: Frontend loads <3s | Browser DevTools Network tab |
| T020 | SC-002: Health check <1s | `curl -w "%{time_total}" /health` |
| T020 | SC-003: E2E query <8s | Frontend timer (submission → first token) |
| T043 | SC-004: Rate limit active | Send 21 requests, verify 21st = HTTP 429 |
| T025 | SC-005: Auto-redeploy <5min | Push commit, measure time to live |
| T053 | SC-006: Cold start handling | Idle 30min, submit query, verify retry |
| T058 | SC-007: URLs accessible 30 days | Daily uptime check (manual) |
| T020 | SC-008: No CORS errors | Browser console during query |
| T044 | SC-009: Rate limit persistence | Redeploy, verify counter persists |

---

## Effort Summary

- **Phase 1 (Setup)**: 30 minutes (3 tasks)
- **Phase 2 (Foundational)**: 2 hours (3 tasks)
- **Phase 3 (User Story 1)**: 6 hours (16 tasks)
- **Phase 4 (User Story 2)**: 2 hours (4 tasks)
- **Phase 5 (User Story 3)**: 5 hours (18 tasks)
- **Phase 6 (Cold Start)**: 4 hours (9 tasks)
- **Phase 7 (Polish)**: 3 hours (7 tasks)

**Total Estimated Time**: 22.5 hours (~3 working days for 1 developer)

**With 3 Developers (Parallel)**: ~10-12 hours (1.5 working days)

---

## Notes

- **[P] tasks** = different files, no dependencies, safe to parallelize
- **[Story] label** maps task to specific user story for traceability
- Tests are REQUIRED for User Story 3 (rate limiter) and Cold Start (retry logic) - these are critical paths that need 80%+ coverage
- Tests MUST be written first (test-first approach) for rate limiter and retry logic
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- If deployment fails, consult `docs/deployment/troubleshooting.md`

---

**Tasks Status**: ✅ COMPLETE - Ready for implementation via `/speckit.implement`
