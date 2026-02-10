"""SQLite query repository implementing QueryRepositoryPort.

This module provides async persistence of query metadata using aiosqlite.
Stores query history, performance metrics, and error tracking.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiosqlite

from courseflow.config import settings
from courseflow.domain.exceptions import ServiceUnavailableError
from courseflow.domain.models import Answer, Query
from courseflow.domain.ports import QueryRepositoryPort


class SQLiteQueryRepository(QueryRepositoryPort):
    @property
    def db_path(self) -> str:
        return self.database_path

    """SQLite repository for query metadata and analytics.
    
    Provides async database operations using aiosqlite for query logging
    and retrieval of historical data.
    
    Attributes:
        database_url: SQLite database file path
    """
    
    def __init__(
        self,
        database_url: str = settings.DATABASE_URL,
        db_path: str | None = None,
    ):
        """Initialize SQLite repository.

        Args:
            database_url: SQLite database URL (e.g., "sqlite+aiosqlite:///./data/courseflow.db")
            db_path: Direct SQLite file path (test-friendly)
        """
        if db_path:
            self.database_path = db_path
            return
        # Extract file path from URL (remove "sqlite+aiosqlite:///" prefix)
        self.database_path = database_url.replace("sqlite+aiosqlite:///", "")

    async def initialize(self) -> None:
        """Ensure database schema exists (test-friendly)."""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_id TEXT UNIQUE NOT NULL,
                        query_text TEXT NOT NULL,
                        answer_text TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        prompt_tokens INTEGER,
                        completion_tokens INTEGER,
                        total_tokens INTEGER,
                        latency_ms INTEGER NOT NULL,
                        error_type TEXT
                    )
                    """
                )
                await db.execute(
                    """CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at)"""
                )
                await db.execute(
                    """CREATE INDEX IF NOT EXISTS idx_queries_error_type ON queries(error_type) WHERE error_type IS NOT NULL"""
                )
                await db.commit()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to initialize database schema: {str(e)}"
            ) from e

    async def save_query(
        self,
        query: Query | None = None,
        answer: Optional[Answer] = None,
        latency_ms: int | None = None,
        error_type: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Save query metadata to persistent storage.
        
        Args:
            query: The user's query
            answer: The generated answer (None if error occurred)
            latency_ms: End-to-end response time in milliseconds
            error_type: Error category if request failed (None if success)
        
        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Support both domain-style calls (query, answer, latency_ms)
                # and legacy keyword-style calls used by tests and RAGService.
                if query is not None:
                    query_id = str(query.id)
                    query_text = query.text
                    created_at = query.timestamp
                else:
                    query_id = kwargs.get("query_id")
                    query_text = kwargs.get("query_text")
                    created_at = kwargs.get("created_at") or kwargs.get("timestamp") or datetime.now(timezone.utc)

                if latency_ms is None:
                    latency_ms = kwargs.get("latency_ms", 0)

                answer_text = (
                    answer.answer_text
                    if answer is not None
                    else kwargs.get("answer_text")
                )

                token_usage = (
                    answer.token_usage
                    if (answer is not None and answer.token_usage is not None)
                    else kwargs.get("token_usage")
                )

                prompt_tokens = completion_tokens = total_tokens = None
                if token_usage is not None:
                    prompt_tokens = int(token_usage.prompt_tokens)
                    completion_tokens = int(token_usage.completion_tokens)
                    total_tokens = int(token_usage.total_tokens)

                created_at_val = created_at
                if isinstance(created_at_val, datetime):
                    created_at_val = created_at_val.isoformat(sep=" ")

                await db.execute(
                    """
                    INSERT INTO queries (
                        query_id, query_text, answer_text, created_at,
                        prompt_tokens, completion_tokens, total_tokens,
                        latency_ms, error_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(query_id),
                        query_text,
                        answer_text,
                        created_at_val,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        int(latency_ms),
                        error_type,
                    ),
                )
                await db.commit()

        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to save query to database: {str(e)}"
            ) from e
    
    async def get_recent_query_count(self, hours: int = 24) -> int:
        """Get number of queries in the last N hours.
        
        Args:
            hours: Time window in hours (default: 24)
        
        Returns:
            Number of queries in the specified time window
        
        Raises:
            ServiceUnavailableError: If database is unreachable
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                async with db.execute(
                    "SELECT COUNT(*) FROM queries WHERE created_at > ?",
                    (cutoff.isoformat(sep=' '),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                    
        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to query database: {str(e)}"
            ) from e
