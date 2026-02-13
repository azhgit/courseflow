"""SQLite adapter for conversation persistence.

Implements ConversationRepositoryPort using SQLite with aiosqlite
for async database access. All operations are ACID-compliant and
atomic to ensure conversation integrity.
"""

import sqlite3
from datetime import UTC, datetime
from uuid import UUID, uuid4

import aiosqlite

from courseflow.domain.exceptions import (
    ConversationNotFoundError,
    ConversationPersistenceError,
    ServiceUnavailableError,
)
from courseflow.domain.models import Conversation, ConversationTurn, TurnHistory
from courseflow.domain.ports import ConversationRepositoryPort


class SQLiteConversationRepository(ConversationRepositoryPort):
    """SQLite-backed repository for conversations and turns.

    Assumptions:
    - Database file is at ./data/courseflow.db
    - Tables created by migration: 003_add_conversation_tables.sql
    - All timestamps stored as ISO 8601 strings (SQLite TEXT type)
    - All UUIDs stored as text (36-char format)
    - Proper indexes exist on (conversation_id, created_at DESC)

    Concurrency: Safe for concurrent async access via aiosqlite.
    """

    def __init__(self, db_path: str = "./data/courseflow.db") -> None:
        """Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file (default: ./data/courseflow.db)
        """
        self.db_path = db_path

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get async database connection.

        Returns:
            aiosqlite connection object

        Raises:
            ServiceUnavailableError: If database cannot be opened
        """
        try:
            return await aiosqlite.connect(self.db_path)
        except (sqlite3.Error, FileNotFoundError, OSError) as e:
            raise ServiceUnavailableError(
                f"Failed to connect to database at {self.db_path}: {str(e)}"
            ) from e

    async def create_conversation(self) -> Conversation:
        """Create new conversation session.

        Returns:
            Conversation object with id and created_at set

        Raises:
            ConversationPersistenceError: If database insert fails
            ServiceUnavailableError: If database is unreachable
        """
        try:
            db = await self._get_connection()
            try:
                conv_id = str(uuid4())
                created_at = datetime.now(UTC).isoformat()

                await db.execute(
                    """
                    INSERT INTO conversations (id, created_at)
                    VALUES (?, ?)
                    """,
                    (conv_id, created_at),
                )
                await db.commit()

                return Conversation(
                    id=UUID(conv_id),
                    created_at=datetime.fromisoformat(created_at),
                )
            finally:
                await db.close()
        except sqlite3.Error as e:
            raise ConversationPersistenceError(f"Failed to create conversation: {str(e)}") from e
        except ServiceUnavailableError:
            raise

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Retrieve conversation by ID.

        Args:
            conversation_id: UUID of conversation to retrieve

        Returns:
            Conversation object if found

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        try:
            db = await self._get_connection()
            try:
                cursor = await db.execute(
                    "SELECT id, created_at FROM conversations WHERE id = ?",
                    (str(conversation_id),),
                )
                row = await cursor.fetchone()

                if not row:
                    raise ConversationNotFoundError(str(conversation_id))

                conv_id, created_at_str = row
                return Conversation(
                    id=UUID(conv_id),
                    created_at=datetime.fromisoformat(created_at_str),
                )
            finally:
                await db.close()
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to retrieve conversation: {str(e)}") from e

    async def conversation_exists(self, conversation_id: UUID) -> bool:
        """Check if conversation exists (for validation).

        Args:
            conversation_id: UUID to check

        Returns:
            True if exists, False otherwise

        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        try:
            db = await self._get_connection()
            try:
                cursor = await db.execute(
                    "SELECT 1 FROM conversations WHERE id = ? LIMIT 1",
                    (str(conversation_id),),
                )
                return (await cursor.fetchone()) is not None
            finally:
                await db.close()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to check conversation existence: {str(e)}"
            ) from e

    async def add_turn(self, turn: ConversationTurn) -> ConversationTurn:
        """Add turn (user query or assistant response) to conversation.

        The turn is persisted with its pre-calculated token_count.

        Args:
            turn: ConversationTurn object (id must be None)

        Returns:
            Persisted turn with id field populated by database

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ConversationPersistenceError: If insert fails
            ServiceUnavailableError: If database is unreachable
        """
        try:
            # Verify conversation exists first
            if not await self.conversation_exists(turn.conversation_id):
                raise ConversationNotFoundError(str(turn.conversation_id))

            db = await self._get_connection()
            try:
                created_at_str = turn.created_at.isoformat()
                await db.execute(
                    """
                    INSERT INTO conversation_turns
                    (conversation_id, role, content, token_count, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(turn.conversation_id),
                        turn.role,
                        turn.content,
                        turn.token_count,
                        created_at_str,
                    ),
                )
                await db.commit()

                # Get the auto-assigned ID
                cursor = await db.execute("SELECT last_insert_rowid()")
                row = await cursor.fetchone()
                turn_id = row[0] if row else None

                return ConversationTurn(
                    id=turn_id,
                    conversation_id=turn.conversation_id,
                    role=turn.role,
                    content=turn.content,
                    token_count=turn.token_count,
                    created_at=turn.created_at,
                )
            finally:
                await db.close()
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise ConversationPersistenceError(
                f"Failed to add turn: {str(e)}",
                conversation_id=str(turn.conversation_id),
            ) from e
        except ServiceUnavailableError:
            raise

    async def get_history(
        self,
        conversation_id: UUID,
        max_tokens: int = 2000,
        max_count: int = 5,
    ) -> TurnHistory:
        """Retrieve conversation history with token budget enforcement.

        Fetches all turns for conversation ordered by created_at ASC,
        then applies TurnHistory.from_turns() to trim based on budget.

        Args:
            conversation_id: UUID of conversation
            max_tokens: Token budget limit (default 2000)
            max_count: Hard limit on turn count (default 5)

        Returns:
            TurnHistory with trimmed turns (may be empty if conversation
            has no turns, or if oldest turns removed to meet budget)

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        try:
            # Verify conversation exists
            if not await self.conversation_exists(conversation_id):
                raise ConversationNotFoundError(str(conversation_id))

            db = await self._get_connection()
            try:
                cursor = await db.execute(
                    """
                    SELECT id, conversation_id, role, content, token_count, created_at
                    FROM conversation_turns
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                    """,
                    (str(conversation_id),),
                )
                rows = await cursor.fetchall()

                turns = [
                    ConversationTurn(
                        id=row[0],
                        conversation_id=UUID(row[1]),
                        role=row[2],
                        content=row[3],
                        token_count=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                    )
                    for row in rows
                ]

                return TurnHistory.from_turns(
                    turns,
                    max_tokens=max_tokens,
                    max_count=max_count,
                )
            finally:
                await db.close()
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to retrieve conversation history: {str(e)}"
            ) from e

    async def count_turns(self, conversation_id: UUID) -> int:
        """Get total turn count for conversation (for metrics).

        Args:
            conversation_id: UUID of conversation

        Returns:
            Number of turns (user + assistant combined)

        Raises:
            ConversationNotFoundError: If conversation_id does not exist
            ServiceUnavailableError: If database is unreachable
        """
        try:
            # Verify conversation exists
            if not await self.conversation_exists(conversation_id):
                raise ConversationNotFoundError(str(conversation_id))

            db = await self._get_connection()
            try:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM conversation_turns WHERE conversation_id = ?",
                    (str(conversation_id),),
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
            finally:
                await db.close()
        except ConversationNotFoundError:
            raise
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to count turns: {str(e)}") from e
