# Specification: Multi-turn Conversation Support

**Feature**: Multi-turn Conversation Support  
**Branch**: 003-conversation-context  
**Status**: In Progress  
**Created**: 2026-02-13  

---

## Feature Overview

Enable learners to ask follow-up questions within the same conversation so the AI remembers context and learners don't repeat themselves across multiple queries.

### User Story

> As a learner, I want to ask follow-up questions within the same conversation so that the AI remembers what we discussed and I don't have to repeat context every time.

---

## Actors & Roles

- **Learner** (primary): Uses the query API to ask questions and expects follow-up context to be preserved within a conversation thread
- **System**: Manages conversation state, history, and LLM context window

## Clarifications

### Session 2026-02-13

- Q: How should the semantics of establishing a new conversation (omitting conversation_id vs. null) be defined? → A: Omitting fields or passing null both establish a new conversation and return the conversation_id.

- Q: What should the external format of conversation_id be? → A: Use a pure UUID4 string for both external and storage purposes, without using the `conv_` prefix.

- Q: How should the conversation turn be written to the database when LLM/retrieval fails? → A: Only atomically write the user+assistant turn after a successful assistant response; do not write any turn on failure.

---

## Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| FR-001 | Accept optional `conversation_id` parameter in query requests | When `conversation_id` is provided and valid, system retrieves existing conversation; when `null` or omitted, system creates new conversation |
| FR-002 | Generate and return conversation ID for new conversations | New conversation_id (UUID4) returned in response; persists across subsequent queries with same ID |
| FR-003 | Store conversation turns (user & assistant messages) | Each turn (role, content, timestamp, token_count) persisted in database; retrievable by conversation_id |
| FR-004 | Include conversation history in LLM context | Last 5 turns automatically included in LLM prompt as context; turns ordered chronologically |
| FR-005 | Enhance retrieval via history context | Follow-up questions like "What about error handling?" correctly reference prior question topics ("async functions") in document retrieval |
| FR-006 | Enforce token budget for history | Total tokens in history never exceed 2000 tokens; older turns trimmed first when budget exceeded |
| FR-007 | Retrieve historical conversations | Conversations retrievable by ID; old conversations accessible across application restarts |
| FR-008 | Maintain backward compatibility | Existing clients can omit `conversation_id` and still receive valid answer + sources; omission now creates a new conversation and returns `conversation_id` without breaking request compatibility |
| FR-009 | Validate conversation ID existence | Invalid or non-existent conversation_id returns 404 error with clear message; user directed to create new conversation |
| FR-010 | Prevent partial turn persistence on failed queries | If retrieval or generation fails, system persists neither user turn nor assistant turn; on success, both turns are persisted atomically |

---

## User Scenarios

### Scenario 1: New Conversation (Multi-turn)
```
Turn 1: Learner asks "How do async functions work in Python?"
  → System creates conversation_id: "550e8400-e29b-41d4-a716-446655440000"
  → Stores: role='user', content='How do async functions...', timestamp, token_count
  → LLM answers with sources ["python-async.md"]
  → Stores: role='assistant', content='Async functions use async def...', timestamp, token_count
  → Returns: answer, sources, conversation_id

Turn 2: Learner asks "What about error handling?" (same conversation_id)
  → System retrieves prior turns from conversation
  → Includes Turn 1 (question + answer) as context in LLM prompt
  → LLM generates answer referencing async context
  → Stores Turn 2 messages
  → Returns: answer with enhanced sources ["python-async.md", "python-exceptions.md"], conversation_id unchanged
```

### Scenario 2: History Trimming (Token Budget)
```
Given: Conversation with 10 turns already stored (~2500 tokens total)
When: Learner makes 11th query
Then:
  → System calculates history tokens = 2500 + new_query_tokens
  → Exceeds 2000 token budget
  → System removes oldest turn (Turn 1) until budget met
  → Continues removing oldest turns until total ≤ 2000 tokens (keeps up to last 5 turns)
  → LLM prompt includes only remaining turns (≤5, ≤2000 tokens)
```

### Scenario 3: Backward Compatibility
```
Learner sends query without conversation_id field:
  → Request remains valid for existing clients (field is still optional)
  → System creates a new conversation
  → Response includes answer + sources + generated conversation_id
```

### Scenario 4: Invalid Conversation
```
Learner sends: conversation_id = "conv_invalid_id"
  → System queries database; conversation does not exist
  → Returns 404 error: "Conversation conv_invalid_id does not exist..."
  → Error message suggests: "Start a new conversation by omitting conversation_id"
```

---

## Success Criteria

1. **Context Retention**: Follow-up question "What about error handling?" correctly references async function context from Turn 1; retrieved sources are relevant to both async and error handling
2. **Conversation Persistence**: conversation_id returned in response is a valid UUID; same ID usable in subsequent requests within same session
3. **History Token Budget**: Conversation with 10+ turns automatically trims to ≤5 turns when new query exceeds 2000 token limit; total prompt tokens never exceed 8000
4. **New Conversation Creation**: Query with `conversation_id: null` creates new conversation; returned ID is valid UUID; subsequent queries with same ID retrieve history
5. **Conversation Retrieval**: Conversations persist across application restarts; querying with same conversation_id returns stored history
6. **Backward Compatibility**: Existing clients that omit `conversation_id` continue to work without request changes; response remains valid and now includes generated `conversation_id` for follow-up use
7. **Error Handling**: Invalid conversation_id returns 404 with descriptive error message; valid conversation_ids return proper history context

---

## Out of Scope

- User authentication (conversations remain anonymous sessions)
- Conversation deletion or management UI
- Cross-session conversation linking
- Conversation summarization (trimming only, no summarization)
- Exporting conversation history
- Real-time multi-user collaboration on conversations
- Conversation sharing
- Analytics on conversation length/depth

---

## Non-Functional Requirements

### Performance
- History retrieval time: < 100ms (local database lookup)
- Token counting for history: < 50ms
- Turn insertion: < 50ms

### Reliability
- Conversation data persists across application restarts
- Conversation retrieval succeeds for all valid IDs within 1 week of creation
- Token budget trimming is deterministic (always removes oldest first)
- Conversation writes are atomic per query: user+assistant turns are both stored only on successful completion

### Scalability
- Support conversations with up to 100+ turns (after trimming, only 5 held in context)
- Support concurrent conversations (no limit in v1)

### Constraints (from Constitution)
- Database: SQLite with aiosqlite (./data/courseflow.db)
- Conversation IDs: UUID4 format
- History limit: Last 5 turns (configurable via environment variable, default 5)
- Token budget: History must not exceed 2000 tokens total
- Async-first: All database operations async via aiosqlite
- No user authentication required in v1

---

## Key Entities

### conversations
- **id** (UUID, PK): Unique conversation identifier
- **created_at** (TIMESTAMP): Conversation creation time

### conversation_turns
- **id** (BIGINT, PK, autoincrement): Turn sequence number
- **conversation_id** (UUID, FK): Reference to conversation
- **role** (TEXT): 'user' or 'assistant'
- **content** (TEXT): Full message content
- **token_count** (INTEGER): Tokens consumed by this turn
- **created_at** (TIMESTAMP): Turn timestamp

### Indexing Strategy
- Index on `conversation_turns.conversation_id` (frequent filtering)
- Index on `conversation_turns.created_at` (ordering by recency)
- Unique constraint: conversations(id)

---

## API Contract

### POST /api/v1/query

**Request**:
```json
{
  "query": "What about error handling?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"  // optional; null or omitted for new conversation
}
```

**Response 200** (Success):
```json
{
  "success": true,
  "data": {
    "answer": "For error handling in async functions, use try/except around await calls...",
    "sources": ["python-async.md", "python-exceptions.md"],
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response 404** (Invalid Conversation):
```json
{
  "success": false,
  "error": "conversation_not_found",
  "message": "Conversation 550e8400-e29b-41d4-a716-446655440999 does not exist. Start a new conversation by omitting conversation_id."
}
```

**Response 500** (Server Error):
```json
{
  "success": false,
  "error": "internal_error",
  "message": "Error processing query; please try again"
}
```

---

## Acceptance Tests

### Test 1: Context Retention (UC-001)
**Given**: Conversation with Turn 1 = "How do async functions work in Python?"  
**When**: Query Turn 2 with same conversation_id = "What about error handling?"  
**Then**:
- Answer references async context from Turn 1
- Sources include both python-async.md and python-exceptions.md
- conversation_id unchanged

### Test 2: New Conversation on Null ID (UC-002)
**Given**: Query with `conversation_id: null`  
**When**: Response received  
**Then**:
- conversation_id in response is a valid UUID
- That conversation_id can be used in subsequent requests
- Subsequent request with same ID retrieves history

### Test 3: History Token Budget (UC-003)
**Given**: Conversation with 10 turns (~2500 tokens)  
**When**: Making 11th query with new_query_tokens = ~800  
**Then**:
- Only last 5 turns included in LLM context (trimmed oldest turn)
- Total prompt tokens ≤ 8000
- Answer is still coherent (uses recent context, not removed context)

### Test 4: Backward Compatibility (UC-004)
**Given**: Query without `conversation_id` field  
**When**: POST /api/v1/query { "query": "..." }  
**Then**:
- Request is accepted without requiring client-side changes
- Response includes answer + sources + generated conversation_id
- A conversation is stored and can be reused for follow-up queries

### Test 5: Persistence Across Restarts (UC-005)
**Given**: Active conversation with 3 turns stored  
**When**: Application restarts  
**Then**:
- Same conversation_id query returns stored history
- All 3 turns retrievable
- Token counts and timestamps preserved

### Test 6: Invalid Conversation (UC-006)
**Given**: Query with non-existent conversation_id = "550e8400-e29b-41d4-a716-446655440999"  
**When**: POST /api/v1/query { "query": "...", conversation_id: "550e8400-e29b-41d4-a716-446655440999" }  
**Then**:
- Returns 404 conversation_not_found
- Error message includes suggestion to omit conversation_id

### Test 7: Failed Query Atomicity (UC-007)
**Given**: Valid conversation_id and a simulated LLM/retrieval failure  
**When**: POST /api/v1/query returns an error response  
**Then**:
- No new user turn is persisted
- No assistant turn is persisted
- Conversation history remains unchanged from before the failed request

---

## Assumptions

1. **Turn Trimming Strategy**: When history exceeds token budget (2000 tokens), oldest turns are removed first until budget is met; system stops including turns in LLM prompt once budget is hit (not summarizing or compressing)
2. **No Cross-Turn Summarization**: History is trimmed verbatim; older turns are discarded, not condensed
3. **Token Budget**: 2000 tokens for history is a hard limit; total prompt = context + history + new query must stay ≤ 8000 tokens
4. **Conversation Lifetime**: Conversations persist indefinitely; no automatic cleanup (future feature)
5. **Session Scope**: Each conversation is independent; no linking across multiple user sessions (no user auth in v1)
6. **Default History Depth**: 5 turns is the default; configurable via environment variable
7. **UUID Format**: conversation_id uses UUID4; stored and transmitted as string

---

## Dependencies & Integration

### Internal
- RAG Service (existing): Enhanced to accept conversation context
- Query Repository (existing): Extended to store conversation turns
- Vector Store (existing): No changes; retrieval logic may be enhanced in future for query rewriting

### External
- SQLite (local): Schema extensions for conversations and turns tables
- Google Gemini API (existing): No changes; receives enhanced prompt with history context

### Database Migrations
- Migration script required to create `conversations` and `conversation_turns` tables
- Indexes on conversation_id, created_at for performance

---

## Success Metrics (Measurable)

- **User Experience**: Learners report less need to repeat context (measured via golden dataset acceptance tests)
- **System Performance**: History retrieval completes in < 100ms for 95% of queries
- **Data Integrity**: All conversation turns persisted; 0% data loss on valid inserts
- **Backward Compatibility**: Existing clients can keep omitting `conversation_id` with 0 request-level breakage and 0 regression in answer quality

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| History context pollutes LLM output (confusion) | Acceptance Test 1 verifies answers are coherent; golden dataset tests validate quality |
| Token overflow crashes LLM | Token budget enforced before LLM call; history trimmed to ≤5 turns |
| Database grows unbounded | Assumption: cleanup deferred to future; v1 assumes reasonable conversation count |
| Existing queries break | Backward compatibility requirement (Test 4) ensures no regression |

---

## Version & History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-13 | Initial specification; multi-turn conversation with token budget, history trimming, backward compatibility |
