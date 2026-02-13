# Implementation Tasks: Multi-turn Conversation Support

**Feature**: Multi-turn Conversation Support  
**Branch**: `003-conversation-context`  
**Date**: 2026-02-13  
**Status**: Ready for Implementation  

---

## Overview

This document outlines all tasks required to implement multi-turn conversation support in CourseFlow. The feature enables learners to ask follow-up questions within the same conversation while the system preserves context and history.

**Key Constraints**:
- Zero new dependencies (reuse tiktoken 0.12.0, SQLite, aiosqlite)
- Hexagonal architecture maintained (domain → application → infrastructure)
- Backward compatible (existing single-turn queries still work)
- Token budget: history ≤2000 tokens, total prompt ≤8000 tokens
- Atomic persistence (both user + assistant turns or neither)

**Suggested MVP Scope**: Complete Phase 1-3 (Setup, Foundational, and User Story 1)
- Phase 1: Database schema + shared infrastructure
- Phase 2: Domain entities + repository layer
- Phase 3: RAG service integration + API endpoint
- Result: Users can create conversations and make follow-up queries with preserved context

---

## Phase Dependencies & Parallel Execution

### Dependency Graph

```
Phase 1 (Setup)
   ↓
Phase 2 (Foundational Infrastructure)
   ↓
Phase 3 (User Story 1: Accept & Store Conversations)
   ↓ (optional for MVP)
Phase 4 (Polish & Optimizations)
```

**Parallel Opportunities**:
- Within Phase 2: Domain models and repository port can be coded in parallel
- Within Phase 3: Tests and endpoint can be developed simultaneously (test-first)

**Independent Test Criteria** (per phase):
- Phase 1: Migration runs successfully; tables created with correct schema
- Phase 2: Domain entities validate; repository CRUD operations work
- Phase 3: API accepts conversation_id; history included in LLM prompts; multi-turn queries succeed
- Phase 4: Token budget enforced; turn trimming tested; edge cases handled

---

## Phase 1: Setup & Database Migration

### Goal
Prepare the database schema for storing conversations and turns. This is the foundation for all subsequent phases.

### Success Criteria
- ✅ Migration file created at `scripts/migrations/003_add_conversation_tables.sql`
- ✅ Tables created: `conversations` and `conversation_turns`
- ✅ Composite index created: `idx_turns_conversation_time`
- ✅ Migration can be executed without errors

### Tasks

- [ ] T001 Create database migration file at `scripts/migrations/003_add_conversation_tables.sql`
- [ ] T002 Define conversations table schema (id TEXT PRIMARY KEY, created_at TIMESTAMP)
- [ ] T003 Define conversation_turns table schema with all fields and CHECK constraints
- [ ] T004 Add foreign key from conversation_turns to conversations (ON DELETE CASCADE)
- [ ] T005 Create composite index on (conversation_id, created_at DESC) for efficient history retrieval
- [ ] T006 Test migration execution: verify tables created correctly
- [ ] T007 Document migration execution command in README

---

## Phase 2: Foundational Infrastructure

### Goal
Implement domain entities, repository port, and supporting infrastructure. This phase provides the foundation for all user stories.

### Success Criteria
- ✅ Domain models created and validated
- ✅ Repository port defined with 3 core methods
- ✅ Token counter utility available
- ✅ Exception classes defined
- ✅ All foundational unit tests pass (>80% coverage)

### Tasks

#### Domain Models (Parallelizable)

- [ ] T008 [P] Create Conversation domain entity in `src/courseflow/domain/models.py`
- [ ] T009 [P] Create ConversationTurn domain entity in `src/courseflow/domain/models.py`
- [ ] T010 [P] Add validation to Conversation.__post_init__ (UUID format, no future timestamps)
- [ ] T011 [P] Add validation to ConversationTurn.__post_init__ (role check, non-empty content, non-negative token_count)
- [ ] T012 [P] Create ConversationNotFoundError exception in `src/courseflow/domain/exceptions.py`
- [ ] T013 [P] Create InvalidConversationIDError exception in `src/courseflow/domain/exceptions.py`

#### Repository Port

- [ ] T014 Create ConversationRepositoryPort abstract base class in `src/courseflow/domain/ports.py`
- [ ] T015 Define create_conversation() method signature
- [ ] T016 Define find_conversation(conversation_id: UUID) method signature
- [ ] T017 Define get_turns(conversation_id: UUID, limit: int = 5) method signature (returns TurnHistory)
- [ ] T018 Create TurnHistory value object with token_count property and validation

#### Token Counting Utility

- [ ] T019 [P] Create token counter wrapper in `src/courseflow/infrastructure/token_counting/counter.py`
- [ ] T020 [P] Implement calculate_token_count(content: str) using tiktoken.get_encoding("cl100k_base")
- [ ] T021 [P] Add token counting to domain: token_count = calculate_token_count(turn.content)

#### Unit Tests (Parallelizable)

- [ ] T022 [P] Create test_conversation_entity.py in `tests/unit/domain/`
- [ ] T023 [P] Test Conversation validation (UUID, future timestamp check)
- [ ] T024 [P] Create test_conversation_turn_entity.py in `tests/unit/domain/`
- [ ] T025 [P] Test ConversationTurn validation (role, content, token_count)
- [ ] T026 [P] Create test_token_counter.py in `tests/unit/infrastructure/`
- [ ] T027 [P] Test token count calculation against known values
- [ ] T028 [P] Verify coverage ≥80% for Phase 2 code

---

## Phase 3: Accept & Store Conversations (User Story 1)

### Goal
Implement the core feature: accept optional conversation_id in queries, create new conversations, and store conversation history with context in LLM prompts.

### Success Criteria
- ✅ API accepts optional conversation_id parameter
- ✅ New conversations created and returned to client
- ✅ Conversation history retrieved and included in LLM prompts
- ✅ Multi-turn queries work correctly with context retention
- ✅ Backward compatibility maintained (queries without conversation_id still work)
- ✅ All integration and E2E tests pass

### User Story
> As a learner, I want to ask follow-up questions within the same conversation so that the AI remembers what we discussed and I don't have to repeat context every time.

### Dependencies
- Completion of Phase 1 (database)
- Completion of Phase 2 (domain + repository port)

### Tasks

#### Repository Implementation (SQLite Adapter)

- [ ] T029 [US1] Create SQLiteConversationRepository class in `src/courseflow/infrastructure/repositories/conversation_repo.py`
- [ ] T030 [US1] Implement __init__ to accept aiosqlite connection pool
- [ ] T031 [US1] Implement create_conversation() → Conversation with generated UUID4
- [ ] T032 [US1] Implement find_conversation(conversation_id: UUID) → Optional[Conversation]
- [ ] T033 [US1] Implement get_turns(conversation_id: UUID, limit: int = 5) → TurnHistory
- [ ] T034 [US1] Implement add_turn() to persist user + assistant turns atomically
- [ ] T035 [US1] Add transaction handling: rollback on failure, commit on success
- [ ] T036 [US1] Handle ConversationNotFoundError when conversation_id is invalid

#### API Schema & Route Updates

- [ ] T037 [US1] Update QueryRequest schema in `src/courseflow/api/schemas/query.py` to accept conversation_id: Optional[UUID] = None
- [ ] T038 [US1] Update QueryResponse schema to include conversation_id: UUID
- [ ] T039 [US1] Update error responses to handle ConversationNotFoundError (404 with message)
- [ ] T040 [US1] Create new endpoint response model with conversation_id field

#### RAG Service Enhancement

- [ ] T041 [US1] Modify RAGService.query() signature to accept conversation_id: Optional[UUID] = None
- [ ] T042 [US1] Add logic to create new conversation if conversation_id is None
- [ ] T043 [US1] Add logic to validate and retrieve existing conversation if conversation_id provided
- [ ] T044 [US1] Format conversation history as context in LLM prompt (last 5 turns)
- [ ] T045 [US1] Include history in system prompt: "Previous context: {formatted_history}"
- [ ] T046 [US1] Add token counting for history and validate total prompt tokens < 8000
- [ ] T047 [US1] Implement atomic turn persistence: save user + assistant turns after successful LLM response
- [ ] T048 [US1] Rollback (save nothing) if retrieval or LLM fails

#### API Route Handler

- [ ] T049 [US1] Update POST /api/v1/query handler in `src/courseflow/api/routes/query.py`
- [ ] T050 [US1] Extract conversation_id from request (None if omitted)
- [ ] T051 [US1] Call RAGService.query(conversation_id=conversation_id)
- [ ] T052 [US1] Return response with conversation_id in data
- [ ] T053 [US1] Handle ConversationNotFoundError and return 404 with helpful message

#### Dependency Injection & Wiring

- [ ] T054 [US1] Wire SQLiteConversationRepository in `src/courseflow/api/dependencies.py`
- [ ] T055 [US1] Inject repository into RAGService
- [ ] T056 [US1] Ensure aiosqlite connection pool available at startup

#### Integration Tests

- [ ] T057 [US1] Create test_conversation_repository.py in `tests/integration/`
- [ ] T058 [US1] Test create_conversation() → returns Conversation with UUID
- [ ] T059 [US1] Test find_conversation() → returns existing conversation
- [ ] T060 [US1] Test find_conversation() → returns None for invalid ID
- [ ] T061 [US1] Test get_turns() → returns last N turns in chronological order
- [ ] T062 [US1] Test add_turn() → persists both user and assistant turns atomically

#### E2E Tests (Multi-turn Conversation Flow)

- [ ] T063 [US1] Create test_multi_turn_conversation.py in `tests/e2e/`
- [ ] T064 [US1] Test Turn 1: Create new conversation, send query, get answer with conversation_id
- [ ] T065 [US1] Test Turn 2: Send follow-up with same conversation_id, history included in prompt
- [ ] T066 [US1] Test Turn 3: Another follow-up, verify context from Turn 1 and 2 available
- [ ] T067 [US1] Test invalid conversation_id → 404 error with helpful message
- [ ] T068 [US1] Test omitting conversation_id → new conversation created and returned
- [ ] T069 [US1] Verify conversation_id persists across requests (not regenerated)

#### Manual Testing / Documentation

- [ ] T070 [US1] Create curl examples in `docs/` for:
  - Creating new conversation (no conversation_id)
  - Making follow-up query (with conversation_id)
  - Retrieving conversation history
- [ ] T071 [US1] Document API changes in README or API docs
- [ ] T072 [US1] Test backward compatibility: existing clients still work without conversation_id

---

## Phase 4: Polish & Optimizations

### Goal
Implement history trimming, edge case handling, and performance optimizations.

### Success Criteria
- ✅ History trimmed to 5 turns or 2000 tokens (whichever comes first)
- ✅ Oldest turns removed first when budget exceeded
- ✅ All edge cases tested (concurrent queries, expired conversations, large histories)
- ✅ Performance targets met (<200ms overhead for history operations)
- ✅ Error handling robust and user-friendly

### Optional for MVP (can defer to v2)

#### History Trimming Logic

- [ ] T073 Create TurnHistoryTrimmer utility in `src/courseflow/domain/trimming.py`
- [ ] T074 Implement oldest-first trimming algorithm: remove turns until token_count ≤ 2000
- [ ] T075 Add unit tests for trimming (10 turns → keep 5, etc.)
- [ ] T076 Integrate trimmer into RAGService before including history in prompt

#### Edge Cases & Robustness

- [ ] T077 Test concurrent requests to same conversation (no race conditions)
- [ ] T078 Test conversation with 100+ turns (trimming performance)
- [ ] T079 Test very large turn content (>1000 tokens)
- [ ] T080 Test empty conversation (zero turns)
- [ ] T081 Test conversation after application restart (persistence verified)

#### Performance Optimization

- [ ] T082 Verify database indexes on (conversation_id, created_at DESC)
- [ ] T083 Profile history retrieval (<100ms target)
- [ ] T084 Profile token counting (<50ms target)
- [ ] T085 Profile turn insertion (<50ms target)
- [ ] T086 Document performance characteristics in dev guide

#### Query Rewriting (Deferred to v2)

- [ ] T087 [DEFERRED] Implement query rewriting to enhance document retrieval using history context
- [ ] T088 [DEFERRED] Example: "What about error handling?" → rewrite to include "async" context

#### Conversation Management (Deferred to v2)

- [ ] T089 [DEFERRED] Implement conversation listing endpoint
- [ ] T090 [DEFERRED] Implement conversation deletion endpoint
- [ ] T091 [DEFERRED] Implement conversation cleanup (TTL-based)
- [ ] T092 [DEFERRED] Add conversation metadata (title, summary)

---

## Success Criteria by Phase

### Phase 1 (Database)
```sql
sqlite3 data/courseflow.db ".schema conversations"
sqlite3 data/courseflow.db ".schema conversation_turns"
sqlite3 data/courseflow.db ".indexes conversation_turns"
-- Should show: conversations, conversation_turns, idx_turns_conversation_time
```

### Phase 2 (Foundational)
```bash
pytest tests/unit/domain/ -v --cov=src/courseflow/domain
# Should have ≥80% coverage
# All tests pass
```

### Phase 3 (Core Feature)
```bash
# Manual test: Create conversation
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How do async functions work?"}' | jq '.data.conversation_id'

# Manual test: Follow-up
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What about error handling?","conversation_id":"<UUID>"}' | jq '.data.answer'
```

### Phase 4 (Polish)
```bash
pytest tests/integration/ tests/e2e/ -v --cov=src/courseflow
# All tests pass; ≥80% coverage
# Performance: <200ms overhead verified
```

---

## Implementation Strategy

### MVP Approach (Phases 1-3)
1. Database schema setup (T001-T007)
2. Domain models + repository port (T008-T028)
3. Repository implementation + API integration (T029-T072)
4. Result: Users can create and continue conversations with history context

**Estimated time**: 6-8 hours for experienced developer

### Full Feature (Phases 1-4)
Add Phase 4 tasks for robustness and optimizations.

**Estimated time**: 10-12 hours

### Defer to v2
- Query rewriting (T087-T088)
- Conversation management APIs (T089-T092)

---

## Testing Summary

### Unit Tests (Phase 2)
- 6 test files covering domain entities, exceptions, token counting
- Target coverage: ≥80%

### Integration Tests (Phase 3)
- Repository CRUD operations
- Database transactions and atomicity
- Error handling (ConversationNotFoundError)

### E2E Tests (Phase 3)
- Full multi-turn conversation flow
- Context retention across turns
- Backward compatibility

### Load/Performance Tests (Phase 4)
- Large conversation histories
- Concurrent access
- Index efficiency

---

## Quick Reference: File Changes

### New Files
```
scripts/migrations/
├── 003_add_conversation_tables.sql

src/courseflow/domain/
├── models.py (ADD: Conversation, ConversationTurn)
├── ports.py (ADD: ConversationRepositoryPort)
├── exceptions.py (ADD: ConversationNotFoundError, InvalidConversationIDError)
└── trimming.py (ADD: TurnHistoryTrimmer) [Phase 4]

src/courseflow/infrastructure/
├── repositories/conversation_repo.py (ADD: SQLiteConversationRepository)
├── token_counting/counter.py (ADD: token counting utility)

src/courseflow/api/
├── schemas/query.py (MODIFY: Add conversation_id field)
└── routes/query.py (MODIFY: Accept and return conversation_id)

tests/
├── unit/domain/test_conversation_entity.py
├── unit/domain/test_conversation_turn_entity.py
├── unit/infrastructure/test_token_counter.py
├── integration/test_conversation_repository.py
└── e2e/test_multi_turn_conversation.py
```

### Modified Files
```
src/courseflow/application/
├── rag_service.py (MODIFY: Accept conversation_id, include history in prompt)

src/courseflow/api/
├── dependencies.py (MODIFY: Wire conversation repository)
└── routes/query.py (MODIFY: Handle conversation_id)

src/courseflow/config.py (MODIFY: If needed, add history size limit config)
```

---

## Sign-Off

**Ready for Implementation**: ✅ All design artifacts complete
- [x] spec.md (user stories, acceptance criteria)
- [x] plan.md (technical approach, architecture)
- [x] data-model.md (entities, schema, repository port)
- [x] research.md (technical decisions)
- [x] quickstart.md (implementation guide)
- [x] tasks.md (this file - actionable tasks)

**Next Steps**: 
1. Run Phase 1 database tasks (T001-T007)
2. Implement Phase 2 domain layer (T008-T028)
3. Implement Phase 3 feature (T029-T072)
4. (Optional) Implement Phase 4 polish (T073-T086)

**Questions or Blockers**: Refer to research.md for technical decision rationale or quickstart.md for detailed implementation examples.
