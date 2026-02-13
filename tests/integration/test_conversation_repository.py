"""Integration tests for SQLiteConversationRepository.

Tests cover:
- Full CRUD operations on conversations and turns
- Token budget enforcement
- Database persistence across connections
- Error handling and validation
"""

import pytest
import tempfile
import os
from uuid import uuid4

import aiosqlite

from courseflow.domain.exceptions import ConversationNotFoundError
from courseflow.domain.models import ConversationTurn
from courseflow.infrastructure.repositories.conversation_repo import (
    SQLiteConversationRepository,
)


@pytest.fixture
async def repo() -> SQLiteConversationRepository:
    """Create test repository with temporary SQLite database."""
    # Create temporary file for test database
    fd, db_path = tempfile.mkstemp(suffix=".db", prefix="courseflow_test_")
    os.close(fd)
    os.remove(db_path)  # Remove it so sqlite can create it fresh

    try:
        # Initialize database with schema
        db = await aiosqlite.connect(db_path)

        # Create conversations table
        await db.execute("""
            CREATE TABLE conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # Create conversation_turns table
        await db.execute("""
            CREATE TABLE conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL CHECK (token_count >= 0),
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # Create index on conversation_id and created_at
        await db.execute("""
            CREATE INDEX idx_turns_conversation_time
            ON conversation_turns (conversation_id, created_at DESC)
        """)
        await db.commit()
        await db.close()

        yield SQLiteConversationRepository(db_path=db_path)

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


class TestSQLiteConversationRepository:
    """Integration tests for conversation repository."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_conversation(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test creating and retrieving a conversation."""
        # Create
        conv = await repo.create_conversation()
        assert conv.id is not None
        assert conv.created_at is not None

        # Retrieve
        retrieved = await repo.get_conversation(conv.id)
        assert retrieved.id == conv.id
        assert retrieved.created_at == conv.created_at

    @pytest.mark.asyncio
    async def test_conversation_exists(self, repo: SQLiteConversationRepository) -> None:
        """Test checking conversation existence."""
        conv = await repo.create_conversation()

        assert await repo.conversation_exists(conv.id)
        assert not await repo.conversation_exists(uuid4())

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation_raises_error(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test retrieving nonexistent conversation raises error."""
        with pytest.raises(ConversationNotFoundError):
            await repo.get_conversation(uuid4())

    @pytest.mark.asyncio
    async def test_add_turn_requires_existing_conversation(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test adding turn to nonexistent conversation raises error."""
        turn = ConversationTurn(
            conversation_id=uuid4(),
            role="user",
            content="Test question",
            token_count=3,
        )

        with pytest.raises(ConversationNotFoundError):
            await repo.add_turn(turn)

    @pytest.mark.asyncio
    async def test_add_and_count_turns(self, repo: SQLiteConversationRepository) -> None:
        """Test adding turns and counting them."""
        conv = await repo.create_conversation()

        # Add first turn
        turn1 = ConversationTurn(
            conversation_id=conv.id,
            role="user",
            content="What is Python?",
            token_count=3,
        )
        persisted1 = await repo.add_turn(turn1)
        assert persisted1.id is not None

        # Add second turn
        turn2 = ConversationTurn(
            conversation_id=conv.id,
            role="assistant",
            content="Python is a programming language...",
            token_count=50,
        )
        persisted2 = await repo.add_turn(turn2)
        assert persisted2.id is not None
        assert persisted2.id != persisted1.id

        # Count
        count = await repo.count_turns(conv.id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_history_empty_conversation(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test retrieving history from conversation with no turns."""
        conv = await repo.create_conversation()
        history = await repo.get_history(conv.id)

        assert len(history.turns) == 0
        assert history.total_tokens == 0
        assert not history.is_trimmed

    @pytest.mark.asyncio
    async def test_get_history_with_turns(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test retrieving history from conversation with turns."""
        conv = await repo.create_conversation()

        # Add 3 turns
        for i, (role, tokens) in enumerate([
            ("user", 5),
            ("assistant", 50),
            ("user", 4),
        ]):
            turn = ConversationTurn(
                conversation_id=conv.id,
                role=role,
                content=f"Turn {i}",
                token_count=tokens,
            )
            await repo.add_turn(turn)

        history = await repo.get_history(conv.id)
        assert len(history.turns) == 3
        assert history.total_tokens == 59
        assert not history.is_trimmed

    @pytest.mark.asyncio
    async def test_get_history_respects_max_tokens(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test history trimming when exceeding token budget."""
        conv = await repo.create_conversation()

        # Add 5 turns of 600 tokens each (3000 total)
        for i in range(5):
            turn = ConversationTurn(
                conversation_id=conv.id,
                role="user",
                content=f"Turn {i}",
                token_count=600,
            )
            await repo.add_turn(turn)

        # Request history with 2000 token budget
        history = await repo.get_history(conv.id, max_tokens=2000, max_count=10)

        # Should keep last 3 turns (1800 tokens)
        assert len(history.turns) == 3
        assert history.total_tokens == 1800
        assert history.is_trimmed

    @pytest.mark.asyncio
    async def test_get_history_respects_max_count(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test history trimming when exceeding turn count limit."""
        conv = await repo.create_conversation()

        # Add 10 turns of 100 tokens each
        for i in range(10):
            turn = ConversationTurn(
                conversation_id=conv.id,
                role="user",
                content=f"Turn {i}",
                token_count=100,
            )
            await repo.add_turn(turn)

        # Request history with max 5 turns
        history = await repo.get_history(conv.id, max_tokens=5000, max_count=5)

        # Should keep last 5 turns
        assert len(history.turns) == 5
        assert history.is_trimmed

    @pytest.mark.asyncio
    async def test_count_turns_nonexistent_conversation_raises_error(
        self, repo: SQLiteConversationRepository
    ) -> None:
        """Test counting turns in nonexistent conversation raises error."""
        with pytest.raises(ConversationNotFoundError):
            await repo.count_turns(uuid4())
