-- Migration: Add conversation support tables
-- Feature: 003-conversation-context
-- Date: 2026-02-13
-- Purpose: Enable multi-turn conversation storage with context history

-- conversations table: Aggregate root for conversation sessions
CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,                          -- UUID4 stored as TEXT (36 chars)
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- Conversation creation timestamp
);

-- conversation_turns table: Individual messages in a conversation
CREATE TABLE IF NOT EXISTS conversation_turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,         -- Auto-increment sequence
    conversation_id TEXT NOT NULL,                             -- Foreign key to conversations
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant')),  -- Role enforcement
    content         TEXT NOT NULL,                             -- Full message content
    token_count     INTEGER NOT NULL CHECK(token_count >= 0),  -- Pre-calculated token count
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Turn creation time (determines order)
    
    -- Foreign key: preserve referential integrity
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Composite index: Optimize history retrieval query
-- Covers: WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 5
-- Descending order on created_at ensures most recent turns retrieved first
CREATE INDEX IF NOT EXISTS idx_turns_conversation_time 
ON conversation_turns(conversation_id, created_at DESC);

-- Verify tables created successfully
.print "✓ conversations table created"
.print "✓ conversation_turns table created"
.print "✓ idx_turns_conversation_time index created"
