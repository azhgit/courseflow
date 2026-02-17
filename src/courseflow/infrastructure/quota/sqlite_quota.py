"""SQLite quota store adapter for persistent daily quota tracking.

Implements QuotaStorePort using SQLite for daily usage persistence.
Includes scheduled daily reset task via APScheduler.
"""

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta

import aiosqlite

from courseflow.domain.exceptions import QuotaStorageError
from courseflow.domain.models import DailyQuotaLedger
from courseflow.domain.ports import QuotaStorePort


class SQLiteQuotaStore(QuotaStorePort):
    """SQLite-backed quota store for production persistence.

    Maintains daily quota usage across service restarts via SQLite.
    Provides atomic increment operations for thread safety.
    """

    # SQL schema for daily_quota table
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS daily_quota (
        date TEXT PRIMARY KEY,
        used INTEGER NOT NULL DEFAULT 0,
        limit INTEGER NOT NULL,
        cache_hits INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_daily_quota_date ON daily_quota(date);
    """

    def __init__(self, database_path: str):
        """Initialize SQLite quota store.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure database tables are created."""
        if self._initialized:
            return

        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.executescript(self.SCHEMA)
                await db.commit()
            self._initialized = True
        except Exception as e:
            raise QuotaStorageError(e) from e

    async def get_daily_ledger(self) -> DailyQuotaLedger:
        """Get or create today's quota ledger.

        Returns:
            DailyQuotaLedger for today

        Raises:
            QuotaStorageError: If database operation fails
        """
        await self._ensure_initialized()

        today = datetime.now(UTC).date().isoformat()
        now_iso = datetime.now(UTC).isoformat()

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Retry logic for database locked errors
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        cursor = await db.execute(
                            """
                            SELECT date, used, limit FROM daily_quota
                            WHERE date = ?
                            """,
                            (today,),
                        )
                        row = await cursor.fetchone()

                        if row is None:
                            # Create new entry for today
                            await db.execute(
                                """
                                INSERT INTO daily_quota
                                (date, used, limit, cache_hits, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (today, 0, 300, 0, now_iso, now_iso),
                            )
                            await db.commit()
                            return DailyQuotaLedger(date=today, used=0, limit=300)
                        else:
                            date_str, used, limit_val = row
                            return DailyQuotaLedger(
                                date=date_str,
                                used=used,
                                limit=limit_val,
                            )
                    except sqlite3.OperationalError as oe:
                        if "database is locked" in str(oe) and attempt < max_retries - 1:
                            # Retry on locked database
                            await asyncio.sleep(0.1 * (2**attempt))
                            continue
                        raise
                raise QuotaStorageError(RuntimeError("Failed to fetch daily ledger after retries"))

        except Exception as e:
            raise QuotaStorageError(e) from e

    async def increment_daily_usage(self) -> None:
        """Atomically increment daily usage by 1.

        Raises:
            QuotaStorageError: If database operation fails
        """
        await self._ensure_initialized()

        today = datetime.now(UTC).date().isoformat()
        now_iso = datetime.now(UTC).isoformat()

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Ensure today's ledger exists, then increment
                await db.execute(
                    """
                    INSERT INTO daily_quota
                    (date, used, limit, cache_hits, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                    used = used + 1,
                    updated_at = ?
                    """,
                    (today, 1, 300, 0, now_iso, now_iso, now_iso),
                )
                await db.commit()
        except Exception as e:
            raise QuotaStorageError(e) from e

    async def reset_daily_usage(self, new_date: str) -> None:
        """Reset daily usage for a new day.

        Args:
            new_date: ISO 8601 date string (YYYY-MM-DD)

        Raises:
            QuotaStorageError: If database operation fails
        """
        await self._ensure_initialized()

        now_iso = datetime.now(UTC).isoformat()

        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    """
                    INSERT INTO daily_quota
                    (date, used, limit, cache_hits, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                    used = 0,
                    cache_hits = 0,
                    updated_at = ?
                    """,
                    (new_date, 0, 300, 0, now_iso, now_iso, now_iso),
                )
                await db.commit()
        except Exception as e:
            raise QuotaStorageError(e) from e

    async def get_cache_hit_count(self) -> int:
        """Get cache hits for today.

        Returns:
            Number of cache hits recorded today

        Raises:
            QuotaStorageError: If database operation fails
        """
        await self._ensure_initialized()

        today = datetime.now(UTC).date().isoformat()

        try:
            async with aiosqlite.connect(self.database_path) as db:
                cursor = await db.execute(
                    "SELECT cache_hits FROM daily_quota WHERE date = ?",
                    (today,),
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            raise QuotaStorageError(e) from e

    async def increment_cache_hit(self) -> None:
        """Record a cache hit.

        Raises:
            QuotaStorageError: If database operation fails
        """
        await self._ensure_initialized()

        today = datetime.now(UTC).date().isoformat()
        now_iso = datetime.now(UTC).isoformat()

        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    """
                    INSERT INTO daily_quota
                    (date, used, limit, cache_hits, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                    cache_hits = cache_hits + 1,
                    updated_at = ?
                    """,
                    (today, 0, 300, 1, now_iso, now_iso, now_iso),
                )
                await db.commit()
        except Exception as e:
            raise QuotaStorageError(e) from e


# APScheduler task for daily reset (registered in main.py)
async def reset_daily_quota(quota_store: QuotaStorePort) -> None:
    """APScheduler task: Reset daily quota at midnight UTC.

    Args:
        quota_store: QuotaStorePort instance to reset
    """
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
    await quota_store.reset_daily_usage(tomorrow)
