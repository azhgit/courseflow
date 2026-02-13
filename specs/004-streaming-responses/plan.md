# Implementation Plan: Streaming Responses via Server-Sent Events

**Branch**: `004-streaming-responses` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/004-streaming-responses/spec.md`

## Summary

Implement Server-Sent Events (SSE) streaming endpoint (`POST /api/v1/query/stream`) for RAG question answering. The system retrieves documents from ChromaDB, streams LLM response chunks from Gemini 1.5 Flash via FastAPI `StreamingResponse`, and persists completed turns to SQLite conversation history. All errors (no relevant documents, rate limits, timeouts) are emitted as SSE events without HTTP 5xx responses. Non-streaming endpoint remains unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (async/await, improved type hints)  
**Primary Dependencies**:
- FastAPI 0.109+ (streaming via `StreamingResponse`)
- httpx (async HTTP client for Gemini streaming)
- Pydantic (request/response validation)
- ChromaDB 0.4.22+ (vector store, cosine similarity)
- aiosqlite (async SQLite adapter)
- Google Gemini 1.5 Flash API (streaming: `generate_content(stream=True)`)

**Storage**: SQLite (`./data/courseflow.db`) for conversation history; ChromaDB (`./data/chroma`) for vectors  
**Testing**: pytest + pytest-asyncio + pytest-cov (unit, integration, e2e RAG streaming tests)  
**Target Platform**: Linux/macOS server (FastAPI async application)  
**Project Type**: Web backend (API-only, no UI)  
**Performance Goals**:
- First token <1 second (SC-001)
- Subsequent chunks <2 seconds apart (SC-002)
- 10 concurrent streams without degradation (SC-005)
- p95 RAG latency <2 seconds total (constitution)

**Constraints**:
- 30-second maximum stream duration (FR-012)
- Rate limiting: 15 RPM, 1500/day (Gemini free tier)
- No internal retry mid-stream (FR-006a, clarification Q3)
- Similarity threshold: 0.7 (clarification Q1)
- Input validation before streaming (clarification Q2)

**Scale/Scope**: Single-user API; 10+ concurrent streams support

## Constitution Check

✅ **Code Quality**:
- Streaming handler function + SAE event formatter → <50 lines each
- Integration with existing hexagonal architecture
- Clear separation: route handler (FastAPI) → application layer (RAG service) → infrastructure (Gemini, SQLite adapters)
- Documentation via docstrings (Google style) for public APIs

✅ **Testing Standards**:
- Unit tests: SSE event formatter (mocks Gemini), retrieval failure paths
- Integration tests: Streaming endpoint + SQLite persistence, error event serialization
- E2E: Golden dataset queries streamed end-to-end, verify chunk sequences
- Coverage target: 80% (streaming handler, error paths)

✅ **Performance Requirements**:
- Latency targets: <1s first token, <2s gaps between chunks
- No buffering: stream chunks immediately (Assumption 4 from spec)
- Database indexing: `conversation_id`, `query_id` for fast lookups
- Scalability: Async/await + generators handle concurrent streams without memory buildup

✅ **AI Engineering Standards** (Constitution Section III):
- Error handling: 429 rate limit → emit SSE error event, no retry mid-stream (FR-006a)
- Token logging: Every streaming request logs total tokens at completion
- Hallucination prevention: No LLM call when retrieval finds no docs (FR-002a, clarification Q1)
- Rate limiting: 15 RPM enforced client-side; block requests if exceeded

✅ **Architecture** (Constitution Section IV):
- Hexagonal: Domain (Query, Answer models) → Application (RAG service) → Infrastructure (Gemini streaming, SQLite)
- Dependency injection: FastAPI `Depends()` for service lifecycle
- Async-first: All I/O operations (Gemini API, DB, SSE) use async/await
- Type safety: Pydantic models for SSE events, type hints on all functions

## Architecture Design Decision

**Streaming Pattern**: FastAPI `StreamingResponse` with async generator
- **Why**: Native to FastAPI, built-in SSE support, no external libraries needed
- **Alternative considered**: Manual response objects (more control, higher complexity) ❌
- **Alternative considered**: WebSockets (bidirectional, overkill for one-way streaming) ❌

**Error Handling**: SSE error events (no HTTP 5xx)
- **Why**: Client expects streaming semantics; HTTP error codes break stream contract
- **Alternative**: Return HTTP 500 with partial response (violates spec FR-006) ❌

**Persistence Strategy**: Async save after stream ends
- **Why**: Non-blocking, doesn't delay stream close (Assumption 3)
- **Alternative**: Sync save in background task (introduces concurrency issues) ❌

**Rate Limiting**: Block at route level before retrieval starts
- **Why**: Early validation, prevents unnecessary pipeline execution
- **Alternative**: Block during LLM call (wastes retrieval bandwidth) ❌

## Project Structure

### Documentation (this feature)

```
specs/004-streaming-responses/
├── spec.md              # Feature specification (DONE)
├── checklists/          # Quality validation artifacts
│   └── requirements.md  # Specification quality checklist (DONE)
├── plan.md              # This file (IN PROGRESS)
├── research.md          # Phase 0 output (TBD)
├── data-model.md        # Phase 1 output (TBD)
├── quickstart.md        # Phase 1 output (TBD)
└── contracts/           # Phase 1 output - API contracts (TBD)
    ├── streaming-query.openapi.yml
    └── sse-events.schema.json
```

### Source Code (repository root)

```
src/courseflow/
├── api/
│   ├── routes/
│   │   ├── query.py     # MODIFIED: Add POST /api/v1/query/stream route
│   │   └── ...
│   └── dependencies.py  # No changes (reuse existing DI)
├── application/
│   ├── rag_service.py   # MODIFIED: Add stream_query() method + error handling
│   └── ...
├── infrastructure/
│   ├── llm/
│   │   ├── gemini.py    # MODIFIED: Add stream() method for Gemini streaming
│   │   └── ...
│   ├── repositories/
│   │   ├── query_repo.py # MODIFIED: Add save_streaming_turn() for conversation persistence
│   │   └── ...
│   └── ...
├── domain/
│   ├── models.py        # MODIFIED: Add StreamingQuery, SSEEvent models
│   └── exceptions.py    # No changes (reuse existing exception types)
└── ...

tests/
├── unit/
│   ├── test_sse_formatter.py          # NEW: SSE event formatting
│   ├── test_streaming_validation.py   # NEW: Empty query, no-docs handling
│   └── ...
├── integration/
│   ├── test_streaming_endpoint.py     # NEW: E2E streaming with mocks
│   └── ...
└── e2e/
    └── test_streaming_rag_flow.py     # NEW: Golden dataset streaming tests
```

## Dependencies & Versions

All dependencies already in project (from feature 003-conversation-context):
- ✅ FastAPI 0.109+
- ✅ httpx (async HTTP)
- ✅ Pydantic
- ✅ ChromaDB 0.4.22+
- ✅ aiosqlite
- ✅ Google Gemini API (client library)

**No new dependencies required** ✅

## Phase 0: Research

### Unknowns Resolved

**Q1: Gemini Streaming API**
- **Resolution**: Gemini SDK supports `generate_content(stream=True)` returning iterator
  - Returns `GenerateContentResponse` objects (partial content)
  - Each chunk contains `.text` attribute
  - Handles buffering automatically
  - Token counting available in final response
- **API Syntax**: `response = model.generate_content(content, stream=True)`
- **Link**: [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)

**Q2: FastAPI Streaming Response**
- **Resolution**: `StreamingResponse` accepts async generator yielding byte strings
  - Sets `Content-Type: text/event-stream`
  - Handles SSE protocol automatically (no manual `data:` prefix needed)
  - Can set custom headers (Cache-Control, X-Accel-Buffering)
- **API Syntax**: `return StreamingResponse(async_generator, media_type="text/event-stream")`
- **Link**: [FastAPI Streaming Responses](https://fastapi.tiangolo.com/advanced/response-streams/)

**Q3: SSE Event Format**
- **Resolution**: Standard SSE format: `data: {json}\n\n`
  - Must be newline-delimited (two newlines after data)
  - JSON should be single-line (no embedded newlines in data field)
  - Can include `id`, `event`, `retry` fields (optional)
- **API Syntax**: `f"data: {json.dumps(event)}\n\n"`
- **Link**: [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

**Q4: Async SQLite Persistence**
- **Resolution**: aiosqlite already integrated (from feature 003)
  - `INSERT` and `UPDATE` via `await cursor.execute()`
  - No blocking; non-blocking background saves can use `asyncio.create_task()`
- **API Syntax**: `await conn.execute("INSERT ...", params); await conn.commit()`
- **Link**: [aiosqlite Documentation](https://aiosqlite.omreq.dev/)

## Phase 0 Deliverables

✅ **research.md** (complete above, no ambiguities)

---

## Phase 1: Design & Contracts

### Data Model

**Entities**:

1. **StreamingQuery** (Request)
   - `query: str` (non-empty, required)
   - `conversation_id: Optional[str]` (optional, creates new if null)

2. **SSEEvent** (Response - multiple variants)
   - **ChunkEvent**: `{"type": "chunk", "content": str}`
   - **SourcesEvent**: `{"type": "sources", "sources": List[str], "retrieval_count": int}`
   - **DoneEvent**: `{"type": "done", "conversation_id": str, "token_count": int}`
   - **ErrorEvent**: `{"type": "error", "error": str, "message": str, "retry_after": Optional[int]}`

3. **ConversationTurn** (updated from feature 003)
   - `query: str`
   - `answer: str` (reconstructed from chunks)
   - `sources: List[str]`
   - `completion_status: str` (success|timeout|error)
   - `timeout_flag: bool`
   - `token_count: int`

### API Contracts

**Streaming Query Endpoint**

```
POST /api/v1/query/stream
Content-Type: application/json

Request:
{
  "query": "Explain photosynthesis",
  "conversation_id": null
}

Response:
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no

data: {"type": "chunk", "content": "Photosynthesis"}
data: {"type": "chunk", "content": " is the process"}
...
data: {"type": "sources", "sources": ["biology-photosynthesis.md"], "retrieval_count": 3}
data: {"type": "done", "conversation_id": "conv_abc123", "token_count": 285}
```

**Error Event Example**

```
POST /api/v1/query/stream
(no relevant documents found)

HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"type": "error", "error": "no_relevant_documents", "message": "No relevant content found. Try rephrasing."}
```

**Rate Limit Error (with retry)**

```
data: {"type": "error", "error": "rate_limit_exceeded", "message": "Gemini API quota exceeded (15 RPM). Retry after 60 seconds.", "retry_after": 60}
```

### Quickstart

1. **Send streaming query**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/query/stream \
     -H "Content-Type: application/json" \
     -d '{"query": "What is async/await?", "conversation_id": null}' \
     -N  # Unbuffered output
   ```

2. **Receive SSE stream**:
   ```
   data: {"type": "chunk", "content": "Async/await"}
   data: {"type": "chunk", "content": " is a syntactic sugar"}
   ...
   data: {"type": "sources", "sources": ["python-async.md"], "retrieval_count": 5}
   data: {"type": "done", "conversation_id": "conv_xyz", "token_count": 342}
   ```

3. **Handle errors in client**:
   ```javascript
   const eventSource = new EventSource('/api/v1/query/stream');
   eventSource.onmessage = (e) => {
     const event = JSON.parse(e.data);
     if (event.type === 'chunk') {
       console.log(event.content); // Append to answer
     } else if (event.type === 'error') {
       console.error(`${event.error}: ${event.message}`);
       eventSource.close();
     }
   };
   ```

## Phase 1 Completion: Key Decisions

**Decisions Matrix**:

| Area | Decision | Rationale | Alternatives |
|------|----------|-----------|--------------|
| **Streaming Pattern** | FastAPI StreamingResponse + async generator | Native support, minimal dependencies | Manual response, WebSockets (overkill) |
| **SSE Formatting** | JSON lines (`data: {...}\n\n`) | Standard SSE protocol, JSON-parseable | JSONL (no event types), XML (verbose) |
| **Error Handling** | SSE error events (not HTTP 500) | Maintains stream semantics, client-facing error clarity | HTTP status codes (breaks streaming contract) |
| **Chunk Emission** | Immediate (no buffering) | Meets <1s first token requirement | Micro-buffering (adds latency) |
| **Persistence** | Async save after stream ends | Non-blocking, meets <2s save target | Sync save (blocks response), background task (concurrency issues) |
| **Rate Limit Response** | Block at route level, emit error event | Early validation, prevents wasted retrieval | Block during LLM call (wastes bandwidth) |

---

## Next Steps

1. ✅ Phase 0: Research (DONE)
2. ✅ Phase 1: Design & Contracts (DONE)
3. → **Run `/speckit.tasks`** to generate actionable tasks from this plan
4. → **Run `/speckit.implement`** to execute tasks and build the feature

---

## Technical Debt & Future Considerations

- **Very Long Answers** (>10k words): Implement truncation or chunking strategy (deferred, low priority)
- **Observability Metrics** (FR-014): Define specific metrics dashboard (deferred to operational phase)
- **Concurrent Request Isolation**: Per-user rate limiting (future enhancement if multi-user)
- **Client Reconnection**: Resumable streams via checkpointing (explicitly out-of-scope per spec)

