"""
Unit tests for RateLimitRepository.

Following TDD approach - these tests should FAIL initially until
the repository methods are properly implemented.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from courseflow.infrastructure.repositories.rate_limit_repo import (
    RateLimitEntry,
    SQLiteRateLimitRepository,
)


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create rate_limits table
    import aiosqlite

    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                request_count INTEGER DEFAULT 0,
                window_start TIMESTAMP NOT NULL,
                last_request TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX idx_rate_limits_ip ON rate_limits(ip_address)")
        await db.execute("CREATE INDEX idx_rate_limits_window ON rate_limits(window_start)")
        await db.execute("CREATE INDEX idx_rate_limits_last_request ON rate_limits(last_request)")
        await db.commit()

    yield path

    # Cleanup
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def repo(temp_db):
    """Create repository instance with temp database."""
    return SQLiteRateLimitRepository(db_path=temp_db)


class TestGetByIp:
    """Test RateLimitRepository.get_by_ip() method."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_ip_returns_none(self, repo):
        """Test that get_by_ip returns None for non-existent IP."""
        result = await repo.get_by_ip("192.168.1.1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_existing_ip_returns_entry(self, repo):
        """Test that get_by_ip returns entry for existing IP."""
        # Create entry first
        entry = await repo.create_entry("192.168.1.1")

        # Retrieve it
        result = await repo.get_by_ip("192.168.1.1")

        assert result is not None
        assert result.ip_address == "192.168.1.1"
        assert result.request_count == 1
        assert result.id == entry.id

    @pytest.mark.asyncio
    async def test_get_by_ip_returns_correct_fields(self, repo):
        """Test that get_by_ip returns all fields correctly."""
        # Create entry
        await repo.create_entry("10.0.0.1")

        # Retrieve and verify
        result = await repo.get_by_ip("10.0.0.1")

        assert result is not None
        assert isinstance(result, RateLimitEntry)
        assert result.id is not None
        assert result.ip_address == "10.0.0.1"
        assert result.request_count == 1
        assert isinstance(result.window_start, datetime)
        assert isinstance(result.last_request, datetime)
        assert result.created_at is not None


class TestIncrementCounter:
    """Test RateLimitRepository.increment_counter() method."""

    @pytest.mark.asyncio
    async def test_increment_increases_count(self, repo):
        """Test that increment_counter increases request count."""
        # Create entry with count=1
        await repo.create_entry("192.168.1.1")

        # Increment
        await repo.increment_counter("192.168.1.1")

        # Verify count increased
        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 2

    @pytest.mark.asyncio
    async def test_increment_updates_last_request(self, repo):
        """Test that increment_counter updates last_request timestamp."""
        # Create entry
        entry = await repo.create_entry("192.168.1.1")
        original_time = entry.last_request

        # Wait a tiny bit
        import asyncio

        await asyncio.sleep(0.01)

        # Increment
        await repo.increment_counter("192.168.1.1")

        # Verify timestamp updated
        result = await repo.get_by_ip("192.168.1.1")
        assert result.last_request > original_time

    @pytest.mark.asyncio
    async def test_multiple_increments(self, repo):
        """Test multiple increments increase count correctly."""
        await repo.create_entry("192.168.1.1")

        for _ in range(5):
            await repo.increment_counter("192.168.1.1")

        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 6  # 1 initial + 5 increments


class TestResetWindow:
    """Test RateLimitRepository.reset_window() method."""

    @pytest.mark.asyncio
    async def test_reset_sets_count_to_one(self, repo):
        """Test that reset_window sets request count to 1."""
        # Create entry and increment
        await repo.create_entry("192.168.1.1")
        await repo.increment_counter("192.168.1.1")
        await repo.increment_counter("192.168.1.1")

        # Reset
        await repo.reset_window("192.168.1.1")

        # Verify count reset
        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 1

    @pytest.mark.asyncio
    async def test_reset_updates_window_start(self, repo):
        """Test that reset_window updates window_start timestamp."""
        # Create entry
        entry = await repo.create_entry("192.168.1.1")
        original_window = entry.window_start

        # Wait
        import asyncio

        await asyncio.sleep(0.01)

        # Reset
        await repo.reset_window("192.168.1.1")

        # Verify window_start updated
        result = await repo.get_by_ip("192.168.1.1")
        assert result.window_start > original_window

    @pytest.mark.asyncio
    async def test_reset_updates_last_request(self, repo):
        """Test that reset_window updates last_request timestamp."""
        entry = await repo.create_entry("192.168.1.1")
        original_time = entry.last_request

        import asyncio

        await asyncio.sleep(0.01)

        await repo.reset_window("192.168.1.1")

        result = await repo.get_by_ip("192.168.1.1")
        assert result.last_request > original_time


class TestCleanupOldEntries:
    """Test RateLimitRepository.cleanup_old_entries() method."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_old_entries(self, repo):
        """Test that cleanup_old_entries deletes entries older than cutoff."""
        # Create old entry (manually insert with old timestamp)
        import aiosqlite

        old_time = datetime.utcnow() - timedelta(hours=25)

        async with aiosqlite.connect(repo.db_path) as db:
            await db.execute(
                """
                INSERT INTO rate_limits (ip_address, request_count, window_start, last_request)
                VALUES (?, 1, ?, ?)
                """,
                ("192.168.1.1", old_time.isoformat(), old_time.isoformat()),
            )
            await db.commit()

        # Cleanup entries older than 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted_count = await repo.cleanup_old_entries(cutoff)

        assert deleted_count == 1

        # Verify entry was deleted
        result = await repo.get_by_ip("192.168.1.1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_entries(self, repo):
        """Test that cleanup_old_entries preserves recent entries."""
        # Create recent entry
        await repo.create_entry("192.168.1.1")

        # Cleanup old entries
        cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted_count = await repo.cleanup_old_entries(cutoff)

        assert deleted_count == 0

        # Verify entry still exists
        result = await repo.get_by_ip("192.168.1.1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_cleanup_returns_correct_count(self, repo):
        """Test that cleanup_old_entries returns correct deletion count."""
        import aiosqlite

        old_time = datetime.utcnow() - timedelta(hours=25)

        # Create 3 old entries
        async with aiosqlite.connect(repo.db_path) as db:
            for i in range(3):
                await db.execute(
                    """
                    INSERT INTO rate_limits (ip_address, request_count, window_start, last_request)
                    VALUES (?, 1, ?, ?)
                    """,
                    (f"192.168.1.{i}", old_time.isoformat(), old_time.isoformat()),
                )
            await db.commit()

        # Cleanup
        cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted_count = await repo.cleanup_old_entries(cutoff)

        assert deleted_count == 3


class TestStateTransitions:
    """Test rate limit state transitions."""

    @pytest.mark.asyncio
    async def test_no_entry_to_active(self, repo):
        """Test transition: No Entry → Active (first request)."""
        # No entry exists initially
        assert await repo.get_by_ip("192.168.1.1") is None

        # Create entry (first request)
        entry = await repo.create_entry("192.168.1.1")

        # Verify Active state
        assert entry.request_count == 1
        assert entry.window_start is not None
        assert entry.last_request is not None

    @pytest.mark.asyncio
    async def test_active_to_active_increment(self, repo):
        """Test transition: Active → Active (subsequent request in same window)."""
        # Create initial entry
        await repo.create_entry("192.168.1.1")

        # Make subsequent request
        await repo.increment_counter("192.168.1.1")

        # Verify state
        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 2

    @pytest.mark.asyncio
    async def test_active_to_rate_limited(self, repo):
        """Test transition: Active → RateLimited (count reaches limit)."""
        # Create entry and increment to limit (20)
        await repo.create_entry("192.168.1.1")

        for _ in range(19):
            await repo.increment_counter("192.168.1.1")

        # Verify at limit
        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 20

    @pytest.mark.asyncio
    async def test_rate_limited_to_reset(self, repo):
        """Test transition: RateLimited → Reset (window expires)."""
        # Create entry at limit
        await repo.create_entry("192.168.1.1")
        for _ in range(19):
            await repo.increment_counter("192.168.1.1")

        # Simulate window expiration by resetting
        await repo.reset_window("192.168.1.1")

        # Verify reset state
        result = await repo.get_by_ip("192.168.1.1")
        assert result.request_count == 1
