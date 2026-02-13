# Data Model: Multi-turn Conversation Support

**Feature**: 003-conversation-context | **Date**: 2026-02-13  
**Purpose**: Define domain entities, database schema, and validation rules

---

## Domain Entities

### 1. Conversation (Aggregate Root)

**Purpose**: Represents a multi-turn question-answer session

**Fields**:
```python
@dataclass
class Conversation:
    id: UUID                    # Primary key; UUID4 format
    created_at: datetime        # Timestamp of conversation creation
```

**Invariants**:
- `id` must be a valid UUID4
- `created_at` cannot be in the future

**Business Rules**:
- A conversation is created when user sends first query without conversation_id
- Conversation exists independently of turns (can have zero turns initially)
- Conversation cannot be deleted in v1 (soft delete deferred)

**Validation**:
```python
def __post_init__(self):
    if not isinstance(self.id, UUID):
        raise ValueError("Conversation ID must be UUID")
    if self.created_at > datetime.now():
        raise ValueError("Created time cannot be in future")
```

---

### 2. ConversationTurn (Entity)

**Purpose**: Represents a single message (user query or assistant response) in a conversation

**Fields**:
```python
@dataclass
class ConversationTurn:
    id: int                     # Auto-increment sequence number
    conversation_id: UUID       # Foreign key to conversation
    role: Literal["user", "assistant"]
    content: str                # Full message text
    token_count: int            # Pre-calculated token count (tiktoken)
    created_at: datetime        # Timestamp of turn creation
```

**Invariants**:
- `role` must be exactly "user" or "assistant"
- `content` cannot be empty
- `token_count` must be ≥ 0
- `conversation_id` must reference an existing conversation

**Business Rules**:
- Turns are always created in pairs (user + assistant) atomically
- Turns cannot be modified after creation (immutable)
- Turns cannot be deleted individually (only via conversation cleanup)
- Turn sequence is determined by `created_at` (not `id`)

**Validation**:
```python
def __post_init__(self):
    if self.role not in ("user", "assistant"):
        raise ValueError("Role must be 'user' or 'assistant'")
    if not self.content.strip():
        raise ValueError("Content cannot be empty")
    if self.token_count < 0:
        raise ValueError("Token count cannot be negative")
```

**Token Count Calculation**:
```python
from tiktoken import get_encoding

def calculate_token_count(content: str) -> int:
    """Calculate token count using tiktoken (cl100k_base)."""
    encoder = get_encoding("cl100k_base")
    return len(encoder.encode(content))
```

---

## Database Schema

### conversations Table

```sql
CREATE TABLE conversations (
    id              TEXT PRIMARY KEY,  -- UUID stored as TEXT
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- No additional indexes needed; PK index sufficient for lookups
```

**Notes**:
- SQLite doesn't have native UUID type; stored as TEXT (36 chars)
- `created_at` defaults to current timestamp for convenience
- No foreign keys reference this table (one-way relationship from turns)

---

### conversation_turns Table

```sql
CREATE TABLE conversation_turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    token_count     INTEGER NOT NULL CHECK(token_count >= 0),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Composite index for efficient history retrieval
CREATE INDEX idx_turns_conversation_time 
ON conversation_turns(conversation_id, created_at DESC);
```

**Index Justification**:
- `idx_turns_conversation_time`: Covers `WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 5` query
- Composite index more efficient than two separate indexes
- Descending order on `created_at` optimizes "most recent" queries

**Constraints**:
- `role` CHECK: Enforces valid values at database level
- `token_count` CHECK: Prevents negative values
- `ON DELETE CASCADE`: Auto-deletes turns when conversation is deleted (future cleanup feature)

---

## Relationships

```
Conversation (1) ──< (0..n) ConversationTurn
  └── Aggregate Root      └── Child Entity
```

**Cardinality**:
- One conversation can have zero or more turns
- Each turn belongs to exactly one conversation
- Turns cannot exist without a parent conversation (enforced by FK)

**Aggregate Boundary**:
- `Conversation` is the aggregate root
- `ConversationTurn` is accessed only through the conversation
- Repository operations load/save the entire aggregate

---

## Repository Interface (Port)

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ConversationRepositoryPort(ABC):
    """Port: Defines contract for conversation persistence."""

    @abstractmethod
    async def create_conversation(self) -> Conversation:
        """
        Create a new conversation with generated UUID.
        
        Returns:
            Conversation: New conversation entity with unique ID
        """
        pass

    @abstractmethod
    async def find_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Check if conversation exists.
        
        Args:
            conversation_id: UUID of conversation to find
            
        Returns:
            Conversation if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_turns(
        self,
        conversation_id: UUID,
        limit: int = 5
    ) -> List[ConversationTurn]:
        """
        Retrieve most recent turns for a conversation.
        
        Args:
            conversation_id: UUID of conversation
            limit: Maximum number of turns to retrieve (default 5)
            
        Returns:
            List of turns ordered by created_at DESC (most recent first)
            Empty list if conversation not found or has no turns
        """
        pass

    @abstractmethod
    async def save_turns(
        self,
        conversation_id: UUID,
        user_turn: ConversationTurn,
        assistant_turn: ConversationTurn
    ) -> None:
        """
        Atomically save user + assistant turn pair.
        
        Args:
            conversation_id: UUID of conversation
            user_turn: User's query turn
            assistant_turn: Assistant's response turn
            
        Raises:
            ConversationNotFoundError: If conversation_id doesn't exist
            DatabaseError: If atomic transaction fails (rolls back both turns)
        """
        pass
```

---

## Value Objects

### TurnHistory (Value Object)

**Purpose**: Encapsulates trimmed conversation history with token budget enforcement

```python
@dataclass(frozen=True)
class TurnHistory:
    """Immutable value object representing conversation history."""
    
    turns: tuple[ConversationTurn, ...]  # Immutable tuple
    total_tokens: int
    is_trimmed: bool  # True if original history exceeded budget
    
    @classmethod
    def from_turns(
        cls,
        turns: List[ConversationTurn],
        max_tokens: int = 2000,
        max_count: int = 5
    ) -> "TurnHistory":
        """
        Create TurnHistory with token budget enforcement.
        
        Algorithm:
        1. Calculate total tokens
        2. If under budget and count ≤ max_count: return all
        3. Otherwise: trim oldest turns until budget met
        4. Hard limit: keep last max_count turns
        """
        if not turns:
            return cls(turns=tuple(), total_tokens=0, is_trimmed=False)
        
        total = sum(t.token_count for t in turns)
        original_count = len(turns)
        
        # Trim if over budget
        while total > max_tokens and len(turns) > 1:
            removed = turns.pop(0)  # Remove oldest
            total -= removed.token_count
        
        # Hard limit on count
        if len(turns) > max_count:
            turns = turns[-max_count:]
            total = sum(t.token_count for t in turns)
        
        is_trimmed = len(turns) < original_count
        
        return cls(
            turns=tuple(turns),
            total_tokens=total,
            is_trimmed=is_trimmed
        )
    
    def to_llm_context(self) -> str:
        """Format turns as LLM prompt context."""
        if not self.turns:
            return ""
        
        context_parts = []
        for turn in self.turns:
            prefix = "User" if turn.role == "user" else "Assistant"
            context_parts.append(f"{prefix}: {turn.content}")
        
        return "\n\n".join(context_parts)
```

---

## Domain Exceptions

```python
class ConversationNotFoundError(Exception):
    """Raised when conversation_id doesn't exist."""
    
    def __init__(self, conversation_id: UUID):
        super().__init__(
            f"Conversation {conversation_id} does not exist. "
            "Start a new conversation by omitting conversation_id."
        )
        self.conversation_id = conversation_id

class InvalidConversationIdError(Exception):
    """Raised when conversation_id is malformed (not a valid UUID)."""
    
    def __init__(self, invalid_id: str):
        super().__init__(f"Invalid conversation ID format: {invalid_id}")
        self.invalid_id = invalid_id
```

---

## Migration Script

**File**: `scripts/migrations/003_add_conversation_tables.sql`

```sql
-- Migration: Add conversation support
-- Feature: 003-conversation-context
-- Date: 2026-02-13

-- conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- conversation_turns table
CREATE TABLE IF NOT EXISTS conversation_turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    token_count     INTEGER NOT NULL CHECK(token_count >= 0),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Composite index for efficient history retrieval
CREATE INDEX IF NOT EXISTS idx_turns_conversation_time 
ON conversation_turns(conversation_id, created_at DESC);

-- Verify schema
SELECT 
    'conversations table created' AS status,
    COUNT(*) AS row_count 
FROM conversations;

SELECT 
    'conversation_turns table created' AS status,
    COUNT(*) AS row_count 
FROM conversation_turns;
```

---

## Example Data Flow

### Scenario: Multi-turn conversation

**Turn 1** (new conversation):
```
User query: "How do async functions work?"
→ conversation_id = None

1. Create conversation: 
   Conversation(id=550e8400-..., created_at=2026-02-13T10:00:00)

2. Execute RAG pipeline → answer

3. Save turns atomically:
   - ConversationTurn(
       conversation_id=550e8400-...,
       role="user",
       content="How do async functions work?",
       token_count=7,
       created_at=2026-02-13T10:00:01
     )
   - ConversationTurn(
       conversation_id=550e8400-...,
       role="assistant",
       content="Async functions in Python...",
       token_count=142,
       created_at=2026-02-13T10:00:03
     )

4. Return: {answer, sources, conversation_id: "550e8400-..."}
```

**Turn 2** (follow-up):
```
User query: "What about error handling?"
→ conversation_id = "550e8400-..."

1. Validate conversation exists ✓

2. Retrieve turns:
   SELECT * FROM conversation_turns 
   WHERE conversation_id = "550e8400-..."
   ORDER BY created_at DESC LIMIT 5
   → Returns 2 turns (user + assistant from Turn 1)

3. Build TurnHistory:
   - Total tokens: 7 + 142 = 149
   - Under budget (149 < 2000) → no trimming
   - History context:
     "User: How do async functions work?
      Assistant: Async functions in Python..."

4. Execute RAG with history → answer

5. Save new turns atomically (total: 4 turns now)

6. Return: {answer, sources, conversation_id: "550e8400-..."}
```

---

## Performance Characteristics

| Operation | Complexity | Expected Time |
|-----------|-----------|---------------|
| Create conversation | O(1) | <10ms |
| Find conversation | O(1) - PK lookup | <10ms |
| Get turns (limit 5) | O(log n) - index scan | <50ms |
| Save turns (atomic) | O(1) - 2 inserts | <50ms |
| Build TurnHistory | O(n) - n ≤ 100 | <10ms |

**Total overhead per query**: <140ms (well under 200ms budget)

---

## Validation Rules Summary

| Entity | Field | Rule |
|--------|-------|------|
| Conversation | id | Valid UUID4 |
| Conversation | created_at | Not in future |
| ConversationTurn | role | Exactly "user" or "assistant" |
| ConversationTurn | content | Non-empty after trim |
| ConversationTurn | token_count | ≥ 0 |
| ConversationTurn | conversation_id | References existing conversation |
| TurnHistory | total_tokens | ≤ 2000 (enforced by trimming) |
| TurnHistory | turns count | ≤ 5 (hard limit) |

---

## References

- **Hexagonal Architecture**: `domain/` contains entities, `infrastructure/` contains repository adapter
- **DDD Aggregates**: Conversation is aggregate root; turns are child entities
- **Token Counting**: `tiktoken` with cl100k_base encoding (see `research.md`)
- **Atomic Persistence**: SQLite transactions ensure user+assistant pairs saved together
