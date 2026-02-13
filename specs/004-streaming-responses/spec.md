# Feature Specification: Streaming Responses via Server-Sent Events

**Feature Branch**: `004-streaming-responses`  
**Created**: 2026-02-13  
**Status**: Draft  
**Input**: User description: "Streaming Responses via Server-Sent Events (SSE)"

## Clarifications

### Session 2026-02-13

- **Q1: No Relevant Documents Handling** → A: When retrieval returns no chunks above the similarity threshold (0.7), the system emits a single SSE error event with type "no_relevant_documents" and does NOT call the LLM or save to conversation history (preserves quota and prevents hallucination).
- **Q2: Empty/Whitespace Query Validation** → A: Empty or whitespace-only queries trigger an HTTP 400 Bad Request with message "Query cannot be empty or whitespace-only" before streaming begins (early validation, cleaner error handling).
- **Q3: Rate Limiting Mid-Stream** → A: If rate limiting occurs after streaming has started, immediately emit SSE error event with `error: "rate_limit_exceeded"` and close the stream; do NOT attempt internal retry once chunks have been sent (prevents duplicate chunks, undefined behavior).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Feedback on AI Response (Priority: P1)

As a learner, I want to see the AI's answer appear word-by-word as it's generated, rather than waiting for the complete response, so that I receive immediate feedback that the system is processing my question and can start reading the answer sooner.

**Why this priority**: This is the core value proposition. Without progressive text display, the feature delivers no user benefit—the experience feels like a frozen request until completion. P1 because streaming is meaningless if chunks don't arrive incrementally.

**Independent Test**: User can initiate a query via the streaming endpoint, receive the first answer fragment within 1 second, and continue receiving answer text incrementally without waiting for the full response to complete.

**Acceptance Scenarios**:

1. **Given** a valid query is sent to the streaming endpoint, **When** processing begins, **Then** the first chunk of the answer arrives within 1 second
2. **Given** the AI is generating an answer, **When** chunks arrive, **Then** each chunk contains only a portion of the complete answer (not the full response at once)
3. **Given** answer generation is in progress, **When** subsequent chunks arrive, **Then** they appear continuously until generation completes

---

### User Story 2 - Reliable Streaming with Error Recovery (Priority: P2)

As a learner, I want errors during answer generation to be communicated clearly (not silently dropped), so that I understand when something went wrong and why I'm not getting an answer.

**Why this priority**: Users need confidence that failed requests are reported, not silently abandoned. If a request fails mid-stream, the system must communicate the failure transparently.

**Independent Test**: When the AI service is temporarily unavailable (e.g., rate-limited), the system sends an error notification via the stream, closes cleanly, and does not leave the client hanging.

**Acceptance Scenarios**:

1. **Given** the AI service returns a temporary error (e.g., rate limit), **When** streaming is in progress, **Then** an error event is sent to the client (not an HTTP 500 response)
2. **Given** a network interruption occurs during streaming, **When** the connection drops, **Then** the stream closes gracefully without leaving the client in an ambiguous state
3. **Given** an error is sent to the client, **When** the error is received, **Then** it includes the error type (e.g., "rate_limit_exceeded") and a human-readable message

---

### User Story 3 - Conversation History Integration (Priority: P2)

As a learner, I want my streamed questions and answers to be saved to my conversation history (whether or not I'm actively managing conversation IDs), so that I can review my past interactions and continue learning from them later.

**Why this priority**: Streaming is a new interface to the same RAG system; learners expect conversation continuity. However, streaming must work standalone (conversation_id optional), so this is P2 (not required for MVP).

**Independent Test**: A streaming query (with or without an existing conversation_id) results in the question and answer being saved to conversation history automatically, visible in subsequent conversation retrievals.

**Acceptance Scenarios**:

1. **Given** a streaming query is requested without a conversation_id, **When** the stream completes successfully, **Then** a new conversation is created and the turn is saved
2. **Given** a streaming query is requested with a valid conversation_id, **When** the stream completes, **Then** the turn is appended to that conversation
3. **Given** a stream completes with a full answer, **When** the conversation is queried later, **Then** the complete answer (reconstructed from all chunks) is retrievable

---

### Edge Cases

- **Empty Query**: Empty or whitespace-only queries MUST be rejected with HTTP 400 Bad Request before streaming begins; message: "Query cannot be empty or whitespace-only"
- **Very Long Answer**: What happens if the AI generates an answer longer than reasonable (>10,000 words)?
- **No Relevant Documents**: If the retrieval phase finds no documents above the similarity threshold (0.7), the system emits an error event (`{"type": "error", "error": "no_relevant_documents", "message": "No relevant content found..."}`) and does NOT call the LLM or save to conversation history. This preserves quota and prevents hallucination.
- **Rate Limiting Mid-Stream**: If the AI service rate-limits the request while chunks are being sent, the system immediately emits an SSE error event with `error: "rate_limit_exceeded"` and closes the stream cleanly without attempting internal retry (prevents duplicate chunks, undefined behavior).
- **Concurrent Requests**: If the same learner sends multiple streaming queries simultaneously, does the system handle them independently?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new streaming endpoint (`POST /api/v1/query/stream`) that accepts the same query input as the non-streaming endpoint
- **FR-001a**: System MUST validate that the query is non-empty and not whitespace-only; if validation fails, return HTTP 400 Bad Request with message "Query cannot be empty or whitespace-only"
- **FR-002**: System MUST retrieve relevant documents using the same RAG pipeline as the non-streaming endpoint; if no documents have a similarity score above 0.7, proceed to FR-002a instead
- **FR-002a**: System MUST emit an SSE error event with `error: "no_relevant_documents"` and human-readable message, then close the stream cleanly without calling the LLM or saving to conversation history
- **FR-003**: System MUST stream the AI-generated answer to the client as text chunks, with each chunk sent as soon as it is available
- **FR-004**: System MUST include source documents (the retrieved documents used to generate the answer) in a structured event sent **after** answer generation completes
- **FR-005**: System MUST signal the end of the stream with a completion event after all answer content and sources have been sent
- **FR-006**: System MUST communicate errors (e.g., rate limiting, service unavailability) via a structured error event **within the stream** rather than terminating the connection abruptly
- **FR-006a**: If rate limiting occurs after streaming has started (mid-stream), system MUST emit an SSE error event with `error: "rate_limit_exceeded"` immediately and close the stream; system MUST NOT attempt internal retry once chunks have been sent
- **FR-007**: System MUST support an optional `conversation_id` parameter; if provided, the completed query and answer MUST be saved to that conversation; if not provided, a new conversation MUST be created
- **FR-008**: System MUST save the user's query to conversation history **regardless of whether streaming succeeds or fails**, EXCEPT when the error is a retrieval failure (no relevant documents) or input validation failure (empty query)
- **FR-009**: System MUST save the AI-generated answer to conversation history **only if** generation completes fully OR if a timeout occurs with partial content generated
- **FR-010**: System MUST NOT save the answer if the AI service returns an error before generating any content (e.g., rate limit hit immediately) or if retrieval fails (no_relevant_documents)
- **FR-011**: System MUST implement client-side retry logic for temporary service failures (e.g., rate limiting encountered during initial request) using exponential backoff strategy
- **FR-012**: System MUST enforce a 30-second maximum timeout for the entire streaming operation (retrieval + generation); if exceeded, close the stream cleanly
- **FR-013**: The non-streaming endpoint (`POST /api/v1/query`) MUST continue to function identically to its behavior before this feature is added
- **FR-014**: System MUST log all streaming requests with request ID and final status (success, timeout, error) for observability

### Key Entities

- **Query**: The user's question (non-empty, non-whitespace), with optional `conversation_id` for resuming/extending a conversation
- **Document**: Retrieved documents (same entity as non-streaming RAG), with similarity scores
- **Answer**: The LLM-generated response, transmitted as a sequence of chunks
- **ConversationTurn**: A saved question-answer pair, now including streaming metadata (completion_status, timeout_flag)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: First answer chunk arrives within 1 second of request (measured as time from request submission to receipt of first chunk event)
- **SC-002**: Subsequent chunks arrive continuously with no gaps longer than 2 seconds between events
- **SC-003**: 100% of successfully completed streams include a sources event followed by a done event
- **SC-004**: 100% of error scenarios (rate limit, network failure, timeout, no relevant documents) emit an error event and close the stream without HTTP 5xx errors
- **SC-005**: Streaming endpoint handles at least 10 concurrent streaming queries without degradation (no dropped chunks, no queue buildup)
- **SC-006**: 100% of completed streaming queries with conversation_id have the full answer saved to conversation history within 2 seconds of stream completion
- **SC-007**: 100% of non-streaming queries continue to return complete answers in the same time as before the feature was added (no regression)
- **SC-008**: 100% of empty or whitespace-only queries return HTTP 400 within 100ms (before streaming begins)
- **SC-009**: When rate limiting occurs after streaming has started, SSE error event is emitted within 500ms with error code and message; no duplicate chunks are sent

### Performance & UX Targets

- **Streaming Latency**: First token < 1 second; subsequent tokens within 2 seconds of each other
- **Input Validation**: Empty query rejection < 100ms
- **Error Detection & Reporting**: Rate limit detection mid-stream < 500ms
- **Resource Usage**: Streaming connection does not increase server memory per request beyond non-streaming baseline (streaming uses iterators/generators, not buffering)
- **Error Clarity**: Error events include machine-readable error code and human-readable description
- **Backward Compatibility**: Non-streaming endpoint returns identical responses to pre-feature versions

## Assumptions

1. **Retrieval is non-streamed**: Document retrieval completes fully before streaming begins (fast), so users see consistent sources in the sources event
2. **Similarity threshold is 0.7**: Documents must score above this threshold to be considered relevant; retrieval returning no documents above this threshold triggers no_relevant_documents error
3. **Conversation history is synchronous**: Saving a completed turn to SQLite is fast enough (<2s) not to block the stream close
4. **Error events close the stream**: After an error event is sent, the stream is terminated; the client does not expect further events
5. **Chunk size is small**: Individual chunks are small enough (<1KB) to transmit instantly; no micro-buffering is applied
6. **Client retry is out-of-scope for mid-stream**: The streaming endpoint does not support resumption mid-stream; client retries start a new request from scratch; client-side retry logic (FR-011) applies to initial request failures, not mid-stream errors
7. **No streaming for ingestion**: Document ingestion (`POST /api/v1/ingest`) remains synchronous; only question answering is streamed
8. **Conversation context is optional**: The streaming endpoint does not require an existing conversation; it can initialize new conversations on-the-fly
9. **Hallucination prevention**: When retrieval fails, the system does not attempt to generate answers, preserving hallucination-free responses per constitution Section III
10. **Input validation is lightweight**: Query validation (empty check) happens in-process before pipeline submission; whitespace is trimmed per standard REST practices
11. **No internal retry mid-stream**: Once streaming has started (first chunk sent), the system does not attempt transparent internal retries; all errors are immediately communicated to the client

## Out of Scope

- WebSocket support (SSE is sufficient for one-directional streaming)
- Client-side SDKs or libraries
- Resumable streams (reconnection from last token)
- Streaming for document ingestion or other non-query operations
- Real-time collaboration or multi-user streaming to the same query
- Internal retry logic for errors occurring after streaming has started
