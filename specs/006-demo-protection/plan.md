# Implementation Plan: Demo Quota Protection Middleware

**Branch**: `006-demo-protection` | **Date**: 2026-02-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-demo-protection/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement middleware to protect demo quota by:
1. Enforcing per-IP hourly query limits (20 queries per rolling hour)
2. Enforcing global daily query budget (configurable, default ~300)
3. Serving 10 pre-cached demo questions without consuming quota
4. Providing quota status visibility and warning signals at 80% usage

This ensures reliable demo availability under heavy usage while preserving UX consistency through streaming simulation for cached responses.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.109+, Pydantic 2.5+, APScheduler 3.10+ (for daily resets)  
**Storage**: In-memory for per-IP counters (session-based), SQLite for daily usage persistence  
**Testing**: pytest, pytest-asyncio, pytest-cov (existing test infrastructure)  
**Target Platform**: Linux server (local development, future deployment on free tier hosting)  
**Project Type**: Single FastAPI backend with hexagonal architecture  
**Performance Goals**: <5ms quota check overhead per request  
**Constraints**: Zero-cost (no external services), fail-closed on storage errors, preserve <2s RAG p95 latency  
**Scale/Scope**: Demo usage (~10-50 concurrent users during presentations, 1500 req/day Gemini limit)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality**: 
- [x] Feature complexity justified: Middleware pattern is simple, fits hexagonal arch. Quota logic is straightforward (counter tracking + time window checks).
- [x] Documentation strategy defined: API docs via FastAPI/OpenAPI, inline docstrings for quota logic, update QUICKSTART.md with quota endpoints.
- [x] Code review process: Self-review with automated checks (ruff, mypy --strict, pytest coverage).

**Testing Standards**:
- [x] Test strategy defined:
  - Unit tests: Quota logic (rolling window, cache matching, normalization)
  - Integration tests: Middleware enforcement on query endpoints, quota status endpoint accuracy
  - E2E tests: Full request flow (IP limit, daily limit, cache hit scenarios)
- [x] Coverage targets: 80% minimum for middleware, 100% for quota enforcement logic (critical path).
- [x] Test-first approach: Write tests for each acceptance scenario before implementing middleware.

**User Experience Consistency**:
- [x] Design system: N/A (backend-only feature)
- [x] Accessibility: N/A (API-only)
- [x] Responsive design: N/A (API-only)
- [x] Error handling designed: HTTP 429 (rate limit), 503 (storage unavailable), 400 (IP unavailable), with retry-after headers and clear error messages.

**Performance Requirements**:
- [x] Performance targets: <5ms quota check overhead (in-memory lookups), maintain <2s RAG p95 latency.
- [x] Database strategy: SQLite async queries for daily usage persistence, single row update per request.
- [x] Asset optimization: N/A (backend-only)
- [x] Scalability: In-memory counters scale to ~1000 IPs (demo scope), daily usage persistence ensures restart tolerance.

**AI Engineering Standards** (constitution Section III):
- [x] Quota protection directly implements constitution requirements (Section III.IV: Quota & Rate Limiting).
- [x] Cache-hit bypass aligns with zero-cost constraints (Section VI: maximize Gemini free tier efficiency).
- [x] Fail-closed behavior aligns with graceful degradation principles (Section III.I: Error Handling).

**Gate Status**: ✅ PASS — All constitution checks satisfied, no violations requiring justification.

**Post-Design Re-evaluation** (Phase 1 Complete):
- ✅ Architecture review approved (Grade A - Senior Architect)
- ✅ Hexagonal architecture adherence confirmed
- ✅ API design follows REST best practices (OpenAPI spec generated)
- ✅ Data model follows DDD principles (entities, value objects, ports)
- ✅ Zero new external dependencies (uses existing aiosqlite, apscheduler)
- ✅ Performance targets achievable (<5ms overhead, preserves <2s RAG p95)
- ✅ Observability recommendations documented for implementation phase

**Final Gate Status**: ✅✅ DOUBLE-PASS — Pre-research and post-design checks complete. Ready for task generation.

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
├── domain/
│   ├── models.py               # Add: QuotaWindow, QuotaLedger, CacheEntry models
│   ├── ports.py                # Add: QuotaStorePort interface
│   └── exceptions.py           # Add: QuotaExceededError, IPLimitError
├── application/
│   ├── quota_service.py        # NEW: Core quota enforcement logic
│   ├── cache_service.py        # NEW: Demo cache matching & streaming
│   └── [existing services...]  # rag_service.py, ingestion_service.py, etc.
├── infrastructure/
│   ├── quota/
│   │   ├── in_memory_quota.py  # NEW: In-memory IP tracking
│   │   └── sqlite_quota.py     # NEW: Daily usage persistence
│   └── [existing adapters...]  # llm/, vector_store/, repositories/
├── api/
│   ├── middleware/
│   │   └── quota_middleware.py # NEW: FastAPI middleware
│   ├── routes/
│   │   ├── query.py            # MODIFIED: Apply quota middleware
│   │   ├── health.py           # MODIFIED: Add quota warning to health
│   │   └── quota.py            # NEW: GET /api/v1/quota/status endpoint
│   └── dependencies.py         # MODIFIED: Inject quota services
├── config.py                   # MODIFIED: Add quota config (hourly_limit, daily_budget)
└── [existing files...]

tests/
├── unit/
│   ├── test_quota_service.py   # NEW: Rolling window, normalization tests
│   └── test_cache_service.py   # NEW: Cache matching, streaming tests
├── integration/
│   ├── test_quota_middleware.py # NEW: End-to-end enforcement tests
│   └── test_quota_endpoints.py  # NEW: Status endpoint accuracy tests
└── [existing tests...]
```

**Structure Decision**: Single FastAPI backend (hexagonal architecture). New quota domain with in-memory + SQLite adapters. Middleware pattern for non-invasive enforcement on existing query routes. Aligns with constitution Section IV (Architecture Patterns).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations identified. All checks passed.*
