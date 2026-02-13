# Quickstart: Multi-turn Conversation Support

**Feature**: 003-conversation-context | **Target Audience**: Developers implementing this feature

---

## Overview

This quickstart guides you through implementing multi-turn conversation support for the RAG query endpoint. By the end, learners will be able to ask follow-up questions that reference previous context without repeating themselves.

**Time to complete**: ~4-6 hours (excluding testing)

---

## Prerequisites

- Existing CourseFlow RAG system running (`002-doc-ingestion` complete)
- Python 3.11+ with FastAPI, aiosqlite, tiktoken installed
- SQLite database at `./data/courseflow.db`
- Familiarity with hexagonal architecture pattern

---

## Implementation Steps

### Step 1: Database Migration (15 min)

Create and run the migration to add conversation tables.

**File**: `scripts/migrations/003_add_conversation_tables.sql`

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    token_count     INTEGER NOT NULL CHECK(token_count >= 0),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_turns_conversation_time 
ON conversation_turns(conversation_id, created_at DESC);
```

**Run migration**:
```bash
sqlite3 data/courseflow.db < scripts/migrations/003_add_conversation_tables.sql
```

**Verify**:
```bash
sqlite3 data/courseflow.db "SELECT name FROM sqlite_master WHERE type='table';"
# Should see: conversations, conversation_turns
```

---

### Step 2: Domain Entities (30 min)

Add conversation entities to `src/courseflow/domain/models.py`.

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Literal

@dataclass
class Conversation:
    """Aggregate root for conversation."""
    id: UUID
    created_at: datetime

    def __post_init__(self):
        if self.created_at > datetime.now():
            raise ValueError("Created time cannot be in future")

@dataclass
class ConversationTurn:
    """Individual message in conversation."""
    id: int
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    token_count: int
    created_at: datetime

    def __post_init__(self):
        if self.role not in ("user", "assistant"):
            raise ValueError("Role must be 'user' or 'assistant'")
        if not self.content.strip():
            raise ValueError("Content cannot be empty")
        if self.token_count < 0:
            raise ValueError("Token count cannot be negative")
```

---

### Step 3: Domain Port (15 min)

Add repository interface to `src/courseflow/domain/ports.py`.

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from .models import Conversation, ConversationTurn

class ConversationRepositoryPort(ABC):
    """Port for conversation persistence."""

    @abstractmethod
    async def create_conversation(self) -> Conversation:
        """Create new conversation with UUID."""
        pass

    @abstractmethod
    async def find_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Check if conversation exists."""
        pass

    @abstractmethod
    async def get_turns(
        self,
        conversation_id: UUID,
        limit: int = 5
    ) -> List[ConversationTurn]:
        """Retrieve recent turns."""
        pass

    @abstractmethod
    async def save_turns(
        self,
        conversation_id: UUID,
        user_turn: ConversationTurn,
        assistant_turn: ConversationTurn
    ) -> None:
        """Atomically save turn pair."""
        pass
```

---

### Step 4: Repository Adapter (60 min)

Create `src/courseflow/infrastructure/repositories/conversation_repo.py`.

```python
import uuid
from datetime import datetime
from typing import Optional, List
from uuid import UUID
import aiosqlite

from courseflow.domain.models import Conversation, ConversationTurn
from courseflow.domain.ports import ConversationRepositoryPort
from courseflow.domain.exceptions import ConversationNotFoundError

class SQLiteConversationRepository(ConversationRepositoryPort):
    """SQLite adapter for conversation persistence."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create_conversation(self) -> Conversation:
        """Create new conversation."""
        conversation_id = uuid.uuid4()
        created_at = datetime.now()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (id, created_at) VALUES (?, ?)",
                (str(conversation_id), created_at)
            )
            await db.commit()

        return Conversation(id=conversation_id, created_at=created_at)

    async def find_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """Check if conversation exists."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, created_at FROM conversations WHERE id = ?",
                (str(conversation_id),)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return Conversation(
                    id=UUID(row[0]),
                    created_at=datetime.fromisoformat(row[1])
                )

    async def get_turns(
        self,
        conversation_id: UUID,
        limit: int = 5
    ) -> List[ConversationTurn]:
        """Retrieve recent turns."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT id, conversation_id, role, content, token_count, created_at
                FROM conversation_turns
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (str(conversation_id), limit)
            ) as cursor:
                rows = await cursor.fetchall()
                
                turns = []
                for row in reversed(rows):  # Oldest first for LLM context
                    turns.append(ConversationTurn(
                        id=row[0],
                        conversation_id=UUID(row[1]),
                        role=row[2],
                        content=row[3],
                        token_count=row[4],
                        created_at=datetime.fromisoformat(row[5])
                    ))
                return turns

    async def save_turns(
        self,
        conversation_id: UUID,
        user_turn: ConversationTurn,
        assistant_turn: ConversationTurn
    ) -> None:
        """Atomically save turn pair."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("BEGIN")
                
                # Insert user turn
                await db.execute(
                    """
                    INSERT INTO conversation_turns 
                    (conversation_id, role, content, token_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(conversation_id),
                        user_turn.role,
                        user_turn.content,
                        user_turn.token_count,
                        user_turn.created_at
                    )
                )
                
                # Insert assistant turn
                await db.execute(
                    """
                    INSERT INTO conversation_turns 
                    (conversation_id, role, content, token_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(conversation_id),
                        assistant_turn.role,
                        assistant_turn.content,
                        assistant_turn.token_count,
                        assistant_turn.created_at
                    )
                )
                
                await db.commit()
            except Exception:
                await db.rollback()
                raise
```

---

### Step 5: Token Trimming Logic (30 min)

Add history trimming helper (reuse existing tiktoken).

```python
from tiktoken import get_encoding
from typing import List

def calculate_token_count(content: str) -> int:
    """Calculate tokens using tiktoken."""
    encoder = get_encoding("cl100k_base")
    return len(encoder.encode(content))

def trim_history(
    turns: List[ConversationTurn],
    max_tokens: int = 2000,
    max_count: int = 5
) -> List[ConversationTurn]:
    """Trim history to budget."""
    if not turns:
        return []
    
    total = sum(t.token_count for t in turns)
    
    # Trim oldest until under budget
    while total > max_tokens and len(turns) > 1:
        removed = turns.pop(0)
        total -= removed.token_count
    
    # Hard limit on count
    if len(turns) > max_count:
        turns = turns[-max_count:]
    
    return turns
```

---

### Step 6: Enhance RAG Service (60 min)

Modify `src/courseflow/application/rag_service.py` to accept conversation context.

```python
async def query(
    self,
    query_text: str,
    conversation_id: Optional[UUID] = None,
    subject: Optional[str] = None
) -> dict:
    """Execute RAG query with optional conversation context."""
    
    # Step 1: Handle conversation
    if conversation_id is None:
        # Create new conversation
        conversation = await self.conversation_repo.create_conversation()
        conversation_id = conversation.id
        history_turns = []
    else:
        # Validate and retrieve history
        conversation = await self.conversation_repo.find_conversation(conversation_id)
        if not conversation:
            raise ConversationNotFoundError(conversation_id)
        
        history_turns = await self.conversation_repo.get_turns(conversation_id, limit=5)
        history_turns = trim_history(history_turns, max_tokens=2000, max_count=5)
    
    # Step 2: Build LLM prompt with history
    prompt = self._build_prompt_with_history(query_text, history_turns, retrieved_docs)
    
    # Step 3: Execute RAG (existing logic)
    answer = await self.llm_client.generate(prompt)
    
    # Step 4: Save turns atomically
    user_turn = ConversationTurn(
        id=0,  # Auto-increment
        conversation_id=conversation_id,
        role="user",
        content=query_text,
        token_count=calculate_token_count(query_text),
        created_at=datetime.now()
    )
    
    assistant_turn = ConversationTurn(
        id=0,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        token_count=calculate_token_count(answer),
        created_at=datetime.now()
    )
    
    await self.conversation_repo.save_turns(conversation_id, user_turn, assistant_turn)
    
    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": str(conversation_id)
    }

def _build_prompt_with_history(
    self,
    query: str,
    history: List[ConversationTurn],
    docs: List[str]
) -> str:
    """Build prompt with conversation context."""
    parts = []
    
    if history:
        parts.append("Previous conversation:")
        for turn in history:
            prefix = "User" if turn.role == "user" else "Assistant"
            parts.append(f"{prefix}: {turn.content}")
        parts.append("")  # Blank line
    
    parts.append("Retrieved context:")
    parts.extend(docs)
    parts.append("")
    
    parts.append(f"Current query: {query}")
    
    return "\n".join(parts)
```

---

### Step 7: Update API Route (30 min)

Modify `src/courseflow/api/routes/query.py`.

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[UUID] = None
    subject: Optional[str] = None

    @validator('conversation_id', pre=True)
    def validate_conversation_id(cls, v):
        if v is None or v == "":
            return None
        try:
            return UUID(v)
        except ValueError:
            raise ValueError("Invalid UUID format")

@router.post("/api/v1/query")
async def query(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    try:
        result = await rag_service.query(
            query_text=request.query,
            conversation_id=request.conversation_id,
            subject=request.subject
        )
        return {"success": True, "data": result}
    except ConversationNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": "conversation_not_found",
                "message": str(e)
            }
        )
```

---

## Testing

### Manual Test

```bash
# Start server
uvicorn src.courseflow.api.main:app --reload

# Test 1: New conversation
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do async functions work?"}'

# Copy conversation_id from response

# Test 2: Follow-up
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about error handling?",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Automated Tests

Run existing test suite to verify backward compatibility:
```bash
pytest tests/ -v
```

---

## Success Criteria

- [x] Database migration executed
- [x] New conversation returns UUID
- [x] Follow-up queries include history in LLM prompt
- [x] Invalid conversation_id returns 404
- [x] Omitted conversation_id works (backward compatible)
- [x] Failed queries don't save turns
- [x] History trimmed at 2000 tokens
- [x] All existing tests pass

---

## Next Steps

1. Run `/speckit.tasks` to generate detailed implementation tasks
2. Implement in order: domain → infrastructure → application → API
3. Write tests for each layer before implementation
4. Profile performance to verify <200ms overhead

---

## References

- **Data Model**: `data-model.md`
- **API Contract**: `contracts/query-api.md`
- **Research Decisions**: `research.md`
