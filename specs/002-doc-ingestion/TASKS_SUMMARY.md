# Tasks Summary - Document Ingestion Feature

**Generated**: 2025-02-12  
**Feature**: Document Ingestion and Knowledge Base Management  
**Branch**: 002-document-ingestion

---

## Quick Stats

- **Total Tasks**: 84
- **Parallelizable**: 30 tasks (36%)
- **MVP Tasks**: 34 tasks (Phases 1-3)
- **File**: [tasks.md](./tasks.md)

---

## Phase Overview

| Phase | Description | Tasks | IDs | Critical |
|-------|-------------|-------|-----|----------|
| 1 | Setup | 6 | T001-T006 | - |
| 2 | Foundational | 14 | T007-T020 | ⚠️ BLOCKS ALL STORIES |
| 3 | User Story 1 (P1) | 14 | T021-T034 | 🎯 MVP |
| 4 | User Story 2 (P2) | 9 | T035-T043 | - |
| 5 | User Story 3 (P3) | 8 | T044-T051 | - |
| 6 | User Story 4 (P2) | 15 | T052-T066 | - |
| 7 | Polish | 18 | T067-T084 | - |

---

## User Stories

### US1: Basic Document Upload (P1) - MVP ⭐
**Tasks**: 14 (T021-T034)  
**Goal**: Upload documents and make them immediately queryable  
**Test**: Upload markdown → verify query returns results

**Key Deliverables**:
- IngestionService with text extraction
- POST /api/v1/ingest endpoint
- GET /api/v1/documents endpoint
- GET /api/v1/subjects endpoint
- E2E tests for markdown, PDF, plain text

---

### US2: Idempotent Re-upload Protection (P2)
**Tasks**: 9 (T035-T043)  
**Goal**: Prevent duplicate content via content hashing  
**Test**: Upload same file twice → second skipped, 0 new chunks

**Key Deliverables**:
- Content hash duplicate detection
- Concurrency protection (UNIQUE constraint)
- Race condition handling
- Integration tests for duplicates

---

### US3: Multi-Subject Organization (P3)
**Tasks**: 8 (T044-T051)  
**Goal**: Tag documents with subject metadata for filtered search  
**Test**: Upload with subject tags → filter queries by subject

**Key Deliverables**:
- Subject validation in IngestionService
- Subject filtering in queries
- Default subject handling
- Integration tests for subject organization

---

### US4: Automatic Retry & Failure Handling (P2)
**Tasks**: 15 (T052-T066)  
**Goal**: Graceful handling of rate limits and transient errors  
**Test**: Simulate rate limit → auto-retry or rollback

**Key Deliverables**:
- RateLimiter with queue management
- Exponential backoff (1s start, 2x, max 5 retries)
- Transactional rollback on failure
- HTTP 429 handling
- Integration tests for retry scenarios

---

## Critical Path

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← ⚠️ BLOCKS EVERYTHING
    ↓
Phase 3 (US1) ← MVP starts here
    ↓
Phases 4, 5, 6 (US2, US3, US4) ← Can be parallel
    ↓
Phase 7 (Polish)
```

**Bottleneck**: Phase 2 must complete before any user story work begins.

**Parallelization**: After Phase 2, all user stories can be developed in parallel by different team members.

---

## MVP Delivery Path

**Phases 1-3 only** (34 tasks, ~6-8 hours)

1. **Phase 1** (T001-T006): Install dependencies, setup DB
2. **Phase 2** (T007-T020): Build foundation (ports, adapters, repos)
3. **Phase 3** (T021-T034): Implement core ingestion + API

**MVP Checkpoint**: Upload a markdown file → query it successfully → ✅ DONE!

---

## Parallel Opportunities

### Phase 2 (Foundational)
- Domain entities: T007, T008, T009, T010 (4 parallel)
- Text processing: T011, T012, T013 (3 parallel)
- Repositories: T015, T016 (2 parallel)

### Phase 3 (User Story 1)
- Endpoints: T029, T030 (2 parallel)
- Tests: T031, T032, T033 (3 parallel)

### Cross-Story (after Phase 2)
- 4 developers → US1, US2, US3, US4 simultaneously

---

## Dependencies Added

```toml
pymupdf>=1.27.0      # PDF text extraction
tiktoken>=0.12.0     # Token counting (GPT/Gemini compatible)
nltk>=3.9.0          # Sentence tokenization
```

---

## Database Changes

**New Tables**:
- `subjects` - Subject categories (biology, programming, etc.)
- `documents` - Document metadata (filename, hash, chunks count)
- `chunks` - Text chunks with metadata (sequential index, tokens)

**Migration**: `scripts/migrations/002_add_ingestion_tables.sql`

---

## Implementation Estimates

| Phase | Estimate | Parallelized |
|-------|----------|--------------|
| Phase 1 | 15-30 min | 15-30 min |
| Phase 2 | 3-4 hours | 2-3 hours |
| Phase 3 | 3-4 hours | 3-4 hours |
| Phase 4 | 1-2 hours | 1-2 hours |
| Phase 5 | 1-2 hours | 1-2 hours |
| Phase 6 | 3-4 hours | 3-4 hours |
| Phase 7 | 3-4 hours | 2-3 hours |

**Total**: 15-20 hours (full feature)  
**MVP**: 6-8 hours (Phases 1-3 only)

---

## Architecture Summary

**Pattern**: Hexagonal (Ports & Adapters)

**Ports** (6):
- PDFExtractorPort
- TokenCounterPort
- SentenceTokenizerPort
- ChunkerPort
- DocumentRepositoryPort
- ChunkRepositoryPort

**Adapters** (7):
- PyMuPDFExtractor
- TiktokenCounter
- NLTKSentenceTokenizer
- SentenceChunker
- SubjectRepository (SQLite)
- DocumentRepository (SQLite)
- ChunkRepository (SQLite + ChromaDB)

---

## Validation Checklist

✅ All tasks follow format: `- [ ] [ID] [P?] [Story] Description`  
✅ Task IDs sequential (T001-T084)  
✅ [P] markers on 30 parallelizable tasks  
✅ [Story] labels on 46 user story tasks (US1, US2, US3, US4)  
✅ File paths in all implementation tasks  
✅ User stories independently testable  
✅ Dependency graph documented  
✅ MVP scope identified (Phases 1-3)  
✅ Constitution compliance verified  

---

## Next Steps

1. ✅ Review tasks.md
2. Start Phase 1: T001 (add dependencies)
3. Complete Phase 2 (foundation)
4. Build MVP (Phase 3)
5. Validate end-to-end upload → query
6. Add user stories incrementally
7. Polish and ship! 🚀

---

**Ready for implementation!**
