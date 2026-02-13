# Implementation Plan: Multi-turn Conversation Support

**Branch**: `003-conversation-context` | **Date**: 2026-02-13 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-conversation-context/spec.md`

## Summary

Enable learners to ask follow-up questions with conversation history preservation. System stores conversation turns (user + assistant messages) in SQLite, enforces a 5-turn/2000-token budget, and enhances LLM prompts with recent context. Pure UUID4 conversation IDs; atomic turn persistence on success only. Backward compatible: omitting `conversation_id` creates new conversation.

**Technical Approach**: Extend existing hexagonal architecture with conversation domain entities, add conversation repository port/adapter, enhance RAG service to include history in prompts, implement token-aware history trimming.

## Technical Context

**Language/Version**: Python 3.11+ (existing)  
**Primary Dependencies**: 
- FastAPI 0.109+ (existing)
- aiosqlite (existing, for async SQLite)
- tiktoken 0.12.0 (existing, for token counting)
- Pydantic (existing, for validation)

**Storage**: SQLite with aiosqlite (`./data/courseflow.db`)  
**Testing**: pytest + pytest-asyncio + pytest-cov (existing)  
**Target Platform**: Linux/macOS server (existing)  
**Project Type**: Single backend API (existing structure)

**Performance Goals**:
- History retrieval: <100ms (p95)
- Token counting: <50ms
- Turn insertion: <50ms
- Total query latency increase: <200ms

**Constraints**:
- Async-first: all database operations via aiosqlite
- Zero new dependencies (reuse tiktoken, SQLite, FastAPI)
- Hexagonal architecture: domain → application → infrastructure
- No user auth (anonymous conversations)
- Token budget: history ≤2000 tokens, total prompt ≤8000 tokens

**Scale/Scope**:
- Support 100+ turns per conversation (trimmed to 5 in context)
- No conversation count limit in v1
- Concurrent conversations supported

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

**Code Quality**: 
- [x] Feature complexity justified (conversation storage is simple CRUD; token trimming algorithm <50 lines)
- [x] Documentation strategy defined (docstrings for all ports/use cases, inline comments for token trimming logic)
- [x] Code review process established (existing PR workflow)

**Testing Standards**:
- [x] Test strategy defined:
  - **Unit**: Token counting, turn trimming algorithm, UUID validation
  - **Integration**: Conversation repository CRUD, atomic turn persistence
  - **E2E**: Multi-turn query flow, history context retention, token budget enforcement
- [x] Coverage targets: 80% minimum (existing standard), 100% for token trimming logic
- [x] Test-first approach: conversation repository tests before implementation

**User Experience Consistency** (API-only feature):
- [x] RESTful design confirmed (extend existing `/api/v1/query` endpoint)
- [x] Error handling designed (404 for invalid conversation_id, 500 for failures)
- [x] Consistent JSON responses (follow existing `{success, data/error}` pattern)
- [N/A] UI concerns (backend API only)

**Performance Requirements**:
- [x] Performance targets defined (history retrieval <100ms, token counting <50ms)
- [x] Database query strategy planned (indexes on conversation_id and created_at)
- [N/A] Asset optimization (backend only)
- [x] Scalability considerations: SQLite adequate for v1; future migration to PostgreSQL if needed

**Architecture & Tech Stack** (Hexagonal):
- [x] Ports defined: `ConversationRepositoryPort`, `TokenCounterPort` (reuse existing)
- [x] Adapters planned: `SQLiteConversationRepository`
- [x] Domain entities: `Conversation`, `ConversationTurn`
- [x] Use case: Enhanced `RAGService.query()` to accept `conversation_id`

**Zero-Cost Constraints**:
- [x] No new paid dependencies (reuse SQLite, tiktoken)
- [x] Local storage only
- [x] No quota impact (history reduces Gemini token usage by avoiding repetition)

**Testing & AI Engineering**:
- [x] Token tracking: log token counts per turn
- [x] Golden dataset tests: verify follow-up context retention
- [x] Error handling: atomic rollback on failure

## Constitution Check: PASSED ✅

**No violations.** Feature aligns with existing hexagonal architecture, zero-cost constraints, and async-first principles.

## Project Structure

### Documentation (this feature)

```text
specs/003-conversation-context/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (PENDING)
├── data-model.md        # Phase 1 output (PENDING)
├── quickstart.md        # Phase 1 output (PENDING)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/courseflow/
├── domain/                    # Core business logic (existing)
│   ├── models.py              # ADD: Conversation, ConversationTurn entities
│   ├── ports.py               # ADD: ConversationRepositoryPort
│   └── exceptions.py          # ADD: ConversationNotFoundError
├── application/               # Use cases (existing)
│   └── rag_service.py         # MODIFY: Accept conversation_id, include history in prompt
├── infrastructure/            # Adapters (existing)
│   ├── repositories/
│   │   └── conversation_repo.py  # ADD: SQLiteConversationRepository
│   └── token_counting/
│       └── tiktoken_counter.py   # REUSE: Existing token counter
├── api/                       # FastAPI routes (existing)
│   ├── routes/query.py        # MODIFY: Accept optional conversation_id in request schema
│   └── dependencies.py        # MODIFY: Wire conversation repository
└── config.py                  # Existing settings

scripts/migrations/
└── 003_add_conversation_tables.sql  # ADD: conversations + conversation_turns tables

tests/
├── unit/
│   └── domain/
│       └── test_conversation_trimming.py  # ADD: Token budget tests
├── integration/
│   └── test_conversation_repository.py    # ADD: Repository CRUD tests
└── e2e/
    └── test_multi_turn_query.py          # ADD: Full conversation flow tests
```

**Structure Decision**: Single project structure (existing). Conversation feature extends domain, application, and infrastructure layers following hexagonal architecture. No new top-level directories required.

## Complexity Tracking

> **No violations to justify.** Feature fits cleanly into existing architecture.

---

## Phase 0: Research & Unknowns (NEXT)

**Resolved in next section.**
