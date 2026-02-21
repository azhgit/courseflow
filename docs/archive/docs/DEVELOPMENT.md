
## Database Migrations

### Running Migrations

Migrations are stored in `scripts/migrations/` and should be executed in order:

```bash
# List all migrations
ls -1 scripts/migrations/*.sql

# Execute migration
sqlite3 data/courseflow.db < scripts/migrations/003_add_conversation_tables.sql

# Verify tables created
sqlite3 data/courseflow.db ".schema conversations"
sqlite3 data/courseflow.db ".schema conversation_turns"
sqlite3 data/courseflow.db ".indexes conversation_turns"
```

### Feature 003: Multi-turn Conversation Support

**File**: `scripts/migrations/003_add_conversation_tables.sql`

Creates two tables for conversation context management:

- **conversations**: Stores conversation sessions (id, created_at)
- **conversation_turns**: Stores individual messages (id, conversation_id, role, content, token_count, created_at)

**Index**: `idx_turns_conversation_time` - Optimizes history retrieval by conversation_id + created_at DESC

**Foreign Key**: conversation_turns → conversations (ON DELETE CASCADE)

**Constraints**:
- role CHECK: Enforces 'user' | 'assistant'
- token_count CHECK: Enforces >= 0

Run this migration before implementing conversation features.

