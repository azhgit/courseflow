# Tasks: Streaming Responses via Server-Sent Events

**Input**: Design documents from `/specs/004-streaming-responses/`  
**Dependencies**: Spec (3 user stories, P1/P2/P2), Plan (hexagonal architecture, FastAPI streaming), Constitution (code quality, testing, AI engineering standards)

**Constitution Compliance**: All tasks align with constitution principles:
- ✅ Code Quality: Functions <50 lines, files <500 lines, documented code
- ✅ Testing Standards: 80% coverage minimum (unit + integration + e2e)
- ✅ AI Engineering: Token logging, rate limit handling, hallucination prevention
- ✅ Performance: <1s first token, <2s chunk gaps, 10 concurrent streams
- ✅ Async-First: All I/O operations (Gemini, DB, SSE) use async/await

**MVP Scope** (User Story 1 only):
- Streaming endpoint that delivers chunks incrementally
- Real-time feedback on AI response
- Tests: Latency, chunk delivery order, integration with existing RAG pipeline

---

## Implementation Strategy

### Phase Breakdown

1. **Phase 1 (Setup)**: Project structure and shared infrastructure (0 tasks - reuse existing from feature 003)
2. **Phase 2 (Foundational)**: SSE event models, error handling middleware, rate limiting wrapper
3. **Phase 3 (US1 - P1)**: Streaming query endpoint + chunk delivery (MVP)
4. **Phase 4 (US2 - P2)**: Error event handling and recovery paths
5. **Phase 5 (US3 - P2)**: Conversation persistence for streaming queries
6. **Phase 6 (Polish)**: Logging, testing, backward compatibility validation

### Parallelization Opportunities

- **[P] Tasks**: Different files, no blocking dependencies
  - Models (domain) can be written in parallel with service layer
  - Tests can be written in parallel with implementation
  - Error handlers can be implemented in parallel with main endpoint

### Dependencies Graph

```
Phase 1: Setup (DONE - feature 003)
  ↓
Phase 2: Foundational
  ├─ StreamingQuery + SSEEvent models
  ├─ Rate limiter configuration
  └─ Timeout handler
  ↓
Phase 3: US1 (Real-Time Feedback) ← MVP GATE
  ├─ Query stream route
  ├─ Gemini streaming adapter
  ├─ Chunk formatter
  └─ Integration tests
  ↓
Phase 4: US2 (Error Recovery)
  ├─ Error event types
  ├─ No-relevant-docs handler
  ├─ Rate-limit error handler
  └─ Timeout error handler
  ↓
Phase 5: US3 (Conversation Persistence)
  ├─ ConversationTurn schema updates
  ├─ Conversation save service
  └─ Persistence tests
  ↓
Phase 6: Polish
  ├─ Logging + observability
  ├─ Backward compatibility tests
  └─ E2E golden dataset tests
```

---

## Phase 1: Setup (Shared Infrastructure)

**Status**: ✅ COMPLETE (from feature 003-conversation-context)

No additional setup required. Reusing:
- FastAPI 0.109+ with async support
- ChromaDB 0.4.22+ vector store
- SQLite with aiosqlite
- Existing rate limiter
- Existing conversation repository

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and infrastructure for streaming

**⚠️ CRITICAL**: Must complete before ANY user story work begins

### Tests for Phase 2 (OPTIONAL - writing tests first per TDD)

- [ ] T001 [P] Unit test for StreamingQuery validation in tests/unit/test_models_streaming.py (empty query should raise error)
- [ ] T002 [P] Unit test for SSEEvent serialization in tests/unit/test_models_streaming.py (chunk, sources, done, error events format correctly)

### Implementation for Phase 2

- [ ] T003 [P] Create StreamingQuery and SSEEvent Pydantic models in src/courseflow/domain/models.py
  - StreamingQuery: query (str, non-empty), conversation_id (Optional[str])
  - ChunkEvent, SourcesEvent, DoneEvent, ErrorEvent Pydantic models
  - Validation: query stripped and non-empty (FR-001a)

- [ ] T004 [P] Create SSE event formatter utility in src/courseflow/infrastructure/sse.py
  - Function: `format_chunk(content: str) -> str` → JSON + newlines per SSE spec
  - Function: `format_sources(sources: List[str], retrieval_count: int) -> str`
  - Function: `format_done(conversation_id: str, token_count: int) -> str`
  - Function: `format_error(error: str, message: str, retry_after: Optional[int] = None) -> str`
  - All functions return SSE-formatted strings (data: {...}\n\n)

- [ ] T005 Create stream timeout context manager in src/courseflow/application/streaming_service.py
  - Class: StreamingContext(query_id, timeout_seconds=30)
  - Tracks elapsed time, raises TimeoutError if exceeded
  - Used to wrap entire stream_query() execution

- [ ] T006 Extend rate limiter in src/courseflow/application/rate_limiter.py (if not already 30-second aware)
  - Add method: `start_streaming_request() -> bool` (returns False if rate limit hit)
  - Tracks per-request timeout (30s max) alongside RPM limits
  - Emits rate limit error if attempted mid-stream

**Checkpoint**: Foundational models and utilities ready

---

## Phase 3: User Story 1 - Real-Time Feedback on AI Response (Priority: P1) 🎯 MVP

**Goal**: Learner sees AI answer appear word-by-word; first token within 1 second

**Independent Test**: Send a valid query to `/api/v1/query/stream`, receive first chunk event within 1 second, chunks continue arriving until sources event and done event

**Metrics**:
- SC-001: First token <1 second
- SC-002: Chunks <2 seconds apart
- SC-003: 100% streams end with sources + done events

### Tests for US1 (TDD-first)

- [ ] T007 [P] Contract test for POST /api/v1/query/stream in tests/contract/test_streaming_query.py
  - Valid query {"query": "test", "conversation_id": null}
  - Response Content-Type: text/event-stream
  - First event arrives within 1 second
  - Events are valid JSON

- [ ] T008 [P] Unit test for chunk event formatting in tests/unit/test_sse_formatter.py
  - format_chunk("Async") → 'data: {"type": "chunk", "content": "Async"}\n\n'

- [ ] T009 [P] Integration test for streaming query with mocked Gemini in tests/integration/test_streaming_endpoint.py
  - Mock Gemini stream: chunk stream returns 5 chunks
  - Verify all 5 chunks received as SSE events
  - Verify sources and done events sent
  - Verify timing: first chunk <1s, gaps <2s

- [ ] T010 [P] E2E test with golden dataset query in tests/e2e/test_streaming_golden.py
  - Query: "Explain photosynthesis" (should retrieve docs from biology knowledge base)
  - Verify chunks, sources, and done events
  - Verify answer reconstructed from chunks matches non-streaming answer

### Implementation for US1

- [ ] T011 [P] Extend Gemini LLM client in src/courseflow/infrastructure/llm/gemini.py
  - Add async method: `stream(prompt: str) -> AsyncGenerator[str, None]`
  - Uses Gemini SDK's `generate_content(stream=True)`
  - Yields only `.text` content from each chunk (filters empty chunks)
  - Logs token count at end

- [ ] T012 Add stream_query() method to RAG service in src/courseflow/application/rag_service.py
  - Signature: `async def stream_query(query: StreamingQuery) -> AsyncGenerator[str, None]`
  - Step 1: Validate query (non-empty) → raise ValidationError if fails
  - Step 2: Retrieve documents (same as non-streaming) using ChromaDB
  - Step 3: Check if retrieval found docs; if not, delegate to error handler (Task T017 - dependency)
  - Step 4: Build prompt with retrieved context
  - Step 5: Call `self.llm.stream(prompt)` and yield chunks
  - Step 6: Track completion status (success, timeout, error) for persistence (Task T024)
  - All yields are already SSE-formatted (from T004)

- [ ] T013 Create streaming query route in src/courseflow/api/routes/query.py
  - New endpoint: `POST /api/v1/query/stream`
  - Request model: StreamingQuery (from T003)
  - Validation: Check if query is empty → return 400 (FR-001a, clarification Q2)
  - Check rate limit → return 429 if exceeded (not SSE error at validation stage)
  - Call `rag_service.stream_query(query)` → async generator
  - Wrap generator with timeout (30s, Task T005)
  - Return FastAPI `StreamingResponse(generator, media_type="text/event-stream")`
  - Headers: Cache-Control: no-cache, X-Accel-Buffering: no

**Milestone**: MVP endpoint streaming chunks to client ✅

---

## Phase 4: User Story 2 - Reliable Streaming with Error Recovery (Priority: P2)

**Goal**: Errors during generation communicated clearly via SSE (not HTTP 5xx)

**Independent Test**: Trigger error scenario (no docs, rate limit mid-stream, timeout); verify error event sent with error code and message; stream closes cleanly

**Metrics**:
- SC-004: 100% errors emit SSE error event (no HTTP 5xx)
- SC-008: Empty query returns HTTP 400 within 100ms
- SC-009: Rate limit mid-stream detected <500ms

### Tests for US2

- [ ] T014 [P] Unit test for no-relevant-documents handler in tests/unit/test_error_handlers.py
  - Input: empty retrieval result
  - Output: 'data: {"type": "error", "error": "no_relevant_documents", "message": "..."}\n\n'

- [ ] T015 [P] Unit test for rate_limit_exceeded handler in tests/unit/test_error_handlers.py
  - Input: rate limit exception mid-stream
  - Output: error event with error code, message, retry_after

- [ ] T016 [P] Unit test for timeout handler in tests/unit/test_error_handlers.py
  - Input: TimeoutError after 30 seconds
  - Output: error event "stream_timeout" with human-readable message

- [ ] T017 Integration test for no-relevant-documents path in tests/integration/test_streaming_endpoint.py
  - Query: "xyz12345xyz" (should match no documents)
  - Verify HTTP 200 (not error code)
  - Verify single error event received (no LLM call, no chunks)

- [ ] T018 Integration test for rate limit mid-stream in tests/integration/test_streaming_endpoint.py
  - Mock Gemini: first chunk ok, second chunk raises RateLimitError
  - Verify error event sent within 500ms
  - Verify no duplicate chunks

- [ ] T019 Integration test for timeout in tests/integration/test_streaming_endpoint.py
  - Mock Gemini: stream takes >30 seconds
  - Verify timeout error event sent
  - Verify stream closed cleanly

### Implementation for US2

- [ ] T020 Create error handler for no relevant documents in src/courseflow/application/streaming_service.py
  - Function: `handle_no_relevant_documents() -> str`
  - Returns SSE error event: {"type": "error", "error": "no_relevant_documents", "message": "No relevant content found..."}
  - Called from stream_query() when retrieval returns empty (Task T012 dependency)

- [ ] T021 Create error handler for rate limit mid-stream in src/courseflow/application/streaming_service.py
  - Wraps Gemini stream iteration with try-except for RateLimitError (from googlee-generativeai)
  - Catches: google.api_core.exceptions.ResourceExhausted (429)
  - Returns SSE error event with error code, message, retry_after=60
  - Logs error with request_id for observability (Task T027)

- [ ] T022 Create error handler for timeout in src/courseflow/application/streaming_service.py
  - Wraps stream_query() with `StreamingContext(timeout_seconds=30)` (Task T005)
  - Catches TimeoutError
  - Returns SSE error event: {"type": "error", "error": "stream_timeout", "message": "..."}

- [ ] T023 Update stream_query() method in src/courseflow/application/rag_service.py (Task T012)
  - Integrate error handlers (T020, T021, T022)
  - Step 3.5: If retrieval empty → call handle_no_relevant_documents(), yield result, return
  - Wrap Gemini iteration in try-except for RateLimitError → call handle_rate_limit()
  - Wrap entire method with timeout → call handle_timeout()

**Milestone**: All error paths emit SSE events cleanly ✅

---

## Phase 5: User Story 3 - Conversation History Integration (Priority: P2)

**Goal**: Streaming queries saved to conversation history automatically

**Independent Test**: Stream a query without conversation_id; verify new conversation created and answer saved; retrieve conversation later and verify answer reconstructed from chunks

**Metrics**:
- SC-006: 100% completed streaming queries with conversation_id saved to history within 2 seconds
- FR-007, FR-008, FR-009: Query always saved; answer saved only on success/timeout-with-content

### Tests for US3

- [ ] T024 [P] Unit test for conversation turn reconstruction in tests/unit/test_conversation_persistence.py
  - Input: list of chunks ["Hello", " ", "world"]
  - Output: "Hello world" (reconstructed answer)

- [ ] T025 [P] Unit test for conversation turn model in tests/unit/test_models_streaming.py
  - ConversationTurn includes: query, answer, sources, completion_status, timeout_flag, token_count
  - completion_status: "success" | "timeout" | "error"

- [ ] T026 Integration test for conversation creation in tests/integration/test_streaming_conversation.py
  - Stream query without conversation_id
  - Verify done event contains new conversation_id
  - Query conversation history → verify turn saved with answer reconstructed

- [ ] T027 Integration test for conversation append in tests/integration/test_streaming_conversation.py
  - Create conversation via non-streaming endpoint (feature 003)
  - Stream query with that conversation_id
  - Query conversation history → verify turn appended to conversation

- [ ] T028 Integration test for query-only save on error in tests/integration/test_streaming_conversation.py
  - Stream query to "no relevant documents" error
  - Verify query NOT saved to conversation (per FR-008 exception)
  - Stream query that raises rate limit before any content
  - Verify query saved but answer NOT saved (per FR-009)

### Implementation for US3

- [ ] T029 Update ConversationTurn model in src/courseflow/domain/models.py (if not already)
  - Add fields: completion_status (str), timeout_flag (bool), token_count (int)
  - Reuse from feature 003 if already present

- [ ] T030 Create conversation persistence service in src/courseflow/application/streaming_service.py
  - Class: StreamingConversationService
  - Method: `async save_streaming_turn(query: str, chunks: List[str], sources: List[str], conversation_id: Optional[str], completion_status: str, token_count: int) -> str`
  - Reconstructs answer from chunks
  - Calls conversation_repository.save_turn() (reuse from feature 003)
  - Returns conversation_id (new or existing)
  - Handles: new conversation creation (conversation_id=null), existing conversation append

- [ ] T031 Update stream_query() in src/courseflow/application/rag_service.py
  - Track all chunks in memory as they're yielded
  - Track completion_status and token_count
  - After stream ends (sources event sent): call StreamingConversationService.save_streaming_turn()
  - Save asynchronously (non-blocking) to avoid delaying stream close
  - Use `asyncio.create_task()` to fire-and-forget persistence

- [ ] T032 Update done event handler in src/courseflow/api/routes/query.py (Task T013)
  - Receive conversation_id from stream context
  - Include in done event: {"type": "done", "conversation_id": "...", "token_count": ...}

**Milestone**: Streaming queries saved to conversation history ✅

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, testing, backward compatibility, documentation

### Tests for Cross-Cutting Concerns

- [ ] T033 [P] Backward compatibility test in tests/integration/test_backward_compat.py
  - Verify non-streaming endpoint (POST /api/v1/query) unchanged
  - Same response structure, same latency, same accuracy

- [ ] T034 [P] Golden dataset E2E test in tests/e2e/test_streaming_golden_full.py
  - 10+ golden Q&A pairs across multiple subjects (biology, programming, history)
  - Stream each query, verify answer contains expected keywords
  - Verify chunk sequence is logical (no out-of-order chunks)
  - Verify sources match retrieved documents

- [ ] T035 [P] Concurrency test in tests/integration/test_streaming_concurrency.py
  - Run 10 concurrent streaming queries
  - Verify no dropped chunks, no queue buildup
  - Verify all queries complete within 2 seconds

- [ ] T036 [P] Latency test in tests/integration/test_streaming_latency.py
  - Measure first token arrival time (should be <1 second)
  - Measure gaps between chunks (should be <2 seconds)
  - Measure total stream duration (should be <30 seconds)

### Implementation for Phase 6

- [ ] T037 Add structured logging to streaming routes in src/courseflow/api/routes/query.py
  - Log at request start: request_id, query, conversation_id
  - Log at each chunk: chunk_id, latency_ms (time since first chunk)
  - Log at stream end: final_status (success|timeout|error), total_latency_ms, token_count
  - Per FR-014

- [ ] T038 Add metrics emission in src/courseflow/application/streaming_service.py
  - Track: query_count, success_count, error_count, timeout_count
  - Track: first_token_latency_ms (histogram), chunk_gap_ms (histogram)
  - Expose via `/metrics` endpoint (reuse from existing application)

- [ ] T039 [P] Update project documentation in README.md and INGEST_API_GUIDE.md
  - Add new "Streaming Query" section to API guide
  - Example: curl to /api/v1/query/stream
  - Example: Client-side JavaScript event handling
  - Note: SSE format, error handling, retry strategy

- [ ] T040 Add CHANGELOG entry for feature 004
  - List new endpoint, new event types, breaking changes (none)
  - Link to spec and plan documents

### Final Validation

- [ ] T041 Run full test suite
  - pytest tests/ --cov=src/courseflow --cov-report=html
  - Verify coverage >80% (streaming code should be >85%)
  - Zero failing tests

- [ ] T042 Run linting and type checks
  - ruff check src/
  - mypy --strict src/
  - Zero errors

- [ ] T043 Manual smoke test
  - Start server: uvicorn src.courseflow.api.main:app --reload
  - Test streaming query: curl -X POST http://localhost:8000/api/v1/query/stream -H "Content-Type: application/json" -d '{"query": "Explain photosynthesis", "conversation_id": null}' -N
  - Verify chunks arrive incrementally
  - Verify sources and done events sent
  - Verify conversation saved (query POST /api/v1/conversations/{id})

- [ ] T044 Final review and merge
  - Code review checklist (constitution compliance)
  - Documentation complete
  - Tests passing
  - Performance targets met
  - Ready for deployment

---

## Summary

### Task Counts

- **Phase 1 (Setup)**: 0 tasks (reuse from 003)
- **Phase 2 (Foundational)**: 6 tasks (models, formatters, timeout, rate limiting)
- **Phase 3 (US1 - MVP)**: 10 tasks (endpoint, LLM streaming, tests)
- **Phase 4 (US2)**: 9 tasks (error handlers, tests)
- **Phase 5 (US3)**: 10 tasks (conversation persistence, tests)
- **Phase 6 (Polish)**: 8 tasks (tests, logging, documentation, validation)
- **TOTAL**: 43 tasks

### Task Distribution by Story

| User Story | Tasks | Priority | Status |
|-----------|-------|----------|--------|
| US1 (P1 - Real-Time Feedback) | T001-T013, T033-T034 | 🎯 MVP | 13 tasks |
| US2 (P2 - Error Recovery) | T014-T023 | 🔧 Core | 10 tasks |
| US3 (P2 - Conversation Persistence) | T024-T032 | 🔧 Core | 9 tasks |
| Foundational (Blocking) | T001-T006 | ⚠️ Required | 6 tasks |
| Polish & Cross-Cutting | T033-T044 | ✨ Quality | 12 tasks |

### MVP Scope (User Story 1)

**Recommendation**: Deploy MVP with US1 (Real-Time Feedback) only
- Implement: T001-T013 (endpoint, streaming, basic tests)
- Skip: US2 error handling, US3 persistence (add in v1.1)
- Result: Learners see AI answers appear word-by-word
- Estimated effort: 8-12 hours

### Full Feature Scope (All User Stories)

**Recommended for production**:
- US1 + US2 + US3 + Phase 6 polish
- All error paths handled, persistence working, golden dataset passing
- Estimated effort: 20-30 hours

### Parallel Execution Opportunities

Tasks that can run in parallel (marked [P]):

**Phase 2**:
- T001 + T002 (tests)
- T003 + T004 + T005 + T006 (models, utilities)

**Phase 3**:
- T007 + T008 + T009 + T010 (tests) can run before implementation
- T011 + T013 (different files) can run in parallel

**Phase 4**:
- T014 + T015 + T016 (error handler tests) can run in parallel
- T020 + T021 + T022 (error handler implementations) can run in parallel

**Phase 6**:
- T033-T036 (tests) can run in parallel
- T037-T039 (logging, metrics, docs) can run in parallel

---

## Dependencies

```
T001-T006 (Phase 2: Foundational)
  ↓
T007-T010 (Tests first - TDD approach)
  ↓
T011-T013 (US1 Implementation)
  ↓ [MVP GATE]
T014-T023 (US2 Implementation)
  ↓
T024-T032 (US3 Implementation)
  ↓
T033-T044 (Polish & Validation)
```

**MVP Deployment Gate**: After T013 passes all tests (T007-T010)

---

## Next Steps

1. ✅ Plan complete (`/speckit.plan`)
2. ✅ Tasks generated (`/speckit.tasks`)
3. → **Run `/speckit.implement`** to execute tasks in order
   - Start with Phase 2 (Foundational)
   - Then Phase 3 (US1 - MVP)
   - Optionally Phase 4-6 for full feature

---

## Notes for Implementer

- **Test-First Development**: Write tests (T001-T002, T007-T010, etc.) before implementation
- **Constitution Compliance**: All code must follow <50 line functions, clear separation, proper async/await usage
- **Golden Dataset**: Use existing 10-20 golden Q&A pairs from knowledge base for testing
- **Backward Compatibility**: Verify non-streaming endpoint untouched after each phase
- **Performance Monitoring**: Latency tests (T036) critical to ensure <1s first token target
- **Error Handling**: All errors must emit SSE events, never HTTP 5xx during streaming
- **Rate Limiting**: Respect Gemini free tier (15 RPM, 1500/day) enforced at route level
