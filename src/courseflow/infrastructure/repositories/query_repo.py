"""SQLite query repository implementing QueryRepositoryPort.

This module provides async persistence of query metadata using aiosqlite.
Stores query history, performance metrics, and error tracking.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

from courseflow.config import settings
from courseflow.domain.exceptions import ServiceUnavailableError
from courseflow.domain.models import Answer, Query
from courseflow.domain.ports import QueryRepositoryPort


class SQLiteQueryRepository(QueryRepositoryPort):
    """SQLite repository for query metadata and analytics.
    
    Provides async database operations using aiosqlite for query logging
    and retrieval of historical data.
    
    Attributes:
        database_url: SQLite database file path
    """
    
    def __init__(self, database_url: str = settings.DATABASE_URL):
        """Initialize SQLite repository.
        
        Args:
            database_url: SQLite database URL (e.g., "sqlite+aiosqlite:///./data/courseflow.db")
        """
        # Extract file path from URL (remove "sqlite+aiosqlite:///" prefix)
        self.database_path = database_url.replace("sqlite+aiosqlite:///", "")
    
    async def save_query(
        self,
        query: Query,
        answer: Optional[Answer],
        latency_ms: int,
        error_type: Optional[str] = None
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
                # Prepare data
                request_id = str(query.id)
                query_text = query.text
                answer_text = answer.text if answer else None
                timestamp = query.timestamp
                
                # Token counts (if answer exists)
                embedding_tokens = None
                generation_tokens = None
                total_tokens = None
                if answer:
                    embedding_tokens = 0  # Not tracked separately in current design
                    generation_tokens = answer.token_count.completion_tokens
                    total_tokens = answer.token_count.total_tokens
                
                # Search metrics (if answer exists)
                retrieval_count = answer.retrieval_count if answer else None
                top_similarity = answer.top_similarity if answer else None
                
                # Insert query record
                await db.execute(
                    """
                    INSERT INTO queries (
                        request_id, query_text, answer_text, timestamp,
                        embedding_tokens, generation_tokens, total_tokens,
                        latency_ms, retrieval_count, top_similarity_score, error_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id, query_text, answer_text, timestamp,
                        embedding_tokens, generation_tokens, total_tokens,
                        latency_ms, retrieval_count, top_similarity, error_type
                    )
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
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                
                async with db.execute(
                    "SELECT COUNT(*) FROM queries WHERE timestamp > ?",
                    (cutoff,)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                    
        except sqlite3.Error as e:
            raise ServiceUnavailableError(
                f"Failed to query database: {str(e)}"
            ) from e
