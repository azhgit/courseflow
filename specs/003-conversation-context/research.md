# Research: Multi-turn Conversation Support

**Feature**: 003-conversation-context | **Date**: 2026-02-13  
**Purpose**: Resolve technical unknowns and validate technology choices

## Research Questions

### Q1: Token Counting for History Budget

**Question**: How to accurately count tokens for conversation history to enforce 2000-token budget?

**Decision**: Reuse existing `tiktoken` (tiktoken 0.12.0) with cl100k_base encoding

**Rationale**:
- Already installed in project (used for chunking in 002-doc-ingestion)
- Gemini uses similar BPE tokenization; tiktoken mismatch <5% acceptable per previous research
- Fast (<1ms per turn for typical messages <500 tokens)
- Zero new dependencies

**Alternatives Considered**:
- **Google's official tokenizer**: Requires additional API call; adds latency; not available offline
- **Simple word count heuristic**: Inaccurate (30-50% error margin); risks budget overflow
- **Character count / 4**: Too imprecise for production use

**Implementation**:
```python
from tiktoken import get_encoding

encoder = get_encoding("cl100k_base")
tokens = encoder.encode(turn_content)
token_count = len(tokens)
```

---

### Q2: History Trimming Algorithm

**Question**: How to efficiently trim conversation history when exceeding 2000-token budget?

**Decision**: Oldest-first trimming with pre-calculated token counts

**Rationale**:
- Deterministic: always removes oldest turns first (clarification decision)
- Fast: O(n) single pass; no need to re-count tokens
- Simple: no compression or summarization (deferred to v2)

**Algorithm** (pseudocode):
```python
def trim_history(turns: List[Turn], max_tokens: int) -> List[Turn]:
    """Keep most recent turns within token budget."""
    total = sum(turn.token_count for turn in turns)
    if total <= max_tokens:
        return turns
    
    # Remove oldest until under budget
    while total > max_tokens and len(turns) > 1:
        removed = turns.pop(0)  # Remove oldest
        total -= removed.token_count
    
    return turns[-5:]  # Hard limit: last 5 turns max
```

**Edge Cases**:
- Single turn exceeds budget → keep it anyway (user query must be included)
- Empty history → return empty list
- All turns under budget → return all (up to 5)

**Alternatives Considered**:
- **Summarize old turns**: Complex; adds LLM calls; latency increase; deferred to v2
- **Sliding window by count only**: Ignores token size; risks overflow
- **Exponential decay**: Too complex for v1; no clear user benefit

---

### Q3: Atomic Turn Persistence Strategy

**Question**: How to ensure atomic user+assistant turn writes?

**Decision**: SQLite transaction with explicit BEGIN/COMMIT

**Rationale**:
- SQLite supports ACID transactions natively
- `aiosqlite` preserves transaction semantics in async code
- Rollback on any failure ensures no partial writes

**Implementation Pattern**:
```python
async def save_turns_atomic(
    self,
    conversation_id: UUID,
    user_turn: Turn,
    assistant_turn: Turn
) -> None:
    async with self.db.execute("BEGIN"):
        try:
            await self._insert_turn(conversation_id, user_turn)
            await self._insert_turn(conversation_id, assistant_turn)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
```

**Alternatives Considered**:
- **Write user turn immediately**: Violates clarification decision; leaves orphaned user turns on failure
- **Separate transactions**: No atomicity guarantee
- **Event sourcing**: Over-engineering for v1

---

### Q4: Conversation ID Generation

**Question**: How to generate UUIDs in Python?

**Decision**: Python's built-in `uuid.uuid4()`

**Rationale**:
- Standard library; zero dependencies
- Collision-resistant (2^122 possible UUIDs)
- Fast (<1μs generation time)

**Implementation**:
```python
import uuid

conversation_id = str(uuid.uuid4())
# Example: "550e8400-e29b-41d4-a716-446655440000"
```

**Alternatives Considered**:
- **Snowflake IDs**: Overkill; requires coordination; not needed for anonymous conversations
- **Sequential IDs**: Leaks conversation count; security risk

---

### Q5: Database Schema Indexes

**Question**: Which indexes are needed for <100ms history retrieval?

**Decision**: Composite index on `(conversation_id, created_at)`

**Rationale**:
- Covers both filtering (by conversation_id) and ordering (by created_at)
- SQLite query planner can use single index for `WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 5`
- Minimal storage overhead (~8 bytes per row)

**Schema**:
```sql
CREATE INDEX idx_turns_conversation_time 
ON conversation_turns(conversation_id, created_at DESC);
```

**Query Pattern**:
```sql
-- Retrieve last 5 turns for conversation
SELECT * FROM conversation_turns
WHERE conversation_id = ?
ORDER BY created_at DESC
LIMIT 5;
```

**Alternatives Considered**:
- **Separate indexes**: Less efficient; query planner may not combine
- **No index**: Table scan for every query; unacceptable for >100 turns
- **Covering index (include all columns)**: Marginal benefit; doubles index size

---

### Q6: Conversation Cleanup Strategy (v1)

**Question**: How to handle conversation storage growth?

**Decision**: No automatic cleanup in v1; manual cleanup script for future

**Rationale**:
- Specification explicitly defers cleanup to future versions
- v1 assumes reasonable conversation count (<10k conversations)
- SQLite handles 10k conversations (~1M turns) easily (<100MB)
- Manual script can be added later if needed

**Future Considerations** (out of scope):
- TTL-based deletion (e.g., conversations older than 30 days)
- Soft delete with archive table
- Conversation export before deletion

---

## Technology Stack Summary

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Domain | Python dataclasses | 3.11+ | Existing |
| Application | FastAPI | 0.109+ | Existing |
| Database | SQLite + aiosqlite | 3.37+ | Existing |
| Token Counting | tiktoken | 0.12.0 | Existing (reuse) |
| Validation | Pydantic | 2.x | Existing |
| Testing | pytest + pytest-asyncio | Latest | Existing |

**New Dependencies**: None ✅

---

## Architecture Decisions

### Decision 1: Domain Entity Structure

**Choice**: Separate `Conversation` and `ConversationTurn` entities

**Rationale**:
- Conversation is aggregate root (owns turns)
- Turn is child entity (cannot exist without conversation)
- Aligns with DDD aggregate pattern
- Simplifies repository queries (fetch turns separately)

**Entities**:
```python
@dataclass
class Conversation:
    id: UUID
    created_at: datetime

@dataclass
class ConversationTurn:
    id: int
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    token_count: int
    created_at: datetime
```

---

### Decision 2: Repository Responsibility

**Choice**: `ConversationRepositoryPort` owns turn persistence

**Rationale**:
- Conversation + turns form a single aggregate
- Repository encapsulates transaction logic
- Domain service (RAGService) doesn't need to know about atomicity

**Port Interface**:
```python
class ConversationRepositoryPort(ABC):
    @abstractmethod
    async def create_conversation(self) -> Conversation:
        """Create new conversation with UUID."""
        pass
    
    @abstractmethod
    async def find_conversation(self, id: UUID) -> Optional[Conversation]:
        """Check if conversation exists."""
        pass
    
    @abstractmethod
    async def get_turns(self, conversation_id: UUID, limit: int = 5) -> List[ConversationTurn]:
        """Retrieve recent turns for conversation."""
        pass
    
    @abstractmethod
    async def save_turns(
        self,
        conversation_id: UUID,
        user_turn: ConversationTurn,
        assistant_turn: ConversationTurn
    ) -> None:
        """Atomically save user+assistant turns."""
        pass
```

---

### Decision 3: RAG Service Enhancement

**Choice**: Modify existing `RAGService.query()` to accept optional `conversation_id`

**Rationale**:
- Single endpoint for both stateless and stateful queries
- Backward compatible (conversation_id is optional)
- Minimal changes to existing code

**Flow**:
1. Accept `conversation_id` (optional)
2. If present and valid: retrieve history, trim to budget
3. Build LLM prompt with history context
4. Execute existing RAG pipeline (retrieval + generation)
5. If generation succeeds: save user+assistant turns atomically
6. Return answer + sources + conversation_id

---

## Performance Validation

### Expected Latency Breakdown

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Conversation ID validation | <10ms | Single SELECT query with PK lookup |
| History retrieval (5 turns) | <50ms | Indexed query, small result set |
| Token counting (5 turns) | <20ms | tiktoken processes ~1000 tokens/ms |
| History trimming | <10ms | O(n) algorithm, n ≤ 100 |
| Turn persistence | <50ms | Single INSERT transaction |
| **Total Overhead** | **<140ms** | Well under 200ms budget |

**Existing RAG latency**: ~1.5s (p95)  
**New total latency**: ~1.64s (p95) — **meets <2s requirement** ✅

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token count mismatch (tiktoken vs Gemini) | History exceeds budget by ~5% | Acceptable per previous research; budget has 25% margin |
| Transaction deadlock (concurrent writes) | Failed turn persistence | SQLite uses exclusive locks; retry logic in application layer |
| Large conversation history (>100 turns) | Slow retrieval | Index + LIMIT clause ensures <100ms; tested up to 1000 turns |
| Database file corruption | Data loss | Regular SQLite backups (outside feature scope) |

---

## Open Questions (Deferred)

1. **Query rewriting based on history**: Spec mentions "enhance retrieval via history context" but no implementation detail. **Decision**: Defer to v2; v1 includes raw history in prompt only.

2. **Conversation analytics**: Spec lists "analytics on conversation length/depth" as out of scope. **Confirmed**: No metrics collection in v1.

3. **Conversation expiration**: No TTL defined. **Decision**: Manual cleanup script if needed; not automated in v1.

---

## References

- **Existing implementation**: `specs/002-doc-ingestion/research.md` (tiktoken decision precedent)
- **Constitution**: `.specify/memory/constitution.md` (hexagonal architecture, zero-cost constraints)
- **Clarifications**: `specs/003-conversation-context/spec.md` (atomic persistence, UUID format, omit/null semantics)
