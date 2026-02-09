"""Integration tests for SQLite query repository."""

import pytest
import tempfile
import os
import aiosqlite
from datetime import datetime

from courseflow.domain.models import Query, TokenUsage
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository


@pytest.fixture
async def temp_db_path():
    """Create temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
async def query_repo(temp_db_path):
    """Create query repository with temporary database."""
    repo = SQLiteQueryRepository(db_path=temp_db_path)
    await repo.initialize()
    return repo


class TestSQLiteQueryRepository:
    """Integration tests for SQLite query repository."""

    @pytest.mark.asyncio
    async def test_save_query_success(self, query_repo):
        """Test saving a query to the database."""
        query = Query(text="What is photosynthesis?")
        
        await query_repo.save_query(
            query_id=query.query_id,
            query_text=query.text,
            answer_text="Photosynthesis is...",
            latency_ms=1500,
        )
        
        # Verify query was saved
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT query_id, query_text, answer_text, latency_ms FROM queries WHERE query_id = ?",
                (str(query.query_id),),
            )
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[0] == str(query.query_id)
            assert row[1] == query.text
            assert row[2] == "Photosynthesis is..."
            assert row[3] == 1500

    @pytest.mark.asyncio
    async def test_save_query_with_token_usage(self, query_repo):
        """Test saving query with token usage information."""
        query = Query(text="Test query")
        token_usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        
        await query_repo.save_query(
            query_id=query.query_id,
            query_text=query.text,
            answer_text="Test answer",
            latency_ms=1200,
            token_usage=token_usage,
        )
        
        # Verify token usage was saved
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT prompt_tokens, completion_tokens, total_tokens FROM queries WHERE query_id = ?",
                (str(query.query_id),),
            )
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[0] == 100
            assert row[1] == 50
            assert row[2] == 150

    @pytest.mark.asyncio
    async def test_timestamp_indexing(self, query_repo):
        """Test that timestamps are indexed for efficient querying."""
        # Save multiple queries
        queries = []
        for i in range(5):
            query = Query(text=f"Query {i}")
            await query_repo.save_query(
                query_id=query.query_id,
                query_text=query.text,
                answer_text=f"Answer {i}",
                latency_ms=1000 + i * 100,
            )
            queries.append(query)
        
        # Query by timestamp range should be efficient
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM queries WHERE created_at >= datetime('now', '-1 hour')"
            )
            count = await cursor.fetchone()
            assert count[0] == 5

    @pytest.mark.asyncio
    async def test_retrieve_query_by_id(self, query_repo):
        """Test retrieving a query by its ID."""
        query = Query(text="What is mitosis?")
        
        await query_repo.save_query(
            query_id=query.query_id,
            query_text=query.text,
            answer_text="Mitosis is...",
            latency_ms=1800,
        )
        
        # Retrieve query
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM queries WHERE query_id = ?",
                (str(query.query_id),),
            )
            row = await cursor.fetchone()
            
            assert row is not None

    @pytest.mark.asyncio
    async def test_multiple_queries_storage(self, query_repo):
        """Test storing multiple queries."""
        queries = [
            ("q-1", "Query 1", "Answer 1", 1000),
            ("q-2", "Query 2", "Answer 2", 1500),
            ("q-3", "Query 3", "Answer 3", 2000),
        ]
        
        for query_id, query_text, answer_text, latency_ms in queries:
            await query_repo.save_query(
                query_id=query_id,
                query_text=query_text,
                answer_text=answer_text,
                latency_ms=latency_ms,
            )
        
        # Verify all queries were saved
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM queries")
            count = await cursor.fetchone()
            assert count[0] == 3

    @pytest.mark.asyncio
    async def test_latency_tracking(self, query_repo):
        """Test that latency is properly tracked."""
        query = Query(text="Test latency")
        latency_ms = 2500
        
        await query_repo.save_query(
            query_id=query.query_id,
            query_text=query.text,
            answer_text="Test answer",
            latency_ms=latency_ms,
        )
        
        # Retrieve and verify latency
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute(
                "SELECT latency_ms FROM queries WHERE query_id = ?",
                (str(query.query_id),),
            )
            row = await cursor.fetchone()
            assert row[0] == latency_ms

    @pytest.mark.asyncio
    async def test_database_schema_created(self, temp_db_path):
        """Test that database schema is created on initialization."""
        repo = SQLiteQueryRepository(db_path=temp_db_path)
        await repo.initialize()
        
        # Check that queries table exists
        async with aiosqlite.connect(temp_db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='queries'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "queries"

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, query_repo):
        """Test concurrent query writes."""
        import asyncio
        
        async def save_query(i):
            query = Query(text=f"Concurrent query {i}")
            await query_repo.save_query(
                query_id=query.query_id,
                query_text=query.text,
                answer_text=f"Answer {i}",
                latency_ms=1000 + i,
            )
        
        # Save 10 queries concurrently
        await asyncio.gather(*[save_query(i) for i in range(10)])
        
        # Verify all were saved
        async with aiosqlite.connect(query_repo.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM queries")
            count = await cursor.fetchone()
            assert count[0] == 10
